"""Domain entity models for Oncology XAI."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from oncology_common.models.base import BaseModel


# Enums

class CaseStatus(str, Enum):
    """Case lifecycle status."""
    CREATED = "CREATED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    CLOSED = "CLOSED"


class ImageFormat(str, Enum):
    """Supported image formats."""
    PNG = "png"
    BIFF = "biff"


class PatternType(str, Enum):
    """Histological pattern types for lung adenocarcinoma."""
    LEPIDIC = "lepidic"
    ACINAR = "acinar"
    PAPILLARY = "papillary"
    MICROPAPILLARY = "micropapillary"
    SOLID = "solid"


class MutationType(str, Enum):
    """Genetic mutation types."""
    EGFR = "EGFR"
    KRAS = "KRAS"
    TP53 = "TP53"


class MutationStatus(str, Enum):
    """Mutation prediction status."""
    POSITIVE = "POS"
    NEGATIVE = "NEG"
    INCONCLUSIVE = "INCONCLUSIVE"


class JobStatus(str, Enum):
    """Async job status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    """Types of async jobs."""
    IMAGE_INFERENCE = "IMAGE_INFERENCE"
    EHR_EXTRACTION = "EHR_EXTRACTION"
    GRAPH_REBUILD = "GRAPH_REBUILD"
    ONTOLOGY_UPDATE = "ONTOLOGY_UPDATE"
    EXPLANATION_GENERATION = "EXPLANATION_GENERATION"


class ProposalStatus(str, Enum):
    """Ontology update proposal status."""
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    REQUIRES_FIX = "REQUIRES_FIX"
    ROLLED_BACK = "ROLLED_BACK"


# Patient Models

class PatientCreate(BaseModel):
    """Patient creation request."""
    external_id: str | None = None
    demographics: dict[str, Any] = Field(default_factory=dict)


class Patient(BaseModel):
    """Patient entity."""
    patient_id: UUID
    external_id: str | None = None
    demographics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None


# Case Models

class CaseCreate(BaseModel):
    """Case creation request."""
    patient_id: UUID
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Case(BaseModel):
    """Case entity."""
    case_id: UUID
    patient_id: UUID
    status: CaseStatus = CaseStatus.CREATED
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class CaseUpdate(BaseModel):
    """Case update request."""
    status: CaseStatus | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


# Image Models

class ImageCreate(BaseModel):
    """Image metadata for upload."""
    format: ImageFormat
    stain: str | None = None
    magnification: str | None = None
    notes: str | None = None


class Image(BaseModel):
    """Image entity."""
    image_id: UUID
    case_id: UUID
    format: ImageFormat
    storage_uri: str
    checksum: str
    size_bytes: int
    stain: str | None = None
    magnification: str | None = None
    notes: str | None = None
    uploaded_by: str | None = None
    uploaded_at: datetime


# ML Job Models

class MLJob(BaseModel):
    """ML processing job."""
    job_id: UUID
    case_id: UUID | None = None
    image_id: UUID | None = None
    ehr_id: UUID | None = None
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    error_code: str | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime


# Inference Result Models

class PatternResult(BaseModel):
    """Pattern segmentation result."""
    pattern: PatternType
    score: float = Field(..., ge=0.0, le=1.0)
    is_conclusive: bool = True
    overlay_uri: str | None = None
    heatmap_uri: str | None = None
    area_mm2: float | None = None


class GeneticResult(BaseModel):
    """Genetic mutation prediction result."""
    mutation: MutationType
    score: float = Field(..., ge=0.0, le=1.0)
    status: MutationStatus
    evidence_uri: str | None = None


class XAIArtifact(BaseModel):
    """Explainability artifact."""
    artifact_id: UUID
    artifact_type: str
    uri: str
    hash: str
    created_at: datetime


class ResultBundle(BaseModel):
    """Complete inference result bundle."""
    result_bundle_id: UUID
    case_id: UUID
    image_id: UUID
    job_id: UUID
    model_profile: str
    model_version: str
    thresholds: dict[str, float]
    pattern_results: list[PatternResult]
    genetic_results: list[GeneticResult]
    xai_artifacts: list[XAIArtifact] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ProcessImageRequest(BaseModel):
    """Request to process an image."""
    model_profile: str = "lung_patterns_v1"
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "lepidic": 0.55,
            "acinar": 0.55,
            "papillary": 0.55,
            "micropapillary": 0.55,
            "solid": 0.55,
            "EGFR": 0.60,
            "KRAS": 0.60,
            "TP53": 0.60,
        }
    )
    roi: dict[str, Any] | None = None
    tiles: bool = False


# EHR Models

class EHRIngestRequest(BaseModel):
    """EHR ingestion request."""
    source: str = "paste"  # paste, upload, fhir
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EHRDocument(BaseModel):
    """EHR document entity."""
    ehr_id: UUID
    case_id: UUID
    version: int = 1
    source: str
    content_uri: str | None = None
    content_text: str | None = None
    checksum: str
    created_by: str | None = None
    created_at: datetime


class EHREntity(BaseModel):
    """Extracted entity from EHR."""
    entity_id: UUID
    ehr_id: UUID
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    section: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class EHRMapping(BaseModel):
    """Entity mapping to ontology."""
    mapping_id: UUID
    entity_id: UUID
    ontology: str  # NCIt, MONDO, SO
    iri: str
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    mapping_method: str
    evidence: dict[str, Any] = Field(default_factory=dict)


# Graph Models

class GraphNode(BaseModel):
    """Graph node for visualization."""
    id: str
    label: str
    type: str
    iri: str | None = None
    source: str  # image, ehr, ontology, inferred
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Graph edge for visualization."""
    source: str
    target: str
    label: str
    type: str  # asserted, inferred
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    """Case graph snapshot for visualization."""
    graph_snapshot_id: UUID
    case_id: UUID
    triplestore_graph_iri: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    ontology_versions: dict[str, str]
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    layout: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# Explanation Models

class ExplanationReport(BaseModel):
    """Unified explanation report."""
    report_id: UUID
    case_id: UUID
    result_bundle_id: UUID | None = None
    ehr_id: UUID | None = None
    graph_snapshot_id: UUID | None = None
    report_uri: str
    format: str = "html"
    llm_model: str | None = None
    prompt_hash: str | None = None
    sections: dict[str, Any] = Field(default_factory=dict)
    guardrails_passed: bool = True
    guardrails_violations: list[str] = Field(default_factory=list)
    created_at: datetime


# Ontology Models

class OntologyVersion(BaseModel):
    """Ontology version entity."""
    ontology_version_id: UUID
    name: str  # NCIt, MONDO, SO
    version_tag: str
    source_uri: str
    hash: str
    is_active: bool = False
    imported_at: datetime


class UpdateProposal(BaseModel):
    """Ontology update proposal."""
    proposal_id: UUID
    targets: list[str]  # NCIt, MONDO, SO
    mode: str  # online, offline
    status: ProposalStatus = ProposalStatus.DRAFT
    diff_report_uri: str | None = None
    impact: dict[str, Any] = Field(default_factory=dict)
    reasoner_report_uri: str | None = None
    validation_results: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    approved_by: str | None = None
    created_at: datetime
    published_at: datetime | None = None


# Audit Models

class AuditEvent(BaseModel):
    """Audit event entity."""
    event_id: UUID
    timestamp: datetime
    user_id: str | None = None
    case_id: UUID | None = None
    entity_type: str
    entity_id: str
    action: str
    status: str = "SUCCESS"
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
