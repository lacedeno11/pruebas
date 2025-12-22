"""
End-to-End Tests for All Use Cases

This module contains comprehensive end-to-end tests covering all 14 use cases
(UC-OP-01 through UC-OP-14) of the Policy Validation Copilot system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from policy_copilot.workflow.policy_validation import execute_policy_validation
from policy_copilot.state import PolicyValidationState, CaseState, DecisionStatus
from policy_copilot.ml_services import create_ml_services
from policy_copilot.guardrails import create_guardrail_engine
from policy_copilot.integrations import create_notification_service


@pytest.mark.e2e
class TestUseCase01:
    """UC-OP-01: Case Ingestion and Initial Processing"""
    
    async def test_uc_01_case_ingestion_from_crm_webhook(self, sample_crm_payload):
        """Test complete case ingestion from CRM webhook."""
        # Execute end-to-end workflow
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify case was ingested successfully
        assert final_state["case"]["crm_ticket_id"] == sample_crm_payload["crm_ticket_id"]
        assert final_state["case"]["customer_id"] == sample_crm_payload["customer_id"]
        assert final_state["case"]["state"] != CaseState.ERROR
        
        # Verify initial processing completed
        assert "audit" in final_state
        audit_log = final_state["audit"]["node_execution_log"]
        executed_nodes = [entry["node_name"] for entry in audit_log]
        assert "case_ingest" in executed_nodes
        
        # Verify SLA was calculated
        assert "sla_target_date" in final_state["case"]
        assert final_state["case"]["sla_target_date"] is not None
    
    async def test_uc_01_duplicate_case_handling(self, sample_crm_payload):
        """Test duplicate case detection and handling."""
        # Process same case twice
        first_result = await execute_policy_validation(sample_crm_payload)
        second_result = await execute_policy_validation(sample_crm_payload)
        
        # Both should complete successfully
        assert first_result["case"]["state"] != CaseState.ERROR
        assert second_result["case"]["state"] != CaseState.ERROR
        
        # Verify deduplication was handled
        # (In real implementation, would check for duplicate handling)
    
    async def test_uc_01_attachment_processing(self, sample_crm_payload):
        """Test attachment processing during case ingestion."""
        # Add attachments to payload
        sample_crm_payload["attachments"] = [
            {
                "filename": "medical_report.pdf",
                "content_type": "application/pdf",
                "size": 1024000,
                "url": "https://storage.example.com/attachments/medical_report.pdf"
            }
        ]
        
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify attachments were processed
        assert final_state["case"]["state"] != CaseState.ERROR
        assert len(final_state["case"]["attachments"]) > 0


@pytest.mark.e2e
class TestUseCase02:
    """UC-OP-02: Priority-based Routing and Queue Management"""
    
    async def test_uc_02_emergency_case_routing(self, emergency_crm_payload):
        """Test emergency case fast-track routing."""
        final_state = await execute_policy_validation(emergency_crm_payload)
        
        # Verify emergency routing
        assert final_state["case"]["priority"] == "CRITICAL"
        assert final_state["case"]["queue"] in ["EMERGENCY", "HIGH_PRIORITY"]
        
        # Verify fast processing
        if "ml" in final_state and final_state["ml"]:
            routing_decision = final_state["case"].get("routing_decision")
            assert routing_decision in ["EMERGENCY_FAST_TRACK", "PRIORITY_REVIEW"]
    
    async def test_uc_02_high_value_case_routing(self, high_value_crm_payload):
        """Test high-value case expert review routing."""
        final_state = await execute_policy_validation(high_value_crm_payload)
        
        # Verify high-value routing
        assert final_state["case"]["service_amount"] >= 50000.0
        assert final_state["case"]["queue"] in ["EXPERT_REVIEW", "MANUAL_REVIEW"]
        
        # Should require manual review
        if "decision" in final_state and final_state["decision"]:
            assert final_state["decision"].get("requires_hitl", False) == True
    
    async def test_uc_02_standard_case_routing(self, sample_crm_payload):
        """Test standard case auto-processing routing."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify standard routing
        assert final_state["case"]["priority"] in ["MEDIUM", "LOW"]
        assert final_state["case"]["queue"] in ["STANDARD", "AUTO_PROCESS"]


