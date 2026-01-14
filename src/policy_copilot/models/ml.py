"""
ML Services data models for Policy Validation Copilot

This module contains ML service models for classification, anomaly detection,
and ETA prediction as specified in Anexo B API contracts.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, ModelVersion, AnomalyFlag, RiskLevel


class MLClassificationOutput(BaseEntity):
    """
    ML Classification service output model.
    
    Implements the ML-CLASSIFY API contract from Anexo B for
    request type prediction and policy routing.
    """
    
    # Request identification
    case_id: str = Field(..., description="Case identifier")
    
    # Classification results
    request_type: str = Field(..., description="Predicted request type")
    candidate_policy_ids: List[str] = Field(..., description="Candidate policy document IDs")
    route: str = Field(..., description="Recommended processing route")
    risk_prior: RiskLevel = Field(..., description="Prior risk assessment")
    
    # Prediction confidence
    probabilities: Dict[str, float] = Field(..., description="Class probabilities")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    
    # Feature importance
    top_features: List[Dict[str, float]] = Field(..., description="Top contributing features")
    feature_vector: Optional[Dict[str, float]] = Field(None, description="Complete feature vector")
    
    # Model metadata
    model_version: ModelVersion = Field(..., description="Model version information")
    
    # Processing metadata
    inference_time_ms: int = Field(..., description="Inference time in milliseconds")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    
    @validator('probabilities')
    def validate_probabilities(cls, v):
        """Validate probabilities sum to 1.0."""
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError('Probabilities must sum to approximately 1.0')
        return v
    
    @validator('confidence_score')
    def validate_confidence_with_probabilities(cls, v, values):
        """Validate confidence score consistency with probabilities."""
        if 'probabilities' in values and values['probabilities']:
            max_prob = max(values['probabilities'].values())
            if abs(v - max_prob) > 0.1:  # Allow some difference for ensemble methods
                raise ValueError('Confidence score should be close to maximum probability')
        return v


class MLAnomalyOutput(BaseEntity):
    """
    ML Anomaly Detection service output model.
    
    Implements the ML-ANOMALY API contract from Anexo B for
    pattern deviation detection and risk assessment.
    """
    
    # Request identification
    case_id: str = Field(..., description="Case identifier")
    
    # Anomaly detection results
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Anomaly score (0=normal, 1=highly anomalous)")
    anomaly_flags: List[AnomalyFlag] = Field(default_factory=list, description="Specific anomaly types detected")
    recommended_action: str = Field(..., description="Recommended action based on anomaly level")
    
    # Detailed analysis
    anomaly_details: Dict[str, float] = Field(default_factory=dict, description="Detailed anomaly scores by category")
    contributing_factors: List[str] = Field(default_factory=list, description="Factors contributing to anomaly")
    
    # Baseline comparison
    baseline_comparison: Optional[Dict[str, float]] = Field(None, description="Comparison with baseline metrics")
    historical_context: Optional[Dict] = Field(None, description="Historical context for anomaly assessment")
    
    # Model metadata
    model_version: ModelVersion = Field(..., description="Model version information")
    
    # Processing metadata
    inference_time_ms: int = Field(..., description="Inference time in milliseconds")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    
    @validator('recommended_action')
    def validate_recommended_action(cls, v, values):
        """Validate recommended action based on anomaly score."""
        if 'anomaly_score' in values:
            score = values['anomaly_score']
            valid_actions = {
                'PROCEED': score < 0.3,
                'REVIEW': 0.3 <= score < 0.7,
                'ESCALATE': 0.7 <= score < 0.9,
                'BLOCK': score >= 0.9
            }
            if v not in valid_actions or not valid_actions[v]:
                raise ValueError(f'Recommended action "{v}" inconsistent with anomaly score {score}')
        return v


class MLETAOutput(BaseEntity):
    """
    ML ETA Prediction service output model.
    
    Implements the ML-ETA API contract from Anexo B for
    estimated time of arrival prediction.
    """
    
    # Request identification
    case_id: str = Field(..., description="Case identifier")
    
    # ETA prediction
    eta_minutes: int = Field(..., ge=0, description="Estimated time to completion in minutes")
    eta_timestamp: datetime = Field(..., description="Predicted completion timestamp")
    
    # Confidence intervals
    p50: int = Field(..., ge=0, description="50th percentile estimate (median)")
    p90: Optional[int] = Field(None, ge=0, description="90th percentile estimate")
    confidence_interval: Optional[Dict[str, int]] = Field(None, description="Confidence interval bounds")
    
    # Prediction factors
    complexity_score: float = Field(..., ge=0.0, le=1.0, description="Case complexity score")
    workload_factor: float = Field(..., ge=0.0, description="Current workload factor")
    historical_average: Optional[int] = Field(None, description="Historical average for similar cases")
    
    # Model metadata
    model_version: ModelVersion = Field(..., description="Model version information")
    
    # Processing metadata
    inference_time_ms: int = Field(..., description="Inference time in milliseconds")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    
    @validator('eta_timestamp')
    def validate_eta_timestamp(cls, v, values):
        """Validate ETA timestamp is in the future."""
        if v <= datetime.utcnow():
            raise ValueError('ETA timestamp must be in the future')
        return v
    
    @validator('p90')
    def validate_percentiles(cls, v, values):
        """Validate p90 is greater than p50."""
        if v is not None and 'p50' in values and v <= values['p50']:
            raise ValueError('P90 must be greater than P50')
        return v


class MLDriftMetrics(BaseEntity):
    """
    ML model drift detection metrics.
    
    Tracks model performance degradation and data drift
    for continuous monitoring and retraining decisions.
    """
    
    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    
    # Drift scores
    data_drift_score: float = Field(..., ge=0.0, le=1.0, description="Data drift score")
    concept_drift_score: float = Field(..., ge=0.0, le=1.0, description="Concept drift score")
    performance_drift_score: float = Field(..., ge=0.0, le=1.0, description="Performance drift score")
    
    # Performance metrics
    current_accuracy: Optional[float] = Field(None, description="Current model accuracy")
    baseline_accuracy: Optional[float] = Field(None, description="Baseline model accuracy")
    performance_degradation: Optional[float] = Field(None, description="Performance degradation percentage")
    
    # Drift detection details
    drift_detected: bool = Field(False, description="Whether significant drift was detected")
    drift_threshold: float = Field(0.1, description="Drift detection threshold")
    retraining_recommended: bool = Field(False, description="Whether retraining is recommended")
    
    # Monitoring period
    monitoring_start: datetime = Field(..., description="Monitoring period start")
    monitoring_end: datetime = Field(..., description="Monitoring period end")
    sample_size: int = Field(..., description="Number of samples analyzed")
    
    @validator('performance_degradation')
    def calculate_performance_degradation(cls, v, values):
        """Calculate performance degradation if not provided."""
        if v is None and 'current_accuracy' in values and 'baseline_accuracy' in values:
            current = values['current_accuracy']
            baseline = values['baseline_accuracy']
            if current is not None and baseline is not None and baseline > 0:
                return ((baseline - current) / baseline) * 100
        return v


class MLOutputs(BaseEntity):
    """
    Aggregated ML service outputs for LangGraph state.
    
    Contains outputs from all ML services (classification, anomaly, ETA)
    with model versions as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    
    # ML service outputs
    classification: Optional[MLClassificationOutput] = Field(None, description="Classification service output")
    anomaly: Optional[MLAnomalyOutput] = Field(None, description="Anomaly detection service output")
    eta: Optional[MLETAOutput] = Field(None, description="ETA prediction service output")
    
    # Model versions tracking
    model_versions: Dict[str, ModelVersion] = Field(default_factory=dict, description="All model versions used")
    
    # Aggregated metrics
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall ML confidence score")
    risk_assessment: RiskLevel = Field(RiskLevel.MEDIUM, description="Aggregated risk assessment")
    
    # Processing status
    services_completed: List[str] = Field(default_factory=list, description="Completed ML services")
    services_failed: List[str] = Field(default_factory=list, description="Failed ML services")
    fallback_used: bool = Field(False, description="Whether fallback rules were used")
    
    # Drift monitoring
    drift_metrics: List[MLDriftMetrics] = Field(default_factory=list, description="Model drift metrics")
    
    # Processing metadata
    total_processing_time_ms: int = Field(0, description="Total ML processing time")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing completion timestamp")
    
    def add_classification_output(self, output: MLClassificationOutput) -> None:
        """Add classification service output."""
        self.classification = output
        self.model_versions['classification'] = output.model_version
        self.services_completed.append('classification')
        self.total_processing_time_ms += output.inference_time_ms
        self._update_aggregated_metrics()
    
    def add_anomaly_output(self, output: MLAnomalyOutput) -> None:
        """Add anomaly detection service output."""
        self.anomaly = output
        self.model_versions['anomaly'] = output.model_version
        self.services_completed.append('anomaly')
        self.total_processing_time_ms += output.inference_time_ms
        self._update_aggregated_metrics()
    
    def add_eta_output(self, output: MLETAOutput) -> None:
        """Add ETA prediction service output."""
        self.eta = output
        self.model_versions['eta'] = output.model_version
        self.services_completed.append('eta')
        self.total_processing_time_ms += output.inference_time_ms
        self._update_aggregated_metrics()
    
    def mark_service_failed(self, service_name: str, use_fallback: bool = True) -> None:
        """Mark a service as failed and optionally use fallback."""
        self.services_failed.append(service_name)
        if use_fallback:
            self.fallback_used = True
        self.updated_at = datetime.utcnow()
    
    def _update_aggregated_metrics(self) -> None:
        """Update aggregated confidence and risk metrics."""
        confidences = []
        risks = []
        
        if self.classification:
            confidences.append(self.classification.confidence_score)
            risks.append(self.classification.risk_prior)
        
        if self.anomaly:
            # Convert anomaly score to confidence (inverse relationship)
            confidences.append(1.0 - self.anomaly.anomaly_score)
            # High anomaly score increases risk
            if self.anomaly.anomaly_score > 0.7:
                risks.append(RiskLevel.HIGH)
            elif self.anomaly.anomaly_score > 0.4:
                risks.append(RiskLevel.MEDIUM)
            else:
                risks.append(RiskLevel.LOW)
        
        # Calculate overall confidence as average
        if confidences:
            self.overall_confidence = sum(confidences) / len(confidences)
        
        # Calculate overall risk as maximum
        if risks:
            risk_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
            max_risk_value = max(risk_levels[risk.value] for risk in risks)
            for level, value in risk_levels.items():
                if value == max_risk_value:
                    self.risk_assessment = RiskLevel(level)
                    break
        
        self.updated_at = datetime.utcnow()
    
    def is_high_risk(self) -> bool:
        """Check if case is high risk based on ML outputs."""
        return (
            self.risk_assessment in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            (self.anomaly and self.anomaly.anomaly_score > 0.7) or
            self.overall_confidence < 0.5
        )
    
    def requires_human_review(self) -> bool:
        """Check if case requires human review based on ML outputs."""
        return (
            self.is_high_risk() or
            len(self.services_failed) > 0 or
            self.overall_confidence < 0.6
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "overall_confidence": 0.85,
                "risk_assessment": "MEDIUM",
                "services_completed": ["classification", "anomaly", "eta"],
                "services_failed": [],
                "fallback_used": False,
                "total_processing_time_ms": 1250
            }
        }
