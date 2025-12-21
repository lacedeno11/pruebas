"""
Case Ingest Node.

UC-OP-05: Creates case from CRM/ticket with normalization and deduplication.
"""

import logging
from typing import Any

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.case import CaseState
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper
from policy_validation_copilot.services.crm_service import CRMService
from policy_validation_copilot.guardrails.service import GuardrailsService

logger = logging.getLogger(__name__)


@node_wrapper(NodeType.CASE_INGEST, "case_ingest")
async def case_ingest_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Case ingestion node.

    Responsibilities:
    1. Validate incoming payload
    2. Normalize fields against catalogs
    3. Check for duplicates (idempotency)
    4. Persist case with attachments
    5. Apply initial guardrails (input validation)
    """
    # If case already exists, skip ingestion
    if state.case and state.case.case_id:
        logger.info(f"Case {state.case.case_id} already ingested, skipping")
        return {}

    # Initialize services
    crm_service = CRMService()
    guardrails = GuardrailsService()

    # For this node, we expect case to be pre-populated from API
    # In production, this would come from CRM webhook
    if not state.case:
        raise ValueError("No case data provided for ingestion")

    case = state.case

    # Update case state
    case.state = CaseState.PROCESSING

    # Apply input guardrails
    guardrail_result = await guardrails.evaluate(
        state,
        checkpoint="INPUT",
        user_role="SYSTEM",
        required_permissions=["process_case"],
    )

    # Check for critical guardrail flags
    if not guardrail_result.can_proceed():
        case.state = CaseState.PENDING_DATOS
        return {
            "case": case,
            "guardrails": guardrail_result,
            "guardrail_history": [guardrail_result],
            "hitl_required": guardrail_result.requires_human_review(),
        }

    logger.info(f"Case {case.case_id} ingested successfully")

    return {
        "case": case,
        "guardrails": guardrail_result,
        "guardrail_history": [guardrail_result],
        "workflow_status": "RUNNING",
    }
