"""
Core Data Models for DERCAS 01 Policy Validation Copilot

Contains all Pydantic data models for entities used throughout the system.
Based on the use case specifications and business requirements.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from .enums import (
    AuditEventType,
    CaseStatus,
    ChecklistOutcome,
    ConfidenceLevel,
    DecisionStatus,
    DocumentType,
    ExceptionStatus,
    ExternalQueryStatus,
    GuardrailAction,
    HITLReason,
    MLModelType,
    PolicyStatus,
    Priority,
    QueueType,
    RiskLevel,
    UserRole,
)


class BaseEntity(BaseModel):
    """Base entity with common fields."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator user ID")
    updated_by: Optional[str] = Field(default=None, description="Last updater user ID")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class Case(BaseEntity):
    """
    Core case entity representing a policy validation request.
    
    Based on UC-OP-01 and UC-OP-05 specifications.
    """
    
    case_id: str = Field(..., description="Business case identifier")
    crm_ticket_id: Optional[str] = Field(default=None, description="CRM/Ticketing system ID")
    
    # Customer and contract information
    customer_id: Optional[str] = Field(default=None, description="Customer identifier")
    contract_id: Optional[str] = Field(default=None, description="Contract identifier")
    insurer_id: str = Field(..., description="Insurance company identifier")
    plan_id: str = Field(..., description="Insurance plan identifier")
    
    # Service information
    service_code: Optional[str] = Field(default=None, description="Service code")
    service_description: Optional[str] = Field(default=None, description="Free text service description")
    service_date: Optional[datetime] = Field(default=None, description="Service date")
    provider_id: Optional[str] = Field(default=None, description="Healthcare provider ID")
    
    # Case metadata
    priority: Priority = Field(default=Priority.MEDIUM, description="Case priority")
    sla_target: Optional[datetime] = Field(default=None, description="SLA target completion time")
    status: CaseStatus = Field(default=CaseStatus.CREATED, description="Current case status")
    assigned_queue: QueueType = Field(default=QueueType.AUTO_PROCESSING, description="Assigned processing queue")
    
    # Attachments and context
    attachments: List[str] = Field(default_factory=list, description="List of attachment file IDs")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    
    # Processing metadata
    processing_started_at: Optional[datetime] = Field(default=None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(default=None, description="Processing completion time")
    last_activity_at: Optional[datetime] = Field(default=None, description="Last activity timestamp")


class EvidenceItem(BaseModel):
    """Individual evidence item within an Evidence Pack."""
    
    doc_id: str = Field(..., description="Document identifier")
    version: str = Field(..., description="Document version")
    checksum: str = Field(..., description="Document checksum for integrity")
    pointer: str = Field(..., description="Exact reference (page/cell/section)")
    excerpt: Optional[str] = Field(default=None, description="Relevant text excerpt")
    table_ref: Optional[str] = Field(default=None, description="Table reference if applicable")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in extraction")


class EvidencePack(BaseEntity):
    """
    Evidence Pack containing all supporting documentation for a decision.
    
    Based on UC-OP-06 specifications for RAG and evidence construction.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    items: List[EvidenceItem] = Field(default_factory=list, description="Evidence items")
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall coverage score")
    conflicts_detected: bool = Field(default=False, description="Whether conflicts were detected")
    missing_sources: List[str] = Field(default_factory=list, description="Missing required sources")
    
    # Metadata
    retrieval_query: Optional[str] = Field(default=None, description="Original retrieval query")
    retrieval_timestamp: Optional[datetime] = Field(default=None, description="When evidence was retrieved")
    retrieval_model_version: Optional[str] = Field(default=None, description="RAG model version used")


class PolicyDocument(BaseEntity):
    """
    Policy document entity for UC-OP-02 policy management.
    """
    
    doc_id: str = Field(..., description="Document identifier")
    version: str = Field(..., description="Document version")
    checksum: str = Field(..., description="Document checksum")
    
    # Document metadata
    title: str = Field(..., description="Document title")
    document_type: DocumentType = Field(default=DocumentType.POLICY, description="Document type")
    status: PolicyStatus = Field(default=PolicyStatus.DRAFT, description="Document status")
    
    # Scope and applicability
    insurer_id: str = Field(..., description="Insurance company")
    plan_ids: List[str] = Field(default_factory=list, description="Applicable plan IDs")
    service_codes: List[str] = Field(default_factory=list, description="Applicable service codes")
    
    # Validity period
    effective_date: datetime = Field(..., description="Effective start date")
    expiration_date: Optional[datetime] = Field(default=None, description="Expiration date")
    
    # Content and processing
    file_path: str = Field(..., description="File storage path")
    file_size: int = Field(..., description="File size in bytes")
    parsing_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Parsing quality score")
    
    # Approval workflow
    approved_by: Optional[str] = Field(default=None, description="Approver user ID")
    approved_at: Optional[datetime] = Field(default=None, description="Approval timestamp")
    
    # Priority for conflict resolution
    priority: int = Field(default=0, description="Priority for conflict resolution")


class ExceptionRule(BaseEntity):
    """
    Exception rule entity for UC-OP-03 exception management.
    """
    
    rule_id: str = Field(..., description="Exception rule identifier")
    
    # Scope
    customer_id: Optional[str] = Field(default=None, description="Customer ID (if customer-specific)")
    contract_id: Optional[str] = Field(default=None, description="Contract ID (if contract-specific)")
    insurer_id: str = Field(..., description="Insurance company")
    plan_id: Optional[str] = Field(default=None, description="Plan ID (if plan-specific)")
    service_codes: List[str] = Field(default_factory=list, description="Applicable service codes")
    
    # Rule definition
    rule_type: str = Field(..., description="Type of override/exception")
    rule_description: str = Field(..., description="Human-readable description")
    rule_logic: Dict[str, Any] = Field(..., description="Machine-readable rule logic")
    
    # Validity
    effective_date: datetime = Field(..., description="Effective start date")
    expiration_date: Optional[datetime] = Field(default=None, description="Expiration date")
    status: ExceptionStatus = Field(default=ExceptionStatus.PROPOSED, description="Exception status")
    
    # Evidence and justification
    evidence_links: List[str] = Field(default_factory=list, description="Supporting evidence file IDs")
    justification: str = Field(..., description="Business justification")
    
    # Approval workflow
    proposed_by: str = Field(..., description="Proposer user ID")
    approved_by: Optional[str] = Field(default=None, description="Approver user ID")
    approved_at: Optional[datetime] = Field(default=None, description="Approval timestamp")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection reason if applicable")
    
    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times applied")
    last_used_at: Optional[datetime] = Field(default=None, description="Last usage timestamp")


class ChecklistItem(BaseModel):
    """Individual checklist item evaluation."""
    
    rule_id: str = Field(..., description="Rule identifier")
    rule_description: str = Field(..., description="Human-readable rule description")
    outcome: ChecklistOutcome = Field(..., description="Evaluation outcome")
    evidence_ref: Optional[str] = Field(default=None, description="Reference to supporting evidence")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in evaluation")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class Checklist(BaseEntity):
    """
    Checklist entity for UC-OP-07 rules and checklist builder.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    items: List[ChecklistItem] = Field(default_factory=list, description="Checklist items")
    missing_fields: List[str] = Field(default_factory=list, description="Missing required fields")
    rule_ids_applied: List[str] = Field(default_factory=list, description="Applied rule IDs")
    
    # Evaluation metadata
    evaluation_timestamp: Optional[datetime] = Field(default=None, description="When evaluation was performed")
    rule_set_version: Optional[str] = Field(default=None, description="Rule set version used")
    evaluation_log: Dict[str, Any] = Field(default_factory=dict, description="Detailed evaluation log")
    
    # Summary metrics
    total_items: int = Field(default=0, description="Total checklist items")
    passed_items: int = Field(default=0, description="Number of passed items")
    failed_items: int = Field(default=0, description="Number of failed items")
    missing_items: int = Field(default=0, description="Number of missing items")


class MLScoreRecord(BaseEntity):
    """
    ML model inference record for UC-OP-11/12/13.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    model_type: MLModelType = Field(..., description="Type of ML model")
    model_version: str = Field(..., description="Model version")
    
    # Input and output
    input_features: Dict[str, Any] = Field(..., description="Input features")
    output_scores: Dict[str, Any] = Field(..., description="Model output scores")
    
    # Metadata
    inference_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Inference timestamp")
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    
    # Quality metrics
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model confidence")
    drift_score: Optional[float] = Field(default=None, description="Data drift score")
    
    # Fallback information
    fallback_used: bool = Field(default=False, description="Whether fallback was used")
    fallback_reason: Optional[str] = Field(default=None, description="Reason for fallback")


class DecisionRecord(BaseEntity):
    """
    Decision record for UC-OP-08 decision orchestrator.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    status: DecisionStatus = Field(..., description="Decision status")
    
    # Decision metrics
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    risk_level: RiskLevel = Field(..., description="Risk assessment")
    anomaly_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Anomaly score")
    eta_estimate: Optional[int] = Field(default=None, description="ETA in minutes")
    
    # Decision logic
    next_actions: List[str] = Field(default_factory=list, description="Recommended next actions")
    thresholds_version: str = Field(..., description="Decision thresholds version used")
    
    # Supporting data references
    checklist_id: Optional[UUID] = Field(default=None, description="Associated checklist ID")
    evidence_pack_id: Optional[UUID] = Field(default=None, description="Associated evidence pack ID")
    ml_scores: List[UUID] = Field(default_factory=list, description="Associated ML score record IDs")
    
    # HITL information
    requires_hitl: bool = Field(default=False, description="Whether HITL is required")
    hitl_reasons: List[HITLReason] = Field(default_factory=list, description="Reasons for HITL")
    
    # Final decision (if completed)
    final_decision: Optional[DecisionStatus] = Field(default=None, description="Final decision if completed")
    decision_rationale: Optional[str] = Field(default=None, description="Decision rationale")
    decided_by: Optional[str] = Field(default=None, description="Decision maker (user ID or 'SYSTEM')")
    decided_at: Optional[datetime] = Field(default=None, description="Decision timestamp")


class GuardrailCheck(BaseModel):
    """Individual guardrail check result."""
    
    check_type: str = Field(..., description="Type of guardrail check")
    action: GuardrailAction = Field(..., description="Guardrail action taken")
    flags: List[str] = Field(default_factory=list, description="Security/compliance flags")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in check")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional check details")


