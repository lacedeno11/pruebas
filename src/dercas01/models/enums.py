"""
Enums for DERCAS 01 Policy Validation Copilot

Contains all status enums and constants used throughout the system.
"""

from enum import Enum


class CaseStatus(str, Enum):
    """Case processing status."""
    CREATED = "CREATED"
    INGESTED = "INGESTED"
    ROUTING = "ROUTING"
    RETRIEVING_POLICY = "RETRIEVING_POLICY"
    BUILDING_CHECKLIST = "BUILDING_CHECKLIST"
    DECIDING = "DECIDING"
    EXTERNAL_QUERY = "EXTERNAL_QUERY"
    HITL_REVIEW = "HITL_REVIEW"
    APPROVED = "APPROVED"
    OBSERVED = "OBSERVED"
    REJECTED = "REJECTED"
    PENDIENTE_POLITICA = "PENDIENTE_POLITICA"
    PENDIENTE_DATOS = "PENDIENTE_DATOS"
    PENDIENTE_ASEGURADORA = "PENDIENTE_ASEGURADORA"
    PENDIENTE_SISTEMA = "PENDIENTE_SISTEMA"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


class DecisionStatus(str, Enum):
    """Final decision status for cases."""
    APROBADO = "APROBADO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    ESCALAR = "ESCALAR"
    PENDIENTE = "PENDIENTE"


class GuardrailAction(str, Enum):
    """Guardrail enforcement actions."""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


class MLModelType(str, Enum):
    """Types of ML models in the system."""
    CLASSIFICATION = "CLASSIFICATION"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    ETA_PREDICTION = "ETA_PREDICTION"


class PolicyStatus(str, Enum):
    """Policy document status."""
    DRAFT = "DRAFT"
    PENDING_QA = "PENDING_QA"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class ExceptionStatus(str, Enum):
    """Exception rule status."""
    PROPOSED = "PROPOSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Priority(str, Enum):
    """Case priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    """Confidence levels for decisions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ChecklistOutcome(str, Enum):
    """Checklist item evaluation outcomes."""
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AuditEventType(str, Enum):
    """Types of audit events."""
    CASE_CREATED = "CASE_CREATED"
    CASE_UPDATED = "CASE_UPDATED"
    NODE_EXECUTED = "NODE_EXECUTED"
    ML_INFERENCE = "ML_INFERENCE"
    GUARDRAIL_CHECK = "GUARDRAIL_CHECK"
    HITL_ESCALATION = "HITL_ESCALATION"
    DECISION_MADE = "DECISION_MADE"
    EVIDENCE_ACCESSED = "EVIDENCE_ACCESSED"
    POLICY_APPLIED = "POLICY_APPLIED"
    EXCEPTION_APPLIED = "EXCEPTION_APPLIED"
    EXTERNAL_QUERY = "EXTERNAL_QUERY"
    CASE_CLOSED = "CASE_CLOSED"


class DocumentType(str, Enum):
    """Types of documents in the system."""
    POLICY = "POLICY"
    EXCEPTION_RULE = "EXCEPTION_RULE"
    CASE_ATTACHMENT = "CASE_ATTACHMENT"
    EVIDENCE = "EVIDENCE"
    AUDIT_REPORT = "AUDIT_REPORT"


class StorageType(str, Enum):
    """Object storage types."""
    LOCAL = "LOCAL"
    S3 = "S3"
    AZURE = "AZURE"
    GCP = "GCP"


class UserRole(str, Enum):
    """User roles for RBAC."""
    AGENT = "AGENT"
    SUPERVISOR = "SUPERVISOR"
    AUDITOR = "AUDITOR"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class HITLReason(str, Enum):
    """Reasons for HITL escalation."""
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    HIGH_RISK = "HIGH_RISK"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    GUARDRAIL_BLOCK = "GUARDRAIL_BLOCK"
    EXCEPTION_REQUIRED = "EXCEPTION_REQUIRED"
    EXTERNAL_QUERY_FAILED = "EXTERNAL_QUERY_FAILED"
    MANUAL_REVIEW_REQUESTED = "MANUAL_REVIEW_REQUESTED"


class ExternalQueryStatus(str, Enum):
    """Status of external insurance company queries."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class QueueType(str, Enum):
    """Processing queue types."""
    AUTO_PROCESSING = "AUTO_PROCESSING"
    HITL_AGENT = "HITL_AGENT"
    HITL_SUPERVISOR = "HITL_SUPERVISOR"
    POLICY_REVIEW = "POLICY_REVIEW"
    EXCEPTION_APPROVAL = "EXCEPTION_APPROVAL"
    AUDIT_REVIEW = "AUDIT_REVIEW"
    ERROR_HANDLING = "ERROR_HANDLING"


class MLDegradationLevel(str, Enum):
    """ML service degradation levels."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class ThresholdType(str, Enum):
    """Types of decision thresholds."""
    CONFIDENCE_HIGH = "CONFIDENCE_HIGH"
    CONFIDENCE_MEDIUM = "CONFIDENCE_MEDIUM"
    RISK_LOW = "RISK_LOW"
    RISK_HIGH = "RISK_HIGH"
    COVERAGE_OK = "COVERAGE_OK"
    ANOMALY_HIGH = "ANOMALY_HIGH"


class NotificationType(str, Enum):
    """Types of system notifications."""
    HITL_ESCALATION = "HITL_ESCALATION"
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    POLICY_UPDATE = "POLICY_UPDATE"
    EXCEPTION_APPROVAL = "EXCEPTION_APPROVAL"
    AUDIT_ALERT = "AUDIT_ALERT"
