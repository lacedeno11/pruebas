"""
Insurer Connector Node.

UC-OP-09: External consultation with insurance companies.
"""

import logging
from typing import Any
from uuid import uuid4
from datetime import datetime

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.evidence import EvidenceItem, EvidenceType
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper

logger = logging.getLogger(__name__)


@node_wrapper(NodeType.INSURER_CONNECTOR, "insurer_connector")
async def insurer_connector_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Insurer connector node for external consultations.

    Responsibilities:
    1. Prepare structured query for insurer
    2. Execute appropriate channel (API/portal/email)
    3. Capture and normalize response
    4. Add response as evidence
    5. Handle timeouts and retries
    """
    if not state.case:
        raise ValueError("No case available for insurer consultation")

    case = state.case

    # Check if external consultation is needed
    if not state.pending_external_query:
        logger.info(f"Case {case.case_id} does not require external consultation")
        return {}

    query_context = state.external_query_context or {}

    # Simulate external consultation
    # In production, this would:
    # 1. Determine appropriate channel for insurer
    # 2. Format query according to insurer's API/format
    # 3. Execute request with proper authentication
    # 4. Handle async responses (polling/webhooks)

    try:
        response = await _execute_insurer_query(
            insurer_id=case.insurer_id,
            query=query_context.get("query", "coverage verification"),
            case_context={
                "case_id": case.case_id,
                "service_code": case.service_code,
                "customer_id": case.customer_id,
            },
        )

        # Create evidence item from response
        response_evidence = EvidenceItem(
            evidence_id=str(uuid4()),
            doc_id=f"EXT-{case.insurer_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            doc_version="1.0",
            checksum=_compute_checksum(str(response)),
            pointer="external_response:1",
            evidence_type=EvidenceType.EXTERNAL_RESPONSE,
            excerpt=response.get("response_text", ""),
            relevance_score=1.0,  # Direct response is always relevant
            confidence_score=0.95,
            is_allowlisted=True,  # External responses are trusted
        )

        # Add to evidence pack
        if state.evidence_pack:
            state.evidence_pack.items.append(response_evidence)

        logger.info(
            f"Case {case.case_id} received insurer response: "
            f"{response.get('status', 'unknown')}"
        )

        return {
            "pending_external_query": False,
            "external_query_context": None,
            "evidence_pack": state.evidence_pack,
        }

    except Exception as e:
        logger.error(f"Insurer consultation failed for case {case.case_id}: {e}")

        # Update state for retry or escalation
        retry_count = state.retry_count + 1

        if retry_count >= state.max_retries:
            # Mark as pending insurer response
            from policy_validation_copilot.models.case import CaseState

            case.state = CaseState.PENDING_ASEGURADORA

            return {
                "case": case,
                "pending_external_query": True,
                "retry_count": retry_count,
                "hitl_required": True,  # Escalate after max retries
            }

        return {
            "pending_external_query": True,
            "retry_count": retry_count,
        }


async def _execute_insurer_query(
    insurer_id: str,
    query: str,
    case_context: dict,
) -> dict:
    """
    Execute query to insurer's system.

    In production, this would integrate with:
    - REST APIs
    - SOAP services
    - Portal automation
    - Email systems
    """
    # Simulate response
    return {
        "status": "success",
        "response_text": f"Coverage confirmed for service in plan. Insurer reference: {insurer_id}-REF-{datetime.utcnow().strftime('%Y%m%d')}",
        "timestamp": datetime.utcnow().isoformat(),
        "channel": "API",
        "reference_id": str(uuid4()),
    }


def _compute_checksum(content: str) -> str:
    """Compute checksum for content."""
    import hashlib

    return hashlib.sha256(content.encode()).hexdigest()
