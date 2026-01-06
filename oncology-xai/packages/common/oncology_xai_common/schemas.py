# DERCAS-ONCO-XAI V1 - Standard Schemas
# Common response schemas and enums for the oncology platform

from typing import Optional, Dict, Any, List, Generic, TypeVar
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from .middleware import get_correlation_id

T = TypeVar('T')


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    errorCode: str = Field(..., description="Error code identifying the type of error")
    message: str = Field(..., description="Human-readable error message")
    correlationId: Optional[str] = Field(None, description="Request correlation ID for tracing")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    
    @classmethod
    def from_exception(cls, exc: Exception, correlation_id: Optional[str] = None) -> "ErrorResponse":
        """Create ErrorResponse from exception."""
        if not correlation_id:
            correlation_id = get_correlation_id()
        
        # Handle custom exceptions with error codes
        if hasattr(exc, 'error_code') and hasattr(exc, 'details'):
            return cls(
                errorCode=exc.error_code,
                message=str(exc),
                correlationId=correlation_id,
                details=exc.details
            )
        
        # Handle standard exceptions
        return cls(
            errorCode=exc.__class__.__name__.upper(),
            message=str(exc),
            correlationId=correlation_id,
            details={}
        )


class HealthResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency health status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-based)")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        """Create paginated response."""
        pages = (total + size - 1) // size  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


# Enums for the oncology domain

class JobStatus(str, Enum):
    """Status of background jobs."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CaseStatus(str, Enum):
    """Status of clinical cases."""
    CREATED = "CREATED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CLOSED = "CLOSED"


class PatternType(str, Enum):
    """Lung cancer histological patterns."""
    LEPIDIC = "lepidic"
    ACINAR = "acinar"
    PAPILLARY = "papillary"
    MICROPAPILLARY = "micropapillary"
    SOLID = "solid"


class MutationType(str, Enum):
    """Genetic mutations of interest."""
    EGFR = "EGFR"
    KRAS = "KRAS"
    TP53 = "TP53"


class MutationStatus(str, Enum):
    """Status of genetic mutation predictions."""
    POS = "POS"  # Positive
    NEG = "NEG"  # Negative
    INCONCLUSIVE = "INCONCLUSIVE"  # Inconclusive


class OntologyName(str, Enum):
    """Supported ontologies."""
    NCIT = "NCIt"  # National Cancer Institute Thesaurus
    MONDO = "MONDO"  # Monarch Disease Ontology
    SO = "SO"  # Sequence Ontology


class ImageFormat(str, Enum):
    """Supported image formats."""
    PNG = "png"
    BIFF = "biff"


class EntityType(str, Enum):
    """Types of entities extracted from EHR."""
    DIAGNOSIS = "DIAGNOSIS"
    PROCEDURE = "PROCEDURE"
    MEDICATION = "MEDICATION"
    ANATOMY = "ANATOMY"
    MUTATION = "MUTATION"
    PATTERN = "PATTERN"
    STAGE = "STAGE"
    GRADE = "GRADE"


class ArtifactType(str, Enum):
    """Types of XAI artifacts."""
    OVERLAY = "overlay"
    HEATMAP = "heatmap"
    SALIENCY = "saliency"
    ATTENTION = "attention"
    GRADCAM = "gradcam"


class ProposalStatus(str, Enum):
    """Status of ontology update proposals."""
    DRAFT = "DRAFT"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    ROLLBACK_COMPLETED = "ROLLBACK_COMPLETED"


class EventType(str, Enum):
    """Types of system events."""
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


# Request/Response schemas

class CreatePatientRequest(BaseModel):
    """Request schema for creating a patient."""
    external_id: str = Field(..., description="External patient identifier")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Patient demographics")


class CreateCaseRequest(BaseModel):
    """Request schema for creating a case."""
    patient_id: str = Field(..., description="Patient identifier")
    title: Optional[str] = Field(None, description="Case title")
    description: Optional[str] = Field(None, description="Case description")
    tags: List[str] = Field(default_factory=list, description="Case tags")


class UpdateCaseRequest(BaseModel):
    """Request schema for updating a case."""
    status: Optional[CaseStatus] = Field(None, description="Case status")
    title: Optional[str] = Field(None, description="Case title")
    description: Optional[str] = Field(None, description="Case description")
    tags: Optional[List[str]] = Field(None, description="Case tags")


