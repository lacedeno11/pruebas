# DERCAS-ONCO-XAI V1 - Event Payload Schemas
# Specific payload schemas for different event types

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator


class BaseEventPayload(BaseModel):
    """Base class for all event payloads."""
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


# Case Events

class CaseCreatedEvent(BaseEventPayload):
    """Payload for case.created event."""
    
    case_id: str = Field(..., description="Created case ID")
    patient_id: str = Field(..., description="Associated patient ID")
    title: Optional[str] = Field(None, description="Case title")
    status: str = Field("CREATED", description="Initial case status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional case metadata")


class CaseUpdatedEvent(BaseEventPayload):
    """Payload for case.updated event."""
    
    case_id: str = Field(..., description="Updated case ID")
    changes: Dict[str, Any] = Field(..., description="Fields that were changed")
    previous_values: Optional[Dict[str, Any]] = Field(None, description="Previous values")
    new_status: Optional[str] = Field(None, description="New case status if changed")


# Image Events

class ImageUploadedEvent(BaseEventPayload):
    """Payload for image.uploaded event."""
    
    image_id: str = Field(..., description="Uploaded image ID")
    case_id: str = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Original filename")
    format: str = Field(..., description="Image format")
    size_bytes: int = Field(..., description="File size in bytes")
    checksum: Optional[str] = Field(None, description="File checksum")
    storage_uri: Optional[str] = Field(None, description="Storage location")


class ImageDeletedEvent(BaseEventPayload):
    """Payload for image.deleted event."""
    
    image_id: str = Field(..., description="Deleted image ID")
    case_id: str = Field(..., description="Associated case ID")
    reason: Optional[str] = Field(None, description="Deletion reason")


# Job Events

class JobCreatedEvent(BaseEventPayload):
    """Payload for job.created event."""
    
    job_id: str = Field(..., description="Created job ID")
    job_type: str = Field(..., description="Type of job")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    image_id: Optional[str] = Field(None, description="Associated image ID")
    ehr_id: Optional[str] = Field(None, description="Associated EHR ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Job parameters")
    priority: int = Field(0, description="Job priority")


