"""
Decision data models.

Represents the final decision output from the validation workflow.
Based on UC-OP-08 Decision Orchestrator.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    """Final decision status for a case."""

    APPROVED = "APPROVED"
    OBSERVED = "OBSERVED"
    REJECTED = "REJECTED"
    ESCALATE_HITL = "ESCALATE_HITL"
    PENDING_DATOS = "PENDING_DATOS"
    PENDING_POLITICA = "PENDING_POLITICA"
    PENDING_ASEGURADORA = "PENDING_ASEGURADORA"
    PENDING_SISTEMA = "PENDING_SISTEMA"


class NextAction(BaseModel):
    """Recommended next action for case processing."""

    action_id: str = Field(..., description="Action identifier")
    action_type: str = Field(
        ..., description="Type: REQUEST_DATA, CONSULT_INSURER, HITL_REVIEW, NOTIFY, CLOSE"
    )
    description: str = Field(..., description="Human-readable action description")
    target_role: Optional[str] = Field(None, description="Role responsible: AGENT, SUPERVISOR, SYSTEM")
    priority: int = Field(default=1, ge=1, le=5, description="Priority 1=highest")
    deadline_minutes: Optional[int] = Field(None, description="Suggested completion time")
    parameters: dict = Field(default_factory=dict, description="Action-specific parameters")


class Decision(BaseModel):
    """
    Final decision for a policy validation case.

    Combines checklist outcomes, ML signals, and guardrail checks.
    """

    decision_id: str = Field(..., description="Decision identifier")
    case_id: str = Field(..., description="Associated case identifier")

    # Primary decision
    status: DecisionStatus = Field(..., description="Final decision status")
    status_reason: str = Field(..., description="Explanation of decision")

    # Confidence and risk assessment
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall decision confidence")
    risk_level: float = Field(..., ge=0.0, le=1.0, description="Risk assessment score")
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Anomaly detection score")

    # ETA prediction
    eta_estimate_minutes: Optional[int] = Field(None, description="Predicted resolution time")

    # Decision factors
    auto_close_eligible: bool = Field(
        default=False, description="Whether case qualified for auto-close"
    )
    hitl_required: bool = Field(default=False, description="Whether HITL review is required")
    hitl_reason: Optional[str] = Field(None, description="Reason for HITL escalation")

    # Thresholds used (for reproducibility)
    thresholds_version: str = Field(..., description="Version of threshold config used")
    thresholds_applied: dict = Field(default_factory=dict, description="Actual threshold values")

    # Next actions
    next_actions: list[NextAction] = Field(default_factory=list)

    # Explanation for transparency
    explanation_summary: str = Field(..., description="Brief explanation for user/auditor")
    explanation_details: list[str] = Field(
        default_factory=list, description="Detailed reasoning steps"
    )

    # Evidence references
    primary_evidence_ids: list[str] = Field(
        default_factory=list, description="Key evidence supporting decision"
    )
    rule_ids_decisive: list[str] = Field(
        default_factory=list, description="Rules that determined outcome"
    )

    # Metadata
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    decided_by: str = Field(default="SYSTEM", description="SYSTEM or user ID if HITL")
    processing_duration_ms: Optional[int] = Field(None)

    def requires_external_consultation(self) -> bool:
        """Check if decision requires insurer consultation."""
        return self.status == DecisionStatus.PENDING_ASEGURADORA

    def is_terminal(self) -> bool:
        """Check if decision is a final state."""
        return self.status in (
            DecisionStatus.APPROVED,
            DecisionStatus.OBSERVED,
            DecisionStatus.REJECTED,
        )
