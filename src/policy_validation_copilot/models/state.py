"""
LangGraph State Schema.

Main state object that flows through the LangGraph workflow.
Based on DERCAS 01 Anexo A - Variables de Estado LangGraph.
"""

from datetime import datetime
from typing import Annotated, Optional
from operator import add

from pydantic import BaseModel, Field

from policy_validation_copilot.models.case import Case
from policy_validation_copilot.models.evidence import EvidencePack
from policy_validation_copilot.models.checklist import Checklist
from policy_validation_copilot.models.decision import Decision
from policy_validation_copilot.models.ml import MLOutputs
from policy_validation_copilot.models.guardrails import GuardrailResult
from policy_validation_copilot.models.hitl import HITLRequest, HITLResponse
from policy_validation_copilot.models.audit import NodeExecution


class PolicyValidationState(BaseModel):
    """
    LangGraph state schema for Policy Validation Copilot.

    This is the main state object that flows through all nodes in the workflow.
    Based on Anexo A state schema requirements.
    """

    # ===== CASE =====
    # Core case information (UC-OP-05)
    case: Optional[Case] = Field(None, description="Case entity with all identifiers and context")

    # ===== EVIDENCE PACK =====
    # Retrieved policy evidence (UC-OP-06)
    evidence_pack: Optional[EvidencePack] = Field(
        None, description="Evidence pack with documents, excerpts, and coverage"
    )

    # ===== CHECKLIST =====
    # Rule evaluation results (UC-OP-07)
    checklist: Optional[Checklist] = Field(
        None, description="Checklist with rule evaluations and missing fields"
    )

    # ===== ML OUTPUTS =====
    # Machine learning service outputs (UC-OP-11/12/13)
    ml: Optional[MLOutputs] = Field(
        None, description="ML outputs: classification, anomaly, ETA"
    )

    # ===== DECISION =====
    # Final decision and orchestration (UC-OP-08)
    decision: Optional[Decision] = Field(
        None, description="Decision with confidence, risk, and next actions"
    )

    # ===== GUARDRAILS =====
    # Security and governance results (UC-OP-10)
    guardrails: Optional[GuardrailResult] = Field(
        None, description="Latest guardrail evaluation result"
    )
    guardrail_history: list[GuardrailResult] = Field(
        default_factory=list, description="All guardrail checks performed"
    )

    # ===== HITL =====
    # Human-in-the-loop state
    hitl_required: bool = Field(default=False, description="Whether HITL review is needed")
    hitl_request: Optional[HITLRequest] = Field(None, description="Active HITL request")
    hitl_response: Optional[HITLResponse] = Field(None, description="HITL response if received")
    hitl_history: list[dict] = Field(
        default_factory=list, description="History of HITL interactions"
    )

    # ===== AUDIT =====
    # Node execution log
    node_executions: Annotated[list[NodeExecution], add] = Field(
        default_factory=list, description="LangGraph node execution trace"
    )

    # ===== WORKFLOW CONTROL =====
    # Current workflow state
    current_node: Optional[str] = Field(None, description="Currently executing node")
    workflow_status: str = Field(
        default="INITIALIZED", description="INITIALIZED, RUNNING, WAITING_HITL, COMPLETED, FAILED"
    )

    # Error handling
    errors: list[dict] = Field(default_factory=list, description="Errors encountered")
    last_error: Optional[str] = Field(None)

    # External consultation state (UC-OP-09)
    pending_external_query: bool = Field(default=False)
    external_query_context: Optional[dict] = Field(None)

    # Retry tracking
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    # ===== METADATA =====
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Configuration versions for reproducibility
    config_versions: dict = Field(
        default_factory=lambda: {
            "thresholds": "1.0.0",
            "guardrails": "1.0.0",
            "rules": "1.0.0",
        }
    )

    class Config:
        arbitrary_types_allowed = True

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.utcnow()

    def add_error(self, error_type: str, message: str, node: Optional[str] = None) -> None:
        """Record an error in the state."""
        self.errors.append({
            "type": error_type,
            "message": message,
            "node": node or self.current_node,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.last_error = message
        self.update_timestamp()

    def can_auto_close(self) -> bool:
        """Check if case qualifies for automatic closure."""
        if not self.decision:
            return False

        return (
            self.decision.auto_close_eligible
            and not self.hitl_required
            and (self.guardrails is None or self.guardrails.can_proceed())
            and self.workflow_status not in ("WAITING_HITL", "FAILED")
        )

    def requires_hitl(self) -> bool:
        """Check if HITL review is required."""
        if self.hitl_required:
            return True

        if self.decision and self.decision.hitl_required:
            return True

        if self.guardrails and self.guardrails.requires_human_review():
            return True

        if self.ml and self.ml.anomaly and self.ml.anomaly.is_anomalous:
            return True

        return False

    def get_summary(self) -> dict:
        """Get a summary of current state for logging/display."""
        return {
            "case_id": self.case.case_id if self.case else None,
            "case_state": self.case.state if self.case else None,
            "workflow_status": self.workflow_status,
            "current_node": self.current_node,
            "hitl_required": self.requires_hitl(),
            "decision_status": self.decision.status if self.decision else None,
            "confidence": self.decision.confidence_score if self.decision else None,
            "risk": self.decision.risk_level if self.decision else None,
            "coverage": self.evidence_pack.coverage_score if self.evidence_pack else None,
            "errors_count": len(self.errors),
            "nodes_executed": len(self.node_executions),
        }
