"""
DERCAS-ONCO-XAI Event Consumer

RabbitMQ event consumption utilities.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from .envelope import EventEnvelope, validate_event_envelope, Exchanges, Queues

logger = logging.getLogger(__name__)

# Type alias for event handler functions
EventHandler = Callable[[EventEnvelope], None]


class EventConsumer:
    """RabbitMQ event consumer for DERCAS events."""
    
    def __init__(self, rabbitmq_url: str, exchange: str = Exchanges.EVENTS):
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.connection = None
        self.channel = None
        self._is_connected = False
        self._event_handlers: Dict[str, List[EventHandler]] = {}
        self._queue_bindings: Dict[str, List[str]] = {}
    
    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self.connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            self._is_connected = True
            logger.info(f"Connected to RabbitMQ: {self.exchange}")
            
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close connection to RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            self._is_connected = False
            logger.info("Disconnected from RabbitMQ")
    
    def ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self._is_connected or not self.connection or self.connection.is_closed:
            self.connect()
    
    def declare_queue(
        self,
        queue_name: str,
        routing_keys: List[str],
        durable: bool = True,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None
    ) -> None:
        """Declare a queue and bind it to routing keys."""
        self.ensure_connected()
        
        # Declare queue
        self.channel.queue_declare(
            queue=queue_name,
            durable=durable,
            auto_delete=auto_delete,
            arguments=arguments or {}
        )
        
        # Bind queue to routing keys
        for routing_key in routing_keys:
            self.channel.queue_bind(
                exchange=self.exchange,
                queue=queue_name,
                routing_key=routing_key
            )
        
        # Store bindings for reference
        self._queue_bindings[queue_name] = routing_keys
        
        logger.info(f"Declared queue {queue_name} with routing keys: {routing_keys}")
    
    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")
    
    def unregister_handler(self, event_type: str, handler: EventHandler) -> None:
        """Unregister an event handler."""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                logger.info(f"Unregistered handler for event type: {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type}")
    
    def _process_message(self, channel: BlockingChannel, method, properties, body: bytes) -> None:
        """Process incoming message."""
        try:
            # Parse message body
            message_data = json.loads(body.decode('utf-8'))
            
            # Validate event envelope
            envelope = validate_event_envelope(message_data)
            
            # Get handlers for this event type
            handlers = self._event_handlers.get(envelope.event_type, [])
            
            if not handlers:
                logger.warning(f"No handlers registered for event type: {envelope.event_type}")
                # Acknowledge message even if no handlers (avoid infinite requeue)
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Process with each handler
            for handler in handlers:
                try:
                    handler(envelope)
                except Exception as e:
                    logger.error(
                        f"Handler failed for event {envelope.event_id}: {e}",
                        extra={
                            'event_id': envelope.event_id,
                            'event_type': envelope.event_type,
                            'correlation_id': envelope.correlation_id,
                            'handler': handler.__name__ if hasattr(handler, '__name__') else str(handler)
                        },
                        exc_info=True
                    )
                    # Don't acknowledge on handler failure - message will be requeued
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    return
            
            # Acknowledge successful processing
            channel.basic_ack(delivery_tag=method.delivery_tag)
            
            logger.debug(
                f"Processed event: {envelope.event_type}",
                extra={
                    'event_id': envelope.event_id,
                    'correlation_id': envelope.correlation_id,
                    'handlers_count': len(handlers)
                }
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message JSON: {e}")
            # Reject malformed messages (don't requeue)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            # Requeue on unexpected errors
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(
        self,
        queue_name: str,
        prefetch_count: int = 10,
        auto_ack: bool = False
    ) -> None:
        """Start consuming messages from a queue."""
        self.ensure_connected()
        
        # Set QoS
        self.channel.basic_qos(prefetch_count=prefetch_count)
        
        # Set up consumer
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=self._process_message,
            auto_ack=auto_ack
        )
        
        logger.info(f"Starting to consume from queue: {queue_name}")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.channel.stop_consuming()
            self.disconnect()
    
    def stop_consuming(self) -> None:
        """Stop consuming messages."""
        if self.channel:
            self.channel.stop_consuming()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Global consumer instance
_global_consumer: Optional[EventConsumer] = None


def init_event_consumer(rabbitmq_url: str, exchange: str = Exchanges.EVENTS) -> EventConsumer:
    """Initialize global event consumer."""
    global _global_consumer
    _global_consumer = EventConsumer(rabbitmq_url, exchange)
    _global_consumer.connect()
    return _global_consumer


def get_event_consumer() -> EventConsumer:
    """Get global event consumer instance."""
    if not _global_consumer:
        raise RuntimeError("Event consumer not initialized. Call init_event_consumer() first.")
    return _global_consumer


def register_event_handler(event_type: str, handler: EventHandler) -> None:
    """Register an event handler using the global consumer."""
    consumer = get_event_consumer()
    consumer.register_handler(event_type, handler)


def consume_events(
    queue_name: str,
    routing_keys: List[str],
    handlers: Dict[str, EventHandler],
    prefetch_count: int = 10
) -> None:
    """Convenience function to set up and start consuming events."""
    consumer = get_event_consumer()
    
    # Declare queue
    consumer.declare_queue(queue_name, routing_keys)
    
    # Register handlers
    for event_type, handler in handlers.items():
        consumer.register_handler(event_type, handler)
    
    # Start consuming
    consumer.start_consuming(queue_name, prefetch_count)


# Decorator for event handlers
def event_handler(event_type: str):
    """Decorator to register event handlers."""
    def decorator(func: EventHandler) -> EventHandler:
        # Register handler when decorator is applied
        def register_when_consumer_ready():
            try:
                register_event_handler(event_type, func)
            except RuntimeError:
                # Consumer not initialized yet, store for later registration
                if not hasattr(register_when_consumer_ready, '_pending_handlers'):
                    register_when_consumer_ready._pending_handlers = []
                register_when_consumer_ready._pending_handlers.append((event_type, func))
        
        register_when_consumer_ready()
        return func
    
    return decorator


# Pre-configured consumer setups for common use cases
class ServiceEventConsumer:
    """Pre-configured event consumer for specific services."""
    
    @staticmethod
    def setup_case_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for case service events."""
        consumer.declare_queue(
            queue_name=Queues.CASE_EVENTS,
            routing_keys=["case.*"],
            arguments={
                "x-message-ttl": 604800000,  # 7 days
                "x-max-length": 10000
            }
        )
    
    @staticmethod
    def setup_image_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for image service events."""
        consumer.declare_queue(
            queue_name=Queues.IMAGE_EVENTS,
            routing_keys=["image.*"],
            arguments={
                "x-message-ttl": 604800000,  # 7 days
                "x-max-length": 10000
            }
        )
    
    @staticmethod
    def setup_inference_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for inference service events."""
        consumer.declare_queue(
            queue_name=Queues.INFERENCE_EVENTS,
            routing_keys=["inference.*", "job.inference.*"],
            arguments={
                "x-message-ttl": 3600000,  # 1 hour
                "x-max-length": 1000
            }
        )
    
    @staticmethod
    def setup_ehr_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for EHR service events."""
        consumer.declare_queue(
            queue_name=Queues.EHR_EVENTS,
            routing_keys=["ehr.*", "job.ehr.*"],
            arguments={
                "x-message-ttl": 604800000,  # 7 days
                "x-max-length": 10000
            }
        )
    
    @staticmethod
    def setup_graph_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for graph service events."""
        consumer.declare_queue(
            queue_name=Queues.GRAPH_EVENTS,
            routing_keys=["graph.*", "job.graph.*"],
            arguments={
                "x-message-ttl": 604800000,  # 7 days
                "x-max-length": 10000
            }
        )
    
    @staticmethod
    def setup_ontology_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for ontology service events."""
        consumer.declare_queue(
            queue_name=Queues.ONTOLOGY_EVENTS,
            routing_keys=["ontology.*", "job.ontology.*"],
            arguments={
                "x-message-ttl": 604800000,  # 7 days
                "x-max-length": 10000
            }
        )
    
    @staticmethod
    def setup_audit_service_consumer(consumer: EventConsumer) -> None:
        """Set up consumer for audit service events."""
        consumer.declare_queue(
            queue_name=Queues.AUDIT_EVENTS,
            routing_keys=["audit.*", "*"],  # Audit service listens to all events
            arguments={
                "x-message-ttl": 2592000000,  # 30 days
                "x-max-length": 50000
            }
        )


# Example event handlers
def log_event_handler(envelope: EventEnvelope) -> None:
    """Simple event handler that logs events."""
    logger.info(
        f"Received event: {envelope.event_type}",
        extra={
            'event_id': envelope.event_id,
            'correlation_id': envelope.correlation_id,
            'producer': envelope.producer,
            'case_id': str(envelope.case_id) if envelope.case_id else None
        }
    )


def audit_event_handler(envelope: EventEnvelope) -> None:
    """Event handler for audit logging."""
    # This would typically persist the event to an audit store
    logger.info(
        f"Audit event: {envelope.event_type}",
        extra={
            'event_id': envelope.event_id,
            'correlation_id': envelope.correlation_id,
            'producer': envelope.producer,
            'case_id': str(envelope.case_id) if envelope.case_id else None,
            'payload': envelope.payload
        }
    )