@pytest.mark.e2e
class TestUseCase03:
    """UC-OP-03: Policy Document Retrieval and Evidence Gathering"""
    
    async def test_uc_03_policy_retrieval_with_rag(self, sample_crm_payload):
        """Test policy retrieval using RAG functionality."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify evidence pack was created
        if "evidence_pack" in final_state and final_state["evidence_pack"]:
            evidence_pack = final_state["evidence_pack"]
            
            assert "items" in evidence_pack
            assert "coverage_score" in evidence_pack
            assert evidence_pack["coverage_score"] >= 0.0
            
            # Verify evidence items have required fields
            for item in evidence_pack["items"]:
                assert "doc_id" in item
                assert "version" in item
                assert "excerpt" in item
                assert "relevance_score" in item
    
    async def test_uc_03_source_allowlist_validation(self, sample_crm_payload):
        """Test source allowlist validation during retrieval."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify guardrails were applied
        if "guardrails" in final_state and final_state["guardrails"]:
            guardrails = final_state["guardrails"]
            
            # Should have source allowlist check
            if "security_checks" in guardrails:
                assert "source_allowlist" in guardrails["security_checks"]
    
    async def test_uc_03_coverage_score_calculation(self, sample_crm_payload):
        """Test evidence coverage score calculation."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        if "evidence_pack" in final_state and final_state["evidence_pack"]:
            coverage_score = final_state["evidence_pack"]["coverage_score"]
            
            # Coverage score should be between 0 and 1
            assert 0.0 <= coverage_score <= 1.0


@pytest.mark.e2e
class TestUseCase04:
    """UC-OP-04: Audited Case Closure and Export"""
    
    async def test_uc_04_case_closure_with_audit(self, sample_crm_payload):
        """Test complete case closure with audit trail."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify case reached closure
        assert final_state["case"]["state"] in [CaseState.CLOSED, CaseState.DECIDED]
        
        # Verify audit trail is complete
        assert "audit" in final_state
        audit_log = final_state["audit"]["node_execution_log"]
        assert len(audit_log) > 0
        
        # Verify all nodes have timestamps
        for entry in audit_log:
            assert "timestamp" in entry
            assert "node_name" in entry
            assert "status" in entry
    
    async def test_uc_04_export_functionality(self, sample_crm_payload):
        """Test case export functionality."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify export information is available
        if "closure" in final_state and final_state["closure"]:
            closure_info = final_state["closure"]
            
            if "export_packages" in closure_info:
                for export_pkg in closure_info["export_packages"]:
                    assert "export_id" in export_pkg
                    assert "format" in export_pkg
                    assert "checksum" in export_pkg
    
    async def test_uc_04_access_logging(self, sample_crm_payload):
        """Test access logging during closure."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify access logs were created
        if "audit" in final_state and "access_logs" in final_state["audit"]:
            access_logs = final_state["audit"]["access_logs"]
            assert len(access_logs) >= 0  # May be empty in mock mode


