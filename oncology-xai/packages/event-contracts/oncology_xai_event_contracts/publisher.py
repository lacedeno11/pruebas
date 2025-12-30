# DERCAS-ONCO-XAI V1 - Event Publisher
# RabbitMQ event publishing utilities

import os
import json
import asyncio
from typing import Optional, Dict, Any, TypeVar
from contextlib import asynccontextmanager
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange
import logging

from .envelope import EventEnvelope, EventType, EventMetrics

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Configuration from environment variables
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE", "oncology.events")
EXCHANGE_TYPE = ExchangeType.TOPIC


class EventPublisher:
    """
    RabbitMQ event publisher for the oncology platform.
    
    This publisher handles:
    - Connection management with automatic reconnection
    - Event serialization and publishing
    - Routing key generation
    - Error handling and retries
    - Metrics collection
    """
    
    def __init__(
        self,
        rabbitmq_url: str = RABBITMQ_URL,
        exchange_name: str = EXCHANGE_NAME,
        exchange_type: ExchangeType = EXCHANGE_TYPE,
        producer_name: str = "unknown"
    ):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.producer_name = producer_name
        
        self._connection: Optional[AbstractConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchange: Optional[AbstractExchange] = None
        self._metrics = EventMetrics()
        
        logger.info(f"EventPublisher initialized for producer: {producer_name}")
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(
                self.rabbitmq_url,
                client_properties={"connection_name": f"publisher-{self.producer_name}"}
            )
            self._channel = await self._connection.channel()
            
            # Declare exchange
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                self.exchange_type,
                durable=True
            )
            
            logger.info(f"Connected to RabbitMQ: {self.exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close connection to RabbitMQ."""
        try:
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self._connection or self._connection.is_closed:
            await self.connect()
    
    async def publish_event(
        self,
        event: EventEnvelope[T],
        routing_key: Optional[str] = None,
        priority: int = 0,
        expiration: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish an event to RabbitMQ.
        
        Args:
            event: Event envelope to publish
            routing_key: Custom routing key (defaults to event type)
            priority: Message priority (0-255)
            expiration: Message expiration in milliseconds
            headers: Additional message headers
        
        Returns:
            True if published successfully, False otherwise
        """
        try:
            await self.ensure_connected()
            
            # Generate routing key if not provided
            if routing_key is None:
                routing_key = event.to_routing_key()
            
            # Prepare message headers
            message_headers = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "producer": event.producer,
                "correlation_id": event.correlation_id,
                "case_id": event.case_id,
                "user_id": event.user_id,
            }
            
            # Add custom headers
            if headers:
                message_headers.update(headers)
            
            # Remove None values
            message_headers = {k: v for k, v in message_headers.items() if v is not None}
            
            # Serialize event
            message_body = json.dumps(event.to_dict(), default=str).encode('utf-8')
            
            # Create message
            message = Message(
                message_body,
                headers=message_headers,
                priority=priority,
                delivery_mode=DeliveryMode.PERSISTENT,
                expiration=expiration,
                message_id=event.event_id,
                correlation_id=event.correlation_id,
                timestamp=event.timestamp,
                content_type="application/json",
                content_encoding="utf-8"
            )
            
            # Publish message
            await self._exchange.publish(message, routing_key=routing_key)
            
            # Update metrics
            self._metrics.record_published()
            
            logger.debug(
                f"Published event: {event.event_type.value} "
                f"(ID: {event.event_id}, Routing: {routing_key})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            self._metrics.record_failed()
            return False
    
    async def publish_case_created(
        self,
        case_id: str,
        patient_id: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish case created event."""
        from .schemas import CaseCreatedEvent
        
        payload = CaseCreatedEvent(
            case_id=case_id,
            patient_id=patient_id,
            metadata=metadata or {}
        )
        
        event = EventEnvelope(
            event_type=EventType.CASE_CREATED,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id,
            case_id=case_id,
            user_id=user_id
        )
        
        return await self.publish_event(event)
    
    async def publish_case_updated(
        self,
        case_id: str,
        changes: Dict[str, Any],
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Publish case updated event."""
        from .schemas import CaseUpdatedEvent
        
        payload = CaseUpdatedEvent(
            case_id=case_id,
            changes=changes
        )
        
        event = EventEnvelope(
            event_type=EventType.CASE_UPDATED,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id,
            case_id=case_id,
            user_id=user_id
        )
        
        return await self.publish_event(event)
    
    async def publish_image_uploaded(
        self,
        image_id: str,
        case_id: str,
        filename: str,
        format: str,
        size_bytes: int,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Publish image uploaded event."""
        from .schemas import ImageUploadedEvent
        
        payload = ImageUploadedEvent(
            image_id=image_id,
            case_id=case_id,
            filename=filename,
            format=format,
            size_bytes=size_bytes
        )
        
        event = EventEnvelope(
            event_type=EventType.IMAGE_UPLOADED,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id,
            case_id=case_id,
            user_id=user_id
        )
        
        return await self.publish_event(event)
    
    async def publish_job_created(
        self,
        job_id: str,
        job_type: str,
        case_id: Optional[str] = None,
        image_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Publish job created event."""
        from .schemas import JobCreatedEvent
        
        payload = JobCreatedEvent(
            job_id=job_id,
            job_type=job_type,
            case_id=case_id,
            image_id=image_id
        )
        
        event = EventEnvelope(
            event_type=EventType.JOB_CREATED,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id,
            case_id=case_id,
            user_id=user_id
        )
        
        return await self.publish_event(event)
    
    async def publish_job_progress(
        self,
        job_id: str,
        progress: float,
        message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish job progress event."""
        from .schemas import JobProgressEvent
        
        payload = JobProgressEvent(
            job_id=job_id,
            progress=progress,
            message=message
        )
        
        event = EventEnvelope(
            event_type=EventType.JOB_PROGRESS,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    async def publish_job_completed(
        self,
        job_id: str,
        result: Dict[str, Any],
        processing_time_seconds: Optional[float] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish job completed event."""
        from .schemas import JobCompletedEvent
        
        payload = JobCompletedEvent(
            job_id=job_id,
            result=result,
            processing_time_seconds=processing_time_seconds
        )
        
        event = EventEnvelope(
            event_type=EventType.JOB_COMPLETED,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    async def publish_job_failed(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish job failed event."""
        from .schemas import JobFailedEvent
        
        payload = JobFailedEvent(
            job_id=job_id,
            error_code=error_code,
            error_message=error_message
        )
        
        event = EventEnvelope(
            event_type=EventType.JOB_FAILED,
            payload=payload,
            producer=self.producer_name,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    def get_metrics(self) -> EventMetrics:
        """Get publisher metrics."""
        return self._metrics
    
    @asynccontextmanager
    async def connection_context(self):
        """Context manager for publisher connection."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()


# Global publisher instance (can be configured per service)
_global_publisher: Optional[EventPublisher] = None


def get_publisher(producer_name: str = "unknown") -> EventPublisher:
    """Get or create global publisher instance."""
    global _global_publisher
    
    if _global_publisher is None:
        _global_publisher = EventPublisher(producer_name=producer_name)
    
    return _global_publisher


async def publish_event(
    event: EventEnvelope[T],
    producer_name: str = "unknown"
) -> bool:
    """Convenience function to publish an event."""
    publisher = get_publisher(producer_name)
    return await publisher.publish_event(event)
