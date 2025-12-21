"""
ML service output models.

Based on DERCAS 01 Anexo B - ML Contracts.
Covers UC-OP-11 (Classification), UC-OP-12 (Anomaly), UC-OP-13 (ETA).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MLClassifyOutput(BaseModel):
    """
    ML Classification/Routing output.

    UC-OP-11: Predicts request type, candidate policies, route, and risk.
    """

    # Request classification
    request_type: str = Field(..., description="Predicted request type")
    request_type_confidence: float = Field(..., ge=0.0, le=1.0)

    # Candidate policies
    candidate_policy_ids: list[str] = Field(
        default_factory=list, description="Ranked policy IDs for retrieval"
    )

    # Routing decision
    route: str = Field(..., description="Recommended route: AUTO, HITL_AGENT, HITL_SUPERVISOR")
    route_confidence: float = Field(..., ge=0.0, le=1.0)

    # Risk prior (before full evaluation)
    risk_prior: float = Field(..., ge=0.0, le=1.0, description="Initial risk estimate")

    # Probabilities for all classes
    probabilities: dict[str, float] = Field(
        default_factory=dict, description="Class probabilities"
    )

    # Explainability
    top_features: list[dict] = Field(
        default_factory=list, description="Top contributing features"
    )

    # Model metadata
    model_version: str = Field(..., description="Model version used")
    inference_duration_ms: Optional[int] = Field(None)
    inferred_at: datetime = Field(default_factory=datetime.utcnow)

    # Degradation flag
    ml_degraded: bool = Field(default=False, description="True if using fallback/rules")


class MLAnomalyOutput(BaseModel):
    """
    ML Anomaly Detection output.

    UC-OP-12: Detects atypical patterns that require special attention.
    """

    # Anomaly assessment
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Overall anomaly score")
    is_anomalous: bool = Field(default=False, description="Above threshold flag")

    # Anomaly breakdown
    anomaly_flags: list[str] = Field(
        default_factory=list, description="Specific anomaly types detected"
    )

    # Recommended action
    recommended_action: str = Field(
        default="CONTINUE", description="CONTINUE, REVIEW, ESCALATE, BLOCK"
    )

    # Comparison to baseline
    baseline_deviation: Optional[float] = Field(
        None, description="Standard deviations from baseline"
    )
    similar_cases_count: Optional[int] = Field(
        None, description="Number of similar historical cases"
    )

    # Model metadata
    model_version: str = Field(..., description="Model version used")
    inference_duration_ms: Optional[int] = Field(None)
    inferred_at: datetime = Field(default_factory=datetime.utcnow)

    # Degradation flag
    ml_degraded: bool = Field(default=False, description="True if baseline insufficient")


class MLETAOutput(BaseModel):
    """
    ML ETA Prediction output.

    UC-OP-13: Estimates case resolution time for SLA management.
    """

    # ETA prediction
    eta_minutes: int = Field(..., ge=0, description="Predicted resolution time in minutes")

    # Confidence intervals
    p50_minutes: Optional[int] = Field(None, description="50th percentile estimate")
    p90_minutes: Optional[int] = Field(None, description="90th percentile estimate")

    # SLA assessment
    sla_risk: str = Field(default="LOW", description="LOW, MEDIUM, HIGH based on SLA target")
    sla_breach_probability: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Probability of SLA breach"
    )

    # Contributing factors
    eta_factors: list[dict] = Field(
        default_factory=list, description="Factors affecting ETA"
    )

    # Model metadata
    model_version: str = Field(..., description="Model version used")
    inference_duration_ms: Optional[int] = Field(None)
    inferred_at: datetime = Field(default_factory=datetime.utcnow)

    # Degradation flag
    ml_degraded: bool = Field(default=False, description="True if using fallback averages")


class MLOutputs(BaseModel):
    """Aggregated ML outputs for the decision pipeline."""

    classify: Optional[MLClassifyOutput] = None
    anomaly: Optional[MLAnomalyOutput] = None
    eta: Optional[MLETAOutput] = None

    # Overall ML health
    any_degraded: bool = Field(default=False)

    def update_degradation_status(self) -> None:
        """Check if any ML service is in degraded mode."""
        self.any_degraded = any([
            self.classify.ml_degraded if self.classify else False,
            self.anomaly.ml_degraded if self.anomaly else False,
            self.eta.ml_degraded if self.eta else False,
        ])
