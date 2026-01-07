"""
LangGraph State Schema for Policy Validation Copilot

This module defines the complete state schema for the Policy Validation Copilot
LangGraph workflow as specified in Anexo A of the functional specification.

The state schema includes:
- CaseState: Case identifiers, service details, dates, attachments, SLA, state, queue
- EvidencePackState: Evidence items with doc references and coverage metrics
- ChecklistState: Checklist items with outcomes, evidence references, and missing fields
- MLState: ML service outputs and model versions
- DecisionState: Decision status, confidence, risk, and next actions
- GuardrailsState: Guardrail decisions, flags, and redactions
- HITLState: Human-in-the-loop requirements and approvals
- AuditState: Node execution logs, timestamps, and export logs
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


# Enums for state values
class CaseStatus(str, Enum):
    """Case status enumeration"""
    NUEVO = "NUEVO"
    EN_PROCESO = "EN_PROCESO"
    APROBADO = "APROBADO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    PENDIENTE_DATOS = "PENDIENTE_DATOS"
    PENDIENTE_POLITICA = "PENDIENTE_POLITICA"
    PENDIENTE_ASEGURADORA = "PENDIENTE_ASEGURADORA"
    PENDIENTE_SISTEMA = "PENDIENTE_SISTEMA"
    ESCALADO_HITL = "ESCALADO_HITL"


class Priority(str, Enum):
    """Priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionStatus(str, Enum):
    """Decision status enumeration"""
    PENDING = "PENDING"
    APROBADO = "APROBADO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    ESCALADO = "ESCALADO"


class ConfidenceLevel(str, Enum):
    """Confidence levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskLevel(str, Enum):
    """Risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GuardrailDecision(str, Enum):
    """Guardrail decision types"""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


# Base models for nested structures
class Attachment(BaseModel):
    """Attachment metadata"""
    attachment_id: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    upload_timestamp: datetime
    storage_path: str


class EvidenceItem(BaseModel):
    """Individual evidence item with document reference"""
    doc_id: str
    version: str
    checksum: str
    pointer: str = Field(..., description="Exact reference (page/cell/section)")
    excerpt: Optional[str] = Field(None, description="Text excerpt or table reference")
    table_ref: Optional[str] = Field(None, description="Table reference if applicable")
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class ChecklistItem(BaseModel):
    """Individual checklist item with outcome and evidence"""
    item_id: str
    description: str
    outcome: Optional[str] = Field(None, description="YES/NO/MISSING/UNKNOWN")
    evidence_ref: Optional[str] = Field(None, description="Reference to evidence item")
    rule_id: Optional[str] = Field(None, description="Associated rule identifier")
    is_critical: bool = Field(False, description="Whether this item is critical for approval")


class MLOutput(BaseModel):
    """ML service output structure"""
    service_name: str
    model_version: str
    timestamp: datetime
    outputs: Dict[str, Any]
    confidence_scores: Optional[Dict[str, float]] = None
    top_features: Optional[List[str]] = None


class GuardrailFlag(BaseModel):
    """Guardrail flag with details"""
    flag_type: str
    severity: str
    description: str
    timestamp: datetime
    rule_id: Optional[str] = None


class HITLQuestion(BaseModel):
    """HITL question structure"""
    question_id: str
    question_text: str
    question_type: str
    required: bool = True
    answer: Optional[str] = None
    answered_by: Optional[str] = None
    answered_at: Optional[datetime] = None


class HITLApproval(BaseModel):
    """HITL approval structure"""
    approval_id: str
    approver_id: str
    approval_type: str
    status: str
    comments: Optional[str] = None
    timestamp: datetime


class NodeExecution(BaseModel):
    """Node execution log entry"""
    node_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_id: str


