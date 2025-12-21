"""
Human-in-the-Loop (HITL) data models.

Represents HITL requests, responses, and approvals.
Based on HITL gate requirements across all use cases.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HITLReason(str, Enum):
    """Reason for HITL escalation."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    HIGH_RISK = "HIGH_RISK"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    GUARDRAIL_TRIGGERED = "GUARDRAIL_TRIGGERED"
    EXCEPTION_APPROVAL = "EXCEPTION_APPROVAL"
    POLICY_APPROVAL = "POLICY_APPROVAL"
    MANUAL_REQUEST = "MANUAL_REQUEST"


class HITLStatus(str, Enum):
    """Status of HITL request."""

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"
    EXPIRED = "EXPIRED"


class HITLQuestion(BaseModel):
    """Specific question for human reviewer."""

    question_id: str = Field(..., description="Question identifier")
    question_text: str = Field(..., description="Question for reviewer")
    question_type: str = Field(..., description="YES_NO, MULTIPLE_CHOICE, FREE_TEXT, CONFIRM")
    options: list[str] = Field(default_factory=list, description="Options if applicable")
    is_required: bool = Field(default=True)
    context: Optional[str] = Field(None, description="Additional context for reviewer")
    evidence_refs: list[str] = Field(default_factory=list, description="Related evidence IDs")


class HITLAnswer(BaseModel):
    """Answer provided by human reviewer."""

    question_id: str = Field(..., description="Answered question ID")
    answer_value: str = Field(..., description="The answer provided")
    answer_notes: Optional[str] = Field(None, description="Additional notes")
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    answered_by: str = Field(..., description="Reviewer user ID")


class HITLRequest(BaseModel):
    """
    Request for human review.

    Created when confidence is low or risk is high.
    """

    request_id: str = Field(..., description="HITL request identifier")
    case_id: str = Field(..., description="Associated case identifier")

    # Escalation context
    reason: HITLReason = Field(..., description="Primary reason for escalation")
    reason_details: str = Field(..., description="Detailed explanation")
    urgency: str = Field(default="NORMAL", description="LOW, NORMAL, HIGH, CRITICAL")

    # Current state snapshot
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: float = Field(..., ge=0.0, le=1.0)
    anomaly_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Questions for reviewer
    questions: list[HITLQuestion] = Field(default_factory=list)

    # Suggested decision (for reviewer reference)
    suggested_decision: Optional[str] = Field(None)
    suggested_reasoning: Optional[str] = Field(None)

    # Assignment
    status: HITLStatus = Field(default=HITLStatus.PENDING)
    assigned_to: Optional[str] = Field(None, description="Assigned reviewer user ID")
    assigned_queue: Optional[str] = Field(None, description="Queue for assignment")
    required_role: str = Field(default="AGENT", description="Required role: AGENT, SUPERVISOR")

    # SLA
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sla_deadline: Optional[datetime] = Field(None)
    escalation_count: int = Field(default=0)

    # Evidence references for review
    evidence_pack_id: Optional[str] = Field(None)
    checklist_id: Optional[str] = Field(None)


class HITLResponse(BaseModel):
    """Response from human reviewer."""

    response_id: str = Field(..., description="Response identifier")
    request_id: str = Field(..., description="Original request ID")
    case_id: str = Field(..., description="Associated case ID")

    # Answers
    answers: list[HITLAnswer] = Field(default_factory=list)

    # Decision
    decision: str = Field(..., description="APPROVE, REJECT, RETURN, ESCALATE")
    decision_notes: str = Field(..., description="Explanation of decision")

    # Corrections/overrides
    corrections: dict = Field(default_factory=dict, description="Data corrections made")
    override_confidence: Optional[float] = Field(None, description="Adjusted confidence if any")
    override_risk: Optional[float] = Field(None, description="Adjusted risk if any")

    # Metadata
    responded_at: datetime = Field(default_factory=datetime.utcnow)
    responded_by: str = Field(..., description="Reviewer user ID")
    review_duration_minutes: Optional[int] = Field(None)


class HITLApproval(BaseModel):
    """
    Formal approval record for auditing.

    Used for exceptions, policies, and critical decisions.
    """

    approval_id: str = Field(..., description="Approval identifier")
    entity_type: str = Field(..., description="CASE, EXCEPTION, POLICY, RULE")
    entity_id: str = Field(..., description="Approved entity ID")

    # Approval details
    approved: bool = Field(..., description="Whether approved or rejected")
    approval_type: str = Field(..., description="STANDARD, EXCEPTION, EMERGENCY")
    conditions: list[str] = Field(default_factory=list, description="Conditions of approval")

    # Approver info
    approved_by: str = Field(..., description="Approver user ID")
    approver_role: str = Field(..., description="Role at time of approval")

    # Evidence
    justification: str = Field(..., description="Justification for approval")
    evidence_refs: list[str] = Field(default_factory=list)

    # Metadata
    approved_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="If approval has expiration")

    # Audit
    ip_address: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
