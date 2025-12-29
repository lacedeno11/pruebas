"""Event type definitions and payloads."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Standard event types."""

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


# Payload models


class CaseCreatedPayload(BaseModel):
    """Payload for case.created event."""

    case_id: str
    patient_id: str
    created_by: str | None = None


class CaseUpdatedPayload(BaseModel):
    """Payload for case.updated event."""

    case_id: str
    status: str
    updated_by: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)


class ImageUploadedPayload(BaseModel):
    """Payload for image.uploaded event."""

    image_id: str
    case_id: str
    format: str
    storage_uri: str
    checksum: str
    size_bytes: int


class ImageDeletedPayload(BaseModel):
    """Payload for image.deleted event."""

    image_id: str
    case_id: str
    deleted_by: str | None = None


class JobCreatedPayload(BaseModel):
    """Payload for job.created event."""

    job_id: str
    job_type: str
    image_id: str | None = None
    ehr_id: str | None = None


class JobProgressPayload(BaseModel):
    """Payload for job.progress event."""

    job_id: str
    progress: float
    message: str | None = None


class JobCompletedPayload(BaseModel):
    """Payload for job.completed event."""

    job_id: str
    job_type: str
    result_id: str | None = None
    duration_seconds: float | None = None


class JobFailedPayload(BaseModel):
    """Payload for job.failed event."""

    job_id: str
    job_type: str
    error_code: str
    error_message: str


class InferenceCompletedPayload(BaseModel):
    """Payload for inference.completed event."""

    result_bundle_id: str
    image_id: str
    model_profile: str
    model_version: str
    summary: dict[str, Any] = Field(default_factory=dict)


class EHRIngestedPayload(BaseModel):
    """Payload for ehr.ingested event."""

    ehr_id: str
    case_id: str
    version: int
    source: str


class EHRExtractedPayload(BaseModel):
    """Payload for ehr.extracted event."""

    ehr_id: str
    entity_count: int
    entity_types: list[str] = Field(default_factory=list)


class EHRMappedPayload(BaseModel):
    """Payload for ehr.mapped event."""

    ehr_id: str
    mapping_count: int
    ontologies: list[str] = Field(default_factory=list)
    has_conflicts: bool = False


class GraphBuiltPayload(BaseModel):
    """Payload for graph.built event."""

    graph_snapshot_id: str
    case_id: str
    node_count: int
    edge_count: int
    ontology_versions: dict[str, str] = Field(default_factory=dict)


class OntologyPublishedPayload(BaseModel):
    """Payload for ontology.published event."""

    proposal_id: str
    ontology_name: str
    version_tag: str
    previous_version: str | None = None