class GuardrailRecord(BaseEntity):
    """
    Guardrail enforcement record for UC-OP-10.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    checks: List[GuardrailCheck] = Field(default_factory=list, description="Individual checks performed")
    
    # Overall result
    overall_action: GuardrailAction = Field(..., description="Overall guardrail action")
    blocked_reasons: List[str] = Field(default_factory=list, description="Reasons for blocking if applicable")
    redactions_applied: List[str] = Field(default_factory=list, description="Redactions applied")
    
    # Metadata
    check_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    guardrails_version: str = Field(..., description="Guardrails version")


class HITLRequest(BaseEntity):
    """
    Human-in-the-loop request entity.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    reasons: List[HITLReason] = Field(..., description="Reasons for HITL escalation")
    
    # Request details
    assigned_to_role: UserRole = Field(..., description="Role assigned to handle request")
    assigned_to_user: Optional[str] = Field(default=None, description="Specific user assigned")
    priority: Priority = Field(default=Priority.MEDIUM, description="Request priority")
    
    # Questions and context
    questions: List[str] = Field(default_factory=list, description="Specific questions for human review")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    # Response
    answers: List[str] = Field(default_factory=list, description="Human responses")
    decision: Optional[DecisionStatus] = Field(default=None, description="Human decision")
    notes: Optional[str] = Field(default=None, description="Human notes")
    
    # Workflow
    requested_at: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    assigned_at: Optional[datetime] = Field(default=None, description="Assignment timestamp")
    responded_at: Optional[datetime] = Field(default=None, description="Response timestamp")
    responded_by: Optional[str] = Field(default=None, description="Responder user ID")


