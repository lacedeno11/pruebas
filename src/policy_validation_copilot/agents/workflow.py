"""
Main LangGraph Workflow for Policy Validation Copilot.

UC-OP-01: Complete validation workflow from ingestion to closure.
Implements the TO-BE agentic architecture with LangGraph.
"""

import logging
from typing import Literal, Any
from uuid import uuid4

from langgraph.graph import StateGraph, END

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.case import Case, CaseState
from policy_validation_copilot.nodes import (
    case_ingest_node,
    intelligent_routing_node,
    policy_retrieval_node,
    rules_checklist_node,
    decision_orchestrator_node,
    insurer_connector_node,
    hitl_gate_node,
    audited_closure_node,
)

logger = logging.getLogger(__name__)


# Node names as constants
CASE_INGEST = "case_ingest"
INTELLIGENT_ROUTING = "intelligent_routing"
POLICY_RETRIEVAL = "policy_retrieval"
RULES_CHECKLIST = "rules_checklist"
DECISION_ORCHESTRATOR = "decision_orchestrator"
INSURER_CONNECTOR = "insurer_connector"
HITL_GATE = "hitl_gate"
AUDITED_CLOSURE = "audited_closure"


def should_route_to_hitl(state: PolicyValidationState) -> Literal["hitl_gate", "audited_closure"]:
    """
    Conditional edge: decide if HITL is required.

    Based on:
    - confidence thresholds
    - risk level
    - anomaly detection
    - guardrail flags
    """
    if state.hitl_required:
        logger.info(f"Case {state.case.case_id if state.case else 'unknown'} routed to HITL")
        return HITL_GATE

    if state.decision and state.decision.hitl_required:
        logger.info(f"Case {state.case.case_id if state.case else 'unknown'} requires HITL per decision")
        return HITL_GATE

    if state.decision and state.decision.auto_close_eligible:
        logger.info(f"Case {state.case.case_id if state.case else 'unknown'} eligible for auto-close")
        return AUDITED_CLOSURE

    # Default to HITL for safety
    return HITL_GATE


def should_consult_insurer(
    state: PolicyValidationState,
) -> Literal["insurer_connector", "decision_orchestrator"]:
    """
    Conditional edge: decide if external insurer consultation is needed.
    """
    if state.pending_external_query:
        return INSURER_CONNECTOR

    # Check if decision requires external confirmation
    if state.decision and state.decision.requires_external_consultation():
        return INSURER_CONNECTOR

    return DECISION_ORCHESTRATOR


def after_hitl_gate(
    state: PolicyValidationState,
) -> Literal["audited_closure", "policy_retrieval", "__end__"]:
    """
    Conditional edge after HITL gate.

    Routes based on HITL response or waiting state.
    """
    if state.workflow_status == "WAITING_HITL":
        # Waiting for HITL response - end this execution
        # (will resume when response received)
        return END

    if state.hitl_response:
        if state.hitl_response.decision == "RETURN":
            # Need more data - go back to retrieval
            return POLICY_RETRIEVAL

    return AUDITED_CLOSURE


