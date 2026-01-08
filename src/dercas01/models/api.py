"""
API Request/Response Models for ML Services

Contains Pydantic models for ML service contracts as specified in Anexo B.
Implements the three main ML service contracts: ML-CLASSIFY, ML-ANOMALY, ML-ETA.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .enums import MLModelType


# =============================================================================
# ML-CLASSIFY Service Contract (Anexo B)
# =============================================================================

class ClassificationRequest(BaseModel):
    """
    Request model for ML-CLASSIFY service.
    
    Anexo B Contract:
    Req {case_id, features, model_version?}
    """
    
    case_id: str = Field(..., description="Case identifier")
    features: Dict[str, Any] = Field(..., description="Feature vector for classification")
    model_version: Optional[str] = Field(default=None, description="Specific model version to use")
    
    # Additional metadata
    timestamp: Optional[datetime] = Field(default=None, description="Request timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")


class ClassificationResponse(BaseModel):
    """
    Response model for ML-CLASSIFY service.
    
    Anexo B Contract:
    Res {request_type, candidate_policy_ids, route, risk_prior, probabilities, top_features, model_version}
    """
    
    # Core classification results
    request_type: str = Field(..., description="Predicted request type")
    candidate_policy_ids: List[str] = Field(..., description="Candidate policy document IDs")
    route: str = Field(..., description="Recommended processing route")
    risk_prior: float = Field(..., ge=0.0, le=1.0, description="Prior risk assessment")
    
    # Model outputs
    probabilities: Dict[str, float] = Field(..., description="Class probabilities")
    top_features: List[Dict[str, Any]] = Field(..., description="Most important features")
    model_version: str = Field(..., description="Model version used")
    
    # Quality metrics
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall prediction confidence")
    drift_score: Optional[float] = Field(default=None, description="Data drift score")
    
    # Metadata
    inference_timestamp: datetime = Field(..., description="Inference timestamp")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    @validator("probabilities")
    def validate_probabilities(cls, v):
        """Ensure probabilities sum to approximately 1.0."""
        total = sum(v.values())
        if not (0.95 <= total <= 1.05):  # Allow small floating point errors
            raise ValueError("Probabilities must sum to approximately 1.0")
        return v


# =============================================================================
# ML-ANOMALY Service Contract (Anexo B)
# =============================================================================

class AnomalyDetectionRequest(BaseModel):
    """
    Request model for ML-ANOMALY service.
    
    Anexo B Contract:
    Req {case_id, features, aggregates, model_version?}
    """
    
    case_id: str = Field(..., description="Case identifier")
    features: Dict[str, Any] = Field(..., description="Feature vector for anomaly detection")
    aggregates: Dict[str, Any] = Field(..., description="Aggregate statistics and historical data")
    model_version: Optional[str] = Field(default=None, description="Specific model version to use")
    
    # Additional context
    timestamp: Optional[datetime] = Field(default=None, description="Request timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")
    baseline_period: Optional[str] = Field(default="30d", description="Baseline period for comparison")


class AnomalyDetectionResponse(BaseModel):
    """
    Response model for ML-ANOMALY service.
    
    Anexo B Contract:
    Res {anomaly_score, anomaly_flags, recommended_action, model_version}
    """
    
    # Core anomaly results
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Anomaly score (0=normal, 1=highly anomalous)")
    anomaly_flags: List[str] = Field(..., description="Specific anomaly flags detected")
    recommended_action: str = Field(..., description="Recommended action based on anomaly level")
    model_version: str = Field(..., description="Model version used")
    
    # Detailed analysis
    anomaly_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed anomaly analysis")
    contributing_features: List[Dict[str, Any]] = Field(default_factory=list, description="Features contributing to anomaly")
    
    # Thresholds and context
    anomaly_threshold: float = Field(..., description="Threshold used for anomaly detection")
    baseline_stats: Dict[str, Any] = Field(default_factory=dict, description="Baseline statistics used")
    
    # Quality metrics
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in anomaly detection")
    model_drift: Optional[float] = Field(default=None, description="Model drift indicator")
    
    # Metadata
    inference_timestamp: datetime = Field(..., description="Inference timestamp")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    @validator("recommended_action")
    def validate_recommended_action(cls, v):
        """Validate recommended action values."""
        valid_actions = ["ALLOW", "REVIEW", "BLOCK", "ESCALATE"]
        if v not in valid_actions:
            raise ValueError(f"Recommended action must be one of: {valid_actions}")
        return v


# =============================================================================
# ML-ETA Service Contract (Anexo B)
# =============================================================================

class ETAPredictionRequest(BaseModel):
    """
    Request model for ML-ETA service.
    
    Anexo B Contract:
    Req {case_id, features, model_version?}
    """
    
    case_id: str = Field(..., description="Case identifier")
    features: Dict[str, Any] = Field(..., description="Feature vector for ETA prediction")
    model_version: Optional[str] = Field(default=None, description="Specific model version to use")
    
    # Additional context
    timestamp: Optional[datetime] = Field(default=None, description="Request timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")
    sla_target: Optional[int] = Field(default=None, description="SLA target in minutes")


class ETAPredictionResponse(BaseModel):
    """
    Response model for ML-ETA service.
    
    Anexo B Contract:
    Res {eta_minutes, p50, p90?, model_version}
    """
    
    # Core ETA results
    eta_minutes: int = Field(..., ge=0, description="Estimated time to completion in minutes")
    p50: int = Field(..., ge=0, description="50th percentile estimate (median)")
    p90: Optional[int] = Field(default=None, ge=0, description="90th percentile estimate")
    model_version: str = Field(..., description="Model version used")
    
    # Additional percentiles and statistics
    p25: Optional[int] = Field(default=None, ge=0, description="25th percentile estimate")
    p75: Optional[int] = Field(default=None, ge=0, description="75th percentile estimate")
    p95: Optional[int] = Field(default=None, ge=0, description="95th percentile estimate")
    
    # Confidence and quality
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in ETA prediction")
    prediction_interval: Optional[Dict[str, int]] = Field(default=None, description="Prediction interval bounds")
    
    # SLA analysis
    sla_risk: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Risk of SLA breach")
    sla_buffer: Optional[int] = Field(default=None, description="Buffer time before SLA breach")
    
    # Contributing factors
    key_factors: List[Dict[str, Any]] = Field(default_factory=list, description="Key factors affecting ETA")
    similar_cases: List[Dict[str, Any]] = Field(default_factory=list, description="Similar historical cases")
    
    # Metadata
    inference_timestamp: datetime = Field(..., description="Inference timestamp")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    @validator("eta_minutes", "p50")
    def validate_positive_times(cls, v):
        """Ensure time estimates are positive."""
        if v < 0:
            raise ValueError("Time estimates must be non-negative")
        return v


# =============================================================================
# Common ML Service Models
# =============================================================================

class MLServiceError(BaseModel):
    """Standard error response for ML services."""
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracking")


class MLServiceHealth(BaseModel):
    """Health check response for ML services."""
    
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    model_version: str = Field(..., description="Current model version")
    last_updated: datetime = Field(..., description="Last model update timestamp")
    
    # Performance metrics
    avg_response_time_ms: float = Field(..., description="Average response time")
    requests_per_minute: float = Field(..., description="Current request rate")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Current error rate")
    
    # Model metrics
    model_accuracy: Optional[float] = Field(default=None, description="Current model accuracy")
    drift_score: Optional[float] = Field(default=None, description="Current drift score")
    
    # Infrastructure
    cpu_usage: Optional[float] = Field(default=None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(default=None, description="Memory usage percentage")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")


class MLBatchRequest(BaseModel):
    """Batch request for processing multiple cases."""
    
    requests: List[Dict[str, Any]] = Field(..., description="List of individual requests")
    batch_id: str = Field(..., description="Batch identifier")
    priority: str = Field(default="NORMAL", description="Batch priority")
    callback_url: Optional[str] = Field(default=None, description="Callback URL for results")
    
    # Processing options
    parallel_processing: bool = Field(default=True, description="Enable parallel processing")
    max_retries: int = Field(default=3, description="Maximum retries per request")
    timeout_seconds: int = Field(default=300, description="Timeout per request")


class MLBatchResponse(BaseModel):
    """Batch response for multiple case processing."""
    
    batch_id: str = Field(..., description="Batch identifier")
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    
    # Results
    results: List[Dict[str, Any]] = Field(..., description="Individual results")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details for failed requests")
    
    # Timing
    started_at: datetime = Field(..., description="Batch processing start time")
    completed_at: datetime = Field(..., description="Batch processing completion time")
    total_processing_time_ms: float = Field(..., description="Total processing time")


# =============================================================================
# Feature Engineering Models
# =============================================================================

class FeatureExtractionRequest(BaseModel):
    """Request for feature extraction from case data."""
    
    case_id: str = Field(..., description="Case identifier")
    case_data: Dict[str, Any] = Field(..., description="Raw case data")
    feature_set: str = Field(default="default", description="Feature set to extract")
    
    # Historical context
    include_historical: bool = Field(default=True, description="Include historical features")
    lookback_days: int = Field(default=30, description="Days to look back for historical features")
    
    # Aggregation options
    aggregation_level: str = Field(default="case", description="Aggregation level (case, customer, provider)")


class FeatureExtractionResponse(BaseModel):
    """Response with extracted features."""
    
    case_id: str = Field(..., description="Case identifier")
    features: Dict[str, Any] = Field(..., description="Extracted features")
    feature_metadata: Dict[str, Any] = Field(..., description="Feature metadata and descriptions")
    
    # Quality metrics
    feature_completeness: float = Field(..., ge=0.0, le=1.0, description="Feature completeness score")
    missing_features: List[str] = Field(default_factory=list, description="Missing features")
    
    # Extraction metadata
    extraction_timestamp: datetime = Field(..., description="Feature extraction timestamp")
    feature_set_version: str = Field(..., description="Feature set version used")


# =============================================================================
# Model Management Models
# =============================================================================

class ModelInfo(BaseModel):
    """Model information and metadata."""
    
    model_id: str = Field(..., description="Model identifier")
    model_type: MLModelType = Field(..., description="Type of ML model")
    version: str = Field(..., description="Model version")
    
    # Model metadata
    name: str = Field(..., description="Model name")
    description: str = Field(..., description="Model description")
    algorithm: str = Field(..., description="Algorithm used")
    
    # Performance metrics
    accuracy: Optional[float] = Field(default=None, description="Model accuracy")
    precision: Optional[float] = Field(default=None, description="Model precision")
    recall: Optional[float] = Field(default=None, description="Model recall")
    f1_score: Optional[float] = Field(default=None, description="F1 score")
    
    # Deployment info
    deployed_at: datetime = Field(..., description="Deployment timestamp")
    deployed_by: str = Field(..., description="User who deployed the model")
    status: str = Field(..., description="Model status (active, deprecated, testing)")
    
    # Training info
    training_data_size: Optional[int] = Field(default=None, description="Training dataset size")
    training_completed_at: Optional[datetime] = Field(default=None, description="Training completion timestamp")
    
    # Configuration
    hyperparameters: Dict[str, Any] = Field(default_factory=dict, description="Model hyperparameters")
    feature_importance: Optional[Dict[str, float]] = Field(default=None, description="Feature importance scores")


class ModelPerformanceMetrics(BaseModel):
    """Model performance monitoring metrics."""
    
    model_id: str = Field(..., description="Model identifier")
    model_version: str = Field(..., description="Model version")
    
    # Performance metrics
    accuracy: float = Field(..., description="Current accuracy")
    precision: float = Field(..., description="Current precision")
    recall: float = Field(..., description="Current recall")
    f1_score: float = Field(..., description="Current F1 score")
    
    # Drift metrics
    data_drift_score: float = Field(..., description="Data drift score")
    concept_drift_score: float = Field(..., description="Concept drift score")
    
    # Operational metrics
    avg_response_time_ms: float = Field(..., description="Average response time")
    throughput_per_second: float = Field(..., description="Requests per second")
    error_rate: float = Field(..., description="Error rate")
    
    # Time period
    measurement_period_start: datetime = Field(..., description="Measurement period start")
    measurement_period_end: datetime = Field(..., description="Measurement period end")
    sample_size: int = Field(..., description="Number of samples in measurement")


# =============================================================================
# Utility Functions
# =============================================================================

def create_ml_error_response(
    error_code: str,
    error_message: str,
    correlation_id: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
) -> MLServiceError:
    """Create a standardized ML service error response."""
    return MLServiceError(
        error_code=error_code,
        error_message=error_message,
        error_details=error_details,
        correlation_id=correlation_id,
    )


def validate_feature_vector(features: Dict[str, Any], required_features: List[str]) -> List[str]:
    """
    Validate that required features are present in the feature vector.
    
    Args:
        features: Feature vector to validate
        required_features: List of required feature names
        
    Returns:
        List of missing features
    """
    missing_features = []
    for feature in required_features:
        if feature not in features or features[feature] is None:
            missing_features.append(feature)
    return missing_features