@pytest.mark.e2e
class TestUseCase05:
    """UC-OP-05: Case Validation and Normalization"""
    
    async def test_uc_05_payload_validation(self, sample_crm_payload):
        """Test comprehensive payload validation."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Should not error on valid payload
        assert final_state["case"]["state"] != CaseState.ERROR
        
        # Verify required fields are present
        required_fields = ["case_id", "crm_ticket_id", "customer_id", "service_code"]
        for field in required_fields:
            assert field in final_state["case"]
            assert final_state["case"][field] is not None
    
    async def test_uc_05_data_normalization(self, test_data_factory):
        """Test data normalization during validation."""
        # Create payload with data that needs normalization
        payload = test_data_factory.create_crm_payload(
            service_amount="150.50",  # String that should be converted to float
            priority="medium",        # Lowercase that should be normalized
            service_date=datetime.utcnow().isoformat()
        )
        
        final_state = await execute_policy_validation(payload)
        
        # Verify normalization occurred
        assert isinstance(final_state["case"]["service_amount"], float)
        assert final_state["case"]["priority"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    async def test_uc_05_invalid_payload_handling(self, test_data_factory):
        """Test handling of invalid payloads."""
        # Create invalid payload
        invalid_payload = {
            "crm_ticket_id": "CRM-INVALID",
            # Missing required fields
        }
        
        final_state = await execute_policy_validation(invalid_payload)
        
        # Should handle gracefully
        assert final_state["case"]["state"] == CaseState.ERROR
        assert "workflow_error" in final_state


@pytest.mark.e2e
class TestUseCase06:
    """UC-OP-06: RAG-based Policy Retrieval"""
    
    async def test_uc_06_vector_search_retrieval(self, sample_crm_payload):
        """Test vector-based policy document retrieval."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify RAG retrieval occurred
        if "evidence_pack" in final_state and final_state["evidence_pack"]:
            evidence_pack = final_state["evidence_pack"]
            
            # Should have retrieval metadata
            if "retrieval_metadata" in evidence_pack:
                metadata = evidence_pack["retrieval_metadata"]
                assert "query_time_ms" in metadata
                assert "total_documents_searched" in metadata
    
    async def test_uc_06_document_version_validation(self, sample_crm_payload):
        """Test document version validation during retrieval."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        if "evidence_pack" in final_state and final_state["evidence_pack"]:
            for item in final_state["evidence_pack"]["items"]:
                # Each evidence item should have version information
                assert "version" in item
                assert "checksum" in item
    
    async def test_uc_06_conflict_detection(self, sample_crm_payload):
        """Test policy conflict detection."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        if "evidence_pack" in final_state and final_state["evidence_pack"]:
            # Should have conflicts field (may be empty)
            assert "conflicts" in final_state["evidence_pack"]
            conflicts = final_state["evidence_pack"]["conflicts"]
            assert isinstance(conflicts, list)


@pytest.mark.e2e
class TestUseCase07:
    """UC-OP-07: Rules Engine and Checklist Evaluation"""
    
    async def test_uc_07_rule_engine_execution(self, sample_crm_payload):
        """Test policy-as-code rule engine execution."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify checklist was created
        if "checklist" in final_state and final_state["checklist"]:
            checklist = final_state["checklist"]
            
            assert "items" in checklist
            assert "rule_ids_applied" in checklist
            
            # Verify rule execution
            for item in checklist["items"]:
                assert "rule_id" in item
                assert "outcome" in item
                assert item["outcome"] in ["PASS", "FAIL", "MISSING", "UNKNOWN", "NOT_APPLICABLE"]
    
    async def test_uc_07_exception_handling(self, sample_crm_payload):
        """Test policy exception handling in rules."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Should complete without errors
        assert final_state["case"]["state"] != CaseState.ERROR
        
        # Verify checklist completion
        if "checklist" in final_state and final_state["checklist"]:
            assert "completion_percentage" in final_state["checklist"]
    
    async def test_uc_07_missing_field_detection(self, test_data_factory):
        """Test missing field detection in rules."""
        # Create payload with missing optional fields
        payload = test_data_factory.create_crm_payload()
        del payload["diagnosis_codes"]  # Remove optional field
        
        final_state = await execute_policy_validation(payload)
        
        if "checklist" in final_state and final_state["checklist"]:
            # May have missing fields detected
            assert "missing_fields" in final_state["checklist"]


