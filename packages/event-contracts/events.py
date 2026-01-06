"""
DERCAS-ONCO-XAI V1 - Event Schemas

Event envelope schema and event type definitions for the oncology platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types for the platform."""
    
    # Case Events
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_STATUS_CHANGED = "case.status_changed"
    CASE_ASSIGNED = "case.assigned"
    CASE_CLOSED = "case.closed"
    
    # Patient Events
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    
    # Image Events
    IMAGE_UPLOADED = "image.uploaded"
    IMAGE_VALIDATED = "image.validated"
    IMAGE_DELETED = "image.deleted"
    IMAGE_PROCESSING_STARTED = "image.processing_started"
    IMAGE_PROCESSING_COMPLETED = "image.processing_completed"
    IMAGE_PROCESSING_FAILED = "image.processing_failed"
    
    # Job Events
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    JOB_RETRY = "job.retry"
    
    # Inference Events
    INFERENCE_STARTED = "inference.started"
    INFERENCE_COMPLETED = "inference.completed"
    INFERENCE_FAILED = "inference.failed"
    INFERENCE_LOW_CONFIDENCE = "inference.low_confidence"
    INFERENCE_REVIEW_REQUIRED = "inference.review_required"
    
    # EHR Events
    EHR_INGESTED = "ehr.ingested"
    EHR_NORMALIZED = "ehr.normalized"
    EHR_ENTITIES_EXTRACTED = "ehr.entities_extracted"
    EHR_ENTITIES_MAPPED = "ehr.entities_mapped"
    EHR_PROCESSING_COMPLETED = "ehr.processing_completed"
    EHR_PROCESSING_FAILED = "ehr.processing_failed"
    
    # Graph Events
    GRAPH_BUILD_STARTED = "graph.build_started"
    GRAPH_BUILD_COMPLETED = "graph.build_completed"
    GRAPH_BUILD_FAILED = "graph.build_failed"
    GRAPH_SNAPSHOT_CREATED = "graph.snapshot_created"
    GRAPH_UPDATED = "graph.updated"
    
    # Ontology Events
    ONTOLOGY_UPDATE_PROPOSED = "ontology.update_proposed"
    ONTOLOGY_UPDATE_APPROVED = "ontology.update_approved"
    ONTOLOGY_UPDATE_REJECTED = "ontology.update_rejected"
    ONTOLOGY_PUBLISHED = "ontology.published"
    ONTOLOGY_ROLLBACK = "ontology.rollback"
    
    # Explanation Events
    EXPLANATION_REQUESTED = "explanation.requested"
    EXPLANATION_GENERATED = "explanation.generated"
    EXPLANATION_FAILED = "explanation.failed"
    EXPLANATION_REVIEWED = "explanation.reviewed"
    
    # Audit Events
    AUDIT_LOG_CREATED = "audit.log_created"
    SECURITY_EVENT = "security.event"
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    
    # System Events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_HEALTH_CHECK = "service.health_check"
    CONFIGURATION_CHANGED = "configuration.changed"
    ERROR_OCCURRED = "error.occurred"


class EventEnvelope(BaseModel):
    """Standard event envelope for all platform events."""
    
    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of event")
    event_version: str = Field(default="1.0", description="Event schema version")
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp (UTC)")
    
    # Context
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    
    # Source
    producer: str = Field(..., description="Service that produced the event")
    producer_version: Optional[str] = Field(None, description="Producer service version")
    
    # Payload
    payload: Dict[str, Any] = Field(..., description="Event-specific data")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    # Tracing
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")
    span_id: Optional[str] = Field(None, description="Span ID within trace")


# Event Payload Models
class CaseEventPayload(BaseModel):
    """Payload for case-related events."""
    case_id: str = Field(..., description="Case identifier")
    patient_id: str = Field(..., description="Patient identifier")
    status: Optional[str] = Field(None, description="Case status")
    previous_status: Optional[str] = Field(None, description="Previous status (for status change events)")
    assigned_to: Optional[str] = Field(None, description="Assigned clinician")
    title: Optional[str] = Field(None, description="Case title")
    priority: Optional[int] = Field(None, description="Case priority")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changed fields")


