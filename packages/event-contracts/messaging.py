"""
DERCAS-ONCO-XAI V1 - Messaging Utilities

RabbitMQ publish/consume helpers for the oncology platform.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Union

import aio_pika
from aio_pika import Connection, Exchange, Message, Queue, RobustConnection
from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from .events import EventEnvelope, EventType

logger = logging.getLogger(__name__)


class MessagePublisher:
    """RabbitMQ message publisher with connection management."""
    
    def __init__(
        self,
        connection_url: str,
        exchange_name: str = "oncology.events",
        exchange_type: str = "topic"
    ):
        self.connection_url = connection_url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.connection: Optional[RobustConnection] = None
        self.channel = None
        self.exchange: Optional[Exchange] = None
    
    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(self.connection_url)
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                type=self.exchange_type,
                durable=True
            )
            
            logger.info(f"Connected to RabbitMQ exchange '{self.exchange_name}'")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Close connection to RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def publish_event(
        self,
        event: EventEnvelope,
        routing_key: Optional[str] = None,
        priority: int = 0,
        expiration: Optional[int] = None
    ):
        """
        Publish an event to RabbitMQ.
        
        Args:
            event: Event envelope to publish
            routing_key: Routing key (defaults to event type)
            priority: Message priority (0-255)
            expiration: Message expiration in milliseconds
        """
        if not self.exchange:
            raise RuntimeError("Publisher not connected. Call connect() first.")
        
        # Use event type as routing key if not specified
        if routing_key is None:
            routing_key = event.event_type.value
        
        # Serialize event
        message_body = event.model_dump_json().encode('utf-8')
        
        # Create message
        message = Message(
            message_body,
            headers={
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "correlation_id": event.correlation_id,
                "case_id": event.case_id,
                "producer": event.producer,
                "timestamp": event.timestamp.isoformat(),
            },
            priority=priority,
            expiration=expiration,
            message_id=event.event_id,
            correlation_id=event.correlation_id,
            timestamp=event.timestamp
        )
        
        try:
            await self.exchange.publish(message, routing_key=routing_key)
            
            logger.info(
                f"Published event {event.event_type.value}",
                extra={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "case_id": event.case_id,
                    "routing_key": routing_key
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish event {event.event_type.value}: {e}",
                extra={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "case_id": event.case_id,
                    "routing_key": routing_key
                }
            )
            raise
    
    async def publish_events(self, events: List[EventEnvelope]):
        """Publish multiple events in batch."""
        for event in events:
            await self.publish_event(event)


class MessageConsumer:
    """RabbitMQ message consumer with event handling."""
    
    def __init__(
        self,
        connection_url: str,
        queue_name: str,
        exchange_name: str = "oncology.events",
        exchange_type: str = "topic",
        routing_keys: Optional[List[str]] = None,
        prefetch_count: int = 10
    ):
        self.connection_url = connection_url
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.routing_keys = routing_keys or ["#"]
        self.prefetch_count = prefetch_count
        
        self.connection: Optional[RobustConnection] = None
        self.channel = None
        self.exchange: Optional[Exchange] = None
        self.queue: Optional[Queue] = None
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.default_handler: Optional[Callable] = None
    
    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(self.connection_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.prefetch_count)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                type=self.exchange_type,
                durable=True
            )
            
            # Declare queue
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                    "x-max-priority": 10
                }
            )
            
            # Bind queue to exchange with routing keys
            for routing_key in self.routing_keys:
                await self.queue.bind(self.exchange, routing_key=routing_key)
            
            logger.info(
                f"Connected consumer to queue '{self.queue_name}' with routing keys: {self.routing_keys}"
            )
            
        except Exception as e:
            logger.error(f"Failed to connect consumer: {e}")
            raise
    
    async def disconnect(self):
        """Close connection to RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected consumer from RabbitMQ")
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """Register event handler for specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type.value}")
    
    def register_default_handler(self, handler: Callable):
        """Register default handler for unhandled event types."""
        self.default_handler = handler
        logger.info("Registered default event handler")
    
    async def start_consuming(self):
        """Start consuming messages from the queue."""
        if not self.queue:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        logger.info(f"Starting to consume messages from queue '{self.queue_name}'")
        
        async def process_message(message: AbstractIncomingMessage):
            async with message.process():
                try:
                    # Parse event envelope
                    event_data = json.loads(message.body.decode('utf-8'))
                    event = EventEnvelope(**event_data)
                    
                    logger.info(
                        f"Received event {event.event_type.value}",
                        extra={
                            "event_id": event.event_id,
                            "correlation_id": event.correlation_id,
                            "case_id": event.case_id,
                            "producer": event.producer
                        }
                    )
                    
                    # Find and execute handlers
                    handlers = self.handlers.get(event.event_type, [])
                    if not handlers and self.default_handler:
                        handlers = [self.default_handler]
                    
                    if not handlers:
                        logger.warning(f"No handler found for event type: {event.event_type.value}")
                        return
                    
                    # Execute handlers
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                handler(event)
                        except Exception as e:
                            logger.error(
                                f"Handler failed for event {event.event_type.value}: {e}",
                                extra={
                                    "event_id": event.event_id,
                                    "correlation_id": event.correlation_id,
                                    "handler": handler.__name__
                                },
                                exc_info=True
                            )
                            # Re-raise to trigger message rejection
                            raise
                    
                    logger.debug(f"Successfully processed event {event.event_type.value}")
                    
                except ValidationError as e:
                    logger.error(f"Invalid event format: {e}")
                    # Don't re-raise validation errors to avoid infinite redelivery
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in message: {e}")
                    # Don't re-raise JSON errors to avoid infinite redelivery
                    
                except Exception as e:
                    logger.error(f"Failed to process message: {e}", exc_info=True)
                    # Re-raise to trigger message rejection and potential redelivery
                    raise
        
        # Start consuming
        await self.queue.consume(process_message)
    
    async def stop_consuming(self):
        """Stop consuming messages."""
        if self.queue:
            await self.queue.cancel()
            logger.info("Stopped consuming messages")


class EventBus:
    """High-level event bus for publishing and consuming events."""
    
    def __init__(self, connection_url: str, service_name: str):
        self.connection_url = connection_url
        self.service_name = service_name
        self.publisher = MessagePublisher(connection_url)
        self.consumers: List[MessageConsumer] = []
    
    async def start(self):
        """Start the event bus."""
        await self.publisher.connect()
        for consumer in self.consumers:
            await consumer.connect()
            asyncio.create_task(consumer.start_consuming())
        
        logger.info(f"Event bus started for service '{self.service_name}'")
    
    async def stop(self):
        """Stop the event bus."""
        await self.publisher.disconnect()
        for consumer in self.consumers:
            await consumer.stop_consuming()
            await consumer.disconnect()
        
        logger.info(f"Event bus stopped for service '{self.service_name}'")
    
    async def publish(
        self,
        event: EventEnvelope,
        routing_key: Optional[str] = None,
        priority: int = 0
    ):
        """Publish an event."""
        # Set producer if not already set
        if not event.producer:
            event.producer = self.service_name
        
        await self.publisher.publish_event(event, routing_key, priority)
    
    def create_consumer(
        self,
        queue_name: str,
        routing_keys: Optional[List[str]] = None,
        prefetch_count: int = 10
    ) -> MessageConsumer:
        """Create and register a message consumer."""
        consumer = MessageConsumer(
            connection_url=self.connection_url,
            queue_name=queue_name,
            routing_keys=routing_keys,
            prefetch_count=prefetch_count
        )
        self.consumers.append(consumer)
        return consumer


# Context manager for event bus
@asynccontextmanager
async def event_bus_context(connection_url: str, service_name: str):
    """Context manager for event bus lifecycle."""
    bus = EventBus(connection_url, service_name)
    try:
        await bus.start()
        yield bus
    finally:
        await bus.stop()


# Utility functions
def create_routing_key(event_type: EventType, service: Optional[str] = None) -> str:
    """Create routing key for event type."""
    parts = event_type.value.split('.')
    if service:
        return f"{service}.{'.'.join(parts)}"
    return event_type.value


def create_queue_name(service: str, event_category: str) -> str:
    """Create queue name for service and event category."""
    return f"{service}.{event_category}"


# Decorators for event handlers
def event_handler(event_type: EventType):
    """Decorator to mark function as event handler."""
    def decorator(func):
        func._event_type = event_type
        func._is_event_handler = True
        return func
    return decorator


def default_event_handler(func):
    """Decorator to mark function as default event handler."""
    func._is_default_handler = True
    return func


# Event handler discovery
def discover_event_handlers(module) -> Dict[EventType, List[Callable]]:
    """Discover event handlers in a module."""
    handlers = {}
    default_handlers = []
    
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj):
            if hasattr(obj, '_is_event_handler') and hasattr(obj, '_event_type'):
                event_type = obj._event_type
                if event_type not in handlers:
                    handlers[event_type] = []
                handlers[event_type].append(obj)
            elif hasattr(obj, '_is_default_handler'):
                default_handlers.append(obj)
    
    return handlers, default_handlers


# Message retry utilities
class RetryPolicy:
    """Message retry policy configuration."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.initial_delay * (self.exponential_base ** retry_count)
        return min(delay, self.max_delay)


async def publish_with_retry(
    publisher: MessagePublisher,
    event: EventEnvelope,
    retry_policy: RetryPolicy,
    routing_key: Optional[str] = None
):
    """Publish event with retry logic."""
    for attempt in range(retry_policy.max_retries + 1):
        try:
            await publisher.publish_event(event, routing_key)
            return
        except Exception as e:
            if attempt == retry_policy.max_retries:
                logger.error(f"Failed to publish event after {retry_policy.max_retries} retries: {e}")
                raise
            
            delay = retry_policy.get_delay(attempt)
            logger.warning(f"Publish attempt {attempt + 1} failed, retrying in {delay}s: {e}")
            await asyncio.sleep(delay)


# Health check utilities
async def check_rabbitmq_health(connection_url: str) -> bool:
    """Check RabbitMQ connection health."""
    try:
        connection = await aio_pika.connect(connection_url)
        await connection.close()
        return True
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")
        return False
