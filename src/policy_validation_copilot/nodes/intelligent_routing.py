"""
Intelligent Routing Node.

UC-OP-11/12/13: ML-based classification, anomaly detection, and ETA prediction.
"""

import logging
from typing import Any

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.ml import MLOutputs
from policy_validation_copilot.models.audit import NodeType
from policy_validation_copilot.nodes.base import node_wrapper
from policy_validation_copilot.services.ml_service import MLService

logger = logging.getLogger(__name__)


@node_wrapper(NodeType.INTELLIGENT_ROUTING, "intelligent_routing")
async def intelligent_routing_node(state: PolicyValidationState) -> dict[str, Any]:
    """
    Intelligent routing node with ML integration.

    Responsibilities:
    1. Execute ML classification (UC-OP-11)
    2. Execute anomaly detection (UC-OP-12)
    3. Execute ETA prediction (UC-OP-13)
    4. Determine initial route (AUTO vs HITL)
    5. Flag high-risk or anomalous cases
    """
    if not state.case:
        raise ValueError("No case available for routing")

    case = state.case
    ml_service = MLService(fallback_enabled=True)

    try:
        # Execute ML services in parallel (conceptually)
        # In production, use asyncio.gather for true parallelism

        # 1. Classification and routing
        classify_output = await ml_service.classify(case)
        logger.info(
            f"Case {case.case_id} classified as {classify_output.request_type} "
            f"with route {classify_output.route}"
        )

        # 2. Anomaly detection
        anomaly_output = await ml_service.detect_anomaly(case)
        logger.info(
            f"Case {case.case_id} anomaly score: {anomaly_output.anomaly_score}"
        )

        # 3. ETA prediction
        eta_output = await ml_service.predict_eta(case)
        logger.info(f"Case {case.case_id} ETA: {eta_output.eta_minutes} minutes")

        # Aggregate ML outputs
        ml_outputs = MLOutputs(
            classify=classify_output,
            anomaly=anomaly_output,
            eta=eta_output,
        )
        ml_outputs.update_degradation_status()

        # Determine if HITL required based on ML signals
        hitl_required = False
        hitl_reason = None

        # High anomaly score triggers HITL (RB-12-01)
        if anomaly_output.is_anomalous:
            hitl_required = True
            hitl_reason = f"Anomaly detected: {anomaly_output.anomaly_score:.2f}"

        # High risk prior triggers HITL
        if classify_output.risk_prior > 0.7:
            hitl_required = True
            hitl_reason = f"High risk prior: {classify_output.risk_prior:.2f}"

        # ML routed to HITL
        if classify_output.route in ("HITL_AGENT", "HITL_SUPERVISOR"):
            hitl_required = True
            hitl_reason = f"ML routed to {classify_output.route}"

        # Update case queue based on routing
        case.assigned_queue = classify_output.route

        return {
            "case": case,
            "ml": ml_outputs,
            "hitl_required": hitl_required,
        }

    finally:
        await ml_service.close()
