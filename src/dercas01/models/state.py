"""
LangGraph State Schema for DERCAS 01 Policy Validation Copilot

Contains the PolicyValidationState class that defines the complete state
structure for the LangGraph workflow, based on Anexo A specifications.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from .entities import (
    AuditTrail,
    Case,
    Checklist,
    DecisionRecord,
    EvidencePack,
    GuardrailRecord,
    HITLRequest,
    MLScoreRecord,
)
from .enums import CaseStatus, DecisionStatus, GuardrailAction, HITLReason


class CaseState(BaseModel):
    """
    Case state component containing all case-related information.
    
    Based on Anexo A: case: ids, servicio, fechas, adjuntos, SLA, estado, cola
    """
    
    case_id: str = Field(..., description="Business case identifier")
    crm_ticket_id: Optional[str] = Field(default=None, description="CRM/Ticketing system ID")
    
    # Customer and service information
    customer_id: Optional[str] = Field(default=None, description="Customer identifier")
    contract_id: Optional[str] = Field(default=None, description="Contract identifier")
    insurer_id: str = Field(..., description="Insurance company identifier")
    plan_id: str = Field(..., description="Insurance plan identifier")
    service_code: Optional[str] = Field(default=None, description="Service code")
    service_date: Optional[datetime] = Field(default=None, description="Service date")
    provider_id: Optional[str] = Field(default=None, description="Healthcare provider ID")
    
    # Attachments and metadata
    attachments: List[str] = Field(default_factory=list, description="List of attachment file IDs")
    priority: str = Field(default="MEDIUM", description="Case priority")
    sla_target: Optional[datetime] = Field(default=None, description="SLA target completion time")
    state: CaseStatus = Field(default=CaseStatus.CREATED, description="Current case status")
    assigned_queue: str = Field(default="AUTO_PROCESSING", description="Assigned processing queue")
    
    # Processing context
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class EvidencePackState(BaseModel):
    """
    Evidence Pack state component.
    
    Based on Anexo A: evidence_pack: items[] con doc_id/version/checksum/pointer/excerpt + coverage_score
    """
    
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Evidence items with doc_id/version/checksum/pointer/excerpt")
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall coverage score")
    conflicts_detected: bool = Field(default=False, description="Whether conflicts were detected")
    missing_sources: List[str] = Field(default_factory=list, description="Missing required sources")
    
    # Metadata
    retrieval_timestamp: Optional[datetime] = Field(default=None, description="When evidence was retrieved")
    retrieval_model_version: Optional[str] = Field(default=None, description="RAG model version used")


class ChecklistState(BaseModel):
    """
    Checklist state component.
    
    Based on Anexo A: checklist: items[] outcome + evidence_ref; missing_fields; rule_ids_applied
    """
    
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Checklist items with outcome + evidence_ref")
    missing_fields: List[str] = Field(default_factory=list, description="Missing required fields")
    rule_ids_applied: List[str] = Field(default_factory=list, description="Applied rule IDs")
    
    # Summary metrics
    total_items: int = Field(default=0, description="Total checklist items")
    passed_items: int = Field(default=0, description="Number of passed items")
    failed_items: int = Field(default=0, description="Number of failed items")
    missing_items: int = Field(default=0, description="Number of missing items")
    
    # Metadata
    evaluation_timestamp: Optional[datetime] = Field(default=None, description="When evaluation was performed")
    rule_set_version: Optional[str] = Field(default=None, description="Rule set version used")


class MLState(BaseModel):
    """
    ML state component containing all ML model outputs and versions.
    
    Based on Anexo A: ml: outputs + model_versions (classify/anomaly/eta)
    """
    
    # Classification outputs
    classification_output: Optional[Dict[str, Any]] = Field(default=None, description="Classification model output")
    classification_model_version: Optional[str] = Field(default=None, description="Classification model version")
    
    # Anomaly detection outputs
    anomaly_output: Optional[Dict[str, Any]] = Field(default=None, description="Anomaly detection model output")
    anomaly_model_version: Optional[str] = Field(default=None, description="Anomaly detection model version")
    
    # ETA prediction outputs
    eta_output: Optional[Dict[str, Any]] = Field(default=None, description="ETA prediction model output")
    eta_model_version: Optional[str] = Field(default=None, description="ETA prediction model version")
    
    # Consolidated outputs for decision making
    outputs: Dict[str, Any] = Field(default_factory=dict, description="All ML outputs consolidated")
    model_versions: Dict[str, str] = Field(default_factory=dict, description="All model versions used")
    
    # Quality metrics
    ml_degraded: bool = Field(default=False, description="Whether ML services are degraded")
    fallback_used: bool = Field(default=False, description="Whether fallback mechanisms were used")
    inference_timestamps: Dict[str, datetime] = Field(default_factory=dict, description="Inference timestamps by model type")


class DecisionState(BaseModel):
    """
    Decision state component.
    
    Based on Anexo A: decision: status + confidence/risk + next_actions + thresholds_version
    """
    
    status: Optional[DecisionStatus] = Field(default=None, description="Decision status")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence")
    risk_level: str = Field(default="MEDIUM", description="Risk assessment level")
    
    # Supporting metrics
    anomaly_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Anomaly score")
    eta_estimate: Optional[int] = Field(default=None, description="ETA in minutes")
    
    # Decision logic
    next_actions: List[str] = Field(default_factory=list, description="Recommended next actions")
    thresholds_version: Optional[str] = Field(default=None, description="Decision thresholds version used")
    
    # Decision rationale
    decision_rationale: Optional[str] = Field(default=None, description="Decision rationale")
    auto_close_eligible: bool = Field(default=False, description="Whether case is eligible for auto-close")
    
    # Final decision (when completed)
    final_decision: Optional[DecisionStatus] = Field(default=None, description="Final decision if completed")
    decided_by: Optional[str] = Field(default=None, description="Decision maker (user ID or 'SYSTEM')")
    decided_at: Optional[datetime] = Field(default=None, description="Decision timestamp")


class GuardrailsState(BaseModel):
    """
    Guardrails state component.
    
    Based on Anexo A: guardrails: decision + flags + redactions
    """
    
    decision: GuardrailAction = Field(default=GuardrailAction.ALLOW, description="Overall guardrail decision")
    flags: List[str] = Field(default_factory=list, description="Security/compliance flags raised")
    redactions: List[str] = Field(default_factory=list, description="Redactions applied")
    
    # Detailed check results
    checks_performed: List[Dict[str, Any]] = Field(default_factory=list, description="Individual guardrail checks")
    blocked_reasons: List[str] = Field(default_factory=list, description="Reasons for blocking if applicable")
    
    # Metadata
    check_timestamp: Optional[datetime] = Field(default=None, description="Last check timestamp")
    guardrails_version: Optional[str] = Field(default=None, description="Guardrails version used")
    
    # Security events
    security_events: List[Dict[str, Any]] = Field(default_factory=list, description="Security events detected")


class HITLState(BaseModel):
    """
    Human-in-the-loop state component.
    
    Based on Anexo A: hitl: required + preguntas/respuestas + aprobaciones
    """
    
    required: bool = Field(default=False, description="Whether HITL is required")
    reasons: List[HITLReason] = Field(default_factory=list, description="Reasons for HITL escalation")
    
    # Questions and responses
    questions: List[str] = Field(default_factory=list, description="Questions for human review")
    answers: List[str] = Field(default_factory=list, description="Human responses")
    
    # Approvals and workflow
    approvals: List[Dict[str, Any]] = Field(default_factory=list, description="Approval records")
    assigned_to_role: Optional[str] = Field(default=None, description="Role assigned to handle request")
    assigned_to_user: Optional[str] = Field(default=None, description="Specific user assigned")
    
    # Status and timing
    request_status: str = Field(default="PENDING", description="HITL request status")
    requested_at: Optional[datetime] = Field(default=None, description="Request timestamp")
    assigned_at: Optional[datetime] = Field(default=None, description="Assignment timestamp")
    responded_at: Optional[datetime] = Field(default=None, description="Response timestamp")
    responded_by: Optional[str] = Field(default=None, description="Responder user ID")
    
    # Human decision
    human_decision: Optional[DecisionStatus] = Field(default=None, description="Human decision")
    human_notes: Optional[str] = Field(default=None, description="Human notes")


class AuditState(BaseModel):
    """
    Audit state component.
    
    Based on Anexo A: audit: node_execution_log + timestamps + export_logs
    """
    
    # LangGraph execution tracking
    node_execution_log: List[Dict[str, Any]] = Field(default_factory=list, description="LangGraph node execution log")
    current_node: Optional[str] = Field(default=None, description="Currently executing node")
    execution_path: List[str] = Field(default_factory=list, description="Execution path taken")
    
    # Timestamps
    timestamps: Dict[str, datetime] = Field(default_factory=dict, description="Key event timestamps")
    workflow_started_at: Optional[datetime] = Field(default=None, description="Workflow start time")
    workflow_completed_at: Optional[datetime] = Field(default=None, description="Workflow completion time")
    
    # Export and access logs
    export_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Export access logs")
    access_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Data access logs")
    
    # Versioning and traceability
    model_versions_used: Dict[str, str] = Field(default_factory=dict, description="All model versions used")
    policy_versions_used: Dict[str, str] = Field(default_factory=dict, description="Policy versions used")
    rule_versions_used: Dict[str, str] = Field(default_factory=dict, description="Rule versions used")
    
    # Correlation and session tracking
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for related events")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors encountered during processing")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Warnings generated during processing")


class PolicyValidationState(TypedDict, total=False):
    """
    Complete LangGraph state schema for Policy Validation Copilot.
    
    This is the main state object that flows through the LangGraph workflow,
    containing all the components specified in Anexo A.
    
    Uses TypedDict for LangGraph compatibility while maintaining type safety.
    """
    
    # Core state components (Anexo A specification)
    case: CaseState
    evidence_pack: EvidencePackState
    checklist: ChecklistState
    ml: MLState
    decision: DecisionState
    guardrails: GuardrailsState
    hitl: HITLState
    audit: AuditState
    
    # Workflow control
    next_node: Optional[str]
    workflow_complete: bool
    error_occurred: bool
    error_message: Optional[str]
    
    # External query state (for UC-OP-09)
    external_query_required: bool
    external_query_status: Optional[str]
    external_query_response: Optional[Dict[str, Any]]
    
    # Processing metadata
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    total_processing_time_ms: Optional[float]


# Helper functions for state management

def create_initial_state(case_data: Dict[str, Any]) -> PolicyValidationState:
    """
    Create initial PolicyValidationState from case data.
    
    Args:
        case_data: Initial case information
        
    Returns:
        Initialized PolicyValidationState
    """
    return PolicyValidationState(
        case=CaseState(**case_data),
        evidence_pack=EvidencePackState(),
        checklist=ChecklistState(),
        ml=MLState(),
        decision=DecisionState(),
        guardrails=GuardrailsState(),
        hitl=HITLState(),
        audit=AuditState(
            workflow_started_at=datetime.utcnow(),
            correlation_id=case_data.get("case_id"),
        ),
        next_node="case_ingest",
        workflow_complete=False,
        error_occurred=False,
        external_query_required=False,
        processing_started_at=datetime.utcnow(),
    )


def update_audit_log(
    state: PolicyValidationState,
    node_name: str,
    node_input: Optional[Dict[str, Any]] = None,
    node_output: Optional[Dict[str, Any]] = None,
    execution_time_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> PolicyValidationState:
    """
    Update audit log with node execution information.
    
    Args:
        state: Current state
        node_name: Name of the executed node
        node_input: Input data for the node
        node_output: Output data from the node
        execution_time_ms: Execution time in milliseconds
        error: Error message if any
        
    Returns:
        Updated state with audit information
    """
    audit_entry = {
        "node_name": node_name,
        "timestamp": datetime.utcnow().isoformat(),
        "node_input": node_input,
        "node_output": node_output,
        "execution_time_ms": execution_time_ms,
        "error": error,
    }
    
    state["audit"]["node_execution_log"].append(audit_entry)
    state["audit"]["execution_path"].append(node_name)
    state["audit"]["current_node"] = node_name
    state["audit"]["timestamps"][f"{node_name}_executed_at"] = datetime.utcnow()
    
    if error:
        state["audit"]["errors"].append({
            "node_name": node_name,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["error_occurred"] = True
        state["error_message"] = error
    
    return state


def is_auto_close_eligible(state: PolicyValidationState) -> bool:
    """
    Check if case is eligible for auto-close based on business rules.
    
    Business Rule RB-04: confidence_high + risk_low + coverage_ok + no guardrails
    
    Args:
        state: Current state
        
    Returns:
        True if eligible for auto-close
    """
    decision = state.get("decision", {})
    evidence_pack = state.get("evidence_pack", {})
    guardrails = state.get("guardrails", {})
    
    # Check confidence threshold
    confidence_high = decision.get("confidence_score", 0.0) >= 0.85
    
    # Check risk level
    risk_low = decision.get("risk_level", "HIGH") == "LOW"
    
    # Check coverage
    coverage_ok = evidence_pack.get("coverage_score", 0.0) >= 0.8
    
    # Check guardrails
    no_critical_guardrails = guardrails.get("decision", "BLOCK") == "ALLOW"
    
    # Check for HITL requirements
    no_hitl_required = not state.get("hitl", {}).get("required", False)
    
    return (
        confidence_high
        and risk_low
        and coverage_ok
        and no_critical_guardrails
        and no_hitl_required
    )


def should_escalate_to_hitl(state: PolicyValidationState) -> tuple[bool, List[HITLReason]]:
    """
    Determine if case should be escalated to HITL based on various factors.
    
    Args:
        state: Current state
        
    Returns:
        Tuple of (should_escalate, reasons)
    """
    reasons = []
    
    decision = state.get("decision", {})
    evidence_pack = state.get("evidence_pack", {})
    guardrails = state.get("guardrails", {})
    ml = state.get("ml", {})
    
    # Low/medium confidence
    confidence = decision.get("confidence_score", 0.0)
    if confidence < 0.65:
        reasons.append(HITLReason.LOW_CONFIDENCE)
    
    # High risk
    risk_level = decision.get("risk_level", "MEDIUM")
    if risk_level in ["HIGH", "CRITICAL"]:
        reasons.append(HITLReason.HIGH_RISK)
    
    # Anomaly detected
    anomaly_score = decision.get("anomaly_score", 0.0)
    if anomaly_score > 0.8:
        reasons.append(HITLReason.ANOMALY_DETECTED)
    
    # Missing evidence
    coverage_score = evidence_pack.get("coverage_score", 0.0)
    if coverage_score < 0.8:
        reasons.append(HITLReason.MISSING_EVIDENCE)
    
    # Guardrail blocks
    guardrail_decision = guardrails.get("decision", "ALLOW")
    if guardrail_decision in ["BLOCK", "REQUIRE_HITL"]:
        reasons.append(HITLReason.GUARDRAIL_BLOCK)
    
    # Policy conflicts
    conflicts_detected = evidence_pack.get("conflicts_detected", False)
    if conflicts_detected:
        reasons.append(HITLReason.POLICY_CONFLICT)
    
    # ML degradation
    ml_degraded = ml.get("ml_degraded", False)
    if ml_degraded:
        reasons.append(HITLReason.MANUAL_REVIEW_REQUESTED)
    
    return len(reasons) > 0, reasons
