"""
DERCAS-ONCO-XAI Event Envelope

Standardized event envelope schema for event-driven architecture.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class EventMetadata(BaseModel):
    """Event metadata for additional context."""
    source_service: Optional[str] = None
    source_version: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


class EventEnvelope(BaseModel):
    """Standardized event envelope for all DERCAS events."""
    
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4()}")
    event_type: str = Field(..., description="Event type identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    producer: str = Field(..., description="Service that produced the event")
    case_id: Optional[UUID] = Field(None, description="Associated case ID")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    schema_version: str = Field(default="1.0", description="Event schema version")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "event_id": "evt_123e4567-e89b-12d3-a456-426614174000",
                "event_type": "inference.completed",
                "timestamp": "2024-01-01T12:00:00Z",
                "correlation_id": "corr_123e4567-e89b-12d3-a456-426614174000",
                "producer": "inference-service",
                "case_id": "case_123e4567-e89b-12d3-a456-426614174000",
                "payload": {
                    "result_bundle_id": "rb_123",
                    "image_id": "img_001",
                    "model_profile": "lung_patterns_v3",
                    "model_version": "3.2.1",
                    "summary": {
                        "top_patterns": [{"name": "acinar", "score": 0.81}],
                        "mutations": [{"name": "EGFR", "status": "INCONCLUSIVE", "score": 0.58}]
                    }
                },
                "metadata": {
                    "source_service": "inference-service",
                    "source_version": "0.1.0",
                    "user_id": "user_123",
                    "tags": {"environment": "development"}
                },
                "schema_version": "1.0"
            }
        }
    
    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type format."""
        if not v or '.' not in v:
            raise ValueError('Event type must be in format: domain.action (e.g., case.created)')
        return v
    
    @validator('producer')
    def validate_producer(cls, v):
        """Validate producer service name."""
        if not v:
            raise ValueError('Producer service name is required')
        return v
    
    @validator('correlation_id')
    def validate_correlation_id(cls, v):
        """Validate correlation ID format."""
        if not v:
            raise ValueError('Correlation ID is required')
        return v


def validate_event_envelope(event_data: Dict[str, Any]) -> EventEnvelope:
    """Validate and parse event envelope from dictionary."""
    return EventEnvelope(**event_data)


def create_event_envelope(
    event_type: str,
    producer: str,
    correlation_id: str,
    payload: Dict[str, Any],
    case_id: Optional[UUID] = None,
    metadata: Optional[EventMetadata] = None
) -> EventEnvelope:
    """Create a new event envelope."""
    return EventEnvelope(
        event_type=event_type,
        producer=producer,
        correlation_id=correlation_id,
        payload=payload,
        case_id=case_id,
        metadata=metadata or EventMetadata()
    )


# Event type constants
class EventTypes:
    """Standard event type constants."""
    
    # Case events
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_DELETED = "case.deleted"
    
    # Image events
    IMAGE_UPLOADED = "image.uploaded"
    IMAGE_DELETED = "image.deleted"
    IMAGE_PROCESSED = "image.processed"
    
    # Job events
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    
    # Inference events
    INFERENCE_STARTED = "inference.started"
    INFERENCE_COMPLETED = "inference.completed"
    INFERENCE_FAILED = "inference.failed"
    
    # EHR events
    EHR_INGESTED = "ehr.ingested"
    EHR_EXTRACTED = "ehr.extracted"
    EHR_MAPPED = "ehr.mapped"
    EHR_CONFLICT_DETECTED = "ehr.conflict_detected"
    
    # Graph events
    GRAPH_REBUILD_STARTED = "graph.rebuild_started"
    GRAPH_BUILT = "graph.built"
    GRAPH_FAILED = "graph.failed"
    GRAPH_SNAPSHOT_CREATED = "graph.snapshot_created"
    
    # Ontology events
    ONTOLOGY_PROPOSAL_CREATED = "ontology.proposal.created"
    ONTOLOGY_PROPOSAL_VALIDATED = "ontology.proposal.validated"
    ONTOLOGY_PROPOSAL_APPROVED = "ontology.proposal.approved"
    ONTOLOGY_PROPOSAL_REJECTED = "ontology.proposal.rejected"
    ONTOLOGY_PUBLISHED = "ontology.published"
    ONTOLOGY_ROLLBACKED = "ontology.rollbacked"
    
    # Explanation events
    EXPLANATION_REQUESTED = "explanation.requested"
    EXPLANATION_GENERATED = "explanation.generated"
    EXPLANATION_FAILED = "explanation.failed"
    
    # Audit events
    AUDIT_EVENT_CREATED = "audit.event.created"
    AUDIT_EXPORT_REQUESTED = "audit.export.requested"
    AUDIT_EXPORT_COMPLETED = "audit.export.completed"


# Routing keys for RabbitMQ
class RoutingKeys:
    """Standard routing keys for event routing."""
    
    # Case routing
    CASE_EVENTS = "case.*"
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    
    # Image routing
    IMAGE_EVENTS = "image.*"
    IMAGE_UPLOADED = "image.uploaded"
    IMAGE_PROCESSED = "image.processed"
    
    # Job routing
    JOB_EVENTS = "job.*"
    JOB_INFERENCE = "job.inference.*"
    JOB_EHR = "job.ehr.*"
    JOB_GRAPH = "job.graph.*"
    JOB_ONTOLOGY = "job.ontology.*"
    
    # Service-specific routing
    INFERENCE_EVENTS = "inference.*"
    EHR_EVENTS = "ehr.*"
    GRAPH_EVENTS = "graph.*"
    ONTOLOGY_EVENTS = "ontology.*"
    EXPLANATION_EVENTS = "explanation.*"
    AUDIT_EVENTS = "audit.*"


# Exchange names
class Exchanges:
    """Standard exchange names."""
    
    EVENTS = "dercas.events"  # Topic exchange for all events
    JOBS = "dercas.jobs"      # Direct exchange for job queuing
    DLX = "dercas.dlx"        # Dead letter exchange


# Queue names
class Queues:
    """Standard queue names."""
    
    # Event queues
    CASE_EVENTS = "case.events"
    IMAGE_EVENTS = "image.events"
    INFERENCE_EVENTS = "inference.events"
    EHR_EVENTS = "ehr.events"
    GRAPH_EVENTS = "graph.events"
    ONTOLOGY_EVENTS = "ontology.events"
    EXPLANATION_EVENTS = "explanation.events"
    AUDIT_EVENTS = "audit.events"
    
    # Job queues
    INFERENCE_JOBS = "inference.jobs"
    EHR_JOBS = "ehr.jobs"
    GRAPH_JOBS = "graph.jobs"
    ONTOLOGY_JOBS = "ontology.jobs"
    EXPLANATION_JOBS = "explanation.jobs"
    
    # Celery queues
    CELERY = "celery"
    CELERY_PRIORITY = "celery.priority"
    
    # Dead letter queues
    DLX_EVENTS = "dlx.events"
    DLX_JOBS = "dlx.jobs"
