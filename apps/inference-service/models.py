"""
DERCAS-ONCO-XAI V1 - Inference Service Models

SQLAlchemy 2.0 models for ML jobs, results, and XAI artifacts.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class MLJob(Base):
    """Machine learning processing job model."""
    
    __tablename__ = "ml_jobs"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # External identifier
    job_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="External job identifier"
    )
    
    # Image and case association
    image_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated image ID"
    )
    
    case_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated case ID"
    )
    
    # Job configuration
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="image_analysis",
        comment="Type of ML job"
    )
    
    processing_options: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Processing configuration options"
    )
    
    # Job status and progress
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="Job status (pending, running, completed, failed, cancelled)"
    )
    
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Progress percentage (0-100)"
    )
    
    current_step: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Current processing step"
    )
    
    # Timing information
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Job creation timestamp"
    )
    
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Job start timestamp"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Job completion timestamp"
    )
    
    estimated_completion_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Estimated completion time"
    )
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if job failed"
    )
    
    error_details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Detailed error information"
    )
    
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts"
    )
    
    # Worker information
    worker_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Worker that processed the job"
    )
    
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Celery task ID"
    )
    
    # User and audit information
    user_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="User who initiated the job"
    )
    
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Request correlation ID"
    )
    
    # Results
    result_bundle_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Associated result bundle ID"
    )
    
    # Relationships
    result_bundle: Mapped[Optional["ResultBundle"]] = relationship(
        "ResultBundle",
        back_populates="job",
        uselist=False
    )
    
    def __repr__(self) -> str:
        return f"<MLJob(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"
    
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status in ["completed", "failed", "cancelled"]
    
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == "running"
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None
    
    def mark_as_started(self, worker_id: Optional[str] = None):
        """Mark job as started."""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.worker_id = worker_id
    
    def mark_as_completed(self, result_bundle_id: Optional[str] = None):
        """Mark job as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100
        if result_bundle_id:
            self.result_bundle_id = result_bundle_id
    
    def mark_as_failed(self, error_message: str, error_details: Optional[dict] = None):
        """Mark job as failed."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if error_details:
            self.error_details = error_details
    
    def update_progress(self, percentage: int, current_step: Optional[str] = None):
        """Update job progress."""
        self.progress_percentage = max(0, min(100, percentage))
        if current_step:
            self.current_step = current_step


class ResultBundle(Base):
    """Result bundle containing all analysis results for an image."""
    
    __tablename__ = "result_bundles"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # External identifier
    result_bundle_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="External result bundle identifier"
    )
    
    # Associated entities
    job_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated ML job ID"
    )
    
    image_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated image ID"
    )
    
    case_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated case ID"
    )
    
    # Model and version information
    model_versions: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Model versions used for analysis"
    )
    
    processing_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Processing metadata and parameters"
    )
    
    # Overall analysis results
    overall_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Overall confidence score"
    )
    
    analysis_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable analysis summary"
    )
    
    # Clinical decision support
    clinical_significance: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Clinical significance level"
    )
    
    requires_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether results require human review"
    )
    
    review_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for requiring review"
    )
    
    # Quality metrics
    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Image quality score"
    )
    
    uncertainty_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Prediction uncertainty score"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    # Relationships
    job: Mapped[Optional["MLJob"]] = relationship(
        "MLJob",
        back_populates="result_bundle"
    )
    
    pattern_results: Mapped[list["PatternResult"]] = relationship(
        "PatternResult",
        back_populates="result_bundle",
        cascade="all, delete-orphan"
    )
    
    genetic_results: Mapped[list["GeneticResult"]] = relationship(
        "GeneticResult",
        back_populates="result_bundle",
        cascade="all, delete-orphan"
    )
    
    xai_artifacts: Mapped[list["XAIArtifact"]] = relationship(
        "XAIArtifact",
        back_populates="result_bundle",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<ResultBundle(id={self.id}, result_bundle_id='{self.result_bundle_id}')>"
    
    def get_highest_pattern_confidence(self) -> Optional[float]:
        """Get highest pattern confidence score."""
        if not self.pattern_results:
            return None
        return max(result.confidence_score for result in self.pattern_results)
    
    def get_highest_mutation_confidence(self) -> Optional[float]:
        """Get highest mutation confidence score."""
        if not self.genetic_results:
            return None
        return max(result.confidence_score for result in self.genetic_results)
    
    def get_dominant_pattern(self) -> Optional[str]:
        """Get the dominant histological pattern."""
        if not self.pattern_results:
            return None
        return max(self.pattern_results, key=lambda x: x.confidence_score).pattern_type
    
    def get_significant_mutations(self, threshold: float = 0.7) -> list[str]:
        """Get mutations above confidence threshold."""
        if not self.genetic_results:
            return []
        return [
            result.mutation_type 
            for result in self.genetic_results 
            if result.confidence_score >= threshold
        ]


class PatternResult(Base):
    """Histological pattern recognition result."""
    
    __tablename__ = "pattern_results"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign key to result bundle
    result_bundle_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_bundles.id"),
        nullable=False,
        index=True
    )
    
    # Pattern information
    pattern_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Histological pattern type (lepidic, acinar, papillary, micropapillary, solid)"
    )
    
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Confidence score (0.0-1.0)"
    )
    
    # Model information
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model used for prediction"
    )
    
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model version"
    )
    
    # Prediction details
    raw_prediction: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Raw model prediction output"
    )
    
    prediction_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional prediction metadata"
    )
    
    # Spatial information
    region_coordinates: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Spatial coordinates of detected pattern"
    )
    
    coverage_percentage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Percentage of image covered by this pattern"
    )
    
    # Quality metrics
    prediction_quality: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Quality score for this prediction"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    # Relationships
    result_bundle: Mapped["ResultBundle"] = relationship(
        "ResultBundle",
        back_populates="pattern_results"
    )
    
    def __repr__(self) -> str:
        return f"<PatternResult(id={self.id}, pattern='{self.pattern_type}', confidence={self.confidence_score:.3f})>"
    
    def is_high_confidence(self, threshold: float = 0.85) -> bool:
        """Check if prediction is high confidence."""
        return self.confidence_score >= threshold
    
    def is_significant(self, threshold: float = 0.70) -> bool:
        """Check if prediction is clinically significant."""
        return self.confidence_score >= threshold


class GeneticResult(Base):
    """Genetic mutation detection result."""
    
    __tablename__ = "genetic_results"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign key to result bundle
    result_bundle_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_bundles.id"),
        nullable=False,
        index=True
    )
    
    # Mutation information
    mutation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Genetic mutation type (EGFR, KRAS, TP53)"
    )
    
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Confidence score (0.0-1.0)"
    )
    
    mutation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Mutation status (positive, negative, uncertain)"
    )
    
    # Model information
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model used for prediction"
    )
    
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Model version"
    )
    
    # Prediction details
    raw_prediction: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Raw model prediction output"
    )
    
    prediction_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional prediction metadata"
    )
    
    # Clinical information
    clinical_significance: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Clinical significance of the mutation"
    )
    
    therapeutic_implications: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Therapeutic implications and recommendations"
    )
    
    # Quality metrics
    prediction_quality: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Quality score for this prediction"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    # Relationships
    result_bundle: Mapped["ResultBundle"] = relationship(
        "ResultBundle",
        back_populates="genetic_results"
    )
    
    def __repr__(self) -> str:
        return f"<GeneticResult(id={self.id}, mutation='{self.mutation_type}', status='{self.mutation_status}', confidence={self.confidence_score:.3f})>"
    
    def is_positive(self) -> bool:
        """Check if mutation is detected as positive."""
        return self.mutation_status == "positive"
    
    def is_high_confidence(self, threshold: float = 0.90) -> bool:
        """Check if prediction is high confidence."""
        return self.confidence_score >= threshold
    
    def requires_confirmation(self, threshold: float = 0.75) -> bool:
        """Check if result requires additional confirmation."""
        return self.confidence_score < threshold or self.mutation_status == "uncertain"


class XAIArtifact(Base):
    """Explainable AI artifact (heatmaps, attention maps, etc.)."""
    
    __tablename__ = "xai_artifacts"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign key to result bundle
    result_bundle_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_bundles.id"),
        nullable=False,
        index=True
    )
    
    # Artifact information
    artifact_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of XAI artifact (gradcam, lime, shap, attention)"
    )
    
    artifact_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable artifact name"
    )
    
    # Target information
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Target type (pattern, mutation, overall)"
    )
    
    target_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Specific target name (e.g., 'lepidic', 'EGFR')"
    )
    
    # Storage information
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Storage path for the artifact"
    )
    
    file_format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="File format (png, json, etc.)"
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )
    
    # Artifact metadata
    generation_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Method used to generate the artifact"
    )
    
    generation_parameters: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Parameters used for artifact generation"
    )
    
    # Quality and relevance
    relevance_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Relevance score of the explanation"
    )
    
    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Quality score of the artifact"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    # Relationships
    result_bundle: Mapped["ResultBundle"] = relationship(
        "ResultBundle",
        back_populates="xai_artifacts"
    )
    
    def __repr__(self) -> str:
        return f"<XAIArtifact(id={self.id}, type='{self.artifact_type}', target='{self.target_name}')>"
    
    def get_file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    def is_image_artifact(self) -> bool:
        """Check if artifact is an image."""
        return self.file_format.lower() in ["png", "jpg", "jpeg", "svg"]
    
    def is_data_artifact(self) -> bool:
        """Check if artifact is data/metadata."""
        return self.file_format.lower() in ["json", "csv", "xml"]


class PolicyDecision(Base):
    """Clinical policy decision and HITL intervention record."""
    
    __tablename__ = "policy_decisions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Associated entities
    result_bundle_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_bundles.id"),
        nullable=False,
        index=True
    )
    
    job_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated ML job ID"
    )
    
    # Policy information
    policy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of policy applied"
    )
    
    policy_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Policy version"
    )
    
    # Decision details
    decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Policy decision (approve, reject, require_review)"
    )
    
    decision_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Reason for the decision"
    )
    
    confidence_threshold_used: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Confidence threshold used for decision"
    )
    
    # HITL information
    requires_hitl: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether human intervention is required"
    )
    
    hitl_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for requiring HITL"
    )
    
    hitl_reviewer: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Human reviewer assigned"
    )
    
    hitl_decision: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Human reviewer decision"
    )
    
    hitl_comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human reviewer comments"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    hitl_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="HITL review timestamp"
    )
    
    def __repr__(self) -> str:
        return f"<PolicyDecision(id={self.id}, decision='{self.decision}', requires_hitl={self.requires_hitl})>"
    
    def is_approved(self) -> bool:
        """Check if results are approved for release."""
        return self.decision == "approve"
    
    def is_pending_review(self) -> bool:
        """Check if results are pending human review."""
        return self.requires_hitl and not self.hitl_reviewed_at
    
    def mark_hitl_reviewed(self, reviewer: str, decision: str, comments: Optional[str] = None):
        """Mark as reviewed by human."""
        self.hitl_reviewer = reviewer
        self.hitl_decision = decision
        self.hitl_comments = comments
        self.hitl_reviewed_at = datetime.utcnow()
