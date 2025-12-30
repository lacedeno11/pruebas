# DERCAS-ONCO-XAI V1 - Event Consumer
# RabbitMQ event consumption utilities

import os
import json
import asyncio
from typing import Optional, Dict, Any, Callable, List, TypeVar
from contextlib import asynccontextmanager
import aio_pika
from aio_pika import Message, ExchangeType, Queue
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange, AbstractIncomingMessage
import logging

from .envelope import EventEnvelope, EventType, EventFilter, EventMetrics

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Configuration from environment variables
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "oncology.events")
EXCHANGE_TYPE = ExchangeType.TOPIC

# Event handler type
EventHandler = Callable[[EventEnvelope], None]
AsyncEventHandler = Callable[[EventEnvelope], Any]  # Can be sync or async


class EventConsumer:
    """
    RabbitMQ event consumer for the oncology platform.
    
    This consumer handles:
    - Connection management with automatic reconnection
    - Queue declaration and binding
    - Event deserialization and routing
    - Error handling and dead letter queues
    - Metrics collection
    """
    
    def __init__(
        self,
        rabbitmq_url: str = RABBITMQ_URL,
        exchange_name: str = EXCHANGE_NAME,
        exchange_type: ExchangeType = EXCHANGE_TYPE,
        consumer_name: str = "unknown",
        queue_name: Optional[str] = None,
        durable: bool = True,
        auto_delete: bool = False
    ):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.consumer_name = consumer_name
        self.queue_name = queue_name or f"{consumer_name}.events"
        self.durable = durable
        self.auto_delete = auto_delete
        
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchange: Optional[AbstractExchange] = None
        self._queue: Optional[Queue] = None
        self._handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._global_handlers: List[AsyncEventHandler] = []
        self._metrics = EventMetrics()
        self._filter: Optional[EventFilter] = None
        self._running = False
        
        logger.info(f"EventConsumer initialized: {consumer_name}")
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(
                self.rabbitmq_url,
                client_properties={"connection_name": f"consumer-{self.consumer_name}"}
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)  # Limit unacked messages
            
            # Declare exchange
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                self.exchange_type,
                durable=True
            )
            
            # Declare queue
            self._queue = await self._channel.declare_queue(
                self.queue_name,
                durable=self.durable,
                auto_delete=self.auto_delete,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                    "x-max-length": 10000,
                    "x-dead-letter-exchange": "oncology.dlx"
                }
            )
            
            logger.info(f"Connected to RabbitMQ: {self.queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close connection to RabbitMQ."""
        try:
            self._running = False
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self._connection or self._connection.is_closed:
            await self.connect()
    
    def add_handler(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """
        Add event handler for specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function (can be sync or async)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Added handler for {event_type.value}")
    
    def add_global_handler(self, handler: AsyncEventHandler) -> None:
        """
        Add global event handler for all events.
        
        Args:
            handler: Handler function (can be sync or async)
        """
        self._global_handlers.append(handler)
        logger.info("Added global event handler")
    
    def set_filter(self, event_filter: EventFilter) -> None:
        """
        Set event filter for this consumer.
        
        Args:
            event_filter: Filter to apply to incoming events
        """
        self._filter = event_filter
        logger.info("Event filter set")
    
    async def bind_to_routing_keys(self, routing_keys: List[str]) -> None:
        """
        Bind queue to specific routing keys.
        
        Args:
            routing_keys: List of routing keys to bind to
        """
        await self.ensure_connected()
        
        for routing_key in routing_keys:
            await self._queue.bind(self._exchange, routing_key=routing_key)
            logger.info(f"Bound queue to routing key: {routing_key}")
    
    async def bind_to_event_types(self, event_types: List[EventType]) -> None:
        """
        Bind queue to specific event types.
        
        Args:
            event_types: List of event types to bind to
        """
        routing_keys = [event_type.value for event_type in event_types]
        await self.bind_to_routing_keys(routing_keys)
    
    async def bind_to_all_events(self) -> None:
        """Bind queue to all events using wildcard."""
        await self.bind_to_routing_keys(["*"])
    
    async def _process_message(self, message: AbstractIncomingMessage) -> None:
        """Process incoming message."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Deserialize message
            message_body = message.body.decode('utf-8')
            event_data = json.loads(message_body)
            
            # Create event envelope
            event = EventEnvelope(**event_data)
            
            # Apply filter if set
            if self._filter and not self._filter.matches(event):
                await message.ack()
                return
            
            # Process event with handlers
            await self._handle_event(event)
            
            # Acknowledge message
            await message.ack()
            
            # Update metrics
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self._metrics.record_consumed(processing_time)
            
            logger.debug(f"Processed event: {event.event_type.value} (ID: {event.event_id})")
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            
            # Reject message (will go to DLQ if configured)
            await message.reject(requeue=False)
            self._metrics.record_failed()
    
    async def _handle_event(self, event: EventEnvelope) -> None:
        """Handle event with registered handlers."""
        handlers_to_run = []
        
        # Add specific handlers for this event type
        if event.event_type in self._handlers:
            handlers_to_run.extend(self._handlers[event.event_type])
        
        # Add global handlers
        handlers_to_run.extend(self._global_handlers)
        
        # Run all handlers
        for handler in handlers_to_run:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler failed for event {event.event_id}: {e}")
                # Continue with other handlers
    
    async def start_consuming(self) -> None:
        """Start consuming events."""
        await self.ensure_connected()
        
        self._running = True
        
        # Start consuming messages
        await self._queue.consume(self._process_message)
        
        logger.info(f"Started consuming events on queue: {self.queue_name}")
        
        # Keep running until stopped
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
        finally:
            await self.disconnect()
    
    def stop_consuming(self) -> None:
        """Stop consuming events."""
        self._running = False
        logger.info("Stopping event consumption")
    
    def get_metrics(self) -> EventMetrics:
        """Get consumer metrics."""
        return self._metrics
    
    @asynccontextmanager
    async def connection_context(self):
        """Context manager for consumer connection."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()


class EventRouter:
    """
    Event router for handling multiple event types with different consumers.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.consumers: Dict[str, EventConsumer] = {}
        self._running = False
    
    def create_consumer(
        self,
        consumer_name: str,
        event_types: List[EventType],
        handler: AsyncEventHandler,
        queue_name: Optional[str] = None
    ) -> EventConsumer:
        """
        Create and configure a consumer for specific event types.
        
        Args:
            consumer_name: Name of the consumer
            event_types: Event types to consume
            handler: Handler function for events
            queue_name: Optional custom queue name
        
        Returns:
            Configured EventConsumer
        """
        consumer = EventConsumer(
            consumer_name=f"{self.service_name}-{consumer_name}",
            queue_name=queue_name or f"{self.service_name}.{consumer_name}"
        )
        
        # Add handler for all specified event types
        for event_type in event_types:
            consumer.add_handler(event_type, handler)
        
        self.consumers[consumer_name] = consumer
        return consumer
    
    async def start_all(self) -> None:
        """Start all consumers."""
        self._running = True
        
        # Bind consumers to their event types
        for consumer in self.consumers.values():
            # Bind to all events for now (can be made more specific)
            await consumer.bind_to_all_events()
        
        # Start consuming in parallel
        tasks = []
        for consumer in self.consumers.values():
            task = asyncio.create_task(consumer.start_consuming())
            tasks.append(task)
        
        logger.info(f"Started {len(tasks)} consumers for {self.service_name}")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("All consumers cancelled")
    
    def stop_all(self) -> None:
        """Stop all consumers."""
        self._running = False
        for consumer in self.consumers.values():
            consumer.stop_consuming()
    
    def get_metrics(self) -> Dict[str, EventMetrics]:
        """Get metrics for all consumers."""
        return {name: consumer.get_metrics() for name, consumer in self.consumers.items()}


# Convenience functions for common patterns

async def consume_case_events(handler: AsyncEventHandler, service_name: str = "unknown") -> None:
    """Consume case-related events."""
    consumer = EventConsumer(
        consumer_name=f"{service_name}-case-events",
        queue_name=f"{service_name}.case.events"
    )
    
    consumer.add_handler(EventType.CASE_CREATED, handler)
    consumer.add_handler(EventType.CASE_UPDATED, handler)
    
    await consumer.bind_to_routing_keys(["case.*"])
    await consumer.start_consuming()


async def consume_job_events(handler: AsyncEventHandler, service_name: str = "unknown") -> None:
    """Consume job-related events."""
    consumer = EventConsumer(
        consumer_name=f"{service_name}-job-events",
        queue_name=f"{service_name}.job.events"
    )
    
    consumer.add_handler(EventType.JOB_CREATED, handler)
    consumer.add_handler(EventType.JOB_PROGRESS, handler)
    consumer.add_handler(EventType.JOB_COMPLETED, handler)
    consumer.add_handler(EventType.JOB_FAILED, handler)
    
    await consumer.bind_to_routing_keys(["job.*"])
    await consumer.start_consuming()


async def consume_all_events(handler: AsyncEventHandler, service_name: str = "unknown") -> None:
    """Consume all events (useful for audit service)."""
    consumer = EventConsumer(
        consumer_name=f"{service_name}-all-events",
        queue_name=f"{service_name}.all.events"
    )
    
    consumer.add_global_handler(handler)
    
    await consumer.bind_to_all_events()
    await consumer.start_consuming()


# Decorator for event handlers
def event_handler(event_type: EventType):
    """Decorator to mark functions as event handlers."""
    def decorator(func):
        func._event_type = event_type
        func._is_event_handler = True
        return func
    return decorator


def global_event_handler(func):
    """Decorator to mark functions as global event handlers."""
    func._is_global_event_handler = True
    return func
