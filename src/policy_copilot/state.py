"""
LangGraph State Schema for Policy Validation Copilot

This module defines the complete state schema for the LangGraph workflow as specified in Anexo A.
All state components are implemented as TypedDict classes with proper typing and validation.

State Components:
- Case: Case identification, service data, dates, attachments, SLA, state, queue
- EvidencePack: Document items with references, coverage score, conflicts
- Checklist: Evaluation items with outcomes, missing fields, applied rules
- ML: ML service outputs and model versions (classify/anomaly/eta)
- Decision: Status, confidence/risk scores, next actions, thresholds
- Guardrails: Security decisions, flags, redactions
- HITL: Human-in-the-loop requirements, questions, approvals
- Audit: Node execution log, timestamps, export logs
"""

from typing import Dict, List, Optional, Union, Any, Literal
from typing_extensions import TypedDict, NotRequired
from datetime import datetime
from enum import Enum
import uuid


# =============================================================================
# Enums and Constants
# =============================================================================

class CaseState(str, Enum):
    """Case processing states"""
    INGESTED = "INGESTED"
    PROCESSING = "PROCESSING"
    PENDING_POLICY = "PENDIENTE_POLÍTICA"
    PENDING_DATA = "PENDIENTE_DATOS"
    PENDING_INSURER = "PENDIENTE_ASEGURADORA"
    PENDING_SYSTEM = "PENDIENTE_SISTEMA"
    HITL_REVIEW = "HITL_REVIEW"
    APPROVED = "APROBADO"
    OBSERVED = "OBSERVADO"
    REJECTED = "RECHAZADO"
    CLOSED = "CLOSED"


class DecisionStatus(str, Enum):
    """Decision status values"""
    APPROVED = "APROBADO"
    OBSERVED = "OBSERVADO"
    REJECTED = "RECHAZADO"
    ESCALATE = "ESCALAR"
    PENDING = "PENDIENTE"