# Main state components
class CaseState(BaseModel):
    """Case state containing all case-related information"""
    # Identifiers
    case_id: str
    crm_ticket_id: str
    customer_id: str
    contract_id: Optional[str] = None
    
    # Insurance and service details
    insurer_id: str
    plan_id: str
    service_code: Optional[str] = None
    service_description: Optional[str] = None
    service_date: datetime
    provider_id: Optional[str] = None
    
    # Attachments and documentation
    attachments: List[Attachment] = Field(default_factory=list)
    
    # Operational details
    priority: Priority = Priority.MEDIUM
    sla_target: Optional[datetime] = None
    state: CaseStatus = CaseStatus.NUEVO
    assigned_queue: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional context
    channel: Optional[str] = None
    source_system: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidencePackState(BaseModel):
    """Evidence pack state with document references and coverage metrics"""
    evidence_pack_id: str
    items: List[EvidenceItem] = Field(default_factory=list)
    coverage_score: float = Field(0.0, ge=0.0, le=1.0)
    conflicts_detected: bool = False
    conflict_details: Optional[List[str]] = None
    missing_sources: List[str] = Field(default_factory=list)
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)
    allowlist_validated: bool = False
    
    @validator('coverage_score')
    def validate_coverage_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Coverage score must be between 0.0 and 1.0')
        return v


class ChecklistState(BaseModel):
    """Checklist state with evaluation outcomes and evidence references"""
    checklist_id: str
    items: List[ChecklistItem] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    rule_ids_applied: List[str] = Field(default_factory=list)
    evaluation_log: List[str] = Field(default_factory=list)
    completion_percentage: float = Field(0.0, ge=0.0, le=100.0)
    critical_items_passed: bool = False
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class MLState(BaseModel):
    """ML state containing outputs from all ML services"""
    # Classification service output
    classification: Optional[MLOutput] = None
    
    # Anomaly detection output
    anomaly: Optional[MLOutput] = None
    
    # ETA prediction output
    eta: Optional[MLOutput] = None
    
    # Consolidated ML insights
    ml_degraded: bool = False
    fallback_used: bool = False
    drift_detected: bool = False
    
    # Model versions tracking
    model_versions: Dict[str, str] = Field(default_factory=dict)
    
    # Execution metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class DecisionState(BaseModel):
    """Decision state with confidence, risk, and next actions"""
    decision_id: str
    status: DecisionStatus = DecisionStatus.PENDING
    
    # Confidence and risk metrics
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    risk_level: RiskLevel = RiskLevel.MEDIUM
    anomaly_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # ETA and timing
    eta_estimate: Optional[int] = Field(None, description="ETA in minutes")
    
    # Actions and routing
    next_actions: List[str] = Field(default_factory=list)
    requires_hitl: bool = False
    requires_external_consultation: bool = False
    auto_close_eligible: bool = False
    
    # Thresholds and configuration
    thresholds_version: str
    
    # Decision rationale
    decision_rationale: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    
    # Timestamps
    decision_timestamp: Optional[datetime] = None


class GuardrailsState(BaseModel):
    """Guardrails state with security controls and governance"""
    guardrails_id: str
    decision: GuardrailDecision = GuardrailDecision.ALLOW
    
    # Security flags and controls
    flags: List[GuardrailFlag] = Field(default_factory=list)
    security_events: List[str] = Field(default_factory=list)
    
    # Content controls
    redactions: Dict[str, str] = Field(default_factory=dict)
    pii_detected: bool = False
    injection_detected: bool = False
    
    # Source validation
    allowlist_violations: List[str] = Field(default_factory=list)
    evidence_anchoring_passed: bool = True
    
    # RBAC/ABAC results
    access_granted: bool = True
    role_permissions: Dict[str, bool] = Field(default_factory=dict)
    
    # Execution metadata
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    guardrail_version: str


