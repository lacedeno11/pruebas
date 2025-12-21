"""
Audit trail data models.

Represents complete audit trail for decisions and actions.
Based on UC-OP-04 Auditoría y Evidencia de Decisión.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Type of LangGraph node."""

    CASE_INGEST = "CASE_INGEST"
    INTELLIGENT_ROUTING = "INTELLIGENT_ROUTING"
    POLICY_RETRIEVAL = "POLICY_RETRIEVAL"
    RULES_CHECKLIST = "RULES_CHECKLIST"
    DECISION_ORCHESTRATOR = "DECISION_ORCHESTRATOR"
    INSURER_CONNECTOR = "INSURER_CONNECTOR"
    AUDITED_CLOSURE = "AUDITED_CLOSURE"
    GUARDRAILS = "GUARDRAILS"
    ML_CLASSIFY = "ML_CLASSIFY"
    ML_ANOMALY = "ML_ANOMALY"
    ML_ETA = "ML_ETA"


class NodeExecution(BaseModel):
    """
    Record of a single LangGraph node execution.

    Provides complete traceability of the decision pipeline.
    """

    execution_id: str = Field(..., description="Unique execution identifier")
    case_id: str = Field(..., description="Associated case identifier")
    node_type: NodeType = Field(..., description="Type of node executed")
    node_name: str = Field(..., description="Specific node instance name")

    # Execution timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    duration_ms: Optional[int] = Field(None)

    # Input/Output snapshots (for reproducibility)
    input_state_hash: str = Field(..., description="Hash of input state")
    output_state_hash: Optional[str] = Field(None, description="Hash of output state")

    # Outcome
    status: str = Field(default="RUNNING", description="RUNNING, SUCCESS, FAILED, SKIPPED")
    error_message: Optional[str] = Field(None)
    error_type: Optional[str] = Field(None)

    # Decisions made in this node
    decisions: list[dict] = Field(default_factory=list)

    # Resources accessed
    documents_accessed: list[str] = Field(default_factory=list)
    services_called: list[str] = Field(default_factory=list)

    # Model versions (if ML node)
    model_version: Optional[str] = Field(None)

    # Guardrail results (if applicable)
    guardrail_flags: list[str] = Field(default_factory=list)


class AccessLog(BaseModel):
    """Log of audit data access."""

    access_id: str = Field(..., description="Access log identifier")
    case_id: str = Field(..., description="Accessed case ID")
    accessed_by: str = Field(..., description="User who accessed")
    user_role: str = Field(..., description="User role at access time")
    access_type: str = Field(..., description="VIEW, EXPORT, DOWNLOAD")
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_reason: Optional[str] = Field(None, description="Stated reason for access")
    ip_address: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)


class ExportLog(BaseModel):
    """Log of audit data exports."""

    export_id: str = Field(..., description="Export identifier")
    case_ids: list[str] = Field(..., description="Exported case IDs")
    exported_by: str = Field(..., description="User who exported")
    user_role: str = Field(..., description="User role at export time")
    export_format: str = Field(..., description="PDF, JSON, CSV, etc.")
    export_reason: str = Field(..., description="Reason for export")
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    file_checksum: Optional[str] = Field(None, description="Hash of exported file")
    approval_id: Optional[str] = Field(None, description="Required approval if sensitive")


class Finding(BaseModel):
    """Audit finding or incident."""

    finding_id: str = Field(..., description="Finding identifier")
    case_id: str = Field(..., description="Related case ID")
    finding_type: str = Field(..., description="DISCREPANCY, VIOLATION, ANOMALY, IMPROVEMENT")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW, INFO")
    title: str = Field(..., description="Brief title")
    description: str = Field(..., description="Detailed description")
    evidence_refs: list[str] = Field(default_factory=list)
    created_by: str = Field(..., description="Auditor who created")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="OPEN", description="OPEN, IN_PROGRESS, RESOLVED, CLOSED")
    resolution: Optional[str] = Field(None)
    resolved_at: Optional[datetime] = Field(None)


class AuditTrail(BaseModel):
    """
    Complete audit trail for a case.

    Aggregates all execution logs, access logs, and findings.
    """

    trail_id: str = Field(..., description="Audit trail identifier")
    case_id: str = Field(..., description="Associated case identifier")

    # Node execution log (LangGraph trace)
    node_executions: list[NodeExecution] = Field(default_factory=list)

    # Summary metrics
    total_nodes_executed: int = Field(default=0)
    total_duration_ms: int = Field(default=0)
    failed_nodes: list[str] = Field(default_factory=list)

    # Version tracking
    model_versions: dict[str, str] = Field(
        default_factory=dict, description="ML model versions used"
    )
    policy_versions: dict[str, str] = Field(
        default_factory=dict, description="Policy document versions used"
    )
    rule_set_version: Optional[str] = Field(None)
    guardrail_version: Optional[str] = Field(None)
    threshold_config_version: Optional[str] = Field(None)

    # HITL actions
    hitl_requests: list[str] = Field(default_factory=list, description="HITL request IDs")
    hitl_responses: list[str] = Field(default_factory=list, description="HITL response IDs")

    # Access and export logs
    access_logs: list[AccessLog] = Field(default_factory=list)
    export_logs: list[ExportLog] = Field(default_factory=list)

    # Findings
    findings: list[Finding] = Field(default_factory=list)

    # Final state
    final_decision_id: Optional[str] = Field(None)
    final_status: Optional[str] = Field(None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = Field(None)

    def add_node_execution(self, execution: NodeExecution) -> None:
        """Add node execution and update metrics."""
        self.node_executions.append(execution)
        self.total_nodes_executed = len(self.node_executions)
        if execution.duration_ms:
            self.total_duration_ms += execution.duration_ms
        if execution.status == "FAILED":
            self.failed_nodes.append(execution.node_name)
        self.last_updated_at = datetime.utcnow()