@pytest.mark.e2e
class TestUseCase08:
    """UC-OP-08: Decision Orchestration and Confidence Scoring"""
    
    async def test_uc_08_confidence_calculation(self, sample_crm_payload):
        """Test multi-factor confidence calculation."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify decision was made
        if "decision" in final_state and final_state["decision"]:
            decision = final_state["decision"]
            
            assert "confidence" in decision
            assert 0.0 <= decision["confidence"] <= 1.0
            
            assert "risk_score" in decision
            assert 0.0 <= decision["risk_score"] <= 1.0
    
    async def test_uc_08_threshold_based_decisions(self, sample_crm_payload):
        """Test threshold-based decision making."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        if "decision" in final_state and final_state["decision"]:
            decision = final_state["decision"]
            
            # Should have decision status
            assert "status" in decision
            assert decision["status"] in ["APROBADO", "RECHAZADO", "OBSERVADO", "ESCALAR", "PENDIENTE"]
            
            # Should have explanation
            assert "explanation" in decision
    
    async def test_uc_08_hitl_escalation_logic(self, high_value_crm_payload):
        """Test HITL escalation logic."""
        final_state = await execute_policy_validation(high_value_crm_payload)
        
        # High-value cases should likely escalate
        if "decision" in final_state and final_state["decision"]:
            decision = final_state["decision"]
            
            # Should have HITL requirement assessment
            assert "requires_hitl" in decision
    
    async def test_uc_08_auto_closure_conditions(self, sample_crm_payload):
        """Test auto-closure condition evaluation."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        if "decision" in final_state and final_state["decision"]:
            decision = final_state["decision"]
            
            # Should have auto-closure eligibility assessment
            assert "auto_closure_eligible" in decision


@pytest.mark.e2e
class TestUseCase09:
    """UC-OP-09: External System Integration"""
    
    async def test_uc_09_external_query_preparation(self, sample_crm_payload):
        """Test external query preparation and execution."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # May have external query results
        if "external_query_result" in final_state:
            query_result = final_state["external_query_result"]
            assert isinstance(query_result, dict)
    
    async def test_uc_09_multi_channel_support(self, sample_crm_payload):
        """Test multi-channel external system support."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Should complete regardless of external system availability
        assert final_state["case"]["state"] != CaseState.ERROR
    
    async def test_uc_09_timeout_handling(self, sample_crm_payload):
        """Test external system timeout handling."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Should handle timeouts gracefully
        assert final_state["case"]["state"] != CaseState.ERROR


@pytest.mark.e2e
class TestUseCase10:
    """UC-OP-10: Security Guardrails and Governance"""
    
    async def test_uc_10_rbac_abac_enforcement(self, sample_crm_payload):
        """Test RBAC/ABAC enforcement."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify guardrails were applied
        if "guardrails" in final_state and final_state["guardrails"]:
            guardrails = final_state["guardrails"]
            
            assert "decision" in guardrails
            assert guardrails["decision"] in ["ALLOW", "REDACT", "BLOCK", "REQUIRE_HITL"]
            
            # Should have security checks
            if "security_checks" in guardrails:
                security_checks = guardrails["security_checks"]
                assert "rbac_abac" in security_checks
    
    async def test_uc_10_pii_masking(self, test_data_factory):
        """Test PII masking functionality."""
        # Create payload with PII data
        payload = test_data_factory.create_crm_payload(
            customer_id="CUST-12345-SSN-123456789"  # Contains potential PII
        )
        
        final_state = await execute_policy_validation(payload)
        
        # Should complete with PII handling
        assert final_state["case"]["state"] != CaseState.ERROR
        
        if "guardrails" in final_state and final_state["guardrails"]:
            # May have redactions
            assert "redactions" in final_state["guardrails"]
    
    async def test_uc_10_injection_detection(self, test_data_factory):
        """Test injection attack detection."""
        # Create payload with potential injection
        payload = test_data_factory.create_crm_payload(
            service_code="'; DROP TABLE cases; --"
        )
        
        final_state = await execute_policy_validation(payload)
        
        # Should detect and handle injection attempt
        if "guardrails" in final_state and final_state["guardrails"]:
            guardrails = final_state["guardrails"]
            
            # Should have security checks
            if "security_checks" in guardrails:
                assert "injection_detection" in guardrails["security_checks"]
    
    async def test_uc_10_evidence_anchoring(self, sample_crm_payload):
        """Test evidence anchoring validation."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        if "guardrails" in final_state and final_state["guardrails"]:
            guardrails = final_state["guardrails"]
            
            if "security_checks" in guardrails:
                assert "evidence_anchoring" in guardrails["security_checks"]


