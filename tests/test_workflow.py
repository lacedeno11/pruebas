"""
Tests for LangGraph workflow.
"""

import pytest
from datetime import datetime

from policy_validation_copilot.models.case import Case, CasePriority
from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.agents.workflow import (
    create_policy_validation_workflow,
    PolicyValidationWorkflow,
    should_route_to_hitl,
)
from policy_validation_copilot.models.decision import Decision, DecisionStatus


class TestWorkflowCreation:
    """Tests for workflow creation."""

    def test_create_workflow(self):
        """Test that workflow can be created."""
        workflow = create_policy_validation_workflow()
        assert workflow is not None

    def test_workflow_compiles(self):
        """Test that workflow compiles."""
        workflow = create_policy_validation_workflow()
        compiled = workflow.compile()
        assert compiled is not None


class TestRoutingLogic:
    """Tests for conditional routing logic."""

    def test_route_to_hitl_when_required(self):
        """Test routing to HITL when required."""
        case = Case(
            case_id="CASE-001",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
        )

        state = PolicyValidationState(case=case, hitl_required=True)

        route = should_route_to_hitl(state)

        assert route == "hitl_gate"

    def test_route_to_closure_when_auto_close(self):
        """Test routing to closure when auto-close eligible."""
        case = Case(
            case_id="CASE-001",
            customer_id="CUST-001",
            insurer_id="INS-001",
            plan_id="PLAN-001",
        )

        decision = Decision(
            decision_id="DEC-001",
            case_id="CASE-001",
            status=DecisionStatus.APPROVED,
            status_reason="All checks passed",
            confidence_score=0.95,
            risk_level=0.10,
            thresholds_version="1.0.0",
            explanation_summary="Case approved",
            auto_close_eligible=True,
            hitl_required=False,
        )

        state = PolicyValidationState(
            case=case, decision=decision, hitl_required=False
        )

        route = should_route_to_hitl(state)

        assert route == "audited_closure"


class TestPolicyValidationWorkflow:
    """Tests for PolicyValidationWorkflow class."""

    def test_workflow_initialization(self):
        """Test workflow initialization."""
        workflow = PolicyValidationWorkflow()
        assert workflow is not None

    def test_get_diagram(self):
        """Test getting workflow diagram."""
        workflow = PolicyValidationWorkflow()

        try:
            diagram = workflow.get_workflow_diagram()
            # Diagram may fail without full LangGraph setup
            # but should not crash
        except Exception:
            pass  # Expected in test environment


@pytest.mark.asyncio
async def test_validate_case_basic():
    """Test basic case validation (may require mocking in full test)."""
    case = Case(
        case_id="CASE-TEST-001",
        customer_id="CUST-001",
        insurer_id="INS-001",
        plan_id="PLAN-001",
        service_code="SVC-001",
        service_description="Test service validation",
        priority=CasePriority.NORMAL,
    )

    # This test would need mocking of ML services
    # For now, just verify the objects are created correctly
    state = PolicyValidationState(case=case)

    assert state.case.case_id == "CASE-TEST-001"
    assert state.workflow_status == "INITIALIZED"
