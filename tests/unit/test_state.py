"""
Unit Tests for State Management

This module contains unit tests for the PolicyValidationState and related
state management functionality.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from policy_copilot.state import (
    PolicyValidationState,
    create_initial_state,
    create_case_from_crm_payload,
    validate_case,
    validate_evidence_pack,
    validate_checklist,
    validate_ml_predictions,
    validate_decision,
    validate_guardrails,
    validate_hitl,
    validate_audit,
    validate_complete_state,
    CaseState,
    DecisionStatus,
    Priority,
    ChecklistOutcome,
    GuardrailDecision
)


class TestStateEnums:
    """Test state enumeration values."""
    
    def test_case_state_values(self):
        """Test CaseState enum values."""
        assert CaseState.NUEVO == "NUEVO"
        assert CaseState.INGESTED == "INGESTED"
        assert CaseState.VALIDATED == "VALIDATED"
        assert CaseState.ROUTED == "ROUTED"
        assert CaseState.EVIDENCE_GATHERED == "EVIDENCE_GATHERED"
        assert CaseState.EVALUATED == "EVALUATED"
        assert CaseState.DECIDED == "DECIDED"
        assert CaseState.REQUIRES_REVIEW == "REQUIRES_REVIEW"
        assert CaseState.CLOSED == "CLOSED"
        assert CaseState.ERROR == "ERROR"
    
    def test_decision_status_values(self):
        """Test DecisionStatus enum values."""
        assert DecisionStatus.APROBADO == "APROBADO"
        assert DecisionStatus.RECHAZADO == "RECHAZADO"
        assert DecisionStatus.OBSERVADO == "OBSERVADO"
        assert DecisionStatus.ESCALAR == "ESCALAR"
        assert DecisionStatus.PENDIENTE == "PENDIENTE"
    
    def test_priority_values(self):
        """Test Priority enum values."""
        assert Priority.LOW == "LOW"
        assert Priority.MEDIUM == "MEDIUM"
        assert Priority.HIGH == "HIGH"
        assert Priority.CRITICAL == "CRITICAL"


class TestCaseValidation:
    """Test case validation functionality."""
    
    def test_validate_case_valid(self, sample_crm_payload):
        """Test case validation with valid data."""
        case = create_case_from_crm_payload(sample_crm_payload)
        errors = validate_case(case)
        assert len(errors) == 0
    
    def test_validate_case_missing_required_fields(self):
        """Test case validation with missing required fields."""
        case = {
            "case_id": "test-case-001",
            # Missing required fields
        }
        errors = validate_case(case)
        assert len(errors) > 0
        assert any("crm_ticket_id" in error for error in errors)
        assert any("customer_id" in error for error in errors)
    
    def test_validate_case_invalid_types(self):
        """Test case validation with invalid data types."""
        case = {
            "case_id": "test-case-001",
            "crm_ticket_id": "CRM-12345",
            "customer_id": "CUST-67890",
            "service_amount": "invalid_amount",  # Should be float
            "priority": "INVALID_PRIORITY",      # Should be valid Priority enum
            "created_at": "invalid_date"         # Should be datetime
        }
        errors = validate_case(case)
        assert len(errors) > 0
        assert any("service_amount" in error for error in errors)
        assert any("priority" in error for error in errors)
    
    def test_create_case_from_crm_payload(self, sample_crm_payload):
        """Test case creation from CRM payload."""
        case = create_case_from_crm_payload(sample_crm_payload)
        
        assert case["crm_ticket_id"] == sample_crm_payload["crm_ticket_id"]
        assert case["customer_id"] == sample_crm_payload["customer_id"]
        assert case["service_amount"] == sample_crm_payload["service_amount"]
        assert case["priority"] == sample_crm_payload["priority"]
        assert case["state"] == CaseState.NUEVO
        assert "case_id" in case
        assert "created_at" in case
        assert "sla_target_date" in case


class TestEvidencePackValidation:
    """Test evidence pack validation functionality."""
    
    def test_validate_evidence_pack_valid(self, sample_evidence_pack):
        """Test evidence pack validation with valid data."""
        errors = validate_evidence_pack(sample_evidence_pack)
        assert len(errors) == 0
    
    def test_validate_evidence_pack_missing_items(self):
        """Test evidence pack validation with missing items."""
        evidence_pack = {
            "coverage_score": 0.8,
            "conflicts": [],
            "missing_sources": []
            # Missing items
        }
        errors = validate_evidence_pack(evidence_pack)
        assert len(errors) > 0
        assert any("items" in error for error in errors)
    
    def test_validate_evidence_pack_invalid_coverage_score(self):
        """Test evidence pack validation with invalid coverage score."""
        evidence_pack = {
            "items": [],
            "coverage_score": 1.5,  # Should be between 0 and 1
            "conflicts": [],
            "missing_sources": []
        }
        errors = validate_evidence_pack(evidence_pack)
        assert len(errors) > 0
        assert any("coverage_score" in error for error in errors)
    
    def test_validate_evidence_pack_invalid_item_structure(self):
        """Test evidence pack validation with invalid item structure."""
        evidence_pack = {
            "items": [
                {
                    "doc_id": "POL-001",
                    # Missing required fields like version, checksum, etc.
                }
            ],
            "coverage_score": 0.8,
            "conflicts": [],
            "missing_sources": []
        }
        errors = validate_evidence_pack(evidence_pack)
        assert len(errors) > 0


class TestChecklistValidation:
    """Test checklist validation functionality."""
    
    def test_validate_checklist_valid(self, sample_checklist):
        """Test checklist validation with valid data."""
        errors = validate_checklist(sample_checklist)
        assert len(errors) == 0
    
    def test_validate_checklist_invalid_outcome(self):
        """Test checklist validation with invalid outcome."""
        checklist = {
            "items": [
                {
                    "rule_id": "RULE_001",
                    "description": "Test rule",
                    "outcome": "INVALID_OUTCOME",  # Should be valid ChecklistOutcome
                    "evidence_ref": "POL-001:section_1"
                }
            ],
            "missing_fields": [],
            "rule_ids_applied": ["RULE_001"]
        }
        errors = validate_checklist(checklist)
        assert len(errors) > 0
        assert any("outcome" in error for error in errors)
    
    def test_validate_checklist_missing_evidence_ref(self):
        """Test checklist validation with missing evidence reference."""
        checklist = {
            "items": [
                {
                    "rule_id": "RULE_001",
                    "description": "Test rule",
                    "outcome": ChecklistOutcome.PASS
                    # Missing evidence_ref
                }
            ],
            "missing_fields": [],
            "rule_ids_applied": ["RULE_001"]
        }
        errors = validate_checklist(checklist)
        assert len(errors) > 0
        assert any("evidence_ref" in error for error in errors)


class TestMLPredictionsValidation:
    """Test ML predictions validation functionality."""
    
    def test_validate_ml_predictions_valid(self, sample_ml_predictions):
        """Test ML predictions validation with valid data."""
        errors = validate_ml_predictions(sample_ml_predictions)
        assert len(errors) == 0
    
    def test_validate_ml_predictions_missing_classification(self):
        """Test ML predictions validation with missing classification."""
        ml_predictions = {
            "anomaly": {
                "anomaly_score": 0.1,
                "anomaly_flags": [],
                "recommended_action": "APPROVE",
                "model_version": "anomaly-v1.5.0"
            },
            "eta": {
                "eta_minutes": 480,
                "model_version": "eta-v1.2.0"
            }
            # Missing classification
        }
        errors = validate_ml_predictions(ml_predictions)
        # Should not error as classification is optional
        assert len(errors) == 0
    
    def test_validate_ml_predictions_invalid_anomaly_score(self):
        """Test ML predictions validation with invalid anomaly score."""
        ml_predictions = {
            "anomaly": {
                "anomaly_score": 1.5,  # Should be between 0 and 1
                "anomaly_flags": [],
                "recommended_action": "APPROVE",
                "model_version": "anomaly-v1.5.0"
            }
        }
        errors = validate_ml_predictions(ml_predictions)
        assert len(errors) > 0
        assert any("anomaly_score" in error for error in errors)


class TestDecisionValidation:
    """Test decision validation functionality."""
    
    def test_validate_decision_valid(self, sample_decision):
        """Test decision validation with valid data."""
        errors = validate_decision(sample_decision)
        assert len(errors) == 0
    
    def test_validate_decision_invalid_status(self):
        """Test decision validation with invalid status."""
        decision = {
            "status": "INVALID_STATUS",  # Should be valid DecisionStatus
            "confidence": 0.8,
            "risk_score": 0.2,
            "explanation": "Test decision"
        }
        errors = validate_decision(decision)
        assert len(errors) > 0
        assert any("status" in error for error in errors)
    
    def test_validate_decision_invalid_confidence_range(self):
        """Test decision validation with invalid confidence range."""
        decision = {
            "status": DecisionStatus.APROBADO,
            "confidence": 1.5,  # Should be between 0 and 1
            "risk_score": 0.2,
            "explanation": "Test decision"
        }
        errors = validate_decision(decision)
        assert len(errors) > 0
        assert any("confidence" in error for error in errors)


class TestGuardrailsValidation:
    """Test guardrails validation functionality."""
    
    def test_validate_guardrails_valid(self, sample_guardrails_result):
        """Test guardrails validation with valid data."""
        errors = validate_guardrails(sample_guardrails_result)
        assert len(errors) == 0
    
    def test_validate_guardrails_invalid_decision(self):
        """Test guardrails validation with invalid decision."""
        guardrails = {
            "decision": "INVALID_DECISION",  # Should be valid GuardrailDecision
            "flags": [],
            "redactions": []
        }
        errors = validate_guardrails(guardrails)
        assert len(errors) > 0
        assert any("decision" in error for error in errors)


class TestCompleteStateValidation:
    """Test complete state validation functionality."""
    
    def test_validate_complete_state_valid(self, complete_policy_validation_state):
        """Test complete state validation with valid data."""
        errors = validate_complete_state(complete_policy_validation_state)
        assert len(errors) == 0
    
    def test_validate_complete_state_missing_case(self):
        """Test complete state validation with missing case."""
        state = PolicyValidationState()
        errors = validate_complete_state(state)
        assert len(errors) > 0
        assert any("case" in error for error in errors)
    
    def test_validate_complete_state_invalid_components(self):
        """Test complete state validation with invalid components."""
        state = PolicyValidationState(
            case={
                "case_id": "test-001",
                # Missing required fields
            },
            decision={
                "status": "INVALID_STATUS",
                "confidence": 1.5  # Invalid range
            }
        )
        errors = validate_complete_state(state)
        assert len(errors) > 0


class TestStateFactory:
    """Test state factory functions."""
    
    def test_create_initial_state(self, sample_crm_payload):
        """Test initial state creation."""
        case = create_case_from_crm_payload(sample_crm_payload)
        state = create_initial_state(case)
        
        assert "case" in state
        assert "audit" in state
        assert state["case"]["case_id"] == case["case_id"]
        assert state["case"]["state"] == CaseState.NUEVO
        assert len(state["audit"]["node_execution_log"]) == 0
    
    def test_create_initial_state_with_custom_case(self):
        """Test initial state creation with custom case data."""
        case = {
            "case_id": "custom-case-001",
            "crm_ticket_id": "CRM-CUSTOM-001",
            "customer_id": "CUST-CUSTOM-001",
            "state": CaseState.INGESTED,
            "priority": Priority.HIGH,
            "created_at": datetime.utcnow()
        }
        
        state = create_initial_state(case)
        
        assert state["case"]["case_id"] == "custom-case-001"
        assert state["case"]["state"] == CaseState.INGESTED
        assert state["case"]["priority"] == Priority.HIGH


class TestStateUtilities:
    """Test state utility functions."""
    
    def test_state_immutability(self, complete_policy_validation_state):
        """Test that state modifications don't affect original."""
        original_case_id = complete_policy_validation_state["case"]["case_id"]
        
        # Modify state
        modified_state = complete_policy_validation_state.copy()
        modified_state["case"]["case_id"] = "modified-case-id"
        
        # Original should be unchanged
        assert complete_policy_validation_state["case"]["case_id"] == original_case_id
        assert modified_state["case"]["case_id"] == "modified-case-id"
    
    def test_state_serialization(self, complete_policy_validation_state):
        """Test state serialization and deserialization."""
        import json
        
        # Convert datetime objects to strings for JSON serialization
        serializable_state = {}
        for key, value in complete_policy_validation_state.items():
            if isinstance(value, dict):
                serializable_state[key] = self._make_serializable(value)
            else:
                serializable_state[key] = value
        
        # Serialize to JSON
        json_str = json.dumps(serializable_state, default=str)
        
        # Deserialize from JSON
        deserialized_state = json.loads(json_str)
        
        # Check key components are preserved
        assert deserialized_state["case"]["case_id"] == complete_policy_validation_state["case"]["case_id"]
        assert deserialized_state["decision"]["status"] == complete_policy_validation_state["decision"]["status"]
    
    def _make_serializable(self, obj):
        """Helper to make objects JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj


@pytest.mark.unit
class TestStatePerformance:
    """Test state management performance."""
    
    def test_state_validation_performance(self, complete_policy_validation_state):
        """Test state validation performance."""
        import time
        
        start_time = time.time()
        
        # Run validation multiple times
        for _ in range(100):
            errors = validate_complete_state(complete_policy_validation_state)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should complete 100 validations in under 1 second
        assert elapsed_time < 1.0
        assert len(errors) == 0
    
    def test_state_creation_performance(self, sample_crm_payload):
        """Test state creation performance."""
        import time
        
        start_time = time.time()
        
        # Create states multiple times
        for _ in range(100):
            case = create_case_from_crm_payload(sample_crm_payload)
            state = create_initial_state(case)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should complete 100 creations in under 1 second
        assert elapsed_time < 1.0