def create_policy_validation_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for policy validation.

    Workflow structure:
    1. case_ingest -> intelligent_routing
    2. intelligent_routing -> policy_retrieval
    3. policy_retrieval -> rules_checklist
    4. rules_checklist -> decision_orchestrator
    5. decision_orchestrator -> [hitl_gate | audited_closure]
    6. hitl_gate -> [audited_closure | policy_retrieval | END]
    7. audited_closure -> END

    Optional branch:
    - decision_orchestrator -> insurer_connector -> policy_retrieval
    """
    # Create workflow with state schema
    workflow = StateGraph(PolicyValidationState)

    # Add nodes
    workflow.add_node(CASE_INGEST, case_ingest_node)
    workflow.add_node(INTELLIGENT_ROUTING, intelligent_routing_node)
    workflow.add_node(POLICY_RETRIEVAL, policy_retrieval_node)
    workflow.add_node(RULES_CHECKLIST, rules_checklist_node)
    workflow.add_node(DECISION_ORCHESTRATOR, decision_orchestrator_node)
    workflow.add_node(INSURER_CONNECTOR, insurer_connector_node)
    workflow.add_node(HITL_GATE, hitl_gate_node)
    workflow.add_node(AUDITED_CLOSURE, audited_closure_node)

    # Set entry point
    workflow.set_entry_point(CASE_INGEST)

    # Add edges - main flow
    workflow.add_edge(CASE_INGEST, INTELLIGENT_ROUTING)
    workflow.add_edge(INTELLIGENT_ROUTING, POLICY_RETRIEVAL)
    workflow.add_edge(POLICY_RETRIEVAL, RULES_CHECKLIST)
    workflow.add_edge(RULES_CHECKLIST, DECISION_ORCHESTRATOR)

    # Conditional: after decision, check if HITL required
    workflow.add_conditional_edges(
        DECISION_ORCHESTRATOR,
        should_route_to_hitl,
        {
            HITL_GATE: HITL_GATE,
            AUDITED_CLOSURE: AUDITED_CLOSURE,
        },
    )

    # Conditional: after HITL gate
    workflow.add_conditional_edges(
        HITL_GATE,
        after_hitl_gate,
        {
            AUDITED_CLOSURE: AUDITED_CLOSURE,
            POLICY_RETRIEVAL: POLICY_RETRIEVAL,
            END: END,
        },
    )

    # Insurer connector loops back to retrieval (to include response as evidence)
    workflow.add_edge(INSURER_CONNECTOR, POLICY_RETRIEVAL)

    # Final node
    workflow.add_edge(AUDITED_CLOSURE, END)

    return workflow


class PolicyValidationWorkflow:
    """
    High-level interface for the Policy Validation workflow.

    Provides methods for:
    - Starting new validations
    - Resuming after HITL
    - Querying state
    """

    def __init__(self):
        self._workflow = create_policy_validation_workflow()
        self._compiled = self._workflow.compile()

    async def validate_case(
        self,
        case: Case,
        config: dict | None = None,
    ) -> PolicyValidationState:
        """
        Start validation for a new case.

        Args:
            case: The case to validate
            config: Optional configuration overrides

        Returns:
            Final state after workflow execution
        """
        # Initialize state
        initial_state = PolicyValidationState(
            case=case,
            workflow_status="INITIALIZED",
        )

        logger.info(f"Starting validation workflow for case {case.case_id}")

        # Execute workflow
        final_state = await self._compiled.ainvoke(
            initial_state,
            config=config or {},
        )

        logger.info(
            f"Workflow completed for case {case.case_id}: "
            f"status={final_state.get('workflow_status')}"
        )

        return PolicyValidationState(**final_state)

    async def resume_after_hitl(
        self,
        state: PolicyValidationState,
        hitl_response: "HITLResponse",
    ) -> PolicyValidationState:
        """
        Resume workflow after receiving HITL response.

        Args:
            state: Current workflow state
            hitl_response: Response from human reviewer

        Returns:
            Final state after resuming
        """
        from policy_validation_copilot.models.hitl import HITLResponse

        # Update state with HITL response
        state.hitl_response = hitl_response
        state.workflow_status = "RUNNING"

        logger.info(
            f"Resuming workflow for case {state.case.case_id} "
            f"with HITL response: {hitl_response.decision}"
        )

        # Resume from HITL gate
        final_state = await self._compiled.ainvoke(
            state.model_dump(),
            config={"configurable": {"resume_from": HITL_GATE}},
        )

        return PolicyValidationState(**final_state)

    async def get_state(self, case_id: str) -> PolicyValidationState | None:
        """
        Get current state for a case.

        In production, this would query persisted state.
        """
        # TODO: Implement state persistence and retrieval
        return None

    def get_workflow_diagram(self) -> str:
        """Get Mermaid diagram of the workflow."""
        return self._compiled.get_graph().draw_mermaid()


# Convenience function
async def run_validation(
    case: Case,
    config: dict | None = None,
) -> PolicyValidationState:
    """
    Run policy validation for a case.

    Convenience wrapper around PolicyValidationWorkflow.
    """
    workflow = PolicyValidationWorkflow()
    return await workflow.validate_case(case, config)