class PatientEventPayload(BaseModel):
    """Payload for patient-related events."""
    patient_id: str = Field(..., description="Patient identifier")
    medical_record_number: Optional[str] = Field(None, description="Medical record number")
    age: Optional[int] = Field(None, description="Patient age")
    gender: Optional[str] = Field(None, description="Patient gender")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changed fields")


class ImageEventPayload(BaseModel):
    """Payload for image-related events."""
    image_id: str = Field(..., description="Image identifier")
    case_id: str = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Image filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_format: Optional[str] = Field(None, description="File format")
    storage_path: Optional[str] = Field(None, description="Storage path")
    checksum: Optional[str] = Field(None, description="File checksum")
    processing_job_id: Optional[str] = Field(None, description="Associated processing job ID")


class JobEventPayload(BaseModel):
    """Payload for job-related events."""
    job_id: str = Field(..., description="Job identifier")
    job_type: str = Field(..., description="Job type")
    status: str = Field(..., description="Job status")
    previous_status: Optional[str] = Field(None, description="Previous status")
    image_id: Optional[str] = Field(None, description="Associated image ID")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    worker_id: Optional[str] = Field(None, description="Worker that processed the job")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: Optional[int] = Field(None, description="Number of retries")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class InferenceEventPayload(BaseModel):
    """Payload for inference-related events."""
    result_bundle_id: str = Field(..., description="Result bundle identifier")
    image_id: str = Field(..., description="Associated image ID")
    case_id: str = Field(..., description="Associated case ID")
    job_id: Optional[str] = Field(None, description="Associated job ID")
    overall_confidence: Optional[str] = Field(None, description="Overall confidence level")
    requires_review: Optional[bool] = Field(None, description="Whether review is required")
    review_reason: Optional[str] = Field(None, description="Reason for review")
    model_versions: Optional[Dict[str, str]] = Field(None, description="Model versions used")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class EHREventPayload(BaseModel):
    """Payload for EHR-related events."""
    ehr_id: str = Field(..., description="EHR document identifier")
    case_id: str = Field(..., description="Associated case ID")
    document_type: str = Field(..., description="Document type")
    document_title: Optional[str] = Field(None, description="Document title")
    entities_count: Optional[int] = Field(None, description="Number of extracted entities")
    mappings_count: Optional[int] = Field(None, description="Number of ontology mappings")
    processing_version: Optional[str] = Field(None, description="Processing version")
    extraction_method: Optional[str] = Field(None, description="Entity extraction method")


class GraphEventPayload(BaseModel):
    """Payload for graph-related events."""
    snapshot_id: str = Field(..., description="Graph snapshot identifier")
    case_id: str = Field(..., description="Associated case ID")
    graph_version: str = Field(..., description="Graph version")
    node_count: Optional[int] = Field(None, description="Number of nodes")
    edge_count: Optional[int] = Field(None, description="Number of edges")
    source_components: Optional[list[str]] = Field(None, description="Source components")
    ontology_versions: Optional[Dict[str, str]] = Field(None, description="Ontology versions")
    build_time_seconds: Optional[float] = Field(None, description="Build time")


class OntologyEventPayload(BaseModel):
    """Payload for ontology-related events."""
    proposal_id: Optional[str] = Field(None, description="Update proposal identifier")
    ontology_name: str = Field(..., description="Ontology name")
    ontology_version: str = Field(..., description="Ontology version")
    previous_version: Optional[str] = Field(None, description="Previous version")
    changes_count: Optional[int] = Field(None, description="Number of changes")
    impact_assessment: Optional[Dict[str, Any]] = Field(None, description="Impact assessment")
    approved_by: Optional[str] = Field(None, description="User who approved the update")
    rollback_reason: Optional[str] = Field(None, description="Reason for rollback")


