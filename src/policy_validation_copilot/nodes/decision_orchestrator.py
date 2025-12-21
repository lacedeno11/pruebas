"""
Decision Orchestrator Node.

UC-OP-08: Combines signals to make final decision with threshold evaluation.
"""

import logging
from typing import Any
from uuid import uuid4
from datetime import datetime

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.decision import Decision, DecisionStatus, NextAction
from policy_validation_copilot.models.case import CaseState
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper
from policy_validation_copilot.guardrails.service import GuardrailsService

logger = logging.getLogger(__name__)

# Threshold configuration (in production, loaded from config service)
THRESHOLDS = {
    "version": "1.0.0",
    "confidence_high": 0.85,
    "confidence_medium": 0.60,
    "risk_low": 0.30,
    "risk_high": 0.70,
    "anomaly_high": 0.75,
    "coverage_min": 0.70,
}


@node_wrapper(NodeType.DECISION_ORCHESTRATOR, "decision_orchestrator")
async def decision_orchestrator_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Decision orchestrator node.

    Responsibilities:
    1. Consolidate all signals (checklist, ML, guardrails)
    2. Calculate confidence and risk scores
    3. Apply threshold rules
    4. Determine auto-close eligibility
    5. Build decision with explanation and next actions
    """
    if not state.case:
        raise ValueError("No case available for decision")
    if not state.checklist:
        raise ValueError("No checklist available for decision")

    case = state.case
    checklist = state.checklist
    evidence_pack = state.evidence_pack
    ml = state.ml

    guardrails_service = GuardrailsService()

    # Calculate confidence score
    confidence_score = _calculate_confidence(state)

    # Calculate risk level
    risk_level = _calculate_risk(state)

    # Get anomaly score from ML
    anomaly_score = 0.0
    if ml and ml.anomaly:
        anomaly_score = ml.anomaly.anomaly_score

    # Get ETA estimate
    eta_minutes = None
    if ml and ml.eta:
        eta_minutes = ml.eta.eta_minutes

    # Determine decision status
    status, status_reason, explanation_details = _determine_status(
        checklist, evidence_pack, confidence_score, risk_level, anomaly_score
    )

    # Check auto-close eligibility (RB-08-01)
    auto_close_eligible = (
        confidence_score >= THRESHOLDS["confidence_high"]
        and risk_level <= THRESHOLDS["risk_low"]
        and anomaly_score < THRESHOLDS["anomaly_high"]
        and evidence_pack is not None
        and evidence_pack.coverage_score >= THRESHOLDS["coverage_min"]
        and checklist.can_auto_approve()
        and status in (DecisionStatus.APPROVED, DecisionStatus.OBSERVED)
    )

    # Determine if HITL required
    hitl_required = not auto_close_eligible and status != DecisionStatus.REJECTED
    hitl_reason = None

    if hitl_required:
        hitl_reason = _get_hitl_reason(
            confidence_score, risk_level, anomaly_score, checklist, evidence_pack
        )

    # Build next actions
    next_actions = _build_next_actions(status, hitl_required, checklist)

    # Build explanation
    explanation_summary = _build_explanation_summary(
        status, confidence_score, risk_level, checklist
    )

    # Create decision
    decision = Decision(
        decision_id=str(uuid4()),
        case_id=case.case_id,
        status=status,
        status_reason=status_reason,
        confidence_score=confidence_score,
        risk_level=risk_level,
        anomaly_score=anomaly_score,
        eta_estimate_minutes=eta_minutes,
        auto_close_eligible=auto_close_eligible,
        hitl_required=hitl_required,
        hitl_reason=hitl_reason,
        thresholds_version=THRESHOLDS["version"],
        thresholds_applied=THRESHOLDS,
        next_actions=next_actions,
        explanation_summary=explanation_summary,
        explanation_details=explanation_details,
        primary_evidence_ids=[
            item.evidence_id for item in (evidence_pack.items[:3] if evidence_pack else [])
        ],
        rule_ids_decisive=[
            item.rule_id
            for item in checklist.items
            if item.is_blocking and item.outcome.value in ("FAILED", "MISSING")
        ],
    )

    # Apply output guardrails
    state.decision = decision  # Temporarily set for guardrail check
    guardrail_result = await guardrails_service.evaluate(
        state, checkpoint="OUTPUT"
    )

    if not guardrail_result.can_proceed():
        decision.hitl_required = True
        decision.hitl_reason = "Guardrail check failed"
        hitl_required = True

    # Update case state
    if auto_close_eligible:
        case.state = CaseState(status.value) if status.value in [s.value for s in CaseState] else CaseState.PROCESSING
    elif hitl_required:
        case.state = CaseState.HITL_REVIEW
    else:
        case.state = CaseState.PROCESSING

    logger.info(
        f"Case {case.case_id} decision: {status.value}, "
        f"confidence={confidence_score:.2f}, risk={risk_level:.2f}, "
        f"auto_close={auto_close_eligible}, hitl={hitl_required}"
    )

    return {
        "case": case,
        "decision": decision,
        "hitl_required": hitl_required,
        "guardrails": guardrail_result,
        "guardrail_history": state.guardrail_history + [guardrail_result],
    }


def _calculate_confidence(state: PolicyValidationState) -> float:
    """Calculate overall confidence score."""
    scores = []

    # Evidence coverage
    if state.evidence_pack:
        scores.append(state.evidence_pack.coverage_score)

    # Checklist pass rate
    if state.checklist and state.checklist.total_items > 0:
        pass_rate = state.checklist.passed_count / state.checklist.total_items
        scores.append(pass_rate)

    # ML classification confidence
    if state.ml and state.ml.classify:
        scores.append(state.ml.classify.route_confidence)

    if not scores:
        return 0.5

    return sum(scores) / len(scores)


def _calculate_risk(state: PolicyValidationState) -> float:
    """Calculate overall risk level."""
    risk_factors = []

    # ML risk prior
    if state.ml and state.ml.classify:
        risk_factors.append(state.ml.classify.risk_prior)

    # Anomaly score
    if state.ml and state.ml.anomaly:
        risk_factors.append(state.ml.anomaly.anomaly_score)

    # Checklist failures
    if state.checklist and state.checklist.total_items > 0:
        failure_rate = (
            state.checklist.failed_count + state.checklist.missing_count
        ) / state.checklist.total_items
        risk_factors.append(failure_rate)

    # Low coverage
    if state.evidence_pack:
        risk_factors.append(1 - state.evidence_pack.coverage_score)

    if not risk_factors:
        return 0.5

    return sum(risk_factors) / len(risk_factors)


def _determine_status(
    checklist,
    evidence_pack,
    confidence: float,
    risk: float,
    anomaly: float,
) -> tuple[DecisionStatus, str, list[str]]:
    """Determine decision status based on all factors."""
    details = []

    # Check for blocking failures
    if checklist.has_blocking_failures():
        failed_rules = [
            i.rule_id for i in checklist.items
            if i.is_blocking and i.outcome.value == "FAILED"
        ]
        details.append(f"Blocking rule failures: {failed_rules}")
        return (
            DecisionStatus.REJECTED,
            "Blocking rules failed",
            details,
        )

    # Check for missing critical data
    if checklist.missing_count > 0 and any(f.is_critical for f in checklist.missing_fields):
        details.append(f"Missing critical fields: {[f.field_name for f in checklist.missing_fields]}")
        return (
            DecisionStatus.PENDING_DATOS,
            "Critical data missing",
            details,
        )

    # Check for insufficient evidence
    if evidence_pack and evidence_pack.coverage_score < 0.5:
        details.append(f"Low evidence coverage: {evidence_pack.coverage_score:.2f}")
        return (
            DecisionStatus.PENDING_POLITICA,
            "Insufficient policy evidence",
            details,
        )

    # Check for high anomaly
    if anomaly >= THRESHOLDS["anomaly_high"]:
        details.append(f"High anomaly score: {anomaly:.2f}")
        return (
            DecisionStatus.ESCALATE_HITL,
            "Anomaly detected - requires review",
            details,
        )

    # Check confidence thresholds
    if confidence >= THRESHOLDS["confidence_high"] and risk <= THRESHOLDS["risk_low"]:
        details.append("High confidence, low risk - eligible for auto-approval")
        return (
            DecisionStatus.APPROVED,
            "All checks passed with high confidence",
            details,
        )

    if confidence >= THRESHOLDS["confidence_medium"]:
        details.append("Medium confidence - approved with observations")
        return (
            DecisionStatus.OBSERVED,
            "Approved with observations for review",
            details,
        )

    # Default to escalation
    details.append(f"Low confidence ({confidence:.2f}) or high risk ({risk:.2f})")
    return (
        DecisionStatus.ESCALATE_HITL,
        "Requires human review due to low confidence",
        details,
    )


def _get_hitl_reason(
    confidence: float,
    risk: float,
    anomaly: float,
    checklist,
    evidence_pack,
) -> str:
    """Get specific reason for HITL escalation."""
    reasons = []

    if confidence < THRESHOLDS["confidence_medium"]:
        reasons.append(f"low confidence ({confidence:.2f})")

    if risk > THRESHOLDS["risk_high"]:
        reasons.append(f"high risk ({risk:.2f})")

    if anomaly >= THRESHOLDS["anomaly_high"]:
        reasons.append(f"anomaly detected ({anomaly:.2f})")

    if evidence_pack and evidence_pack.coverage_score < THRESHOLDS["coverage_min"]:
        reasons.append(f"insufficient coverage ({evidence_pack.coverage_score:.2f})")

    if checklist.missing_count > 0:
        reasons.append(f"{checklist.missing_count} missing fields")

    return "HITL required: " + ", ".join(reasons) if reasons else "Manual review required"


def _build_next_actions(
    status: DecisionStatus,
    hitl_required: bool,
    checklist,
) -> list[NextAction]:
    """Build list of next actions based on decision."""
    actions = []

    if status == DecisionStatus.PENDING_DATOS:
        for field in checklist.missing_fields:
            actions.append(
                NextAction(
                    action_id=str(uuid4()),
                    action_type="REQUEST_DATA",
                    description=f"Request missing field: {field.field_name}",
                    target_role="AGENT",
                    priority=1 if field.is_critical else 2,
                    parameters={"field": field.field_name, "source": field.suggested_source},
                )
            )

    if hitl_required:
        actions.append(
            NextAction(
                action_id=str(uuid4()),
                action_type="HITL_REVIEW",
                description="Human review required",
                target_role="AGENT" if status != DecisionStatus.ESCALATE_HITL else "SUPERVISOR",
                priority=1,
            )
        )

    if status in (DecisionStatus.APPROVED, DecisionStatus.OBSERVED):
        actions.append(
            NextAction(
                action_id=str(uuid4()),
                action_type="CLOSE",
                description="Close case with decision",
                target_role="SYSTEM",
                priority=1,
            )
        )

    return actions


def _build_explanation_summary(
    status: DecisionStatus,
    confidence: float,
    risk: float,
    checklist,
) -> str:
    """Build human-readable explanation summary."""
    status_text = {
        DecisionStatus.APPROVED: "approved",
        DecisionStatus.OBSERVED: "approved with observations",
        DecisionStatus.REJECTED: "rejected",
        DecisionStatus.ESCALATE_HITL: "escalated for human review",
        DecisionStatus.PENDING_DATOS: "pending additional data",
        DecisionStatus.PENDING_POLITICA: "pending policy clarification",
        DecisionStatus.PENDING_ASEGURADORA: "pending insurer response",
        DecisionStatus.PENDING_SISTEMA: "pending system availability",
    }

    summary = f"Case {status_text.get(status, 'processed')}. "
    summary += f"Confidence: {confidence:.0%}, Risk: {risk:.0%}. "
    summary += f"Checklist: {checklist.passed_count}/{checklist.total_items} passed."

    return summary
