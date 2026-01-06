"""
DERCAS-ONCO-XAI V1 - Inference Service Schemas

Pydantic request/response schemas for the AI Inference Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')


# Processing request schemas
class ProcessingOptions(BaseModel):
    """Processing configuration options."""
    enable_pattern_analysis: bool = Field(default=True, description="Enable histological pattern analysis")
    enable_mutation_analysis: bool = Field(default=True, description="Enable genetic mutation analysis")
    enable_xai_generation: bool = Field(default=True, description="Generate XAI artifacts")
    
    # Pattern analysis options
    pattern_models: Optional[List[str]] = Field(
        default=None,
        description="Specific pattern models to use (default: all)"
    )
    pattern_confidence_threshold: Optional[float] = Field(
        default=None,
        description="Custom confidence threshold for patterns",
        ge=0.0,
        le=1.0
    )
    
    # Mutation analysis options
    mutation_models: Optional[List[str]] = Field(
        default=None,
        description="Specific mutation models to use (default: all)"
    )
    mutation_confidence_threshold: Optional[float] = Field(
        default=None,
        description="Custom confidence threshold for mutations",
        ge=0.0,
        le=1.0
    )
    
    # XAI options
    xai_methods: Optional[List[str]] = Field(
        default=None,
        description="XAI methods to use (gradcam, lime, shap, attention)"
    )
    generate_heatmaps: bool = Field(default=True, description="Generate attention heatmaps")
    generate_region_analysis: bool = Field(default=True, description="Generate region-based analysis")
    
    # Processing options
    high_resolution_mode: bool = Field(default=False, description="Use high resolution processing")
    batch_processing: bool = Field(default=False, description="Enable batch processing optimizations")
    priority: str = Field(default="normal", description="Processing priority (low, normal, high)")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high']:
            raise ValueError('Priority must be low, normal, or high')
        return v


class ProcessImageRequest(BaseModel):
    """Request schema for image processing."""
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    callback_url: Optional[str] = Field(None, description="Callback URL for completion notification")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional request metadata")


# Response schemas
class ProcessImageResponse(BaseModel):
    """Response schema for image processing request."""
    job_id: str = Field(..., description="Processing job ID")
    image_id: str = Field(..., description="Image ID being processed")
    status: str = Field(..., description="Initial job status")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    processing_options: ProcessingOptions = Field(..., description="Processing configuration used")
    created_at: datetime = Field(..., description="Job creation timestamp")


class JobStatusResponse(BaseModel):
    """Response schema for job status."""
    id: UUID = Field(..., description="Internal job ID")
    job_id: str = Field(..., description="External job ID")
    image_id: str = Field(..., description="Associated image ID")
    case_id: str = Field(..., description="Associated case ID")
    status: str = Field(..., description="Job status")
    progress_percentage: int = Field(..., description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current processing step")
    
    # Timing information
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(..., description="Number of retry attempts")
    
    # Worker information
    worker_id: Optional[str] = Field(None, description="Worker processing the job")
    
    # Results
    result_bundle_id: Optional[str] = Field(None, description="Result bundle ID if completed")
    
    # Computed fields
    duration_seconds: Optional[float] = Field(None, description="Job duration in seconds")
    is_completed: bool = Field(..., description="Whether job is completed")
    is_running: bool = Field(..., description="Whether job is running")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object with computed fields."""
        data = {
            'id': obj.id,
            'job_id': obj.job_id,
            'image_id': obj.image_id,
            'case_id': obj.case_id,
            'status': obj.status,
            'progress_percentage': obj.progress_percentage,
            'current_step': obj.current_step,
            'created_at': obj.created_at,
            'started_at': obj.started_at,
            'completed_at': obj.completed_at,
            'estimated_completion_time': obj.estimated_completion_time,
            'error_message': obj.error_message,
            'retry_count': obj.retry_count,
            'worker_id': obj.worker_id,
            'result_bundle_id': obj.result_bundle_id,
            'duration_seconds': obj.get_duration_seconds(),
            'is_completed': obj.is_completed(),
            'is_running': obj.is_running()
        }
        return cls(**data)


