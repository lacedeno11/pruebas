"""
DERCAS-ONCO-XAI Event Definitions

Specific event payload schemas for type safety and validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# CASE EVENTS
# =============================================================================

class CaseCreatedEvent(BaseModel):
    """Case created event payload."""
    case_id: UUID
    patient_id: UUID
    status: str = "CREATED"
    created_by: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseUpdatedEvent(BaseModel):
    """Case updated event payload."""
    case_id: UUID
    changes: Dict[str, Any]
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    updated_by: str


# =============================================================================
# IMAGE EVENTS
# =============================================================================

class ImageUploadedEvent(BaseModel):
    """Image uploaded event payload."""
    image_id: UUID
    case_id: UUID
    format: str
    size_bytes: int
    checksum: str
    storage_uri: str
    uploaded_by: str
    stain: Optional[str] = None
    magnification: Optional[str] = None


class ImageDeletedEvent(BaseModel):
    """Image deleted event payload."""
    image_id: UUID
    case_id: UUID
    deleted_by: str
    reason: Optional[str] = None


# =============================================================================
# JOB EVENTS
# =============================================================================

class JobCreatedEvent(BaseModel):
    """Job created event payload."""
    job_id: UUID
    job_type: str
    case_id: Optional[UUID] = None
    image_id: Optional[UUID] = None
    ehr_id: Optional[UUID] = None
    created_by: str
    priority: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobProgressEvent(BaseModel):
    """Job progress event payload."""
    job_id: UUID
    job_type: str
    progress: float  # 0.0 to 1.0
    status: str
    message: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class JobCompletedEvent(BaseModel):
    """Job completed event payload."""
    job_id: UUID
    job_type: str
    case_id: Optional[UUID] = None
    result: Dict[str, Any]
    duration_seconds: float
    resources_used: Dict[str, Any] = Field(default_factory=dict)


class JobFailedEvent(BaseModel):
    """Job failed event payload."""
    job_id: UUID
    job_type: str
    case_id: Optional[UUID] = None
    error_code: str
    error_message: str
    error_details: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    can_retry: bool = True


# =============================================================================
# INFERENCE EVENTS
# =============================================================================

class InferenceCompletedEvent(BaseModel):
    """Inference completed event payload."""
    result_bundle_id: UUID
    image_id: UUID
    case_id: UUID
    job_id: UUID
    model_profile: str
    model_version: str
    summary: Dict[str, Any]
    pattern_results: List[Dict[str, Any]] = Field(default_factory=list)
    genetic_results: List[Dict[str, Any]] = Field(default_factory=list)
    xai_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_seconds: float
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class InferenceFailedEvent(BaseModel):
    """Inference failed event payload."""
    job_id: UUID
    image_id: UUID
    case_id: UUID
    model_profile: str
    error_code: str
    error_message: str
    error_details: Dict[str, Any] = Field(default_factory=dict)
    partial_results: Optional[Dict[str, Any]] = None


# =============================================================================
# EHR EVENTS
# =============================================================================

class EHRIngestedEvent(BaseModel):
    """EHR ingested event payload."""
    ehr_id: UUID
    case_id: UUID
    version: int
    source: str  # paste, upload, fhir
    content_size: int
    checksum: str
    created_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EHRExtractedEvent(BaseModel):
    """EHR extracted event payload."""
    ehr_id: UUID
    case_id: UUID
    job_id: UUID
    entities_count: int
    extraction_method: str
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    processing_time_seconds: float


class EHRMappedEvent(BaseModel):
    """EHR mapped event payload."""
    ehr_id: UUID
    case_id: UUID
    job_id: UUID
    mappings_count: int
    ontologies_used: List[str]
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list)
    mapping_confidence: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# GRAPH EVENTS
# =============================================================================

class GraphBuiltEvent(BaseModel):
    """Graph built event payload."""
    graph_snapshot_id: UUID
    case_id: UUID
    job_id: UUID
    nodes_count: int
    edges_count: int
    ontology_versions: Dict[str, str]
    processing_time_seconds: float
    triplestore_graph_iri: str


class GraphFailedEvent(BaseModel):
    """Graph build failed event payload."""
    case_id: UUID
    job_id: UUID
    error_code: str
    error_message: str
    error_details: Dict[str, Any] = Field(default_factory=dict)
    partial_graph_available: bool = False


# =============================================================================
# ONTOLOGY EVENTS
# =============================================================================

class OntologyProposalCreatedEvent(BaseModel):
    """Ontology proposal created event payload."""
    proposal_id: UUID
    targets: List[str]  # NCIt, MONDO, SO
    mode: str  # online, offline
    created_by: str
    source_urls: List[str] = Field(default_factory=list)
    estimated_impact: Dict[str, Any] = Field(default_factory=dict)


class OntologyPublishedEvent(BaseModel):
    """Ontology published event payload."""
    proposal_id: UUID
    ontology_name: str
    version_tag: str
    previous_version: Optional[str] = None
    source_uri: str
    hash: str
    published_by: str
    changes_summary: Dict[str, Any] = Field(default_factory=dict)
    impact_analysis: Dict[str, Any] = Field(default_factory=dict)


class OntologyRollbackedEvent(BaseModel):
    """Ontology rollbacked event payload."""
    proposal_id: UUID
    ontology_name: str
    rolled_back_version: str
    restored_version: str
    rollback_reason: str
    rolled_back_by: str
    affected_cases: List[UUID] = Field(default_factory=list)


# =============================================================================
# EXPLANATION EVENTS
# =============================================================================

class ExplanationRequestedEvent(BaseModel):
    """Explanation requested event payload."""
    case_id: UUID
    job_id: UUID
    requested_by: str
    include_image_analysis: bool = True
    include_ehr_analysis: bool = True
    include_graph_analysis: bool = True
    format: str = "html"  # html, pdf, json
    template: Optional[str] = None


class ExplanationGeneratedEvent(BaseModel):
    """Explanation generated event payload."""
    report_id: UUID
    case_id: UUID
    job_id: UUID
    result_bundle_id: Optional[UUID] = None
    ehr_id: Optional[UUID] = None
    graph_snapshot_id: Optional[UUID] = None
    report_uri: str
    format: str
    llm_model: Optional[str] = None
    guardrails_passed: bool
    processing_time_seconds: float


class ExplanationFailedEvent(BaseModel):
    """Explanation generation failed event payload."""
    case_id: UUID
    job_id: UUID
    error_code: str
    error_message: str
    guardrails_violations: List[str] = Field(default_factory=list)
    partial_report_available: bool = False


# =============================================================================
# AUDIT EVENTS
# =============================================================================

class AuditEventCreatedEvent(BaseModel):
    """Audit event created event payload."""
    audit_event_id: UUID
    entity_type: str
    entity_id: str
    action: str
    status: str
    user_id: Optional[str] = None
    case_id: Optional[UUID] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# =============================================================================
# SYSTEM EVENTS
# =============================================================================

class ServiceStartedEvent(BaseModel):
    """Service started event payload."""
    service_name: str
    version: str
    instance_id: str
    startup_time_seconds: float
    configuration: Dict[str, Any] = Field(default_factory=dict)


class ServiceStoppedEvent(BaseModel):
    """Service stopped event payload."""
    service_name: str
    instance_id: str
    shutdown_reason: str
    uptime_seconds: float
    final_stats: Dict[str, Any] = Field(default_factory=dict)


class HealthCheckEvent(BaseModel):
    """Health check event payload."""
    service_name: str
    instance_id: str
    status: str  # healthy, unhealthy, degraded
    checks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    response_time_ms: float


# =============================================================================
# CONFLICT DETECTION EVENTS
# =============================================================================

class ConflictDetectedEvent(BaseModel):
    """Conflict detected event payload."""
    case_id: UUID
    conflict_type: str  # ehr_vs_image, model_disagreement, etc.
    entities_involved: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    resolution_required: bool = True
    severity: str = "medium"  # low, medium, high, critical
    details: Dict[str, Any] = Field(default_factory=dict)


class ConflictResolvedEvent(BaseModel):
    """Conflict resolved event payload."""
    case_id: UUID
    conflict_id: UUID
    resolution_method: str  # manual, automatic, escalated
    resolved_by: Optional[str] = None
    resolution_details: Dict[str, Any] = Field(default_factory=dict)
    final_decision: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# HITL (Human-in-the-Loop) EVENTS
# =============================================================================

class HITLReviewRequestedEvent(BaseModel):
    """HITL review requested event payload."""
    case_id: UUID
    review_type: str  # low_confidence, conflict, quality_check
    entity_type: str  # inference_result, ehr_mapping, explanation
    entity_id: UUID
    reason: str
    priority: str = "normal"  # low, normal, high, urgent
    assigned_to: Optional[str] = None
    deadline: Optional[datetime] = None


class HITLReviewCompletedEvent(BaseModel):
    """HITL review completed event payload."""
    case_id: UUID
    review_id: UUID
    entity_type: str
    entity_id: UUID
    reviewed_by: str
    decision: str  # approved, rejected, modified
    comments: Optional[str] = None
    modifications: Dict[str, Any] = Field(default_factory=dict)
    review_time_seconds: float


# =============================================================================
# PERFORMANCE MONITORING EVENTS
# =============================================================================

class PerformanceMetricEvent(BaseModel):
    """Performance metric event payload."""
    service_name: str
    metric_name: str
    metric_value: float
    metric_unit: str
    tags: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResourceUsageEvent(BaseModel):
    """Resource usage event payload."""
    service_name: str
    instance_id: str
    cpu_percent: float
    memory_mb: float
    disk_usage_mb: float
    network_io_mb: float
    active_connections: int
    queue_size: int = 0
