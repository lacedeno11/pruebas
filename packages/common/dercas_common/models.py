"""
DERCAS-ONCO-XAI Pydantic Models

Core data models shared across all microservices.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


# =============================================================================
# ENUMS
# =============================================================================

class CaseStatus(str, Enum):
    """Case status enumeration."""
    CREATED = "CREATED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CLOSED = "CLOSED"


class PatternType(str, Enum):
    """Histological pattern types for lung cancer."""
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


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    """Job type enumeration."""
    IMAGE_INFERENCE = "IMAGE_INFERENCE"
    EHR_EXTRACTION = "EHR_EXTRACTION"
    GRAPH_REBUILD = "GRAPH_REBUILD"
    ONTOLOGY_UPDATE = "ONTOLOGY_UPDATE"
    EXPLANATION_GENERATION = "EXPLANATION_GENERATION"


class MutationStatus(str, Enum):
    """Mutation prediction status."""
    POSITIVE = "POS"
    NEGATIVE = "NEG"
    INCONCLUSIVE = "INCONCLUSIVE"


# =============================================================================
# BASE MODELS
# =============================================================================

class BaseEntity(BaseModel):
    """Base entity with common fields."""
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class TimestampedEntity(BaseModel):
    """Entity with timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# CORE DOMAIN MODELS
# =============================================================================

class Patient(BaseEntity):
    """Patient model."""
    external_id: str = Field(..., description="External patient identifier")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Patient demographics (anonymized)")
    
    @validator('external_id')
    def validate_external_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('External ID cannot be empty')
        return v.strip()


class Case(BaseEntity):
    """Clinical case model."""
    patient_id: UUID = Field(..., description="Associated patient ID")
    status: CaseStatus = Field(default=CaseStatus.CREATED, description="Case status")
    tags: List[str] = Field(default_factory=list, description="Case tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Case metadata")
    created_by: str = Field(..., description="User who created the case")


class Image(BaseEntity):
    """Histopathological image model."""
    case_id: UUID = Field(..., description="Associated case ID")
    format: str = Field(..., description="Image format (png, biff)")
    storage_uri: str = Field(..., description="Storage URI")
    checksum: str = Field(..., description="SHA256 checksum")
    size_bytes: int = Field(..., description="File size in bytes")
    stain: Optional[str] = Field(None, description="Staining method")
    magnification: Optional[str] = Field(None, description="Magnification level")
    uploaded_by: str = Field(..., description="User who uploaded the image")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['png', 'biff']
        if v.lower() not in allowed_formats:
            raise ValueError(f'Format must be one of: {allowed_formats}')
        return v.lower()


class MLJob(BaseEntity):
    """Machine learning job model."""
    case_id: Optional[UUID] = Field(None, description="Associated case ID")
    image_id: Optional[UUID] = Field(None, description="Associated image ID")
    ehr_id: Optional[UUID] = Field(None, description="Associated EHR ID")
    job_type: JobType = Field(..., description="Job type")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    progress: float = Field(default=0.0, description="Job progress (0.0-1.0)")
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")


class PatternResult(BaseEntity):
    """Pattern analysis result."""
    result_bundle_id: UUID = Field(..., description="Associated result bundle ID")
    pattern: PatternType = Field(..., description="Pattern type")
    score: float = Field(..., description="Confidence score (0.0-1.0)")
    area_mm2: Optional[float] = Field(None, description="Pattern area in mm²")
    overlay_uri: Optional[str] = Field(None, description="Overlay image URI")
    heatmap_uri: Optional[str] = Field(None, description="Heatmap image URI")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score must be between 0.0 and 1.0')
        return v


class GeneticResult(BaseEntity):
    """Genetic mutation result."""
    result_bundle_id: UUID = Field(..., description="Associated result bundle ID")
    mutation: MutationType = Field(..., description="Mutation type")
    score: float = Field(..., description="Confidence score (0.0-1.0)")
    status: MutationStatus = Field(..., description="Mutation status")
    evidence_uri: Optional[str] = Field(None, description="Evidence artifact URI")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score must be between 0.0 and 1.0')
        return v


class XAIArtifact(BaseEntity):
    """Explainable AI artifact."""
    result_bundle_id: UUID = Field(..., description="Associated result bundle ID")
    artifact_type: str = Field(..., description="Artifact type (gradcam, saliency, etc.)")
    uri: str = Field(..., description="Artifact URI")
    hash: str = Field(..., description="Artifact hash")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Artifact metadata")


class ResultBundle(BaseEntity):
    """ML inference result bundle."""
    case_id: UUID = Field(..., description="Associated case ID")
    image_id: UUID = Field(..., description="Associated image ID")
    job_id: UUID = Field(..., description="Associated job ID")
    model_profile: str = Field(..., description="Model profile used")
    model_version: str = Field(..., description="Model version")
    thresholds: Dict[str, float] = Field(..., description="Thresholds used")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Result summary")
    pattern_results: List[PatternResult] = Field(default_factory=list)
    genetic_results: List[GeneticResult] = Field(default_factory=list)
    xai_artifacts: List[XAIArtifact] = Field(default_factory=list)