class HITLState(BaseModel):
    """Human-in-the-loop state for manual interventions"""
    hitl_id: str
    required: bool = False
    
    # HITL triggers
    trigger_reasons: List[str] = Field(default_factory=list)
    escalation_level: str = "STANDARD"
    
    # Questions and interactions
    questions: List[HITLQuestion] = Field(default_factory=list)
    approvals: List[HITLApproval] = Field(default_factory=list)
    
    # Status tracking
    hitl_status: str = "NOT_REQUIRED"  # NOT_REQUIRED, PENDING, IN_PROGRESS, COMPLETED
    assigned_to: Optional[str] = None
    
    # Timing
    requested_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    
    # Outcomes
    hitl_decision: Optional[str] = None
    hitl_comments: Optional[str] = None


class AuditState(BaseModel):
    """Audit state with complete execution traceability"""
    audit_id: str
    
    # Node execution tracking
    node_execution_log: List[NodeExecution] = Field(default_factory=list)
    
    # Timestamps and timing
    workflow_start_time: datetime = Field(default_factory=datetime.utcnow)
    workflow_end_time: Optional[datetime] = None
    total_execution_time: Optional[int] = Field(None, description="Total time in seconds")
    
    # Export and access logs
    export_logs: List[str] = Field(default_factory=list)
    access_logs: List[str] = Field(default_factory=list)
    
    # Traceability
    policy_versions_used: Dict[str, str] = Field(default_factory=dict)
    rule_versions_used: Dict[str, str] = Field(default_factory=dict)
    model_versions_used: Dict[str, str] = Field(default_factory=dict)
    
    # Compliance and governance
    compliance_flags: List[str] = Field(default_factory=list)
    data_lineage: Dict[str, Any] = Field(default_factory=dict)
    
    # Immutability controls
    audit_hash: Optional[str] = None
    previous_audit_hash: Optional[str] = None


# Main PolicyValidationState
class PolicyValidationState(BaseModel):
    """
    Main LangGraph state for Policy Validation Copilot workflow
    
    This is the complete state that flows through all LangGraph nodes
    and maintains the full context of the policy validation process.
    """
    # Core state components
    case: CaseState
    evidence_pack: Optional[EvidencePackState] = None
    checklist: Optional[ChecklistState] = None
    ml: Optional[MLState] = None
    decision: Optional[DecisionState] = None
    guardrails: Optional[GuardrailsState] = None
    hitl: Optional[HITLState] = None
    audit: AuditState
    
    # Workflow metadata
    workflow_id: str
    workflow_version: str = "1.0.0"
    current_node: Optional[str] = None
    
    # Global flags and controls
    workflow_status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED, PAUSED
    error_state: bool = False
    error_messages: List[str] = Field(default_factory=list)
    
    # Configuration references
    config_version: str
    environment: str = "production"
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    
    def update_audit_log(self, node_name: str, status: str, **kwargs):
        """Helper method to update audit log"""
        execution = NodeExecution(
            node_name=node_name,
            start_time=datetime.utcnow(),
            status=status,
            execution_id=f"{self.workflow_id}_{node_name}_{len(self.audit.node_execution_log)}",
            **kwargs
        )
        self.audit.node_execution_log.append(execution)
    
    def set_current_node(self, node_name: str):
        """Helper method to set current node and update audit"""
        self.current_node = node_name
        self.update_audit_log(node_name, "STARTED")
    
    def complete_current_node(self, outputs: Optional[Dict[str, Any]] = None):
        """Helper method to complete current node execution"""
        if self.current_node and self.audit.node_execution_log:
            last_execution = self.audit.node_execution_log[-1]
            if last_execution.node_name == self.current_node:
                last_execution.end_time = datetime.utcnow()
                last_execution.status = "COMPLETED"
                if outputs:
                    last_execution.outputs = outputs
    
    def add_error(self, error_message: str, node_name: Optional[str] = None):
        """Helper method to add error to state"""
        self.error_state = True
        self.error_messages.append(error_message)
        if node_name and self.audit.node_execution_log:
            last_execution = self.audit.node_execution_log[-1]
            if last_execution.node_name == node_name:
                last_execution.status = "FAILED"
                last_execution.error_message = error_message
