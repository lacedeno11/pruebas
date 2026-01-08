"""
Test Data Fixtures

This module provides pytest fixtures for test data management including
sample payloads, mock responses, and test scenarios.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid

from policy_copilot.state import PolicyValidationState, create_case_from_crm_payload


@pytest.fixture
def sample_crm_payload() -> Dict[str, Any]:
    """Sample CRM webhook payload for testing."""
    return {
        "crm_ticket_id": "CRM-12345",
        "customer_id": "CUST-67890",
        "contract_id": "CONT-11111",
        "insurer_id": "INS001",
        "plan_id": "PLAN_BASIC",
        "service_code": "CONSULTATION_GENERAL",
        "service_date": datetime.utcnow().isoformat(),
        "service_amount": 150.0,
        "provider_id": "PROV_001",
        "priority": "MEDIUM",
        "diagnosis_codes": ["Z00.00"],
        "procedure_codes": ["99213"],
        "service_urgency": "NORMAL",
        "attachments": [
            {
                "filename": "medical_report.pdf",
                "content_type": "application/pdf",
                "size": 1024000,
                "url": "https://storage.example.com/attachments/medical_report.pdf"
            }
        ],
        "metadata": {
            "source": "CRM_WEBHOOK",
            "version": "1.0"
        }
    }


@pytest.fixture
def emergency_crm_payload() -> Dict[str, Any]:
    """Emergency case CRM payload for testing."""
    return {
        "crm_ticket_id": "CRM-EMRG-001",
        "customer_id": "CUST-EMRG-001",
        "contract_id": "CONT-EMRG-001",
        "insurer_id": "INS001",
        "plan_id": "PLAN_PREMIUM",
        "service_code": "EMERGENCY_CARE",
        "service_date": datetime.utcnow().isoformat(),
        "service_amount": 5000.0,
        "provider_id": "PROV_HOSPITAL_001",
        "priority": "CRITICAL",
        "diagnosis_codes": ["I21.9"],
        "procedure_codes": ["99291"],
        "service_urgency": "EMERGENCY",
        "attachments": [
            {
                "filename": "emergency_report.pdf",
                "content_type": "application/pdf",
                "size": 2048000,
                "url": "https://storage.example.com/attachments/emergency_report.pdf"
            },
            {
                "filename": "lab_results.pdf",
                "content_type": "application/pdf",
                "size": 512000,
                "url": "https://storage.example.com/attachments/lab_results.pdf"
            }
        ]
    }


@pytest.fixture
def high_value_crm_payload() -> Dict[str, Any]:
    """High-value case CRM payload for testing."""
    return {
        "crm_ticket_id": "CRM-HV-001",
        "customer_id": "CUST-HV-001",
        "contract_id": "CONT-HV-001",
        "insurer_id": "INS001",
        "plan_id": "PLAN_PREMIUM",
        "service_code": "SURGERY_CARDIAC",
        "service_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "service_amount": 75000.0,
        "provider_id": "PROV_SPECIALIST_001",
        "priority": "HIGH",
        "diagnosis_codes": ["I25.10", "Z95.1"],
        "procedure_codes": ["33533", "33534"],
        "service_urgency": "SCHEDULED",
        "attachments": [
            {
                "filename": "surgical_plan.pdf",
                "content_type": "application/pdf",
                "size": 3072000,
                "url": "https://storage.example.com/attachments/surgical_plan.pdf"
            },
            {
                "filename": "pre_op_assessment.pdf",
                "content_type": "application/pdf",
                "size": 1536000,
                "url": "https://storage.example.com/attachments/pre_op_assessment.pdf"
            }
        ]
    }


@pytest.fixture
def sample_policy_document() -> Dict[str, Any]:
    """Sample policy document for testing."""
    return {
        "doc_id": "POL-MED-001",
        "title": "Basic Medical Consultation Policy",
        "version": "2.1.0",
        "content": """
        This policy covers basic medical consultations for plan members.
        
        Coverage includes:
        - General practitioner consultations
        - Routine check-ups
        - Basic diagnostic procedures
        
        Exclusions:
        - Emergency room visits (covered under emergency policy)
        - Specialist consultations (require referral)
        - Experimental treatments
        
        Pre-authorization required for:
        - Consultations exceeding $500
        - Multiple consultations within 30 days
        """,
        "checksum": "abc123def456",
        "document_type": "POLICY",
        "source": "INTERNAL",
        "effective_date": "2024-01-01",
        "metadata": {
            "department": "Medical",
            "reviewer": "Dr. Smith",
            "approval_date": "2023-12-15"
        }
    }


@pytest.fixture
def sample_evidence_pack() -> Dict[str, Any]:
    """Sample evidence pack for testing."""
    return {
        "items": [
            {
                "doc_id": "POL-MED-001",
                "version": "2.1.0",
                "checksum": "abc123def456",
                "pointer": "section_2.1",
                "excerpt": "General practitioner consultations are covered under this policy",
                "table_ref": None,
                "relevance_score": 0.95,
                "confidence_score": 0.88
            },
            {
                "doc_id": "PROC-CONS-001",
                "version": "1.0.0",
                "checksum": "def456ghi789",
                "pointer": "step_3",
                "excerpt": "Consultation fees are subject to plan limits",
                "table_ref": "table_1",
                "relevance_score": 0.82,
                "confidence_score": 0.91
            }
        ],
        "coverage_score": 0.87,
        "conflicts": [],
        "missing_sources": [],
        "retrieval_metadata": {
            "query_time_ms": 150,
            "total_documents_searched": 45,
            "vector_similarity_threshold": 0.7
        }
    }


@pytest.fixture
def sample_checklist() -> Dict[str, Any]:
    """Sample checklist for testing."""
    return {
        "items": [
            {
                "rule_id": "RULE_001",
                "description": "Verify customer eligibility",
                "outcome": "PASS",
                "evidence_ref": "POL-MED-001:section_2.1",
                "details": "Customer is active plan member"
            },
            {
                "rule_id": "RULE_002",
                "description": "Check service code coverage",
                "outcome": "PASS",
                "evidence_ref": "POL-MED-001:section_2.1",
                "details": "Service code CONSULTATION_GENERAL is covered"
            },
            {
                "rule_id": "RULE_003",
                "description": "Validate amount within limits",
                "outcome": "PASS",
                "evidence_ref": "PROC-CONS-001:table_1",
                "details": "Amount $150 is within plan limits"
            }
        ],
        "missing_fields": [],
        "rule_ids_applied": ["RULE_001", "RULE_002", "RULE_003"],
        "completion_percentage": 100.0,
        "overall_status": "COMPLETE"
    }


@pytest.fixture
def sample_ml_predictions() -> Dict[str, Any]:
    """Sample ML predictions for testing."""
    return {
        "classification": {
            "request_type": "MEDICAL_CONSULTATION",
            "candidate_policy_ids": ["POL-MED-001", "POL-MED-002"],
            "route": "AUTO_PROCESS",
            "risk_prior": 0.15,
            "probabilities": {
                "MEDICAL_CONSULTATION": 0.85,
                "EMERGENCY_CARE": 0.10,
                "SPECIALIST_REFERRAL": 0.05
            },
            "top_features": ["service_code", "provider_type", "service_amount"],
            "model_version": "classification-v2.1.0"
        },
        "anomaly": {
            "anomaly_score": 0.12,
            "anomaly_flags": [],
            "recommended_action": "APPROVE",
            "model_version": "anomaly-v1.5.0"
        },
        "eta": {
            "eta_minutes": 480,
            "p50": 360,
            "p90": 720,
            "model_version": "eta-v1.2.0"
        },
        "processing_time_ms": 250,
        "errors": [],
        "model_versions": {
            "classification": "classification-v2.1.0",
            "anomaly": "anomaly-v1.5.0",
            "eta": "eta-v1.2.0"
        }
    }


@pytest.fixture
def sample_decision() -> Dict[str, Any]:
    """Sample decision for testing."""
    return {
        "status": "APROBADO",
        "confidence": 0.87,
        "risk_score": 0.13,
        "explanation": "Case approved based on policy compliance and low risk assessment",
        "evidence_references": ["POL-MED-001:section_2.1", "PROC-CONS-001:table_1"],
        "next_actions": ["NOTIFY_CUSTOMER", "UPDATE_CRM"],
        "requires_hitl": False,
        "auto_closure_eligible": True,
        "thresholds_version": "v1.0.0",
        "decided_by": "SYSTEM",
        "decided_at": datetime.utcnow(),
        "is_final": True
    }


@pytest.fixture
def sample_guardrails_result() -> Dict[str, Any]:
    """Sample guardrails result for testing."""
    return {
        "decision": "ALLOW",
        "flags": [],
        "redactions": [],
        "security_checks": {
            "rbac_abac": "PASS",
            "source_allowlist": "PASS",
            "injection_detection": "PASS",
            "evidence_anchoring": "PASS",
            "pii_detection": "PASS"
        },
        "security_context": {
            "user_id": "SYSTEM",
            "roles": ["SYSTEM_PROCESSOR"],
            "permissions": ["CASE_PROCESS", "POLICY_READ"],
            "session_id": str(uuid.uuid4())
        },
        "version": "guardrails-v1.0.0"
    }


@pytest.fixture
def sample_audit_trail() -> Dict[str, Any]:
    """Sample audit trail for testing."""
    return {
        "node_execution_log": [
            {
                "node_name": "case_ingest",
                "status": "COMPLETED",
                "timestamp": datetime.utcnow(),
                "processing_time_ms": 150,
                "error_message": None
            },
            {
                "node_name": "guardrails_validation",
                "status": "COMPLETED",
                "timestamp": datetime.utcnow(),
                "processing_time_ms": 75,
                "error_message": None
            },
            {
                "node_name": "intelligent_routing",
                "status": "COMPLETED",
                "timestamp": datetime.utcnow(),
                "processing_time_ms": 200,
                "error_message": None
            }
        ],
        "export_logs": [],
        "access_logs": [
            {
                "user_id": "SYSTEM",
                "action": "CASE_CREATED",
                "timestamp": datetime.utcnow(),
                "ip_address": "127.0.0.1"
            }
        ]
    }


@pytest.fixture
def complete_policy_validation_state(
    sample_crm_payload: Dict[str, Any],
    sample_evidence_pack: Dict[str, Any],
    sample_checklist: Dict[str, Any],
    sample_ml_predictions: Dict[str, Any],
    sample_decision: Dict[str, Any],
    sample_guardrails_result: Dict[str, Any],
    sample_audit_trail: Dict[str, Any]
) -> PolicyValidationState:
    """Complete policy validation state for testing."""
    case = create_case_from_crm_payload(sample_crm_payload)
    
    return PolicyValidationState(
        case=case,
        evidence_pack=sample_evidence_pack,
        checklist=sample_checklist,
        ml=sample_ml_predictions,
        decision=sample_decision,
        guardrails=sample_guardrails_result,
        hitl=None,
        audit=sample_audit_trail
    )


@pytest.fixture
def test_scenarios() -> List[Dict[str, Any]]:
    """Test scenarios for different use cases."""
    return [
        {
            "name": "UC-OP-01: Standard Medical Consultation",
            "description": "Basic medical consultation with standard approval",
            "input": {
                "service_code": "CONSULTATION_GENERAL",
                "service_amount": 150.0,
                "priority": "MEDIUM"
            },
            "expected_outcome": {
                "decision_status": "APROBADO",
                "confidence_min": 0.8,
                "processing_time_max": 600000  # 10 minutes
            }
        },
        {
            "name": "UC-OP-02: Emergency Care",
            "description": "Emergency care with fast-track processing",
            "input": {
                "service_code": "EMERGENCY_CARE",
                "service_amount": 5000.0,
                "priority": "CRITICAL"
            },
            "expected_outcome": {
                "decision_status": "APROBADO",
                "confidence_min": 0.7,
                "processing_time_max": 300000  # 5 minutes
            }
        },
        {
            "name": "UC-OP-03: High-Value Surgery",
            "description": "High-value surgical procedure requiring expert review",
            "input": {
                "service_code": "SURGERY_CARDIAC",
                "service_amount": 75000.0,
                "priority": "HIGH"
            },
            "expected_outcome": {
                "decision_status": "ESCALAR",
                "requires_hitl": True,
                "processing_time_max": 1800000  # 30 minutes
            }
        }
    ]


class TestDataFactory:
    """Factory for creating test data with variations."""
    
    @staticmethod
    def create_crm_payload(**overrides) -> Dict[str, Any]:
        """Create CRM payload with custom overrides."""
        base_payload = {
            "crm_ticket_id": f"CRM-{uuid.uuid4().hex[:8]}",
            "customer_id": f"CUST-{uuid.uuid4().hex[:8]}",
            "contract_id": f"CONT-{uuid.uuid4().hex[:8]}",
            "insurer_id": "INS001",
            "plan_id": "PLAN_BASIC",
            "service_code": "CONSULTATION_GENERAL",
            "service_date": datetime.utcnow().isoformat(),
            "service_amount": 150.0,
            "provider_id": "PROV_001",
            "priority": "MEDIUM",
            "diagnosis_codes": ["Z00.00"],
            "procedure_codes": ["99213"],
            "service_urgency": "NORMAL",
            "attachments": []
        }
        base_payload.update(overrides)
        return base_payload
    
    @staticmethod
    def create_policy_document(**overrides) -> Dict[str, Any]:
        """Create policy document with custom overrides."""
        base_document = {
            "doc_id": f"POL-{uuid.uuid4().hex[:8]}",
            "title": "Test Policy Document",
            "version": "1.0.0",
            "content": "Test policy content for validation",
            "checksum": uuid.uuid4().hex,
            "document_type": "POLICY",
            "source": "INTERNAL",
            "effective_date": datetime.utcnow().isoformat()
        }
        base_document.update(overrides)
        return base_document
    
    @staticmethod
    def create_ml_prediction(service_name: str, **overrides) -> Dict[str, Any]:
        """Create ML prediction with custom overrides."""
        base_predictions = {
            "classification": {
                "request_type": "MEDICAL_CONSULTATION",
                "candidate_policy_ids": ["POL-001"],
                "route": "AUTO_PROCESS",
                "risk_prior": 0.15,
                "probabilities": {"MEDICAL_CONSULTATION": 0.85},
                "top_features": ["service_code"],
                "model_version": "classification-v2.1.0"
            },
            "anomaly": {
                "anomaly_score": 0.12,
                "anomaly_flags": [],
                "recommended_action": "APPROVE",
                "model_version": "anomaly-v1.5.0"
            },
            "eta": {
                "eta_minutes": 480,
                "p50": 360,
                "p90": 720,
                "model_version": "eta-v1.2.0"
            }
        }
        
        if service_name in base_predictions:
            prediction = base_predictions[service_name].copy()
            prediction.update(overrides)
            return prediction
        
        return overrides


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Test data factory fixture."""
    return TestDataFactory()
