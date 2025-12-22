"""
LangGraph State Schema for Policy Validation Copilot

This module defines the PolicyValidationState class that serves as the central
state object for the LangGraph workflow. It contains all the data structures
needed to track case processing, evidence collection, decision making, and
audit trails throughout the policy validation process.

Based on Anexo A specifications and technical requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from typing_extensions import TypedDict


class CaseState(str, Enum):
    """Case processing states"""
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PENDING_EVIDENCE = "PENDING_EVIDENCE"
    PENDING_HITL = "PENDING_HITL"
    PENDING_EXTERNAL = "PENDING_EXTERNAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Priority(str, Enum):
    """Case priority levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecisionStatus(str, Enum):
    """Decision status values"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUIRES_HITL = "REQUIRES_HITL"
    REQUIRES_EXTERNAL = "REQUIRES_EXTERNAL"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GuardrailDecision(str, Enum):
    """Guardrail enforcement decisions"""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


class ChecklistOutcome(str, Enum):
    """Checklist item outcomes"""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"


# ============================================================================
# Case Data Models
# ============================================================================

class AttachmentInfo(BaseModel):
    """Attachment metadata"""
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    upload_timestamp: datetime
    storage_path: str


class CaseData(BaseModel):
    """Case information and metadata"""
    case_id: str = Field(default_factory=lambda: str(uuid4()))
    crm_ticket_id: str
    customer_id: str
    contract_id: str
    insurer_id: str
    plan_id: str
    service_code: str
    service_date: datetime
    provider_id: str
    attachments: List[AttachmentInfo] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    sla_target: datetime
    state: CaseState = CaseState.RECEIVED
    assigned_queue: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Evidence Pack Models
# ============================================================================

class EvidenceScores(BaseModel):
    """Evidence relevance and quality scores"""
    relevance_score: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    coverage_score: float = Field(ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    """Individual evidence item with metadata"""
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    doc_id: str
    version: str
    checksum: str
    pointer: str  # Page/section/cell reference
    excerpt: str
    table_ref: Optional[str] = None
    scores: EvidenceScores
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    source_type: str  # "policy", "exception", "external"


class EvidenceConflict(BaseModel):
    """Evidence conflict information"""
    conflict_id: str = Field(default_factory=lambda: str(uuid4()))
    evidence_ids: List[str]
    conflict_type: str  # "contradiction", "version_mismatch", "scope_overlap"
    description: str
    severity: str  # "low", "medium", "high"


class EvidencePack(BaseModel):
    """Collection of evidence items and metadata"""
    items: List[EvidenceItem] = Field(default_factory=list)
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    conflicts: List[EvidenceConflict] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Checklist Models
# ============================================================================

class ChecklistItem(BaseModel):
    """Individual checklist evaluation item"""
    item_id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    description: str
    outcome: ChecklistOutcome
    evidence_ref: Optional[str] = None  # Reference to evidence item
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class Checklist(BaseModel):
    """Policy validation checklist"""
    items: List[ChecklistItem] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    rule_ids_applied: List[str] = Field(default_factory=list)
    evaluation_log: List[str] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completed_at: Optional[datetime] = None


# ============================================================================
# ML Models
# ============================================================================

class MLClassificationOutput(BaseModel):
    """ML Classification service output"""
    request_type: str
    candidate_policy_ids: List[str]
    route: str
    risk_prior: float = Field(ge=0.0, le=1.0)
    probabilities: Dict[str, float]
    top_features: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class MLAnomalyOutput(BaseModel):
    """ML Anomaly detection service output"""
    anomaly_score: float = Field(ge=0.0, le=1.0)
    anomaly_flags: List[str]
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)


class MLETAOutput(BaseModel):
    """ML ETA prediction service output"""
    eta_minutes: int = Field(ge=0)
    p50: int = Field(ge=0)
    p90: Optional[int] = Field(default=None, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class MLModelVersions(BaseModel):
    """ML model version tracking"""
    classify_version: Optional[str] = None
    anomaly_version: Optional[str] = None
    eta_version: Optional[str] = None


class MLOutputs(BaseModel):
    """ML service outputs container"""
    classification: Optional[MLClassificationOutput] = None
    anomaly: Optional[MLAnomalyOutput] = None
    eta: Optional[MLETAOutput] = None
    model_versions: MLModelVersions = Field(default_factory=MLModelVersions)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Decision Models
# ============================================================================

class Decision(BaseModel):
    """Final decision and scoring"""
    status: DecisionStatus = DecisionStatus.PENDING
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    eta_estimate: Optional[int] = None  # minutes
    next_actions: List[str] = Field(default_factory=list)
    thresholds_version: str = "v1.0.0"
    reasoning: str = ""
    decided_at: Optional[datetime] = None
    decided_by: str = "system"  # "system" or user_id


# ============================================================================
# Guardrails Models
# ============================================================================

class GuardrailFlag(BaseModel):
    """Individual guardrail flag"""
    flag_id: str = Field(default_factory=lambda: str(uuid4()))
    rule_name: str
    severity: str  # "info", "warning", "error", "critical"
    message: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)


class GuardrailRedaction(BaseModel):
    """PII/sensitive data redaction record"""
    field_path: str
    original_value_hash: str
    redaction_type: str  # "mask", "remove", "encrypt"
    redacted_at: datetime = Field(default_factory=datetime.utcnow)


class Guardrails(BaseModel):
    """Guardrails enforcement results"""
    decision: GuardrailDecision = GuardrailDecision.ALLOW
    flags: List[GuardrailFlag] = Field(default_factory=list)
    redactions: List[GuardrailRedaction] = Field(default_factory=list)
    last_checked: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# HITL Models
# ============================================================================

class HITLQuestion(BaseModel):
    """Human-in-the-loop question"""
    question_id: str = Field(default_factory=lambda: str(uuid4()))
    question_text: str
    question_type: str  # "yes_no", "multiple_choice", "text", "evidence_review"
    options: Optional[List[str]] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HITLResponse(BaseModel):
    """Human-in-the-loop response"""
    question_id: str
    response: Union[str, bool, List[str]]
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    notes: Optional[str] = None
    responded_by: str
    responded_at: datetime = Field(default_factory=datetime.utcnow)


class HITLApproval(BaseModel):
    """Human-in-the-loop approval record"""
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_status: DecisionStatus
    approved_by: str
    approval_notes: str
    approved_at: datetime = Field(default_factory=datetime.utcnow)


class HITL(BaseModel):
    """Human-in-the-loop interaction tracking"""
    required: bool = False
    preguntas: List[HITLQuestion] = Field(default_factory=list)
    respuestas: List[HITLResponse] = Field(default_factory=list)
    aprobaciones: List[HITLApproval] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============================================================================
# Audit Models
# ============================================================================

class NodeExecutionLog(BaseModel):
    """Individual node execution record"""
    node_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "started", "completed", "failed", "skipped"
    input_hash: str
    output_hash: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class AuditTimestamp(BaseModel):
    """Key workflow timestamps"""
    case_received: datetime
    processing_started: Optional[datetime] = None
    evidence_collected: Optional[datetime] = None
    decision_made: Optional[datetime] = None
    case_closed: Optional[datetime] = None


class ExportLog(BaseModel):
    """Data export audit log"""
    export_id: str = Field(default_factory=lambda: str(uuid4()))
    exported_by: str
    export_type: str  # "full", "summary", "evidence_only"
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    data_hash: str


class Audit(BaseModel):
    """Comprehensive audit trail"""
    node_execution_log: List[NodeExecutionLog] = Field(default_factory=list)
    timestamps: AuditTimestamp
    export_logs: List[ExportLog] = Field(default_factory=list)
    data_lineage: Dict[str, Any] = Field(default_factory=dict)
    compliance_flags: List[str] = Field(default_factory=list)


# ============================================================================
# Main State Class
# ============================================================================

class PolicyValidationState(TypedDict):
    """
    Main LangGraph state for Policy Validation Copilot workflow.
    
    This TypedDict defines the complete state structure that flows through
    the LangGraph workflow nodes. Each field represents a major component
    of the policy validation process.
    
    Fields:
        case: Core case information and metadata
        evidence_pack: Collected evidence items with scores and conflicts
        checklist: Policy validation checklist with rule evaluations
        ml: Machine learning service outputs and model versions
        decision: Final decision with confidence and risk scores
        guardrails: Security and governance enforcement results
        hitl: Human-in-the-loop interaction tracking
        audit: Comprehensive audit trail and compliance tracking
    """
    case: CaseData
    evidence_pack: EvidencePack
    checklist: Checklist
    ml: MLOutputs
    decision: Decision
    guardrails: Guardrails
    hitl: HITL
    audit: Audit


# ============================================================================
# State Utilities
# ============================================================================

def create_initial_state(
    crm_ticket_id: str,
    customer_id: str,
    contract_id: str,
    insurer_id: str,
    plan_id: str,
    service_code: str,
    service_date: datetime,
    provider_id: str,
    priority: Priority = Priority.MEDIUM,
    assigned_queue: str = "default_queue"
) -> PolicyValidationState:
    """
    Create an initial PolicyValidationState with minimal required data.
    
    Args:
        crm_ticket_id: CRM system ticket identifier
        customer_id: Customer identifier
        contract_id: Insurance contract identifier
        insurer_id: Insurance company identifier
        plan_id: Insurance plan identifier
        service_code: Medical/service code
        service_date: Date of service
        provider_id: Healthcare provider identifier
        priority: Case priority level
        assigned_queue: Processing queue assignment
        
    Returns:
        PolicyValidationState: Initialized state object
    """
    now = datetime.utcnow()
    
    # Calculate SLA target based on priority
    sla_hours = {
        Priority.HIGH: 1,
        Priority.MEDIUM: 4,
        Priority.LOW: 24
    }
    sla_target = datetime.utcnow().replace(
        hour=now.hour + sla_hours[priority],
        minute=0,
        second=0,
        microsecond=0
    )
    
    case_data = CaseData(
        crm_ticket_id=crm_ticket_id,
        customer_id=customer_id,
        contract_id=contract_id,
        insurer_id=insurer_id,
        plan_id=plan_id,
        service_code=service_code,
        service_date=service_date,
        provider_id=provider_id,
        priority=priority,
        sla_target=sla_target,
        assigned_queue=assigned_queue
    )
    
    audit_timestamps = AuditTimestamp(case_received=now)
    
    return PolicyValidationState(
        case=case_data,
        evidence_pack=EvidencePack(),
        checklist=Checklist(),
        ml=MLOutputs(),
        decision=Decision(),
        guardrails=Guardrails(),
        hitl=HITL(),
        audit=Audit(timestamps=audit_timestamps)
    )


def update_state_audit(
    state: PolicyValidationState,
    node_name: str,
    status: str,
    input_hash: str,
    output_hash: Optional[str] = None,
    error_message: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> PolicyValidationState:
    """
    Update the audit trail with node execution information.
    
    Args:
        state: Current state object
        node_name: Name of the executing node
        status: Execution status
        input_hash: Hash of input data
        output_hash: Hash of output data (if completed)
        error_message: Error message (if failed)
        execution_time_ms: Execution time in milliseconds
        
    Returns:
        PolicyValidationState: Updated state object
    """
    now = datetime.utcnow()
    
    # Find existing log entry or create new one
    existing_log = None
    for log in state["audit"].node_execution_log:
        if log.node_name == node_name and log.status == "started":
            existing_log = log
            break
    
    if existing_log and status in ["completed", "failed"]:
        # Update existing log entry
        existing_log.completed_at = now
        existing_log.status = status
        existing_log.output_hash = output_hash
        existing_log.error_message = error_message
        if existing_log.started_at:
            existing_log.execution_time_ms = int(
                (now - existing_log.started_at).total_seconds() * 1000
            )
    else:
        # Create new log entry
        log_entry = NodeExecutionLog(
            node_name=node_name,
            started_at=now,
            status=status,
            input_hash=input_hash,
            output_hash=output_hash,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
        if status in ["completed", "failed"]:
            log_entry.completed_at = now
            
        state["audit"].node_execution_log.append(log_entry)
    
    return state


# ============================================================================
# Validation Utilities
# ============================================================================

def validate_state_consistency(state: PolicyValidationState) -> List[str]:
    """
    Validate state consistency and return list of validation errors.
    
    Args:
        state: State object to validate
        
    Returns:
        List[str]: List of validation error messages
    """
    errors = []
    
    # Check case data consistency
    if state["case"].state == CaseState.APPROVED and state["decision"].status != DecisionStatus.APPROVED:
        errors.append("Case state is APPROVED but decision status is not APPROVED")
    
    # Check evidence-checklist consistency
    evidence_refs = {item.evidence_id for item in state["evidence_pack"].items}
    checklist_refs = {item.evidence_ref for item in state["checklist"].items if item.evidence_ref}
    orphaned_refs = checklist_refs - evidence_refs
    if orphaned_refs:
        errors.append(f"Checklist references non-existent evidence: {orphaned_refs}")
    
    # Check HITL consistency
    if state["hitl"].required and not state["hitl"].preguntas:
        errors.append("HITL is required but no questions are defined")
    
    # Check decision consistency
    if state["decision"].status == DecisionStatus.APPROVED and state["decision"].confidence_score < 0.5:
        errors.append("Decision is APPROVED but confidence score is below 0.5")
    
    return errors