class EHRDocument(BaseEntity):
    """Electronic Health Record document."""
    case_id: UUID = Field(..., description="Associated case ID")
    version: int = Field(default=1, description="Document version")
    source: str = Field(..., description="Document source (paste, upload, fhir)")
    content_uri: Optional[str] = Field(None, description="Content storage URI")
    content_text: Optional[str] = Field(None, description="Direct text content")
    checksum: str = Field(..., description="Content checksum")
    created_by: str = Field(..., description="User who created the document")
    
    @validator('source')
    def validate_source(cls, v):
        allowed_sources = ['paste', 'upload', 'fhir']
        if v not in allowed_sources:
            raise ValueError(f'Source must be one of: {allowed_sources}')
        return v


class EHREntity(BaseEntity):
    """Extracted entity from EHR."""
    ehr_id: UUID = Field(..., description="Associated EHR document ID")
    entity_text: str = Field(..., description="Entity text")
    entity_type: str = Field(..., description="Entity type")
    start: int = Field(..., description="Start position in text")
    end: int = Field(..., description="End position in text")
    confidence: float = Field(..., description="Extraction confidence")
    section: Optional[str] = Field(None, description="Document section")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Evidence metadata")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class EHRMapping(BaseEntity):
    """EHR entity to ontology mapping."""
    ehr_entity_id: UUID = Field(..., description="Associated EHR entity ID")
    ontology: str = Field(..., description="Ontology name (NCIt, MONDO, SO)")
    iri: str = Field(..., description="Ontology IRI")
    label: str = Field(..., description="Ontology label")
    confidence: float = Field(..., description="Mapping confidence")
    mapping_method: str = Field(..., description="Mapping method used")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Mapping evidence")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    @validator('ontology')
    def validate_ontology(cls, v):
        allowed_ontologies = ['NCIt', 'MONDO', 'SO']
        if v not in allowed_ontologies:
            raise ValueError(f'Ontology must be one of: {allowed_ontologies}')
        return v


class CaseGraphSnapshot(BaseEntity):
    """Case knowledge graph snapshot."""
    case_id: UUID = Field(..., description="Associated case ID")
    triplestore_graph_iri: str = Field(..., description="Triple store graph IRI")
    layout: Dict[str, Any] = Field(default_factory=dict, description="Graph layout for visualization")
    ontology_versions: Dict[str, str] = Field(default_factory=dict, description="Ontology versions used")
    nodes_count: int = Field(default=0, description="Number of nodes")
    edges_count: int = Field(default=0, description="Number of edges")


class ExplanationReport(BaseEntity):
    """Unified explanation report."""
    case_id: UUID = Field(..., description="Associated case ID")
    result_bundle_id: Optional[UUID] = Field(None, description="Associated result bundle ID")
    ehr_id: Optional[UUID] = Field(None, description="Associated EHR ID")
    graph_snapshot_id: Optional[UUID] = Field(None, description="Associated graph snapshot ID")
    report_uri: str = Field(..., description="Report storage URI")
    format: str = Field(default="html", description="Report format")
    llm_model: Optional[str] = Field(None, description="LLM model used")
    prompt_hash: Optional[str] = Field(None, description="Prompt hash for reproducibility")
    guardrails_passed: bool = Field(default=True, description="Clinical guardrails validation")


class OntologyVersion(BaseEntity):
    """Ontology version tracking."""
    name: str = Field(..., description="Ontology name (NCIt, MONDO, SO)")
    version_tag: str = Field(..., description="Version tag")
    source_uri: str = Field(..., description="Source URI")
    hash: str = Field(..., description="Content hash")
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False, description="Is this the active version")
    
    @validator('name')
    def validate_name(cls, v):
        allowed_names = ['NCIt', 'MONDO', 'SO']
        if v not in allowed_names:
            raise ValueError(f'Name must be one of: {allowed_names}')
        return v


class OntologyUpdateProposal(BaseEntity):
    """Ontology update proposal."""
    targets: List[str] = Field(..., description="Target ontologies")
    mode: str = Field(..., description="Update mode (online, offline)")
    status: str = Field(default="PENDING", description="Proposal status")
    diff_report_uri: Optional[str] = Field(None, description="Diff report URI")
    impact: Dict[str, Any] = Field(default_factory=dict, description="Impact analysis")
    reasoner_report_uri: Optional[str] = Field(None, description="Reasoner report URI")
    created_by: str = Field(..., description="User who created the proposal")
    approved_by: Optional[str] = Field(None, description="User who approved the proposal")
    published_at: Optional[datetime] = None
    
    @validator('mode')
    def validate_mode(cls, v):
        allowed_modes = ['online', 'offline']
        if v not in allowed_modes:
            raise ValueError(f'Mode must be one of: {allowed_modes}')
        return v


class AuditEvent(BaseEntity):
    """Audit event for compliance tracking."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(None, description="User ID")
    case_id: Optional[UUID] = Field(None, description="Associated case ID")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")
    action: str = Field(..., description="Action performed")
    status: str = Field(..., description="Action status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    correlation_id: str = Field(..., description="Correlation ID for tracing")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="0.1.0")
    service: str = Field(..., description="Service name")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any] = Field(..., description="Response items")
    total: int = Field(..., description="Total items count")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")
    
    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        total = values.get('total', 0)
        size = values.get('size', 20)
        return (total + size - 1) // size if total > 0 else 0