class JobProgressEvent(BaseEventPayload):
    """Payload for job.progress event."""
    
    job_id: str = Field(..., description="Job ID")
    progress: float = Field(..., description="Progress percentage (0.0-1.0)")
    message: Optional[str] = Field(None, description="Progress message")
    stage: Optional[str] = Field(None, description="Current processing stage")
    
    @validator('progress')
    def validate_progress(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Progress must be between 0.0 and 1.0')
        return v


class JobCompletedEvent(BaseEventPayload):
    """Payload for job.completed event."""
    
    job_id: str = Field(..., description="Completed job ID")
    result: Dict[str, Any] = Field(..., description="Job result data")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")
    output_artifacts: List[str] = Field(default_factory=list, description="Generated artifact IDs")


class JobFailedEvent(BaseEventPayload):
    """Payload for job.failed event."""
    
    job_id: str = Field(..., description="Failed job ID")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    retry_count: int = Field(0, description="Number of retries attempted")


# Inference Events

class InferenceCompletedEvent(BaseEventPayload):
    """Payload for inference.completed event."""
    
    result_bundle_id: str = Field(..., description="Result bundle ID")
    image_id: str = Field(..., description="Processed image ID")
    case_id: str = Field(..., description="Associated case ID")
    model_profile: str = Field(..., description="ML model profile used")
    model_version: str = Field(..., description="ML model version")
    patterns_detected: List[Dict[str, Any]] = Field(default_factory=list, description="Detected patterns")
    mutations_predicted: List[Dict[str, Any]] = Field(default_factory=list, description="Predicted mutations")
    xai_artifacts: List[str] = Field(default_factory=list, description="XAI artifact IDs")
    processing_time_seconds: float = Field(..., description="Processing time")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence scores")


class InferenceFailedEvent(BaseEventPayload):
    """Payload for inference.failed event."""
    
    image_id: str = Field(..., description="Image ID that failed processing")
    case_id: str = Field(..., description="Associated case ID")
    model_profile: str = Field(..., description="ML model profile attempted")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    stage: Optional[str] = Field(None, description="Processing stage where failure occurred")


# EHR Events

class EHRIngestedEvent(BaseEventPayload):
    """Payload for ehr.ingested event."""
    
    ehr_id: str = Field(..., description="Ingested EHR ID")
    case_id: str = Field(..., description="Associated case ID")
    source: str = Field(..., description="EHR source")
    version: int = Field(..., description="EHR version")
    content_length: int = Field(..., description="Content length in characters")
    checksum: str = Field(..., description="Content checksum")


class EHRExtractedEvent(BaseEventPayload):
    """Payload for ehr.extracted event."""
    
    ehr_id: str = Field(..., description="EHR ID")
    case_id: str = Field(..., description="Associated case ID")
    entities_count: int = Field(..., description="Number of entities extracted")
    entity_types: List[str] = Field(default_factory=list, description="Types of entities found")
    extraction_method: str = Field(..., description="Extraction method used")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Average confidence by type")


class EHRMappedEvent(BaseEventPayload):
    """Payload for ehr.mapped event."""
    
    ehr_id: str = Field(..., description="EHR ID")
    case_id: str = Field(..., description="Associated case ID")
    mappings_count: int = Field(..., description="Number of mappings created")
    ontologies_used: List[str] = Field(default_factory=list, description="Ontologies mapped to")
    mapping_method: str = Field(..., description="Mapping method used")
    conflicts_detected: int = Field(0, description="Number of conflicts detected")


# Graph Events

class GraphBuiltEvent(BaseEventPayload):
    """Payload for graph.built event."""
    
    graph_snapshot_id: str = Field(..., description="Graph snapshot ID")
    case_id: str = Field(..., description="Associated case ID")
    node_count: int = Field(..., description="Number of nodes in graph")
    edge_count: int = Field(..., description="Number of edges in graph")
    ontology_versions: Dict[str, str] = Field(default_factory=dict, description="Ontology versions used")
    build_time_seconds: float = Field(..., description="Graph build time")


class GraphFailedEvent(BaseEventPayload):
    """Payload for graph.failed event."""
    
    case_id: str = Field(..., description="Associated case ID")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    stage: Optional[str] = Field(None, description="Build stage where failure occurred")


# Ontology Events

class OntologyProposalCreatedEvent(BaseEventPayload):
    """Payload for ontology.proposal.created event."""
    
    proposal_id: str = Field(..., description="Proposal ID")
    targets: List[str] = Field(..., description="Target ontologies")
    mode: str = Field(..., description="Update mode (online|offline)")
    description: Optional[str] = Field(None, description="Proposal description")
    created_by: str = Field(..., description="User who created the proposal")


class OntologyPublishedEvent(BaseEventPayload):
    """Payload for ontology.published event."""
    
    ontology_name: str = Field(..., description="Published ontology name")
    version: str = Field(..., description="New version")
    previous_version: Optional[str] = Field(None, description="Previous version")
    changes_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of changes")
    published_by: str = Field(..., description="User who published")
    impact_analysis: Dict[str, Any] = Field(default_factory=dict, description="Impact analysis results")


class OntologyRollbackedEvent(BaseEventPayload):
    """Payload for ontology.rollbacked event."""
    
    ontology_name: str = Field(..., description="Rolled back ontology name")
    from_version: str = Field(..., description="Version rolled back from")
    to_version: str = Field(..., description="Version rolled back to")
    reason: str = Field(..., description="Rollback reason")
    rolled_back_by: str = Field(..., description="User who performed rollback")


# Audit Events

class AuditEventCreatedEvent(BaseEventPayload):
    """Payload for audit.event.created event."""
    
    audit_event_id: str = Field(..., description="Audit event ID")
    entity_type: str = Field(..., description="Type of entity audited")
    entity_id: str = Field(..., description="ID of entity audited")
    action: str = Field(..., description="Action performed")
    user_id: Optional[str] = Field(None, description="User who performed action")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    changes: Dict[str, Any] = Field(default_factory=dict, description="Changes made")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional audit metadata")


# Explanation Events

class ExplanationGeneratedEvent(BaseEventPayload):
    """Payload for explanation.generated event."""
    
    report_id: str = Field(..., description="Explanation report ID")
    case_id: str = Field(..., description="Associated case ID")
    format: str = Field(..., description="Report format")
    includes_image: bool = Field(..., description="Whether image analysis is included")
    includes_ehr: bool = Field(..., description="Whether EHR analysis is included")
    includes_graph: bool = Field(..., description="Whether graph context is included")
    guardrails_passed: bool = Field(..., description="Whether clinical guardrails passed")
    generation_time_seconds: float = Field(..., description="Generation time")


class ExplanationFailedEvent(BaseEventPayload):
    """Payload for explanation.failed event."""
    
    case_id: str = Field(..., description="Associated case ID")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    stage: Optional[str] = Field(None, description="Generation stage where failure occurred")
    guardrail_violations: List[str] = Field(default_factory=list, description="Guardrail violations if any")


# System Events

class ServiceStartedEvent(BaseEventPayload):
    """Payload for service.started event."""
    
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    startup_time_seconds: float = Field(..., description="Startup time")
    dependencies_healthy: bool = Field(..., description="Whether dependencies are healthy")


class ServiceStoppedEvent(BaseEventPayload):
    """Payload for service.stopped event."""
    
    service_name: str = Field(..., description="Service name")
    reason: str = Field(..., description="Shutdown reason")
    uptime_seconds: float = Field(..., description="Service uptime")
    graceful_shutdown: bool = Field(..., description="Whether shutdown was graceful")


class HealthCheckEvent(BaseEventPayload):
    """Payload for health check events."""
    
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency health status")
    response_time_ms: float = Field(..., description="Health check response time")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")
