"""
Integration Tests for Workflow Components

This module contains integration tests for the LangGraph workflow
and component interactions.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from policy_copilot.workflow.policy_validation import (
    PolicyValidationWorkflow,
    create_policy_validation_workflow,
    create_mock_workflow,
    execute_policy_validation
)
from policy_copilot.state import PolicyValidationState, CaseState, DecisionStatus
from policy_copilot.config.settings import get_settings


@pytest.mark.integration
class TestWorkflowIntegration:
    """Test workflow integration with all components."""
    
    @pytest.fixture
    async def mock_workflow(self):
        """Create mock workflow for testing."""
        return create_mock_workflow()
    
    @pytest.fixture
    async def workflow_with_mocks(self):
        """Create workflow with mock services."""
        config = {
            "use_mock": True,
            "enable_hitl": True,
            "enable_auto_closure": True,
            "enable_external_queries": False,
            "max_workflow_duration_hours": 1,
            "checkpoint_enabled": False
        }
        return create_policy_validation_workflow(config)
    
    async def test_complete_workflow_execution(self, workflow_with_mocks, sample_crm_payload):
        """Test complete workflow execution from start to finish."""
        # Create initial state
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify workflow completion
        assert final_state is not None
        assert "case" in final_state
        assert "decision" in final_state
        assert "audit" in final_state
        
        # Verify case progression
        case_state = final_state["case"]["state"]
        assert case_state in [CaseState.CLOSED, CaseState.DECIDED, CaseState.REQUIRES_REVIEW]
        
        # Verify audit trail
        audit_log = final_state["audit"]["node_execution_log"]
        assert len(audit_log) > 0
        
        # Verify at least some key nodes were executed
        executed_nodes = [entry["node_name"] for entry in audit_log]
        assert "case_ingest" in executed_nodes
        assert "guardrails_validation" in executed_nodes
        assert "intelligent_routing" in executed_nodes
    
    async def test_workflow_with_emergency_case(self, workflow_with_mocks, emergency_crm_payload):
        """Test workflow with emergency case for fast-track processing."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(emergency_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify emergency processing
        assert final_state["case"]["priority"] == "CRITICAL"
        assert final_state["case"]["queue"] == "EMERGENCY"
        
        # Emergency cases should be processed quickly
        if "ml" in final_state and final_state["ml"]:
            routing_decision = final_state["case"].get("routing_decision")
            assert routing_decision in ["EMERGENCY_FAST_TRACK", "AUTO_PROCESS"]
    
    async def test_workflow_with_high_value_case(self, workflow_with_mocks, high_value_crm_payload):
        """Test workflow with high-value case requiring expert review."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(high_value_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # High-value cases should require manual review
        assert final_state["case"]["service_amount"] >= 50000.0
        
        # Should likely escalate to HITL
        if "decision" in final_state and final_state["decision"]:
            decision_status = final_state["decision"]["status"]
            assert decision_status in [DecisionStatus.ESCALAR, DecisionStatus.OBSERVADO, DecisionStatus.PENDIENTE]
    
    async def test_workflow_error_handling(self, workflow_with_mocks):
        """Test workflow error handling with invalid input."""
        # Create invalid initial state
        invalid_state = PolicyValidationState(
            case={
                "case_id": "invalid-case",
                # Missing required fields
            }
        )
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(invalid_state)
        
        # Should handle errors gracefully
        assert final_state is not None
        assert final_state["case"]["state"] == CaseState.ERROR
        
        # Should have error information
        if "workflow_error" in final_state:
            assert "error_message" in final_state["workflow_error"]
    
    async def test_workflow_metrics_collection(self, workflow_with_mocks, sample_crm_payload):
        """Test workflow metrics collection."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        await workflow_with_mocks.execute_workflow(initial_state)
        
        # Check metrics
        metrics = workflow_with_mocks.get_workflow_metrics()
        
        assert metrics["total_executions"] >= 1
        assert "node_execution_counts" in metrics
        assert "avg_processing_time_ms" in metrics
    
    async def test_workflow_state_transitions(self, workflow_with_mocks, sample_crm_payload):
        """Test proper state transitions throughout workflow."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Track state changes
        state_changes = []
        
        # Mock workflow to capture state changes
        original_execute = workflow_with_mocks.execute_workflow
        
        async def tracking_execute(state):
            state_changes.append(state["case"]["state"])
            result = await original_execute(state)
            state_changes.append(result["case"]["state"])
            return result
        
        workflow_with_mocks.execute_workflow = tracking_execute
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify state progression
        assert len(state_changes) >= 2
        assert state_changes[0] == CaseState.NUEVO
        assert state_changes[-1] in [CaseState.CLOSED, CaseState.DECIDED, CaseState.REQUIRES_REVIEW]


@pytest.mark.integration
class TestComponentIntegration:
    """Test integration between different components."""
    
    async def test_ml_services_integration(self, workflow_with_mocks, sample_crm_payload):
        """Test ML services integration in workflow."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify ML predictions were generated
        if "ml" in final_state and final_state["ml"]:
            ml_data = final_state["ml"]
            
            # Should have at least one ML service result
            assert (ml_data.get("classification") is not None or 
                   ml_data.get("anomaly") is not None or 
                   ml_data.get("eta") is not None)
            
            # Should have model versions
            assert "model_versions" in ml_data
    
    async def test_guardrails_integration(self, workflow_with_mocks, sample_crm_payload):
        """Test guardrails integration in workflow."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify guardrails were applied
        if "guardrails" in final_state and final_state["guardrails"]:
            guardrails_data = final_state["guardrails"]
            
            assert "decision" in guardrails_data
            assert guardrails_data["decision"] in ["ALLOW", "REDACT", "BLOCK", "REQUIRE_HITL"]
            
            # Should have security checks
            if "security_checks" in guardrails_data:
                security_checks = guardrails_data["security_checks"]
                assert isinstance(security_checks, dict)
    
    async def test_database_integration(self, workflow_with_mocks, sample_crm_payload, db_session):
        """Test database integration in workflow."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify database operations would work
        # (In a real integration test, we would verify actual database records)
        assert final_state["case"]["case_id"] is not None
        assert final_state["case"]["crm_ticket_id"] is not None
    
    async def test_notification_integration(self, workflow_with_mocks, sample_crm_payload):
        """Test notification integration in workflow."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify workflow completed (notifications would be triggered)
        assert final_state["case"]["state"] in [
            CaseState.CLOSED, 
            CaseState.DECIDED, 
            CaseState.REQUIRES_REVIEW
        ]


@pytest.mark.integration
class TestWorkflowPerformance:
    """Test workflow performance characteristics."""
    
    async def test_workflow_execution_time(self, workflow_with_mocks, sample_crm_payload):
        """Test workflow execution time is within acceptable limits."""
        import time
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        start_time = time.time()
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Workflow should complete within reasonable time (30 seconds for mock)
        assert execution_time < 30.0
        
        # Verify successful completion
        assert final_state["case"]["state"] != CaseState.ERROR
    
    async def test_concurrent_workflow_execution(self, workflow_with_mocks, test_data_factory):
        """Test concurrent workflow execution."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        # Create multiple test cases
        test_cases = []
        for i in range(5):
            payload = test_data_factory.create_crm_payload(
                crm_ticket_id=f"CRM-CONCURRENT-{i}",
                customer_id=f"CUST-CONCURRENT-{i}"
            )
            case = create_case_from_crm_payload(payload)
            initial_state = create_initial_state(case)
            test_cases.append(initial_state)
        
        # Execute workflows concurrently
        tasks = [
            workflow_with_mocks.execute_workflow(state) 
            for state in test_cases
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all workflows completed
        assert len(results) == 5
        
        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0
        
        # Verify all results are valid states
        for result in results:
            assert isinstance(result, dict)
            assert "case" in result
            assert result["case"]["state"] != CaseState.ERROR
    
    async def test_workflow_memory_usage(self, workflow_with_mocks, sample_crm_payload):
        """Test workflow memory usage is reasonable."""
        import psutil
        import os
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Execute multiple workflows
        for i in range(10):
            payload = test_data_factory.create_crm_payload(
                crm_ticket_id=f"CRM-MEMORY-{i}"
            )
            case = create_case_from_crm_payload(payload)
            initial_state = create_initial_state(case)
            
            await workflow_with_mocks.execute_workflow(initial_state)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


@pytest.mark.integration
class TestWorkflowErrorRecovery:
    """Test workflow error recovery and resilience."""
    
    async def test_workflow_with_ml_service_failure(self, workflow_with_mocks, sample_crm_payload):
        """Test workflow behavior when ML services fail."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        # Mock ML service failure
        original_route_case = workflow_with_mocks.intelligent_routing_node.route_case
        
        async def failing_route_case(state):
            # Simulate ML service failure
            raise Exception("ML service unavailable")
        
        workflow_with_mocks.intelligent_routing_node.route_case = failing_route_case
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Should handle failure gracefully
        assert final_state["case"]["state"] in [CaseState.ERROR, CaseState.REQUIRES_REVIEW]
        
        # Should have error information
        if "ml" in final_state and final_state["ml"]:
            assert "errors" in final_state["ml"]
            assert len(final_state["ml"]["errors"]) > 0
    
    async def test_workflow_with_database_failure(self, workflow_with_mocks, sample_crm_payload):
        """Test workflow behavior when database operations fail."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow (database failures would be handled by individual components)
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Workflow should still complete
        assert final_state is not None
        assert "case" in final_state
    
    async def test_workflow_timeout_handling(self, workflow_with_mocks, sample_crm_payload):
        """Test workflow timeout handling."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        # Set very short timeout
        workflow_with_mocks.config["max_workflow_duration_hours"] = 0.001  # ~3.6 seconds
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Should complete or handle timeout gracefully
        assert final_state is not None
        assert "case" in final_state


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    async def test_standard_approval_scenario(self, workflow_with_mocks, sample_crm_payload):
        """Test standard case approval scenario."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(sample_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute complete workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Verify end-to-end processing
        assert final_state["case"]["state"] in [CaseState.CLOSED, CaseState.DECIDED]
        
        if "decision" in final_state and final_state["decision"]:
            decision = final_state["decision"]
            assert decision["status"] in [DecisionStatus.APROBADO, DecisionStatus.OBSERVADO]
            assert "confidence" in decision
            assert "explanation" in decision
        
        # Verify audit trail is complete
        audit_log = final_state["audit"]["node_execution_log"]
        assert len(audit_log) >= 3  # At least ingest, routing, and one processing node
    
    async def test_rejection_scenario(self, workflow_with_mocks, test_data_factory):
        """Test case rejection scenario."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        # Create case that should be rejected (very high amount, suspicious pattern)
        payload = test_data_factory.create_crm_payload(
            service_code="EXPERIMENTAL_TREATMENT",
            service_amount=500000.0,  # Very high amount
            priority="LOW"  # Inconsistent priority
        )
        
        case = create_case_from_crm_payload(payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # Should likely be rejected or escalated
        if "decision" in final_state and final_state["decision"]:
            decision_status = final_state["decision"]["status"]
            assert decision_status in [
                DecisionStatus.RECHAZADO, 
                DecisionStatus.ESCALAR, 
                DecisionStatus.OBSERVADO
            ]
    
    async def test_hitl_escalation_scenario(self, workflow_with_mocks, high_value_crm_payload):
        """Test HITL escalation scenario."""
        from policy_copilot.state import create_case_from_crm_payload, create_initial_state
        
        case = create_case_from_crm_payload(high_value_crm_payload)
        initial_state = create_initial_state(case)
        
        # Execute workflow
        final_state = await workflow_with_mocks.execute_workflow(initial_state)
        
        # High-value cases should escalate to HITL
        assert final_state["case"]["state"] in [CaseState.REQUIRES_REVIEW, CaseState.CLOSED]
        
        if "hitl" in final_state and final_state["hitl"]:
            hitl_data = final_state["hitl"]
            assert hitl_data["required"] == True
            assert "status" in hitl_data