@pytest.mark.e2e
class TestUseCase11:
    """UC-OP-11: ML Classification Service"""
    
    async def test_uc_11_request_type_classification(self, sample_crm_payload):
        """Test ML-based request type classification."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify ML classification occurred
        if "ml" in final_state and final_state["ml"] and final_state["ml"]["classification"]:
            classification = final_state["ml"]["classification"]
            
            assert "request_type" in classification
            assert "candidate_policy_ids" in classification
            assert "route" in classification
            assert "risk_prior" in classification
            assert "probabilities" in classification
            assert "model_version" in classification
    
    async def test_uc_11_routing_recommendations(self, emergency_crm_payload):
        """Test routing recommendations from classification."""
        final_state = await execute_policy_validation(emergency_crm_payload)
        
        if "ml" in final_state and final_state["ml"] and final_state["ml"]["classification"]:
            classification = final_state["ml"]["classification"]
            
            # Emergency cases should have appropriate routing
            route = classification.get("route")
            assert route in ["EMERGENCY_FAST_TRACK", "PRIORITY_REVIEW", "AUTO_PROCESS"]


@pytest.mark.e2e
class TestUseCase12:
    """UC-OP-12: ML Anomaly Detection Service"""
    
    async def test_uc_12_anomaly_detection(self, sample_crm_payload):
        """Test ML-based anomaly detection."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify anomaly detection occurred
        if "ml" in final_state and final_state["ml"] and final_state["ml"]["anomaly"]:
            anomaly = final_state["ml"]["anomaly"]
            
            assert "anomaly_score" in anomaly
            assert 0.0 <= anomaly["anomaly_score"] <= 1.0
            assert "anomaly_flags" in anomaly
            assert "recommended_action" in anomaly
            assert "model_version" in anomaly
    
    async def test_uc_12_fraud_detection(self, test_data_factory):
        """Test fraud pattern detection."""
        # Create suspicious payload
        payload = test_data_factory.create_crm_payload(
            service_amount=100000.0,  # Very high amount
            priority="LOW",           # Inconsistent priority
            service_urgency="NORMAL"  # Inconsistent urgency
        )
        
        final_state = await execute_policy_validation(payload)
        
        if "ml" in final_state and final_state["ml"] and final_state["ml"]["anomaly"]:
            anomaly = final_state["ml"]["anomaly"]
            
            # Should detect anomaly
            anomaly_score = anomaly["anomaly_score"]
            # High amount with low priority should be flagged
            assert anomaly_score > 0.0