class ExplanationEventPayload(BaseModel):
    """Payload for explanation-related events."""
    report_id: str = Field(..., description="Explanation report identifier")
    case_id: str = Field(..., description="Associated case ID")
    report_version: str = Field(..., description="Report version")
    confidence_assessment: Optional[str] = Field(None, description="Overall confidence")
    contains_diagnosis: Optional[bool] = Field(None, description="Contains diagnostic language")
    clinical_review_required: Optional[bool] = Field(None, description="Requires clinical review")
    generated_by: Optional[str] = Field(None, description="Generation method")
    generation_time_seconds: Optional[float] = Field(None, description="Generation time")


class AuditEventPayload(BaseModel):
    """Payload for audit-related events."""
    audit_event_id: str = Field(..., description="Audit event identifier")
    event_category: str = Field(..., description="Event category")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    action: str = Field(..., description="Action performed")
    outcome: str = Field(..., description="Action outcome (success/failure)")
    user_id: Optional[str] = Field(None, description="User who performed the action")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    additional_details: Optional[Dict[str, Any]] = Field(None, description="Additional audit details")


class SystemEventPayload(BaseModel):
    """Payload for system-related events."""
    service_name: str = Field(..., description="Service name")
    service_version: Optional[str] = Field(None, description="Service version")
    event_details: str = Field(..., description="Event details")
    health_status: Optional[str] = Field(None, description="Health status")
    configuration_changes: Optional[Dict[str, Any]] = Field(None, description="Configuration changes")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    metrics: Optional[Dict[str, float]] = Field(None, description="Performance metrics")


# Event Factory Functions
def create_case_event(
    event_type: EventType,
    case_id: str,
    patient_id: str,
    producer: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **payload_kwargs
) -> EventEnvelope:
    """Create a case-related event."""
    payload = CaseEventPayload(
        case_id=case_id,
        patient_id=patient_id,
        **payload_kwargs
    )
    
    return EventEnvelope(
        event_type=event_type,
        correlation_id=correlation_id,
        case_id=case_id,
        user_id=user_id,
        producer=producer,
        payload=payload.model_dump()
    )


def create_image_event(
    event_type: EventType,
    image_id: str,
    case_id: str,
    filename: str,
    producer: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **payload_kwargs
) -> EventEnvelope:
    """Create an image-related event."""
    payload = ImageEventPayload(
        image_id=image_id,
        case_id=case_id,
        filename=filename,
        **payload_kwargs
    )
    
    return EventEnvelope(
        event_type=event_type,
        correlation_id=correlation_id,
        case_id=case_id,
        user_id=user_id,
        producer=producer,
        payload=payload.model_dump()
    )


def create_job_event(
    event_type: EventType,
    job_id: str,
    job_type: str,
    status: str,
    producer: str,
    correlation_id: Optional[str] = None,
    case_id: Optional[str] = None,
    **payload_kwargs
) -> EventEnvelope:
    """Create a job-related event."""
    payload = JobEventPayload(
        job_id=job_id,
        job_type=job_type,
        status=status,
        **payload_kwargs
    )
    
    return EventEnvelope(
        event_type=event_type,
        correlation_id=correlation_id,
        case_id=case_id,
        producer=producer,
        payload=payload.model_dump()
    )


def create_inference_event(
    event_type: EventType,
    result_bundle_id: str,
    image_id: str,
    case_id: str,
    producer: str,
    correlation_id: Optional[str] = None,
    **payload_kwargs
) -> EventEnvelope:
    """Create an inference-related event."""
    payload = InferenceEventPayload(
        result_bundle_id=result_bundle_id,
        image_id=image_id,
        case_id=case_id,
        **payload_kwargs
    )
    
    return EventEnvelope(
        event_type=event_type,
        correlation_id=correlation_id,
        case_id=case_id,
        producer=producer,
        payload=payload.model_dump()
    )


def create_audit_event(
    event_category: str,
    action: str,
    outcome: str,
    producer: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **payload_kwargs
) -> EventEnvelope:
    """Create an audit event."""
    payload = AuditEventPayload(
        audit_event_id=str(uuid4()),
        event_category=event_category,
        action=action,
        outcome=outcome,
        **payload_kwargs
    )
    
    return EventEnvelope(
        event_type=EventType.AUDIT_LOG_CREATED,
        correlation_id=correlation_id,
        user_id=user_id,
        producer=producer,
        payload=payload.model_dump()
    )