class Priority(str, Enum):
    """Case priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ChecklistOutcome(str, Enum):
    """Checklist item evaluation outcomes"""
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GuardrailDecision(str, Enum):
    """Guardrail enforcement decisions"""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


# =============================================================================
# Case State Component
# =============================================================================

class CaseAttachment(TypedDict):
    """Case attachment metadata"""
    attachment_id: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    storage_path: str
    uploaded_at: datetime


class Case(TypedDict):
    """
    Case state component containing case identification, service data, 
    dates, attachments, SLA, state, and queue assignment.
    """
    # Core identifiers
    case_id: str
    crm_ticket_id: str
    customer_id: str
    contract_id: str
    
    # Service information
    insurer_id: str
    plan_id: str
    service_code: str
    service_description: NotRequired[str]
    service_date: datetime
    provider_id: NotRequired[str]
    
    # Attachments and documents
    attachments: List[CaseAttachment]
    
    # Processing metadata
    priority: Priority
    sla_target: datetime
    created_at: datetime
    updated_at: datetime
    
    # State management
    state: CaseState
    assigned_queue: str
    assigned_agent: NotRequired[str]
    
    # Additional context
    channel: NotRequired[str]  # Source channel (web, api, email, etc.)
    notes: NotRequired[str]
    tags: NotRequired[List[str]]


# =============================================================================
# Evidence Pack State Component
# =============================================================================

class EvidenceItem(TypedDict):
    """Individual evidence item with document reference and metadata"""
    doc_id: str
    version: str
    checksum: str
    pointer: str  # Page/cell reference (e.g., "page:5", "sheet:Coverage,cell:A1:C10")
    excerpt: str  # Extracted text or table content
    table_ref: NotRequired[str]  # Table reference if applicable
    relevance_score: float
    confidence_score: float


class EvidencePack(TypedDict):
    """
    Evidence Pack state component containing document items with references,
    coverage score, and conflict detection.
    """
    items: List[EvidenceItem]
    coverage_score: float  # Overall coverage quality (0.0 to 1.0)
    conflicts_detected: List[str]  # List of detected conflicts
    missing_sources: List[str]  # Required sources not found
    retrieval_timestamp: datetime
    query_used: str
    total_documents_searched: int
    filters_applied: Dict[str, Any]


# =============================================================================
# Checklist State Component
# =============================================================================

class ChecklistItem(TypedDict):
    """Individual checklist evaluation item"""
    item_id: str
    description: str
    outcome: ChecklistOutcome
    evidence_ref: NotRequired[str]  # Reference to evidence item
    rule_id: NotRequired[str]  # Rule that generated this item
    explanation: NotRequired[str]
    confidence: NotRequired[float]


class Checklist(TypedDict):
    """
    Checklist state component containing evaluation items with outcomes,
    missing fields, and applied rules.
    """
    items: List[ChecklistItem]
    missing_fields: List[str]  # Critical fields that are missing
    rule_ids_applied: List[str]  # Rules that were executed
    evaluation_log: List[str]  # Detailed evaluation steps
    overall_status: ChecklistOutcome
    completion_percentage: float
    evaluated_at: datetime


# =============================================================================
# ML State Component
# =============================================================================

class MLClassificationOutput(TypedDict):
    """ML Classification service output (UC-OP-11)"""
    request_type: str
    candidate_policy_ids: List[str]
    route: str
    risk_prior: float
    probabilities: Dict[str, float]
    top_features: List[str]
    model_version: str


class MLAnomalyOutput(TypedDict):
    """ML Anomaly detection service output (UC-OP-12)"""
    anomaly_score: float
    anomaly_flags: List[str]
    recommended_action: str
    model_version: str


class MLETAOutput(TypedDict):
    """ML ETA prediction service output (UC-OP-13)"""
    eta_minutes: int
    p50: NotRequired[int]  # 50th percentile estimate
    p90: NotRequired[int]  # 90th percentile estimate
    model_version: str


class ML(TypedDict):
    """
    ML state component containing outputs from all ML services
    and their model versions.
    """
    classification: NotRequired[MLClassificationOutput]
    anomaly: NotRequired[MLAnomalyOutput]
    eta: NotRequired[MLETAOutput]
    
    # Model versions for tracking
    model_versions: Dict[str, str]  # service_name -> version
    
    # Processing metadata
    processed_at: datetime
    ml_degraded: bool  # True if any ML service failed
    fallback_used: List[str]  # List of services that used fallback


# =============================================================================
# Decision State Component
# =============================================================================

class Decision(TypedDict):
    """
    Decision state component containing status, confidence/risk scores,
    next actions, and thresholds version.
    """
    status: DecisionStatus
    confidence_score: float  # 0.0 to 1.0
    risk_level: float  # 0.0 to 1.0
    anomaly_score: NotRequired[float]  # From ML anomaly service
    eta_estimate: NotRequired[int]  # Minutes from ML ETA service
    
    # Action planning
    next_actions: List[str]
    requires_hitl: bool
    auto_closure_eligible: bool
    
    # Configuration tracking
    thresholds_version: str
    decision_rules_version: str
    
    # Metadata
    decided_at: datetime
    decided_by: str  # "system" or agent identifier
    explanation: str
    supporting_evidence: List[str]  # References to evidence items


# =============================================================================
# Guardrails State Component
# =============================================================================

class GuardrailFlag(TypedDict):
    """Individual guardrail flag with details"""
    flag_type: str  # e.g., "pii_detected", "injection_attempt", "unauthorized_source"
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    description: str
    detected_at: datetime
    rule_id: str


class GuardrailRedaction(TypedDict):
    """PII redaction record"""
    field_name: str
    original_value: str
    redacted_value: str
    redaction_type: str  # e.g., "email", "phone", "ssn", "name"


class Guardrails(TypedDict):
    """
    Guardrails state component containing security decisions,
    flags, and redactions.
    """
    decision: GuardrailDecision
    flags: List[GuardrailFlag]
    redactions: List[GuardrailRedaction]
    
    # Security checks performed
    rbac_check_passed: bool
    abac_check_passed: bool
    source_allowlist_passed: bool
    injection_check_passed: bool
    evidence_anchoring_passed: bool
    
    # Processing metadata
    checked_at: datetime
    guardrail_version: str
    security_context: Dict[str, Any]


# =============================================================================
# HITL State Component
# =============================================================================

class HITLQuestion(TypedDict):
    """Human-in-the-loop question"""
    question_id: str
    question_text: str
    question_type: str  # "yes_no", "multiple_choice", "text", "approval"
    options: NotRequired[List[str]]  # For multiple choice
    required: bool


class HITLResponse(TypedDict):
    """Human-in-the-loop response"""
    question_id: str
    response: str
    responded_by: str
    responded_at: datetime
    confidence: NotRequired[float]


class HITLApproval(TypedDict):
    """Human-in-the-loop approval record"""
    approval_type: str  # "decision", "exception", "policy_override"
    approved: bool
    approved_by: str
    approved_at: datetime
    comments: NotRequired[str]
    conditions: NotRequired[List[str]]


class HITL(TypedDict):
    """
    HITL (Human-in-the-Loop) state component containing requirements,
    questions/responses, and approvals.
    """
    required: bool
    reason: NotRequired[str]  # Why HITL is required
    priority: Priority
    
    # Questions and responses
    questions: List[HITLQuestion]
    responses: List[HITLResponse]
    
    # Approvals
    approvals: List[HITLApproval]
    
    # Assignment and timing
    assigned_to: NotRequired[str]
    assigned_at: NotRequired[datetime]
    due_at: NotRequired[datetime]
    completed_at: NotRequired[datetime]
    
    # Status tracking
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "ESCALATED", "TIMEOUT"]


# =============================================================================
# Audit State Component
# =============================================================================

class NodeExecution(TypedDict):
    """Individual node execution record"""
    node_name: str
    started_at: datetime
    completed_at: NotRequired[datetime]
    status: Literal["STARTED", "COMPLETED", "FAILED", "SKIPPED"]
    input_data: Dict[str, Any]
    output_data: NotRequired[Dict[str, Any]]
    error_message: NotRequired[str]
    execution_time_ms: NotRequired[int]


class ExportLog(TypedDict):
    """Audit export log entry"""
    export_id: str
    exported_by: str
    exported_at: datetime
    export_format: str
    export_reason: str
    data_exported: List[str]  # List of data types exported
    access_level: str


class Audit(TypedDict):
    """
    Audit state component containing node execution log,
    timestamps, and export logs.
    """
    # Workflow execution tracking
    node_execution_log: List[NodeExecution]
    workflow_started_at: datetime
    workflow_completed_at: NotRequired[datetime]
    workflow_status: Literal["RUNNING", "COMPLETED", "FAILED", "PAUSED"]
    
    # Export and access tracking
    export_logs: List[ExportLog]
    access_logs: List[Dict[str, Any]]
    
    # Data integrity
    state_checksum: str
    last_modified_at: datetime
    modification_count: int
    
    # Compliance and retention
    retention_until: datetime
    compliance_flags: List[str]


# =============================================================================
# Complete LangGraph State
# =============================================================================

class PolicyValidationState(TypedDict):
    """
    Complete LangGraph state for Policy Validation Copilot workflow.
    
    This is the main state object that flows through all nodes and agents
    in the LangGraph workflow. Each component represents a different aspect
    of the policy validation process.
    """
    # Core state components as specified in Anexo A
    case: Case
    evidence_pack: NotRequired[EvidencePack]
    checklist: NotRequired[Checklist]
    ml: NotRequired[ML]
    decision: NotRequired[Decision]
    guardrails: NotRequired[Guardrails]
    hitl: NotRequired[HITL]
    audit: Audit
    
    # Workflow metadata
    workflow_id: str
    workflow_version: str
    current_node: NotRequired[str]
    next_node: NotRequired[str]
    
    # Error handling
    errors: List[str]
    warnings: List[str]


# =============================================================================
# State Validation Functions
# =============================================================================

def validate_case(case: Case) -> List[str]:
    """
    Validate case state component.
    
    Args:
        case: Case state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Required field validation
    required_fields = ['case_id', 'crm_ticket_id', 'customer_id', 'contract_id', 
                      'insurer_id', 'plan_id', 'service_code', 'service_date']
    
    for field in required_fields:
        if not case.get(field):
            errors.append(f"Missing required field: {field}")
    
    # UUID validation for case_id
    try:
        uuid.UUID(case.get('case_id', ''))
    except (ValueError, TypeError):
        errors.append("case_id must be a valid UUID")
    
    # Date validation
    if case.get('sla_target') and case.get('created_at'):
        if case['sla_target'] <= case['created_at']:
            errors.append("sla_target must be after created_at")
    
    # State validation
    if case.get('state') and case['state'] not in [s.value for s in CaseState]:
        errors.append(f"Invalid case state: {case['state']}")
    
    return errors


