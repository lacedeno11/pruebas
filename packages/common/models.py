"""
DERCAS-ONCO-XAI V1 - Common Data Models

Pydantic v2 models for the oncology platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class CaseStatus(str, Enum):
    """Case processing status enumeration."""
    CREATED = "CREATED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CLOSED = "CLOSED"


class JobStatus(str, Enum):
    """Job processing status enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class HistologicalPattern(str, Enum):
    """Histological pattern types for lung adenocarcinoma."""
    LEPIDIC = "lepidic"
    ACINAR = "acinar"
    PAPILLARY = "papillary"
    MICROPAPILLARY = "micropapillary"
    SOLID = "solid"


class GeneticMutation(str, Enum):
    """Genetic mutation types."""
    EGFR = "EGFR"
    KRAS = "KRAS"
    TP53 = "TP53"


class ConfidenceLevel(str, Enum):
    """Confidence level for AI predictions."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INCONCLUSIVE = "INCONCLUSIVE"


# Base Models
class BaseEntity(BaseModel):
    """Base entity with common fields."""
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class Patient(BaseEntity):
    """Patient data model."""
    patient_id: str = Field(..., description="External patient identifier", min_length=1, max_length=100)
    age: Optional[int] = Field(None, description="Patient age", ge=0, le=150)
    gender: Optional[str] = Field(None, description="Patient gender", max_length=20)
    medical_record_number: Optional[str] = Field(None, description="Medical record number", max_length=100)
    
    # Clinical metadata
    diagnosis_date: Optional[datetime] = Field(None, description="Initial diagnosis date")
    primary_site: Optional[str] = Field(None, description="Primary tumor site", max_length=200)
    histology: Optional[str] = Field(None, description="Histological type", max_length=200)
    stage: Optional[str] = Field(None, description="Cancer stage", max_length=50)


class Case(BaseEntity):
    """Case data model."""
    case_id: str = Field(..., description="External case identifier", min_length=1, max_length=100)
    patient_id: UUID = Field(..., description="Associated patient ID")
    status: CaseStatus = Field(default=CaseStatus.CREATED, description="Case processing status")
    
    # Case metadata
    title: Optional[str] = Field(None, description="Case title", max_length=200)
    description: Optional[str] = Field(None, description="Case description", max_length=1000)
    priority: int = Field(default=1, description="Case priority", ge=1, le=5)
    
    # Clinical context
    clinical_context: Optional[Dict[str, Any]] = Field(default=None, description="Additional clinical context")
    assigned_to: Optional[str] = Field(None, description="Assigned clinician", max_length=100)
    
    # Processing metadata
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    review_required_reason: Optional[str] = Field(None, description="Reason for review requirement", max_length=500)


class Image(BaseEntity):
    """Image data model."""
    image_id: str = Field(..., description="External image identifier", min_length=1, max_length=100)
    case_id: UUID = Field(..., description="Associated case ID")
    
    # File metadata
    filename: str = Field(..., description="Original filename", max_length=255)
    file_size: int = Field(..., description="File size in bytes", gt=0)
    file_format: str = Field(..., description="File format (png, tiff)", max_length=10)
    checksum: str = Field(..., description="File checksum (SHA-256)", min_length=64, max_length=64)
    
    # Storage metadata
    storage_path: str = Field(..., description="Storage path/key", max_length=500)
    storage_bucket: str = Field(..., description="Storage bucket name", max_length=100)
    
    # Image metadata
    width: Optional[int] = Field(None, description="Image width in pixels", gt=0)
    height: Optional[int] = Field(None, description="Image height in pixels", gt=0)
    channels: Optional[int] = Field(None, description="Number of channels", gt=0)
    bit_depth: Optional[int] = Field(None, description="Bit depth", gt=0)
    
    # Acquisition metadata
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition date")
    modality: Optional[str] = Field(None, description="Imaging modality", max_length=50)
    magnification: Optional[float] = Field(None, description="Magnification level", gt=0)
    staining: Optional[str] = Field(None, description="Staining method", max_length=100)


class PatternResult(BaseModel):
    """Histological pattern analysis result."""
    model_config = ConfigDict(use_enum_values=True)
    
    pattern: HistologicalPattern = Field(..., description="Detected pattern")
    confidence_score: float = Field(..., description="Confidence score", ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level")
    percentage: float = Field(..., description="Pattern percentage", ge=0.0, le=100.0)
    
    # Model metadata
    model_name: str = Field(..., description="Model name", max_length=100)
    model_version: str = Field(..., description="Model version", max_length=50)
    threshold: float = Field(..., description="Confidence threshold used", ge=0.0, le=1.0)


class GeneticResult(BaseModel):
    """Genetic mutation analysis result."""
    model_config = ConfigDict(use_enum_values=True)
    
    mutation: GeneticMutation = Field(..., description="Detected mutation")
    confidence_score: float = Field(..., description="Confidence score", ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level")
    mutation_status: str = Field(..., description="Mutation status (positive/negative/uncertain)", max_length=20)
    
    # Additional mutation details
    variant_details: Optional[Dict[str, Any]] = Field(default=None, description="Variant-specific details")
    allele_frequency: Optional[float] = Field(None, description="Allele frequency", ge=0.0, le=1.0)
    
    # Model metadata
    model_name: str = Field(..., description="Model name", max_length=100)
    model_version: str = Field(..., description="Model version", max_length=50)
    threshold: float = Field(..., description="Confidence threshold used", ge=0.0, le=1.0)


class XAIArtifact(BaseModel):
    """Explainable AI artifact."""
    artifact_type: str = Field(..., description="Artifact type (heatmap, attention, etc.)", max_length=50)
    artifact_path: str = Field(..., description="Storage path for artifact", max_length=500)
    artifact_format: str = Field(..., description="Artifact format (png, json, etc.)", max_length=10)
    description: Optional[str] = Field(None, description="Artifact description", max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ResultBundle(BaseEntity):
    """Complete analysis result bundle."""
    result_bundle_id: str = Field(..., description="External result bundle identifier", min_length=1, max_length=100)
    image_id: UUID = Field(..., description="Associated image ID")
    case_id: UUID = Field(..., description="Associated case ID")
    
    # Analysis results
    pattern_results: List[PatternResult] = Field(default_factory=list, description="Pattern analysis results")
    genetic_results: List[GeneticResult] = Field(default_factory=list, description="Genetic analysis results")
    xai_artifacts: List[XAIArtifact] = Field(default_factory=list, description="XAI artifacts")
    
    # Overall assessment
    overall_confidence: ConfidenceLevel = Field(..., description="Overall confidence level")
    requires_review: bool = Field(default=False, description="Whether human review is required")
    review_reason: Optional[str] = Field(None, description="Reason for review requirement", max_length=500)
    
    # Processing metadata
    processing_time_seconds: Optional[float] = Field(None, description="Processing time in seconds", ge=0)
    model_versions: Dict[str, str] = Field(default_factory=dict, description="Model versions used")
    ontology_version: Optional[str] = Field(None, description="Ontology version used", max_length=50)
    
    # Quality metrics
    quality_metrics: Optional[Dict[str, float]] = Field(default=None, description="Quality assessment metrics")
    limitations: Optional[List[str]] = Field(default=None, description="Analysis limitations")


class MLJob(BaseEntity):
    """Machine learning job tracking."""
    job_id: str = Field(..., description="External job identifier", min_length=1, max_length=100)
    job_type: str = Field(..., description="Job type", max_length=50)
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    
    # Job context
    image_id: Optional[UUID] = Field(None, description="Associated image ID")
    case_id: Optional[UUID] = Field(None, description="Associated case ID")
    
    # Processing details
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed", max_length=1000)
    
    # Results
    result_bundle_id: Optional[UUID] = Field(None, description="Associated result bundle ID")
    progress_percentage: int = Field(default=0, description="Progress percentage", ge=0, le=100)
    
    # Metadata
    worker_id: Optional[str] = Field(None, description="Worker that processed the job", max_length=100)
    retry_count: int = Field(default=0, description="Number of retries", ge=0)
    max_retries: int = Field(default=3, description="Maximum retries allowed", ge=0)


# EHR Models
class EHRDocument(BaseEntity):
    """EHR document model."""
    ehr_id: str = Field(..., description="External EHR identifier", min_length=1, max_length=100)
    case_id: UUID = Field(..., description="Associated case ID")
    
    # Document metadata
    document_type: str = Field(..., description="Document type", max_length=100)
    document_title: Optional[str] = Field(None, description="Document title", max_length=200)
    document_date: Optional[datetime] = Field(None, description="Document date")
    
    # Content
    raw_content: str = Field(..., description="Raw document content")
    normalized_content: Optional[str] = Field(None, description="Normalized content")
    
    # Processing status
    is_processed: bool = Field(default=False, description="Whether document has been processed")
    processing_version: Optional[str] = Field(None, description="Processing version", max_length=50)


class EHREntity(BaseEntity):
    """Extracted EHR entity."""
    entity_id: str = Field(..., description="External entity identifier", min_length=1, max_length=100)
    ehr_id: UUID = Field(..., description="Associated EHR document ID")
    
    # Entity details
    entity_type: str = Field(..., description="Entity type", max_length=100)
    entity_text: str = Field(..., description="Original entity text", max_length=500)
    normalized_text: Optional[str] = Field(None, description="Normalized entity text", max_length=500)
    
    # Position in document
    start_position: int = Field(..., description="Start position in document", ge=0)
    end_position: int = Field(..., description="End position in document", ge=0)
    
    # Confidence and metadata
    confidence_score: float = Field(..., description="Extraction confidence", ge=0.0, le=1.0)
    extraction_method: str = Field(..., description="Extraction method used", max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class OntologyMapping(BaseEntity):
    """Ontology mapping for EHR entities."""
    mapping_id: str = Field(..., description="External mapping identifier", min_length=1, max_length=100)
    entity_id: UUID = Field(..., description="Associated entity ID")
    
    # Ontology details
    ontology_code: str = Field(..., description="Ontology code", max_length=100)
    ontology_name: str = Field(..., description="Ontology name", max_length=100)
    ontology_version: str = Field(..., description="Ontology version", max_length=50)
    
    # Mapping details
    mapped_term: str = Field(..., description="Mapped term", max_length=500)
    mapping_confidence: float = Field(..., description="Mapping confidence", ge=0.0, le=1.0)
    mapping_method: str = Field(..., description="Mapping method", max_length=100)
    
    # Evidence
    evidence_score: Optional[float] = Field(None, description="Evidence score", ge=0.0, le=1.0)
    evidence_sources: Optional[List[str]] = Field(default=None, description="Evidence sources")


# Graph Models
class GraphSnapshot(BaseEntity):
    """Case graph snapshot."""
    snapshot_id: str = Field(..., description="External snapshot identifier", min_length=1, max_length=100)
    case_id: UUID = Field(..., description="Associated case ID")
    
    # Graph metadata
    graph_version: str = Field(..., description="Graph version", max_length=50)
    node_count: int = Field(..., description="Number of nodes", ge=0)
    edge_count: int = Field(..., description="Number of edges", ge=0)
    
    # Storage
    graph_data_path: str = Field(..., description="Graph data storage path", max_length=500)
    layout_data_path: Optional[str] = Field(None, description="Layout data storage path", max_length=500)
    
    # Provenance
    source_components: List[str] = Field(default_factory=list, description="Source components used")
    ontology_versions: Dict[str, str] = Field(default_factory=dict, description="Ontology versions")


# Explanation Models
class ExplanationReport(BaseEntity):
    """Generated explanation report."""
    report_id: str = Field(..., description="External report identifier", min_length=1, max_length=100)
    case_id: UUID = Field(..., description="Associated case ID")
    
    # Report content
    executive_summary: str = Field(..., description="Executive summary")
    detailed_findings: str = Field(..., description="Detailed findings")
    limitations: str = Field(..., description="Analysis limitations")
    recommendations: Optional[str] = Field(None, description="Clinical recommendations")
    
    # Report metadata
    report_version: str = Field(..., description="Report version", max_length=50)
    generated_by: str = Field(..., description="Generation method", max_length=100)
    confidence_assessment: ConfidenceLevel = Field(..., description="Overall confidence")
    
    # Clinical compliance
    contains_diagnosis: bool = Field(default=False, description="Whether report contains diagnostic language")
    requires_disclaimer: bool = Field(default=True, description="Whether disclaimer is required")
    clinical_review_required: bool = Field(default=False, description="Whether clinical review is required")


# Request/Response Models
class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Service version")
    dependencies: Optional[Dict[str, str]] = Field(default=None, description="Dependency status")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, description="Page number", ge=1)
    page_size: int = Field(default=20, description="Page size", ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any] = Field(..., description="Response items")
    total: int = Field(..., description="Total item count", ge=0)
    page: int = Field(..., description="Current page", ge=1)
    page_size: int = Field(..., description="Page size", ge=1)
    total_pages: int = Field(..., description="Total pages", ge=1)
