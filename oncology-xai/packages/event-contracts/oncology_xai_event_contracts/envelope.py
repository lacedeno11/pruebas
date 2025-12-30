# DERCAS-ONCO-XAI V1 - Event Envelope Schema
# Standard event envelope for all platform events

import uuid
from typing import Optional, Dict, Any, TypeVar, Generic
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid7

T = TypeVar('T')


class EventType(str, Enum):
    """Standard event types for the oncology platform."""
    
    # Case events
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    
    # Image events
    IMAGE_UPLOADED = "image.uploaded"
    IMAGE_DELETED = "image.deleted"
    
    # Job events
    JOB_CREATED = "job.created"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    
    # Inference events
    INFERENCE_COMPLETED = "inference.completed"
    INFERENCE_FAILED = "inference.failed"
    
    # EHR events
    EHR_INGESTED = "ehr.ingested"
    EHR_EXTRACTED = "ehr.extracted"
    EHR_MAPPED = "ehr.mapped"
    
    # Graph events
    GRAPH_BUILT = "graph.built"
    GRAPH_FAILED = "graph.failed"
    
    # Ontology events
    ONTOLOGY_PROPOSAL_CREATED = "ontology.proposal.created"
    ONTOLOGY_PUBLISHED = "ontology.published"
    ONTOLOGY_ROLLBACKED = "ontology.rollbacked"
    
    # Audit events
    AUDIT_EVENT_CREATED = "audit.event.created"


class EventEnvelope(BaseModel, Generic[T]):
    """
    Standard event envelope for all platform events.
    
    This envelope provides a consistent structure for all events in the system,
    enabling proper routing, correlation, and auditing.
    """
    
    event_id: str = Field(
        default_factory=lambda: str(uuid7.uuid7()),
        description="Unique event identifier (UUID7 for time-ordering)"
    )
    event_type: EventType = Field(
        ...,
        description="Type of event (determines routing and handling)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event creation timestamp (UTC)"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for request tracing"
    )
    producer: str = Field(
        ...,
        description="Service that produced this event"
    )
    case_id: Optional[str] = Field(
        None,
        description="Associated case ID (if applicable)"
    )
    user_id: Optional[str] = Field(
        None,
        description="User who triggered the event (if applicable)"
    )
    payload: T = Field(
        ...,
        description="Event-specific payload data"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    
    @validator('event_id')
    def validate_event_id(cls, v):
        """Validate event ID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('Invalid UUID format for event_id')
    
    @validator('correlation_id')
    def validate_correlation_id(cls, v):
        """Validate correlation ID format if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
                return v
            except ValueError:
                raise ValueError('Invalid UUID format for correlation_id')
        return v
    
    @validator('producer')
    def validate_producer(cls, v):
        """Validate producer name."""
        if not v or not v.strip():
            raise ValueError('Producer cannot be empty')
        return v.strip()
    
    def to_routing_key(self) -> str:
        """Generate RabbitMQ routing key for this event."""
        # Convert event type to routing key format
        # e.g., "case.created" -> "case.created"
        return self.event_type.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return self.dict(by_alias=True)
    
    def get_trace_context(self) -> Dict[str, str]:
        """Get trace context for distributed tracing."""
        context = {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'producer': self.producer,
        }
        
        if self.correlation_id:
            context['correlation_id'] = self.correlation_id
        
        if self.case_id:
            context['case_id'] = self.case_id
        
        if self.user_id:
            context['user_id'] = self.user_id
        
        return context
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def create_event(
    event_type: EventType,
    payload: T,
    producer: str,
    correlation_id: Optional[str] = None,
    case_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EventEnvelope[T]:
    """
    Create a new event envelope.
    
    Args:
        event_type: Type of event
        payload: Event payload data
        producer: Service producing the event
        correlation_id: Optional correlation ID for tracing
        case_id: Optional associated case ID
        user_id: Optional user ID who triggered the event
        metadata: Optional additional metadata
    
    Returns:
        EventEnvelope with the provided data
    """
    return EventEnvelope(
        event_type=event_type,
        payload=payload,
        producer=producer,
        correlation_id=correlation_id,
        case_id=case_id,
        user_id=user_id,
        metadata=metadata or {}
    )


class EventMetrics(BaseModel):
    """Metrics for event processing."""
    
    events_published: int = Field(0, description="Number of events published")
    events_consumed: int = Field(0, description="Number of events consumed")
    events_failed: int = Field(0, description="Number of failed events")
    last_event_timestamp: Optional[datetime] = Field(None, description="Last event timestamp")
    processing_time_ms: Optional[float] = Field(None, description="Average processing time in ms")
    
    def record_published(self):
        """Record a published event."""
        self.events_published += 1
        self.last_event_timestamp = datetime.utcnow()
    
    def record_consumed(self, processing_time_ms: Optional[float] = None):
        """Record a consumed event."""
        self.events_consumed += 1
        self.last_event_timestamp = datetime.utcnow()
        
        if processing_time_ms is not None:
            if self.processing_time_ms is None:
                self.processing_time_ms = processing_time_ms
            else:
                # Simple moving average
                self.processing_time_ms = (self.processing_time_ms + processing_time_ms) / 2
    
    def record_failed(self):
        """Record a failed event."""
        self.events_failed += 1
        self.last_event_timestamp = datetime.utcnow()


class EventFilter(BaseModel):
    """Filter for event consumption."""
    
    event_types: Optional[list[EventType]] = Field(None, description="Event types to filter")
    case_ids: Optional[list[str]] = Field(None, description="Case IDs to filter")
    producers: Optional[list[str]] = Field(None, description="Producers to filter")
    user_ids: Optional[list[str]] = Field(None, description="User IDs to filter")
    from_timestamp: Optional[datetime] = Field(None, description="Filter events from this timestamp")
    to_timestamp: Optional[datetime] = Field(None, description="Filter events to this timestamp")
    
    def matches(self, event: EventEnvelope) -> bool:
        """Check if an event matches this filter."""
        
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.case_ids and event.case_id not in self.case_ids:
            return False
        
        if self.producers and event.producer not in self.producers:
            return False
        
        if self.user_ids and event.user_id not in self.user_ids:
            return False
        
        if self.from_timestamp and event.timestamp < self.from_timestamp:
            return False
        
        if self.to_timestamp and event.timestamp > self.to_timestamp:
            return False
        
        return True