def validate_evidence_pack(evidence_pack: EvidencePack) -> List[str]:
    """
    Validate evidence pack state component.
    
    Args:
        evidence_pack: Evidence pack state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Coverage score validation
    coverage_score = evidence_pack.get('coverage_score', 0)
    if not (0.0 <= coverage_score <= 1.0):
        errors.append("coverage_score must be between 0.0 and 1.0")
    
    # Evidence items validation
    items = evidence_pack.get('items', [])
    if not items:
        errors.append("Evidence pack must contain at least one item")
    
    for i, item in enumerate(items):
        if not item.get('doc_id'):
            errors.append(f"Evidence item {i}: missing doc_id")
        if not item.get('version'):
            errors.append(f"Evidence item {i}: missing version")
        if not item.get('checksum'):
            errors.append(f"Evidence item {i}: missing checksum")
        if not item.get('pointer'):
            errors.append(f"Evidence item {i}: missing pointer")
        
        # Score validation
        relevance_score = item.get('relevance_score', 0)
        if not (0.0 <= relevance_score <= 1.0):
            errors.append(f"Evidence item {i}: relevance_score must be between 0.0 and 1.0")
    
    return errors


def validate_checklist(checklist: Checklist) -> List[str]:
    """
    Validate checklist state component.
    
    Args:
        checklist: Checklist state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Items validation
    items = checklist.get('items', [])
    if not items:
        errors.append("Checklist must contain at least one item")
    
    for i, item in enumerate(items):
        if not item.get('item_id'):
            errors.append(f"Checklist item {i}: missing item_id")
        if not item.get('description'):
            errors.append(f"Checklist item {i}: missing description")
        
        outcome = item.get('outcome')
        if outcome and outcome not in [o.value for o in ChecklistOutcome]:
            errors.append(f"Checklist item {i}: invalid outcome {outcome}")
    
    # Completion percentage validation
    completion = checklist.get('completion_percentage', 0)
    if not (0.0 <= completion <= 100.0):
        errors.append("completion_percentage must be between 0.0 and 100.0")
    
    return errors


