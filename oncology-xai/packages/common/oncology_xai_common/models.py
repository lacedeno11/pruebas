# DERCAS-ONCO-XAI V1 - Shared Pydantic Models
# Common data models for the oncology platform

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from .schemas import (
    CaseStatus, JobStatus, PatternType, MutationType, MutationStatus,
    OntologyName, ImageFormat, EntityType, ArtifactType, ProposalStatus
)


class BaseOncologyModel(BaseModel):
    """Base model with common fields for all oncology models."""
    
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="User who created the record")
    updated_by: Optional[str] = Field(None, description="User who last updated the record")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Patient(BaseOncologyModel):
    """Patient model."""
    
    external_id: str = Field(..., description="External patient identifier")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Patient demographics")
    
    @validator('external_id')
    def validate_external_id(cls, v):
        if not v or not v.strip():
            raise ValueError('External ID cannot be empty')
        return v.strip()


class Case(BaseOncologyModel):
    """Clinical case model."""
    
    patient_id: str = Field(..., description="Associated patient ID")
    title: Optional[str] = Field(None, description="Case title")
    description: Optional[str] = Field(None, description="Case description")
    status: CaseStatus = Field(CaseStatus.CREATED, description="Case status")
    tags: List[str] = Field(default_factory=list, description="Case tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional case metadata")
    
    @validator('tags')
    def validate_tags(cls, v):
        return [tag.strip().lower() for tag in v if tag.strip()]


class Image(BaseOncologyModel):
    """Medical image model."""
    
    case_id: str = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Original filename")
    format: ImageFormat = Field(..., description="Image format")
    storage_uri: str = Field(..., description="Storage location URI")
    checksum: str = Field(..., description="File checksum (SHA-256)")
    size_bytes: int = Field(..., description="File size in bytes")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    stain: Optional[str] = Field(None, description="Staining method")
    magnification: Optional[str] = Field(None, description="Magnification level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional image metadata")
    
    @validator('size_bytes')
    def validate_size_bytes(cls, v):
        if v <= 0:
            raise ValueError('Size must be positive')
        return v
    
    @validator('checksum')
    def validate_checksum(cls, v):
        if not v or len(v) != 64:  # SHA-256 hex length
            raise ValueError('Invalid SHA-256 checksum')
        return v.lower()