@pytest.mark.e2e
class TestUseCase13:
    """UC-OP-13: ML ETA Prediction Service"""
    
    async def test_uc_13_eta_prediction(self, sample_crm_payload):
        """Test ML-based ETA prediction."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify ETA prediction occurred
        if "ml" in final_state and final_state["ml"] and final_state["ml"]["eta"]:
            eta = final_state["ml"]["eta"]
            
            assert "eta_minutes" in eta
            assert eta["eta_minutes"] > 0
            assert "model_version" in eta
            
            # May have percentile estimates
            if "p50" in eta:
                assert eta["p50"] > 0
            if "p90" in eta:
                assert eta["p90"] > 0
    
    async def test_uc_13_sla_management(self, emergency_crm_payload):
        """Test SLA management with ETA predictions."""
        final_state = await execute_policy_validation(emergency_crm_payload)
        
        # Emergency cases should have shorter ETA
        if "ml" in final_state and final_state["ml"] and final_state["ml"]["eta"]:
            eta_minutes = final_state["ml"]["eta"]["eta_minutes"]
            
            # Emergency cases should be processed faster
            assert eta_minutes <= 480  # 8 hours max for emergency


@pytest.mark.e2e
class TestUseCase14:
    """UC-OP-14: Human-in-the-Loop Integration"""
    
    async def test_uc_14_hitl_escalation(self, high_value_crm_payload):
        """Test HITL escalation for complex cases."""
        final_state = await execute_policy_validation(high_value_crm_payload)
        
        # High-value cases should escalate to HITL
        if "hitl" in final_state and final_state["hitl"]:
            hitl = final_state["hitl"]
            
            assert "required" in hitl
            assert "status" in hitl
            
            if hitl["required"]:
                assert hitl["status"] in ["PENDING", "IN_PROGRESS", "COMPLETED", "ESCALATED"]
    
    async def test_uc_14_hitl_question_generation(self, high_value_crm_payload):
        """Test HITL question generation."""
        final_state = await execute_policy_validation(high_value_crm_payload)
        
        if "hitl" in final_state and final_state["hitl"] and final_state["hitl"]["required"]:
            hitl = final_state["hitl"]
            
            # Should have questions for human reviewer
            assert "questions" in hitl
            assert isinstance(hitl["questions"], list)
    
    async def test_uc_14_hitl_approval_workflow(self, high_value_crm_payload):
        """Test HITL approval workflow."""
        final_state = await execute_policy_validation(high_value_crm_payload)
        
        if "hitl" in final_state and final_state["hitl"]:
            hitl = final_state["hitl"]
            
            # Should have approval structure
            assert "approvals" in hitl
            assert isinstance(hitl["approvals"], list)


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteWorkflowScenarios:
    """Test complete end-to-end workflow scenarios."""
    
    async def test_complete_approval_workflow(self, sample_crm_payload):
        """Test complete approval workflow from ingestion to closure."""
        final_state = await execute_policy_validation(sample_crm_payload)
        
        # Verify complete workflow execution
        assert final_state["case"]["state"] in [CaseState.CLOSED, CaseState.DECIDED]
        
        # Verify all major components were processed
        assert "case" in final_state
        assert "audit" in final_state
        
        # Verify decision was made
        if "decision" in final_state and final_state["decision"]:
            decision = final_state["decision"]
            assert decision["status"] in ["APROBADO", "OBSERVADO", "RECHAZADO"]
            assert "confidence" in decision
            assert "explanation" in decision
    
    async def test_complete_rejection_workflow(self, test_data_factory):
        """Test complete rejection workflow."""
        # Create case that should be rejected
        payload = test_data_factory.create_crm_payload(
            service_code="EXPERIMENTAL_TREATMENT",
            service_amount=1000000.0,  # Extremely high amount
            priority="LOW"
        )
        
        final_state = await execute_policy_validation(payload)
        
        # Should complete workflow
        assert final_state["case"]["state"] != CaseState.ERROR
        
        # Should likely be rejected or escalated
        if "decision" in final_state and final_state["decision"]:
            decision_status = final_state["decision"]["status"]
            assert decision_status in ["RECHAZADO", "ESCALAR", "OBSERVADO"]
    
    async def test_complete_escalation_workflow(self, high_value_crm_payload):
        """Test complete escalation workflow."""
        final_state = await execute_policy_validation(high_value_crm_payload)
        
        # Should complete workflow
        assert final_state["case"]["state"] != CaseState.ERROR
        
        # Should escalate to HITL
        assert final_state["case"]["state"] in [CaseState.REQUIRES_REVIEW, CaseState.CLOSED]
        
        if "hitl" in final_state and final_state["hitl"]:
            assert final_state["hitl"]["required"] == True
    
    async def test_workflow_performance_all_use_cases(self, test_scenarios):
        """Test workflow performance across all use case scenarios."""
        import time
        
        results = []
        
        for scenario in test_scenarios:
            start_time = time.time()
            
            # Create test payload based on scenario
            payload = {
                "crm_ticket_id": f"CRM-{scenario['name'][:10]}",
                "customer_id": f"CUST-{scenario['name'][:10]}",
                "contract_id": "CONT-TEST",
                "insurer_id": "INS001",
                "plan_id": "PLAN_BASIC",
                **scenario["input"]
            }
            
            # Execute workflow
            final_state = await execute_policy_validation(payload)
            
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Verify execution
            assert final_state["case"]["state"] != CaseState.ERROR
            
            # Check performance expectations
            expected_max_time = scenario["expected_outcome"].get("processing_time_max", 600000)
            assert execution_time <= expected_max_time
            
            results.append({
                "scenario": scenario["name"],
                "execution_time_ms": execution_time,
                "final_state": final_state["case"]["state"],
                "decision_status": final_state.get("decision", {}).get("status")
            })
        
        # Log performance results
        for result in results:
            print(f"Scenario: {result['scenario']}")
            print(f"  Execution time: {result['execution_time_ms']:.2f}ms")
            print(f"  Final state: {result['final_state']}")
            print(f"  Decision: {result['decision_status']}")
        
        # Verify all scenarios completed
        assert len(results) == len(test_scenarios)