def validate_ml(ml: ML) -> List[str]:
    """
    Validate ML state component.
    
    Args:
        ml: ML state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Model versions validation
    model_versions = ml.get('model_versions', {})
    if not model_versions:
        errors.append("model_versions cannot be empty")
    
    # Classification output validation
    if 'classification' in ml:
        classification = ml['classification']
        if not classification.get('model_version'):
            errors.append("Classification output missing model_version")
        
        risk_prior = classification.get('risk_prior', 0)
        if not (0.0 <= risk_prior <= 1.0):
            errors.append("Classification risk_prior must be between 0.0 and 1.0")
    
    # Anomaly output validation
    if 'anomaly' in ml:
        anomaly = ml['anomaly']
        if not anomaly.get('model_version'):
            errors.append("Anomaly output missing model_version")
        
        anomaly_score = anomaly.get('anomaly_score', 0)
        if not (0.0 <= anomaly_score <= 1.0):
            errors.append("Anomaly score must be between 0.0 and 1.0")
    
    # ETA output validation
    if 'eta' in ml:
        eta = ml['eta']
        if not eta.get('model_version'):
            errors.append("ETA output missing model_version")
        
        eta_minutes = eta.get('eta_minutes', 0)
        if eta_minutes < 0:
            errors.append("ETA minutes cannot be negative")
    
    return errors


def validate_decision(decision: Decision) -> List[str]:
    """
    Validate decision state component.
    
    Args:
        decision: Decision state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Status validation
    status = decision.get('status')
    if status and status not in [s.value for s in DecisionStatus]:
        errors.append(f"Invalid decision status: {status}")
    
    # Score validation
    confidence_score = decision.get('confidence_score', 0)
    if not (0.0 <= confidence_score <= 1.0):
        errors.append("confidence_score must be between 0.0 and 1.0")
    
    risk_level = decision.get('risk_level', 0)
    if not (0.0 <= risk_level <= 1.0):
        errors.append("risk_level must be between 0.0 and 1.0")
    
    # Required fields
    if not decision.get('thresholds_version'):
        errors.append("Missing thresholds_version")
    if not decision.get('decision_rules_version'):
        errors.append("Missing decision_rules_version")
    if not decision.get('explanation'):
        errors.append("Missing explanation")
    
    return errors