# Result schemas
class PatternResultResponse(BaseModel):
    """Response schema for pattern recognition result."""
    id: UUID = Field(..., description="Result ID")
    pattern_type: str = Field(..., description="Histological pattern type")
    confidence_score: float = Field(..., description="Confidence score")
    model_name: str = Field(..., description="Model used")
    model_version: str = Field(..., description="Model version")
    
    # Spatial information
    region_coordinates: Optional[Dict[str, Any]] = Field(None, description="Spatial coordinates")
    coverage_percentage: Optional[float] = Field(None, description="Coverage percentage")
    
    # Quality metrics
    prediction_quality: Optional[float] = Field(None, description="Prediction quality score")
    
    # Computed fields
    is_high_confidence: bool = Field(..., description="Whether prediction is high confidence")
    is_significant: bool = Field(..., description="Whether prediction is clinically significant")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class GeneticResultResponse(BaseModel):
    """Response schema for genetic mutation result."""
    id: UUID = Field(..., description="Result ID")
    mutation_type: str = Field(..., description="Genetic mutation type")
    confidence_score: float = Field(..., description="Confidence score")
    mutation_status: str = Field(..., description="Mutation status")
    model_name: str = Field(..., description="Model used")
    model_version: str = Field(..., description="Model version")
    
    # Clinical information
    clinical_significance: Optional[str] = Field(None, description="Clinical significance")
    therapeutic_implications: Optional[Dict[str, Any]] = Field(None, description="Therapeutic implications")
    
    # Quality metrics
    prediction_quality: Optional[float] = Field(None, description="Prediction quality score")
    
    # Computed fields
    is_positive: bool = Field(..., description="Whether mutation is detected")
    is_high_confidence: bool = Field(..., description="Whether prediction is high confidence")
    requires_confirmation: bool = Field(..., description="Whether result requires confirmation")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class ArtifactResponse(BaseModel):
    """Response schema for XAI artifact."""
    id: UUID = Field(..., description="Artifact ID")
    artifact_type: str = Field(..., description="Artifact type")
    artifact_name: str = Field(..., description="Artifact name")
    target_type: str = Field(..., description="Target type")
    target_name: Optional[str] = Field(None, description="Target name")
    
    # Storage information
    storage_path: str = Field(..., description="Storage path")
    file_format: str = Field(..., description="File format")
    file_size: int = Field(..., description="File size in bytes")
    
    # Generation information
    generation_method: str = Field(..., description="Generation method")
    generation_parameters: Optional[Dict[str, Any]] = Field(None, description="Generation parameters")
    
    # Quality metrics
    relevance_score: Optional[float] = Field(None, description="Relevance score")
    quality_score: Optional[float] = Field(None, description="Quality score")
    
    # Computed fields
    file_size_mb: float = Field(..., description="File size in MB")
    is_image_artifact: bool = Field(..., description="Whether artifact is an image")
    is_data_artifact: bool = Field(..., description="Whether artifact is data")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object with computed fields."""
        data = {
            'id': obj.id,
            'artifact_type': obj.artifact_type,
            'artifact_name': obj.artifact_name,
            'target_type': obj.target_type,
            'target_name': obj.target_name,
            'storage_path': obj.storage_path,
            'file_format': obj.file_format,
            'file_size': obj.file_size,
            'generation_method': obj.generation_method,
            'generation_parameters': obj.generation_parameters,
            'relevance_score': obj.relevance_score,
            'quality_score': obj.quality_score,
            'file_size_mb': obj.get_file_size_mb(),
            'is_image_artifact': obj.is_image_artifact(),
            'is_data_artifact': obj.is_data_artifact(),
            'created_at': obj.created_at
        }
        return cls(**data)


class PolicyDecisionResponse(BaseModel):
    """Response schema for policy decision."""
    id: UUID = Field(..., description="Decision ID")
    policy_type: str = Field(..., description="Policy type")
    policy_version: str = Field(..., description="Policy version")
    decision: str = Field(..., description="Policy decision")
    decision_reason: str = Field(..., description="Decision reason")
    confidence_threshold_used: float = Field(..., description="Confidence threshold used")
    
    # HITL information
    requires_hitl: bool = Field(..., description="Whether HITL is required")
    hitl_reason: Optional[str] = Field(None, description="HITL reason")
    hitl_reviewer: Optional[str] = Field(None, description="HITL reviewer")
    hitl_decision: Optional[str] = Field(None, description="HITL decision")
    hitl_comments: Optional[str] = Field(None, description="HITL comments")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    hitl_reviewed_at: Optional[datetime] = Field(None, description="HITL review timestamp")
    
    # Computed fields
    is_approved: bool = Field(..., description="Whether results are approved")
    is_pending_review: bool = Field(..., description="Whether pending review")
    
    class Config:
        from_attributes = True


class ResultBundleResponse(BaseModel):
    """Response schema for complete result bundle."""
    id: UUID = Field(..., description="Bundle ID")
    result_bundle_id: str = Field(..., description="External bundle ID")
    job_id: str = Field(..., description="Associated job ID")
    image_id: str = Field(..., description="Associated image ID")
    case_id: str = Field(..., description="Associated case ID")
    
    # Model information
    model_versions: Dict[str, str] = Field(..., description="Model versions used")
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")
    
    # Overall results
    overall_confidence: float = Field(..., description="Overall confidence score")
    analysis_summary: Optional[str] = Field(None, description="Analysis summary")
    
    # Clinical information
    clinical_significance: Optional[str] = Field(None, description="Clinical significance")
    requires_review: bool = Field(..., description="Whether requires review")
    review_reason: Optional[str] = Field(None, description="Review reason")
    
    # Quality metrics
    quality_score: Optional[float] = Field(None, description="Quality score")
    uncertainty_score: Optional[float] = Field(None, description="Uncertainty score")
    
    # Results
    pattern_results: List[PatternResultResponse] = Field(..., description="Pattern recognition results")
    genetic_results: List[GeneticResultResponse] = Field(..., description="Genetic mutation results")
    xai_artifacts: List[ArtifactResponse] = Field(..., description="XAI artifacts")
    policy_decisions: List[PolicyDecisionResponse] = Field(..., description="Policy decisions")
    
    # Computed fields
    highest_pattern_confidence: Optional[float] = Field(None, description="Highest pattern confidence")
    highest_mutation_confidence: Optional[float] = Field(None, description="Highest mutation confidence")
    dominant_pattern: Optional[str] = Field(None, description="Dominant pattern")
    significant_mutations: List[str] = Field(..., description="Significant mutations")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object with computed fields."""
        data = {
            'id': obj.id,
            'result_bundle_id': obj.result_bundle_id,
            'job_id': obj.job_id,
            'image_id': obj.image_id,
            'case_id': obj.case_id,
            'model_versions': obj.model_versions,
            'processing_metadata': obj.processing_metadata,
            'overall_confidence': obj.overall_confidence,
            'analysis_summary': obj.analysis_summary,
            'clinical_significance': obj.clinical_significance,
            'requires_review': obj.requires_review,
            'review_reason': obj.review_reason,
            'quality_score': obj.quality_score,
            'uncertainty_score': obj.uncertainty_score,
            'pattern_results': [PatternResultResponse.from_orm(r) for r in obj.pattern_results],
            'genetic_results': [GeneticResultResponse.from_orm(r) for r in obj.genetic_results],
            'xai_artifacts': [ArtifactResponse.from_orm(a) for a in obj.xai_artifacts],
            'policy_decisions': [],  # Would need to add relationship
            'highest_pattern_confidence': obj.get_highest_pattern_confidence(),
            'highest_mutation_confidence': obj.get_highest_mutation_confidence(),
            'dominant_pattern': obj.get_dominant_pattern(),
            'significant_mutations': obj.get_significant_mutations(),
            'created_at': obj.created_at
        }
        return cls(**data)