class MLJob(BaseOncologyModel):
    """Machine learning job model."""
    
    case_id: Optional[str] = Field(None, description="Associated case ID")
    image_id: Optional[str] = Field(None, description="Associated image ID")
    ehr_id: Optional[str] = Field(None, description="Associated EHR ID")
    job_type: str = Field(..., description="Type of job")
    status: JobStatus = Field(JobStatus.PENDING, description="Job status")
    progress: float = Field(0.0, description="Job progress (0.0-1.0)")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    ended_at: Optional[datetime] = Field(None, description="Job end time")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_detail: Optional[str] = Field(None, description="Error details if failed")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Job parameters")
    results: Dict[str, Any] = Field(default_factory=dict, description="Job results")
    
    @validator('progress')
    def validate_progress(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Progress must be between 0.0 and 1.0')
        return v


class ResultBundle(BaseOncologyModel):
    """ML inference result bundle."""
    
    case_id: str = Field(..., description="Associated case ID")
    image_id: str = Field(..., description="Associated image ID")
    job_id: str = Field(..., description="Associated job ID")
    model_profile: str = Field(..., description="ML model profile used")
    model_version: str = Field(..., description="ML model version")
    thresholds: Dict[str, float] = Field(..., description="Confidence thresholds used")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Result summary")
    runtime_metrics: Dict[str, Any] = Field(default_factory=dict, description="Runtime performance metrics")


class PatternResult(BaseOncologyModel):
    """Histological pattern analysis result."""
    
    result_bundle_id: str = Field(..., description="Associated result bundle ID")
    pattern: PatternType = Field(..., description="Pattern type")
    score: float = Field(..., description="Confidence score")
    area_mm2: Optional[float] = Field(None, description="Pattern area in mm²")
    overlay_uri: Optional[str] = Field(None, description="Overlay image URI")
    heatmap_uri: Optional[str] = Field(None, description="Heatmap image URI")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score must be between 0.0 and 1.0')
        return v


class GeneticResult(BaseOncologyModel):
    """Genetic mutation analysis result."""
    
    result_bundle_id: str = Field(..., description="Associated result bundle ID")
    mutation: MutationType = Field(..., description="Mutation type")
    score: float = Field(..., description="Confidence score")
    status: MutationStatus = Field(..., description="Mutation status")
    evidence_uri: Optional[str] = Field(None, description="Evidence artifact URI")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score must be between 0.0 and 1.0')
        return v


class XAIArtifact(BaseOncologyModel):
    """Explainable AI artifact."""
    
    result_bundle_id: str = Field(..., description="Associated result bundle ID")
    artifact_type: ArtifactType = Field(..., description="Artifact type")
    uri: str = Field(..., description="Artifact storage URI")
    hash: str = Field(..., description="Artifact hash")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Artifact metadata")


class EHRDocument(BaseOncologyModel):
    """Electronic Health Record document."""
    
    case_id: str = Field(..., description="Associated case ID")
    version: int = Field(1, description="Document version")
    source: str = Field(..., description="Document source")
    content_uri: Optional[str] = Field(None, description="Content storage URI")
    content_text: Optional[str] = Field(None, description="Document text content")
    checksum: str = Field(..., description="Content checksum")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    
    @validator('version')
    def validate_version(cls, v):
        if v < 1:
            raise ValueError('Version must be positive')
        return v


class EHREntity(BaseOncologyModel):
    """Entity extracted from EHR."""
    
    ehr_id: str = Field(..., description="Associated EHR document ID")
    entity_text: str = Field(..., description="Entity text")
    entity_type: EntityType = Field(..., description="Entity type")
    start: int = Field(..., description="Start position in text")
    end: int = Field(..., description="End position in text")
    confidence: float = Field(..., description="Extraction confidence")
    section: Optional[str] = Field(None, description="Document section")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Extraction evidence")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    @validator('start', 'end')
    def validate_positions(cls, v):
        if v < 0:
            raise ValueError('Position must be non-negative')
        return v


class EHRMapping(BaseOncologyModel):
    """Ontology mapping for EHR entity."""
    
    ehr_entity_id: str = Field(..., description="Associated EHR entity ID")
    ontology: OntologyName = Field(..., description="Target ontology")
    iri: str = Field(..., description="Ontology concept IRI")
    label: str = Field(..., description="Concept label")
    confidence: float = Field(..., description="Mapping confidence")
    mapping_method: str = Field(..., description="Mapping method used")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Mapping evidence")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    @validator('iri')
    def validate_iri(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('IRI must be a valid HTTP(S) URL')
        return v


class CaseGraphSnapshot(BaseOncologyModel):
    """Case knowledge graph snapshot."""
    
    case_id: str = Field(..., description="Associated case ID")
    triplestore_graph_iri: str = Field(..., description="Triple store graph IRI")
    layout_json: Dict[str, Any] = Field(default_factory=dict, description="Graph layout data")
    ontology_versions: Dict[str, str] = Field(default_factory=dict, description="Ontology versions used")
    node_count: int = Field(0, description="Number of nodes")
    edge_count: int = Field(0, description="Number of edges")
    
    @validator('node_count', 'edge_count')
    def validate_counts(cls, v):
        if v < 0:
            raise ValueError('Count must be non-negative')
        return v


class ExplanationReport(BaseOncologyModel):
    """Explanation report for a case."""
    
    case_id: str = Field(..., description="Associated case ID")
    result_bundle_id: Optional[str] = Field(None, description="Associated result bundle ID")
    ehr_id: Optional[str] = Field(None, description="Associated EHR ID")
    graph_snapshot_id: Optional[str] = Field(None, description="Associated graph snapshot ID")
    report_uri: str = Field(..., description="Report storage URI")
    format: str = Field(..., description="Report format")
    llm_model: Optional[str] = Field(None, description="LLM model used")
    prompt_hash: Optional[str] = Field(None, description="Prompt hash for reproducibility")
    guardrails_passed: bool = Field(True, description="Whether clinical guardrails passed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Report metadata")


class OntologyVersion(BaseOncologyModel):
    """Ontology version record."""
    
    name: OntologyName = Field(..., description="Ontology name")
    version_tag: str = Field(..., description="Version identifier")
    source_uri: str = Field(..., description="Source URI")
    hash: str = Field(..., description="Content hash")
    imported_at: datetime = Field(default_factory=datetime.utcnow, description="Import timestamp")
    active: bool = Field(False, description="Whether this version is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Version metadata")


class OntologyUpdateProposal(BaseOncologyModel):
    """Ontology update proposal."""
    
    targets: List[OntologyName] = Field(..., description="Target ontologies")
    mode: str = Field(..., description="Update mode (online|offline)")
    status: ProposalStatus = Field(ProposalStatus.DRAFT, description="Proposal status")
    description: Optional[str] = Field(None, description="Proposal description")
    diff_report_uri: Optional[str] = Field(None, description="Diff report URI")
    impact_analysis: Dict[str, Any] = Field(default_factory=dict, description="Impact analysis")
    reasoner_report_uri: Optional[str] = Field(None, description="Reasoner report URI")
    approved_by: Optional[str] = Field(None, description="User who approved")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Proposal metadata")


class AuditEvent(BaseOncologyModel):
    """Audit event record."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    entity_type: str = Field(..., description="Type of entity affected")
    entity_id: str = Field(..., description="ID of entity affected")
    action: str = Field(..., description="Action performed")
    status: str = Field(..., description="Action status")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Utility models for API responses

class ImageUploadResponse(BaseModel):
    """Response for image upload."""
    
    image_id: str = Field(..., description="Image identifier")
    case_id: str = Field(..., description="Case identifier")
    format: ImageFormat = Field(..., description="Image format")
    storage_uri: str = Field(..., description="Storage URI")
    checksum: str = Field(..., description="File checksum")
    status: str = Field("STORED", description="Upload status")


class ViewerUrlResponse(BaseModel):
    """Response for viewer URL generation."""
    
    viewer_url: str = Field(..., description="Signed viewer URL")
    expires_at: datetime = Field(..., description="URL expiration time")


class ProcessingStatusResponse(BaseModel):
    """Response for processing status."""
    
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Processing status")
    progress: float = Field(..., description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class InferenceResultsResponse(BaseModel):
    """Response for inference results."""
    
    result_bundle_id: str = Field(..., description="Result bundle identifier")
    patterns: List[PatternResult] = Field(..., description="Pattern analysis results")
    mutations: List[GeneticResult] = Field(..., description="Genetic mutation results")
    xai_artifacts: List[XAIArtifact] = Field(..., description="XAI artifacts")
    model_info: Dict[str, Any] = Field(..., description="Model information")
    processing_time: float = Field(..., description="Processing time in seconds")
