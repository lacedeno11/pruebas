"""
Policy Retrieval Node.

UC-OP-06: RAG-based policy retrieval and evidence pack construction.
"""

import logging
from typing import Any

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper
from policy_validation_copilot.services.kb_service import KnowledgeBaseService
from policy_validation_copilot.guardrails.source_validator import SourceValidator

logger = logging.getLogger(__name__)


@node_wrapper(NodeType.POLICY_RETRIEVAL, "policy_retrieval")
async def policy_retrieval_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Policy retrieval node (RAG).

    Responsibilities:
    1. Build semantic query from case context
    2. Retrieve relevant policy documents
    3. Extract and validate evidence items
    4. Calculate coverage score
    5. Detect conflicts between sources
    """
    if not state.case:
        raise ValueError("No case available for policy retrieval")

    case = state.case
    kb_service = KnowledgeBaseService()
    source_validator = SourceValidator()

    # Build query from case context
    query_parts = []
    if case.service_code:
        query_parts.append(f"service code {case.service_code}")
    if case.service_description:
        query_parts.append(case.service_description)

    query = " ".join(query_parts) if query_parts else "policy coverage validation"

    # Build case context for retrieval
    case_context = {
        "case_id": case.case_id,
        "insurer_id": case.insurer_id,
        "plan_id": case.plan_id,
        "service_code": case.service_code,
        "service_date": case.service_date.isoformat() if case.service_date else None,
    }

    # Get candidate policies from ML if available
    candidate_policies = []
    if state.ml and state.ml.classify:
        candidate_policies = state.ml.classify.candidate_policy_ids

    # Retrieve evidence
    evidence_pack = await kb_service.retrieve_evidence(
        query=query,
        case_context=case_context,
        allowlist=candidate_policies if candidate_policies else None,
        top_k=10,
    )

    # Validate sources
    evidence_pack = source_validator.filter_allowed_only(evidence_pack)

    # Log coverage assessment
    logger.info(
        f"Case {case.case_id} evidence pack: "
        f"{len(evidence_pack.items)} items, "
        f"coverage={evidence_pack.coverage_score:.2f}, "
        f"conflicts={len(evidence_pack.conflicts)}"
    )

    # Check for insufficient coverage (A1: Política no encontrada)
    hitl_required = state.hitl_required
    if evidence_pack.coverage_score < 0.5:
        logger.warning(f"Case {case.case_id} has low coverage score")
        hitl_required = True

    # Check for conflicts
    if evidence_pack.conflicts_detected:
        logger.warning(f"Case {case.case_id} has evidence conflicts")
        hitl_required = True

    return {
        "evidence_pack": evidence_pack,
        "hitl_required": hitl_required,
    }