def validate_guardrails(guardrails: Guardrails) -> List[str]:
    """
    Validate guardrails state component.
    
    Args:
        guardrails: Guardrails state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Decision validation
    decision = guardrails.get('decision')
    if decision and decision not in [d.value for d in GuardrailDecision]:
        errors.append(f"Invalid guardrail decision: {decision}")
    
    # Flags validation
    flags = guardrails.get('flags', [])
    for i, flag in enumerate(flags):
        if not flag.get('flag_type'):
            errors.append(f"Guardrail flag {i}: missing flag_type")
        if not flag.get('severity'):
            errors.append(f"Guardrail flag {i}: missing severity")
        
        severity = flag.get('severity')
        if severity and severity not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            errors.append(f"Guardrail flag {i}: invalid severity {severity}")
    
    # Required version
    if not guardrails.get('guardrail_version'):
        errors.append("Missing guardrail_version")
    
    return errors


def validate_hitl(hitl: HITL) -> List[str]:
    """
    Validate HITL state component.
    
    Args:
        hitl: HITL state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Status validation
    status = hitl.get('status')
    if status and status not in ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'ESCALATED', 'TIMEOUT']:
        errors.append(f"Invalid HITL status: {status}")
    
    # Questions validation
    questions = hitl.get('questions', [])
    for i, question in enumerate(questions):
        if not question.get('question_id'):
            errors.append(f"HITL question {i}: missing question_id")
        if not question.get('question_text'):
            errors.append(f"HITL question {i}: missing question_text")
        if not question.get('question_type'):
            errors.append(f"HITL question {i}: missing question_type")
    
    # Responses validation
    responses = hitl.get('responses', [])
    question_ids = {q.get('question_id') for q in questions}
    for i, response in enumerate(responses):
        response_qid = response.get('question_id')
        if response_qid not in question_ids:
            errors.append(f"HITL response {i}: question_id {response_qid} not found in questions")
    
    return errors


def validate_audit(audit: Audit) -> List[str]:
    """
    Validate audit state component.
    
    Args:
        audit: Audit state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Workflow status validation
    status = audit.get('workflow_status')
    if status and status not in ['RUNNING', 'COMPLETED', 'FAILED', 'PAUSED']:
        errors.append(f"Invalid workflow status: {status}")
    
    # Node execution log validation
    node_log = audit.get('node_execution_log', [])
    for i, execution in enumerate(node_log):
        if not execution.get('node_name'):
            errors.append(f"Node execution {i}: missing node_name")
        if not execution.get('started_at'):
            errors.append(f"Node execution {i}: missing started_at")
        
        exec_status = execution.get('status')
        if exec_status and exec_status not in ['STARTED', 'COMPLETED', 'FAILED', 'SKIPPED']:
            errors.append(f"Node execution {i}: invalid status {exec_status}")
    
    # Required fields
    if not audit.get('state_checksum'):
        errors.append("Missing state_checksum")
    if not audit.get('workflow_started_at'):
        errors.append("Missing workflow_started_at")
    
    return errors


def validate_state(state: PolicyValidationState) -> List[str]:
    """
    Validate complete PolicyValidationState.
    
    Args:
        state: Complete state to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Required components
    if 'case' not in state:
        errors.append("Missing required component: case")
    else:
        errors.extend(validate_case(state['case']))
    
    if 'audit' not in state:
        errors.append("Missing required component: audit")
    else:
        errors.extend(validate_audit(state['audit']))
    
    # Optional components validation
    if 'evidence_pack' in state:
        errors.extend(validate_evidence_pack(state['evidence_pack']))
    
    if 'checklist' in state:
        errors.extend(validate_checklist(state['checklist']))
    
    if 'ml' in state:
        errors.extend(validate_ml(state['ml']))
    
    if 'decision' in state:
        errors.extend(validate_decision(state['decision']))
    
    if 'guardrails' in state:
        errors.extend(validate_guardrails(state['guardrails']))
    
    if 'hitl' in state:
        errors.extend(validate_hitl(state['hitl']))
    
    # Workflow metadata validation
    if not state.get('workflow_id'):
        errors.append("Missing workflow_id")
    if not state.get('workflow_version'):
        errors.append("Missing workflow_version")
    
    return errors


