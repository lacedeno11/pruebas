"""
DERCAS-ONCO-XAI Event Publisher

RabbitMQ event publishing utilities.
"""

import json
import logging
from typing import Any, Dict, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from .envelope import EventEnvelope, EventMetadata, create_event_envelope, Exchanges, RoutingKeys

logger = logging.getLogger(__name__)


class EventPublisher:
    """RabbitMQ event publisher for DERCAS events."""
    
    def __init__(self, rabbitmq_url: str, exchange: str = Exchanges.EVENTS):
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.connection = None
        self.channel = None
        self._is_connected = False
    
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
    
    def publish_event(
        self,
        event_type: str,
        producer: str,
        correlation_id: str,
        payload: Dict[str, Any],
        case_id: Optional[str] = None,
        metadata: Optional[EventMetadata] = None,
        routing_key: Optional[str] = None
    ) -> str:
        """Publish an event to RabbitMQ."""
        self.ensure_connected()
        
        # Create event envelope
        envelope = create_event_envelope(
            event_type=event_type,
            producer=producer,
            correlation_id=correlation_id,
            payload=payload,
            case_id=case_id,
            metadata=metadata
        )
        
        # Determine routing key
        if not routing_key:
            routing_key = event_type
        
        try:
            # Publish message
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=envelope.json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    correlation_id=correlation_id,
                    message_id=envelope.event_id,
                    timestamp=int(envelope.timestamp.timestamp()),
                    headers={
                        'event_type': event_type,
                        'producer': producer,
                        'case_id': str(case_id) if case_id else None,
                        'schema_version': envelope.schema_version
                    }
                )
            )
            
            logger.debug(
                f"Published event: {event_type}",
                extra={
                    'event_id': envelope.event_id,
                    'correlation_id': correlation_id,
                    'routing_key': routing_key,
                    'case_id': case_id
                }
            )
            
            return envelope.event_id
            
        except AMQPChannelError as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            raise
    
    def publish_envelope(self, envelope: EventEnvelope, routing_key: Optional[str] = None) -> str:
        """Publish an event envelope directly."""
        return self.publish_event(
            event_type=envelope.event_type,
            producer=envelope.producer,
            correlation_id=envelope.correlation_id,
            payload=envelope.payload,
            case_id=str(envelope.case_id) if envelope.case_id else None,
            metadata=envelope.metadata,
            routing_key=routing_key
        )
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Global publisher instance
_global_publisher: Optional[EventPublisher] = None


def init_event_publisher(rabbitmq_url: str, exchange: str = Exchanges.EVENTS) -> EventPublisher:
    """Initialize global event publisher."""
    global _global_publisher
    _global_publisher = EventPublisher(rabbitmq_url, exchange)
    _global_publisher.connect()
    return _global_publisher


def get_event_publisher() -> EventPublisher:
    """Get global event publisher instance."""
    if not _global_publisher:
        raise RuntimeError("Event publisher not initialized. Call init_event_publisher() first.")
    return _global_publisher


def publish_event(
    event_type: str,
    producer: str,
    correlation_id: str,
    payload: Dict[str, Any],
    case_id: Optional[str] = None,
    metadata: Optional[EventMetadata] = None,
    routing_key: Optional[str] = None
) -> str:
    """Publish an event using the global publisher."""
    publisher = get_event_publisher()
    return publisher.publish_event(
        event_type=event_type,
        producer=producer,
        correlation_id=correlation_id,
        payload=payload,
        case_id=case_id,
        metadata=metadata,
        routing_key=routing_key
    )


# Convenience functions for common events
def publish_case_created(
    case_id: str,
    patient_id: str,
    correlation_id: str,
    producer: str = "case-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish case created event."""
    return publish_event(
        event_type="case.created",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "case_id": case_id,
            "patient_id": patient_id
        },
        case_id=case_id,
        metadata=metadata,
        routing_key=RoutingKeys.CASE_CREATED
    )


def publish_case_updated(
    case_id: str,
    changes: Dict[str, Any],
    correlation_id: str,
    producer: str = "case-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish case updated event."""
    return publish_event(
        event_type="case.updated",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "case_id": case_id,
            "changes": changes
        },
        case_id=case_id,
        metadata=metadata,
        routing_key=RoutingKeys.CASE_UPDATED
    )


def publish_image_uploaded(
    image_id: str,
    case_id: str,
    correlation_id: str,
    producer: str = "image-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish image uploaded event."""
    return publish_event(
        event_type="image.uploaded",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "image_id": image_id,
            "case_id": case_id
        },
        case_id=case_id,
        metadata=metadata,
        routing_key=RoutingKeys.IMAGE_UPLOADED
    )


def publish_job_created(
    job_id: str,
    job_type: str,
    case_id: str,
    correlation_id: str,
    producer: str,
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish job created event."""
    return publish_event(
        event_type="job.created",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "job_id": job_id,
            "job_type": job_type,
            "case_id": case_id
        },
        case_id=case_id,
        metadata=metadata,
        routing_key="job.created"
    )


def publish_job_completed(
    job_id: str,
    job_type: str,
    case_id: str,
    result: Dict[str, Any],
    correlation_id: str,
    producer: str,
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish job completed event."""
    return publish_event(
        event_type="job.completed",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "job_id": job_id,
            "job_type": job_type,
            "case_id": case_id,
            "result": result
        },
        case_id=case_id,
        metadata=metadata,
        routing_key="job.completed"
    )


def publish_inference_completed(
    result_bundle_id: str,
    image_id: str,
    case_id: str,
    model_profile: str,
    model_version: str,
    summary: Dict[str, Any],
    correlation_id: str,
    producer: str = "inference-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish inference completed event."""
    return publish_event(
        event_type="inference.completed",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "result_bundle_id": result_bundle_id,
            "image_id": image_id,
            "case_id": case_id,
            "model_profile": model_profile,
            "model_version": model_version,
            "summary": summary
        },
        case_id=case_id,
        metadata=metadata,
        routing_key=RoutingKeys.INFERENCE_EVENTS
    )


def publish_ehr_ingested(
    ehr_id: str,
    case_id: str,
    version: int,
    correlation_id: str,
    producer: str = "ehr-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish EHR ingested event."""
    return publish_event(
        event_type="ehr.ingested",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "ehr_id": ehr_id,
            "case_id": case_id,
            "version": version
        },
        case_id=case_id,
        metadata=metadata,
        routing_key=RoutingKeys.EHR_EVENTS
    )


def publish_ontology_published(
    ontology_name: str,
    version_tag: str,
    proposal_id: str,
    correlation_id: str,
    producer: str = "ontology-admin-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish ontology published event."""
    return publish_event(
        event_type="ontology.published",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "ontology_name": ontology_name,
            "version_tag": version_tag,
            "proposal_id": proposal_id
        },
        metadata=metadata,
        routing_key=RoutingKeys.ONTOLOGY_EVENTS
    )


def publish_audit_event(
    entity_type: str,
    entity_id: str,
    action: str,
    status: str,
    details: Dict[str, Any],
    correlation_id: str,
    user_id: Optional[str] = None,
    case_id: Optional[str] = None,
    producer: str = "audit-service",
    metadata: Optional[EventMetadata] = None
) -> str:
    """Publish audit event."""
    return publish_event(
        event_type="audit.event.created",
        producer=producer,
        correlation_id=correlation_id,
        payload={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "status": status,
            "details": details,
            "user_id": user_id,
            "case_id": case_id
        },
        case_id=case_id,
        metadata=metadata,
        routing_key=RoutingKeys.AUDIT_EVENTS
    )