# Statistics and monitoring schemas
class ModelInfo(BaseModel):
    """Model information schema."""
    model_id: str = Field(..., description="Model identifier")
    model_name: str = Field(..., description="Model name")
    model_type: str = Field(..., description="Model type (pattern, mutation)")
    version: str = Field(..., description="Model version")
    status: str = Field(..., description="Model status")
    accuracy: Optional[float] = Field(None, description="Model accuracy")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class InferenceStatistics(BaseModel):
    """Inference service statistics."""
    total_jobs: int = Field(..., description="Total number of jobs")
    completed_jobs: int = Field(..., description="Number of completed jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    running_jobs: int = Field(..., description="Number of running jobs")
    pending_jobs: int = Field(..., description="Number of pending jobs")
    
    # Performance metrics
    average_processing_time_seconds: float = Field(..., description="Average processing time")
    success_rate: float = Field(..., description="Success rate percentage")
    
    # Model usage
    jobs_by_model: Dict[str, int] = Field(..., description="Job count by model")
    
    # Quality metrics
    average_confidence_score: float = Field(..., description="Average confidence score")
    high_confidence_results: int = Field(..., description="Number of high confidence results")
    hitl_required_count: int = Field(..., description="Number of results requiring HITL")
    
    # Time-based statistics
    jobs_last_24h: int = Field(..., description="Jobs in last 24 hours")
    jobs_last_week: int = Field(..., description="Jobs in last week")
    
    # Resource usage
    total_processing_time_hours: float = Field(..., description="Total processing time in hours")
    average_queue_time_seconds: float = Field(..., description="Average queue time")


# Search and filter schemas
class JobSearchFilters(BaseModel):
    """Job search filters."""
    status: Optional[str] = Field(None, description="Filter by status")
    image_id: Optional[str] = Field(None, description="Filter by image ID")
    case_id: Optional[str] = Field(None, description="Filter by case ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    job_type: Optional[str] = Field(None, description="Filter by job type")
    created_after: Optional[datetime] = Field(None, description="Filter jobs created after")
    created_before: Optional[datetime] = Field(None, description="Filter jobs created before")
    min_confidence: Optional[float] = Field(None, description="Minimum confidence score", ge=0.0, le=1.0)
    max_confidence: Optional[float] = Field(None, description="Maximum confidence score", ge=0.0, le=1.0)
    requires_review: Optional[bool] = Field(None, description="Filter by review requirement")


class ResultSearchFilters(BaseModel):
    """Result search filters."""
    case_id: Optional[str] = Field(None, description="Filter by case ID")
    pattern_type: Optional[str] = Field(None, description="Filter by pattern type")
    mutation_type: Optional[str] = Field(None, description="Filter by mutation type")
    min_confidence: Optional[float] = Field(None, description="Minimum confidence score", ge=0.0, le=1.0)
    clinical_significance: Optional[str] = Field(None, description="Filter by clinical significance")
    requires_review: Optional[bool] = Field(None, description="Filter by review requirement")
    created_after: Optional[datetime] = Field(None, description="Filter results created after")
    created_before: Optional[datetime] = Field(None, description="Filter results created before")


# Batch operation schemas
class BatchProcessRequest(BaseModel):
    """Batch processing request."""
    image_ids: List[str] = Field(..., description="List of image IDs to process", min_items=1, max_items=50)
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    batch_name: Optional[str] = Field(None, description="Batch name for tracking")
    priority: str = Field(default="normal", description="Batch priority")
    
    @validator('image_ids')
    def validate_image_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate image IDs are not allowed')
        return v


class BatchProcessResponse(BaseModel):
    """Batch processing response."""
    batch_id: str = Field(..., description="Batch identifier")
    job_ids: List[str] = Field(..., description="Individual job IDs")
    total_images: int = Field(..., description="Total number of images")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    created_at: datetime = Field(..., description="Batch creation timestamp")


# Health check schemas
class ModelHealthCheck(BaseModel):
    """Model health check result."""
    model_id: str = Field(..., description="Model identifier")
    status: str = Field(..., description="Model status")
    last_prediction: Optional[datetime] = Field(None, description="Last successful prediction")
    error_rate: float = Field(..., description="Recent error rate")
    average_latency_ms: float = Field(..., description="Average prediction latency")


class ServiceHealthCheck(BaseModel):
    """Service health check result."""
    database_connected: bool = Field(..., description="Database connection status")
    celery_connected: bool = Field(..., description="Celery connection status")
    event_bus_connected: bool = Field(..., description="Event bus connection status")
    models_loaded: int = Field(..., description="Number of loaded models")
    active_workers: int = Field(..., description="Number of active workers")
    queue_size: int = Field(..., description="Current queue size")
    model_health: List[ModelHealthCheck] = Field(..., description="Individual model health")


# HITL schemas
class HITLReviewRequest(BaseModel):
    """HITL review request."""
    decision: str = Field(..., description="Review decision (approve, reject, modify)")
    comments: Optional[str] = Field(None, description="Reviewer comments")
    confidence_override: Optional[float] = Field(None, description="Confidence override", ge=0.0, le=1.0)
    modifications: Optional[Dict[str, Any]] = Field(None, description="Result modifications")
    
    @validator('decision')
    def validate_decision(cls, v):
        if v not in ['approve', 'reject', 'modify']:
            raise ValueError('Decision must be approve, reject, or modify')
        return v


class HITLReviewResponse(BaseModel):
    """HITL review response."""
    review_id: str = Field(..., description="Review identifier")
    result_bundle_id: str = Field(..., description="Result bundle ID")
    reviewer: str = Field(..., description="Reviewer identifier")
    decision: str = Field(..., description="Review decision")
    comments: Optional[str] = Field(None, description="Reviewer comments")
    reviewed_at: datetime = Field(..., description="Review timestamp")
    final_status: str = Field(..., description="Final result status")


# Error schemas
class InferenceError(BaseModel):
    """Inference-specific error schema."""
    error_code: str = Field(..., description="Error code")
    error_type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    job_id: Optional[str] = Field(None, description="Associated job ID")
    image_id: Optional[str] = Field(None, description="Associated image ID")
    model_info: Optional[Dict[str, str]] = Field(None, description="Model information")
    timestamp: datetime = Field(..., description="Error timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