# =============================================================================
# State Factory Functions
# =============================================================================

def create_initial_state(case: Case) -> PolicyValidationState:
    """
    Create initial PolicyValidationState with case and audit components.
    
    Args:
        case: Initial case data
        
    Returns:
        Initial state with case and audit components
    """
    workflow_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    initial_audit = Audit(
        node_execution_log=[],
        workflow_started_at=now,
        workflow_status="RUNNING",
        export_logs=[],
        access_logs=[],
        state_checksum="",  # Will be calculated after state creation
        last_modified_at=now,
        modification_count=0,
        retention_until=datetime(now.year + 7, now.month, now.day),  # 7 year retention
        compliance_flags=[]
    )
    
    state = PolicyValidationState(
        case=case,
        audit=initial_audit,
        workflow_id=workflow_id,
        workflow_version="1.0.0",
        errors=[],
        warnings=[]
    )
    
    return state


def create_case_from_crm_payload(payload: Dict[str, Any]) -> Case:
    """
    Create Case state from CRM payload.
    
    Args:
        payload: CRM webhook payload
        
    Returns:
        Case state object
    """
    now = datetime.utcnow()
    case_id = str(uuid.uuid4())
    
    # Calculate SLA based on priority
    priority_str = payload.get('priority', 'MEDIUM').upper()
    priority = Priority(priority_str) if priority_str in [p.value for p in Priority] else Priority.MEDIUM
    
    # SLA calculation (hours)
    sla_hours = {
        Priority.CRITICAL: 4,
        Priority.HIGH: 12,
        Priority.MEDIUM: 24,
        Priority.LOW: 48
    }
    
    from datetime import timedelta
    sla_target = now + timedelta(hours=sla_hours[priority])
    
    # Process attachments
    attachments = []
    for attachment_data in payload.get('attachments', []):
        attachment = CaseAttachment(
            attachment_id=str(uuid.uuid4()),
            filename=attachment_data.get('filename', ''),
            content_type=attachment_data.get('content_type', ''),
            size_bytes=attachment_data.get('size_bytes', 0),
            checksum=attachment_data.get('checksum', ''),
            storage_path=attachment_data.get('storage_path', ''),
            uploaded_at=now
        )
        attachments.append(attachment)
    
    case = Case(
        case_id=case_id,
        crm_ticket_id=payload.get('ticket_id', ''),
        customer_id=payload.get('customer_id', ''),
        contract_id=payload.get('contract_id', ''),
        insurer_id=payload.get('insurer_id', ''),
        plan_id=payload.get('plan_id', ''),
        service_code=payload.get('service_code', ''),
        service_description=payload.get('service_description'),
        service_date=datetime.fromisoformat(payload.get('service_date', now.isoformat())),
        provider_id=payload.get('provider_id'),
        attachments=attachments,
        priority=priority,
        sla_target=sla_target,
        created_at=now,
        updated_at=now,
        state=CaseState.INGESTED,
        assigned_queue=payload.get('queue', 'default'),
        channel=payload.get('channel'),
        notes=payload.get('notes'),
        tags=payload.get('tags', [])
    )
    
    return case
