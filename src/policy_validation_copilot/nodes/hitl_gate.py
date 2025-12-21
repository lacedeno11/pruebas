"""
HITL Gate Node.

Handles Human-in-the-Loop escalation and response processing.
"""

import logging
from typing import Any
from uuid import uuid4
from datetime import datetime, timedelta

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.hitl import (
    HITLRequest,
    HITLReason,
    HITLStatus,
    HITLQuestion,
)
from policy_validation_copilot.models.decision import DecisionStatus
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper

logger = logging.getLogger(__name__)


@node_wrapper(NodeType.GUARDRAILS, "hitl_gate")  # Using GUARDRAILS as proxy
async def hitl_gate_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    HITL gate node.

    Responsibilities:
    1. Evaluate if HITL is required
    2. Create HITL request with context
    3. Build questions for reviewer
    4. Assign to appropriate queue
    5. Wait for or process HITL response
    """
    if not state.case:
        raise ValueError("No case available for HITL gate")
    if not state.decision:
        raise ValueError("No decision available for HITL gate")

    case = state.case
    decision = state.decision

    # If HITL response already received, process it
    if state.hitl_response:
        return _process_hitl_response(state)

    # If HITL not required, pass through
    if not state.hitl_required and not decision.hitl_required:
        logger.info(f"Case {case.case_id} does not require HITL, passing through")
        return {}

    # Determine HITL reason
    reason = _determine_hitl_reason(state)

    # Determine required role
    required_role = "AGENT"
    if reason in (HITLReason.EXCEPTION_APPROVAL, HITLReason.POLICY_APPROVAL):
        required_role = "SUPERVISOR"
    if decision.status == DecisionStatus.ESCALATE_HITL:
        required_role = "SUPERVISOR"

    # Build questions for reviewer
    questions = _build_hitl_questions(state, reason)

    # Calculate SLA for HITL
    sla_minutes = 60 if required_role == "AGENT" else 120
    if case.priority.value == "URGENT":
        sla_minutes = sla_minutes // 2

    # Create HITL request
    hitl_request = HITLRequest(
        request_id=str(uuid4()),
        case_id=case.case_id,
        reason=reason,
        reason_details=decision.hitl_reason or "Manual review required",
        urgency="HIGH" if case.priority.value in ("HIGH", "URGENT") else "NORMAL",
        confidence_score=decision.confidence_score,
        risk_level=decision.risk_level,
        anomaly_score=decision.anomaly_score,
        questions=questions,
        suggested_decision=decision.status.value,
        suggested_reasoning=decision.explanation_summary,
        required_role=required_role,
        assigned_queue=f"{required_role.lower()}_queue",
        sla_deadline=datetime.utcnow() + timedelta(minutes=sla_minutes),
        evidence_pack_id=state.evidence_pack.pack_id if state.evidence_pack else None,
        checklist_id=state.checklist.checklist_id if state.checklist else None,
    )

    logger.info(
        f"Case {case.case_id} HITL request created: "
        f"reason={reason.value}, role={required_role}"
    )

    # Add to HITL history
    hitl_history = state.hitl_history + [
        {
            "request_id": hitl_request.request_id,
            "reason": reason.value,
            "created_at": datetime.utcnow().isoformat(),
        }
    ]

    return {
        "hitl_request": hitl_request,
        "hitl_history": hitl_history,
        "workflow_status": "WAITING_HITL",
    }


def _determine_hitl_reason(state: PolicyValidationState) -> HITLReason:
    """Determine the primary reason for HITL escalation."""
    decision = state.decision

    if decision.anomaly_score and decision.anomaly_score >= 0.75:
        return HITLReason.ANOMALY_DETECTED

    if decision.risk_level >= 0.7:
        return HITLReason.HIGH_RISK

    if decision.confidence_score < 0.6:
        return HITLReason.LOW_CONFIDENCE

    if decision.confidence_score < 0.85:
        return HITLReason.MEDIUM_CONFIDENCE

    if state.evidence_pack and state.evidence_pack.conflicts_detected:
        return HITLReason.POLICY_CONFLICT

    if state.evidence_pack and state.evidence_pack.coverage_score < 0.7:
        return HITLReason.EVIDENCE_INSUFFICIENT

    if state.guardrails and state.guardrails.requires_human_review():
        return HITLReason.GUARDRAIL_TRIGGERED

    return HITLReason.MANUAL_REQUEST


def _build_hitl_questions(
    state: PolicyValidationState,
    reason: HITLReason,
) -> list[HITLQuestion]:
    """Build questions for HITL reviewer."""
    questions = []

    # Standard confirmation question
    questions.append(
        HITLQuestion(
            question_id=str(uuid4()),
            question_text="Do you approve the suggested decision?",
            question_type="YES_NO",
            is_required=True,
            context=state.decision.explanation_summary if state.decision else None,
        )
    )

    # Reason-specific questions
    if reason == HITLReason.ANOMALY_DETECTED:
        questions.append(
            HITLQuestion(
                question_id=str(uuid4()),
                question_text="Is this case a legitimate anomaly or a false positive?",
                question_type="MULTIPLE_CHOICE",
                options=["Legitimate anomaly - investigate further", "False positive - proceed normally", "Needs more information"],
                is_required=True,
            )
        )

    if reason in (HITLReason.LOW_CONFIDENCE, HITLReason.MEDIUM_CONFIDENCE):
        questions.append(
            HITLQuestion(
                question_id=str(uuid4()),
                question_text="What additional evidence or information is needed?",
                question_type="FREE_TEXT",
                is_required=False,
            )
        )

    if reason == HITLReason.POLICY_CONFLICT:
        questions.append(
            HITLQuestion(
                question_id=str(uuid4()),
                question_text="Which policy interpretation should apply?",
                question_type="FREE_TEXT",
                is_required=True,
                context="Conflicting policies detected in evidence",
            )
        )

    if reason == HITLReason.EVIDENCE_INSUFFICIENT:
        questions.append(
            HITLQuestion(
                question_id=str(uuid4()),
                question_text="Should this case proceed with available evidence or request more?",
                question_type="MULTIPLE_CHOICE",
                options=["Proceed with current evidence", "Request additional documentation", "Consult insurer"],
                is_required=True,
            )
        )

    return questions


def _process_hitl_response(state: PolicyValidationState) -> dict[str, Any]:
    """Process received HITL response."""
    response = state.hitl_response
    decision = state.decision

    if not response:
        return {}

    logger.info(
        f"Processing HITL response for case {state.case.case_id}: "
        f"decision={response.decision}"
    )

    # Update decision based on HITL response
    if response.decision == "APPROVE":
        decision.status = DecisionStatus.APPROVED
        decision.decided_by = response.responded_by
    elif response.decision == "REJECT":
        decision.status = DecisionStatus.REJECTED
        decision.decided_by = response.responded_by
    elif response.decision == "RETURN":
        decision.status = DecisionStatus.PENDING_DATOS
    elif response.decision == "ESCALATE":
        decision.hitl_required = True
        decision.hitl_reason = "Escalated by reviewer"

    # Apply any overrides
    if response.override_confidence:
        decision.confidence_score = response.override_confidence
    if response.override_risk:
        decision.risk_level = response.override_risk

    # Update HITL history
    hitl_history = state.hitl_history + [
        {
            "response_id": response.response_id,
            "decision": response.decision,
            "responded_at": response.responded_at.isoformat(),
            "responded_by": response.responded_by,
        }
    ]

    return {
        "decision": decision,
        "hitl_response": None,  # Clear after processing
        "hitl_history": hitl_history,
        "workflow_status": "RUNNING",
    }
