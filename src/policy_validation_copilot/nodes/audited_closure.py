"""
Audited Closure Node.

UC-OP-04: Final case closure with complete audit trail.
"""

import logging
from typing import Any
from datetime import datetime

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.case import CaseState
from policy_validation_copilot.models.decision import DecisionStatus
from policy_validation_copilot.models.audit import NodeType, AuditTrail
from policy_validation_copilot.nodes.base import node_wrapper

logger = logging.getLogger(__name__)


@node_wrapper(NodeType.AUDITED_CLOSURE, "audited_closure")
async def audited_closure_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Audited closure node.

    Responsibilities:
    1. Validate all requirements for closure
    2. Build complete audit trail
    3. Persist final state
    4. Update case status
    5. Trigger notifications
    """
    if not state.case:
        raise ValueError("No case available for closure")
    if not state.decision:
        raise ValueError("No decision available for closure")

    case = state.case
    decision = state.decision

    # Validate closure eligibility
    if not _can_close(state):
        logger.warning(f"Case {case.case_id} cannot be closed yet")
        return {}

    # Build audit trail
    audit_trail = _build_audit_trail(state)

    # Update case to final state
    case.state = _map_decision_to_case_state(decision.status)
    case.updated_at = datetime.utcnow()

    # Mark decision as final
    decision.decided_at = datetime.utcnow()

    logger.info(
        f"Case {case.case_id} closed with status {case.state.value}. "
        f"Audit trail: {audit_trail.total_nodes_executed} nodes, "
        f"{audit_trail.total_duration_ms}ms total"
    )

    return {
        "case": case,
        "decision": decision,
        "workflow_status": "COMPLETED",
    }


def _can_close(state: PolicyValidationState) -> bool:
    """Check if case can be closed."""
    decision = state.decision

    # Cannot close if HITL still pending
    if state.workflow_status == "WAITING_HITL":
        return False

    # Cannot close if external query pending
    if state.pending_external_query:
        return False

    # Can close if decision is terminal
    if decision.is_terminal():
        return True

    # Can close if auto-close eligible
    if decision.auto_close_eligible:
        return True

    # Can close after HITL approval
    if state.hitl_response and state.hitl_response.decision in ("APPROVE", "REJECT"):
        return True

    return False


def _map_decision_to_case_state(status: DecisionStatus) -> CaseState:
    """Map decision status to case state."""
    mapping = {
        DecisionStatus.APPROVED: CaseState.APPROVED,
        DecisionStatus.OBSERVED: CaseState.APPROVED,  # Observed is still approved
        DecisionStatus.REJECTED: CaseState.REJECTED,
        DecisionStatus.ESCALATE_HITL: CaseState.HITL_REVIEW,
        DecisionStatus.PENDING_DATOS: CaseState.PENDING_DATOS,
        DecisionStatus.PENDING_POLITICA: CaseState.PENDING_POLITICA,
        DecisionStatus.PENDING_ASEGURADORA: CaseState.PENDING_ASEGURADORA,
        DecisionStatus.PENDING_SISTEMA: CaseState.PENDING_SISTEMA,
    }
    return mapping.get(status, CaseState.CLOSED)


def _build_audit_trail(state: PolicyValidationState) -> AuditTrail:
    """Build complete audit trail for the case."""
    from uuid import uuid4

    audit = AuditTrail(
        trail_id=str(uuid4()),
        case_id=state.case.case_id,
        node_executions=list(state.node_executions),
        final_decision_id=state.decision.decision_id,
        final_status=state.decision.status.value,
    )

    # Calculate totals
    audit.total_nodes_executed = len(audit.node_executions)
    audit.total_duration_ms = sum(
        e.duration_ms or 0 for e in audit.node_executions
    )
    audit.failed_nodes = [
        e.node_name for e in audit.node_executions if e.status == "FAILED"
    ]

    # Extract model versions
    if state.ml:
        if state.ml.classify:
            audit.model_versions["classify"] = state.ml.classify.model_version
        if state.ml.anomaly:
            audit.model_versions["anomaly"] = state.ml.anomaly.model_version
        if state.ml.eta:
            audit.model_versions["eta"] = state.ml.eta.model_version

    # Extract policy versions from evidence
    if state.evidence_pack:
        for item in state.evidence_pack.items:
            audit.policy_versions[item.doc_id] = item.doc_version

    # Rule set version
    if state.checklist:
        audit.rule_set_version = state.checklist.rule_set_version

    # Guardrail version
    if state.guardrails:
        audit.guardrail_version = state.guardrails.guardrail_version

    # Threshold version
    if state.decision:
        audit.threshold_config_version = state.decision.thresholds_version

    # HITL tracking
    if state.hitl_request:
        audit.hitl_requests.append(state.hitl_request.request_id)
    if state.hitl_response:
        audit.hitl_responses.append(state.hitl_response.response_id)

    audit.closed_at = datetime.utcnow()

    return audit