class ExternalQuery(BaseEntity):
    """
    External insurance company query for UC-OP-09.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    insurer_id: str = Field(..., description="Target insurance company")
    
    # Query details
    query_type: str = Field(..., description="Type of query")
    query_data: Dict[str, Any] = Field(..., description="Query payload")
    channel: str = Field(..., description="Communication channel used")
    
    # Response
    status: ExternalQueryStatus = Field(default=ExternalQueryStatus.PENDING, description="Query status")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="Response payload")
    response_checksum: Optional[str] = Field(default=None, description="Response integrity checksum")
    
    # Timing
    sent_at: Optional[datetime] = Field(default=None, description="Query sent timestamp")
    received_at: Optional[datetime] = Field(default=None, description="Response received timestamp")
    timeout_at: Optional[datetime] = Field(default=None, description="Query timeout timestamp")
    
    # Error handling
    retry_count: int = Field(default=0, description="Number of retries")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class AuditTrail(BaseEntity):
    """
    Audit trail entity for UC-OP-04 audit and evidence tracking.
    """
    
    case_id: str = Field(..., description="Associated case ID")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    
    # Event details
    event_data: Dict[str, Any] = Field(..., description="Event-specific data")
    user_id: Optional[str] = Field(default=None, description="User who triggered the event")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    # LangGraph node execution
    node_name: Optional[str] = Field(default=None, description="LangGraph node name")
    node_input: Optional[Dict[str, Any]] = Field(default=None, description="Node input data")
    node_output: Optional[Dict[str, Any]] = Field(default=None, description="Node output data")
    execution_time_ms: Optional[float] = Field(default=None, description="Node execution time")
    
    # Versioning
    model_versions: Dict[str, str] = Field(default_factory=dict, description="Model versions used")
    policy_versions: Dict[str, str] = Field(default_factory=dict, description="Policy versions used")
    rule_versions: Dict[str, str] = Field(default_factory=dict, description="Rule versions used")
    
    # Access control
    access_level: Optional[str] = Field(default=None, description="Required access level")
    export_restricted: bool = Field(default=False, description="Whether export is restricted")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for related events")