class ProcessImageRequest(BaseModel):
    """Request schema for processing an image."""
    model_profile: str = Field("lung_patterns_v3", description="ML model profile to use")
    thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "lepidic": 0.55,
            "acinar": 0.55,
            "papillary": 0.55,
            "micropapillary": 0.55,
            "solid": 0.55,
            "EGFR": 0.6,
            "KRAS": 0.6,
            "TP53": 0.6
        },
        description="Confidence thresholds for patterns and mutations"
    )
    roi: Optional[Dict[str, Any]] = Field(None, description="Region of interest coordinates")


class IngestEHRRequest(BaseModel):
    """Request schema for ingesting EHR."""
    source: str = Field(..., description="EHR source (paste|upload|fhir)")
    content: str = Field(..., description="EHR content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="EHR metadata")


class ExtractAndMapRequest(BaseModel):
    """Request schema for EHR extraction and mapping."""
    ontologies: List[OntologyName] = Field(
        default=[OntologyName.NCIT, OntologyName.MONDO, OntologyName.SO],
        description="Ontologies to map to"
    )
    extract_entities: bool = Field(True, description="Whether to extract entities")
    map_to_ontologies: bool = Field(True, description="Whether to map to ontologies")


class CreateOntologyProposalRequest(BaseModel):
    """Request schema for creating ontology update proposal."""
    targets: List[OntologyName] = Field(..., description="Target ontologies to update")
    mode: str = Field("offline", description="Update mode (online|offline)")
    sources_policy_id: Optional[str] = Field(None, description="Sources policy identifier")
    description: Optional[str] = Field(None, description="Proposal description")


class GenerateExplanationRequest(BaseModel):
    """Request schema for generating explanation."""
    include_image_results: bool = Field(True, description="Include image analysis results")
    include_ehr_findings: bool = Field(True, description="Include EHR findings")
    include_graph_context: bool = Field(True, description="Include graph context")
    format: str = Field("html", description="Output format (html|pdf)")
    template: Optional[str] = Field(None, description="Report template to use")


# Response schemas

class JobResponse(BaseModel):
    """Response schema for job creation."""
    job_id: str = Field(..., description="Job identifier")
    type: str = Field(..., description="Job type")
    status: JobStatus = Field(..., description="Job status")
    progress: float = Field(0.0, description="Job progress (0.0-1.0)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation time")


class PatternResultResponse(BaseModel):
    """Response schema for pattern analysis results."""
    pattern: PatternType = Field(..., description="Pattern type")
    score: float = Field(..., description="Confidence score")
    area_mm2: Optional[float] = Field(None, description="Pattern area in mm²")
    overlay_uri: Optional[str] = Field(None, description="Overlay image URI")
    heatmap_uri: Optional[str] = Field(None, description="Heatmap image URI")


class GeneticResultResponse(BaseModel):
    """Response schema for genetic mutation results."""
    mutation: MutationType = Field(..., description="Mutation type")
    score: float = Field(..., description="Confidence score")
    status: MutationStatus = Field(..., description="Mutation status")
    evidence_uri: Optional[str] = Field(None, description="Evidence artifact URI")


class EntityResponse(BaseModel):
    """Response schema for extracted entities."""
    text: str = Field(..., description="Entity text")
    type: EntityType = Field(..., description="Entity type")
    start: int = Field(..., description="Start position in text")
    end: int = Field(..., description="End position in text")
    confidence: float = Field(..., description="Extraction confidence")
    section: Optional[str] = Field(None, description="Document section")


class MappingResponse(BaseModel):
    """Response schema for ontology mappings."""
    entity_id: str = Field(..., description="Entity identifier")
    ontology: OntologyName = Field(..., description="Target ontology")
    iri: str = Field(..., description="Ontology concept IRI")
    label: str = Field(..., description="Concept label")
    confidence: float = Field(..., description="Mapping confidence")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Mapping evidence")


class GraphNodeResponse(BaseModel):
    """Response schema for graph nodes."""
    id: str = Field(..., description="Node identifier")
    label: str = Field(..., description="Node label")
    type: str = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Node provenance")


class GraphEdgeResponse(BaseModel):
    """Response schema for graph edges."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str = Field(..., description="Edge label")
    type: str = Field(..., description="Edge type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Edge provenance")


class GraphResponse(BaseModel):
    """Response schema for case graphs."""
    nodes: List[GraphNodeResponse] = Field(..., description="Graph nodes")
    edges: List[GraphEdgeResponse] = Field(..., description="Graph edges")
    ontology_versions: Dict[str, str] = Field(default_factory=dict, description="Ontology versions used")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Graph creation time")
