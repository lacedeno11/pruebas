"""
Audit data model for Policy Validation Copilot

This module contains the Audit model for complete decision traceability
and compliance reporting as specified in UC-OP-04 and Anexo A.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity


class NodeExecution(BaseEntity):
    """
    Individual LangGraph node execution record.
    
    Tracks execution of each node in the LangGraph workflow
    with inputs, outputs, timing, and error information.
    """
    
    node_name: str = Field(..., description="Name of the executed node")
    node_type: str = Field(..., description="Type of node (AGENT, FUNCTION, CONDITION)")
    execution_id: str = Field(..., description="Unique execution identifier")
    
    # Execution timing
    started_at: datetime = Field(..., description="Node execution start time")
    completed_at: Optional[datetime] = Field(None, description="Node execution completion time")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    
    # Input/Output data
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data to the node")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output data from the node")
    state_changes: Dict[str, Any] = Field(default_factory=dict, description="Changes made to workflow state")
    
    # Execution status
    status: str = Field(..., description="Execution status (SUCCESS, FAILED, SKIPPED)")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    
    # Resource usage
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    
    # Metadata
    agent_version: Optional[str] = Field(None, description="Agent version if applicable")
    model_versions: Dict[str, str] = Field(default_factory=dict, description="Model versions used")
    
    @validator('status')
    def validate_status(cls, v):
        """Validate execution status is from allowed set."""
        valid_statuses = ['SUCCESS', 'FAILED', 'SKIPPED', 'TIMEOUT', 'CANCELLED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v
    
    @validator('duration_ms')
    def calculate_duration(cls, v, values):
        """Calculate duration if not provided."""
        if v is None and 'started_at' in values and 'completed_at' in values:
            started = values['started_at']
            completed = values['completed_at']
            if completed and started:
                duration = completed - started
                return int(duration.total_seconds() * 1000)
        return v


class ExportLog(BaseEntity):
    """
    Audit data export log record.
    
    Tracks all exports of audit data for compliance
    and access control monitoring.
    """
    
    export_id: str = Field(..., description="Unique export identifier")
    case_id: str = Field(..., description="Associated case identifier")
    
    # Export details
    export_type: str = Field(..., description="Type of export (FULL, PARTIAL, SUMMARY)")
    export_format: str = Field(..., description="Export format (JSON, PDF, CSV, XML)")
    export_scope: List[str] = Field(..., description="Scope of data exported")
    
    # Requester information
    requested_by: str = Field(..., description="User who requested export")
    requester_role: str = Field(..., description="Role of the requester")
    request_reason: str = Field(..., description="Reason for export request")
    
    # Authorization
    authorized_by: Optional[str] = Field(None, description="User who authorized export")
    authorization_level: Optional[str] = Field(None, description="Authorization level required")
    
    # Export metadata
    exported_at: datetime = Field(default_factory=datetime.utcnow, description="Export timestamp")
    export_size_bytes: Optional[int] = Field(None, description="Size of exported data in bytes")
    export_checksum: Optional[str] = Field(None, description="Checksum of exported data")
    
    # Access control
    access_restrictions: List[str] = Field(default_factory=list, description="Access restrictions applied")
    retention_period_days: Optional[int] = Field(None, description="Data retention period in days")
    
    # Delivery information
    delivery_method: str = Field(..., description="How export was delivered")
    delivery_destination: Optional[str] = Field(None, description="Delivery destination")
    delivery_confirmed: bool = Field(False, description="Whether delivery was confirmed")
    
    @validator('export_type')
    def validate_export_type(cls, v):
        """Validate export type is from allowed set."""
        valid_types = ['FULL', 'PARTIAL', 'SUMMARY', 'EVIDENCE_ONLY', 'DECISIONS_ONLY']
        if v not in valid_types:
            raise ValueError(f'Export type must be one of: {valid_types}')
        return v
    
    @validator('export_format')
    def validate_export_format(cls, v):
        """Validate export format is supported."""
        valid_formats = ['JSON', 'PDF', 'CSV', 'XML', 'XLSX', 'HTML']
        if v not in valid_formats:
            raise ValueError(f'Export format must be one of: {valid_formats}')
        return v


class AuditAccessLog(BaseEntity):
    """
    Audit system access log record.
    
    Tracks all access to audit data and system functions
    for security monitoring and compliance.
    """
    
    access_id: str = Field(..., description="Unique access identifier")
    case_id: Optional[str] = Field(None, description="Associated case identifier if applicable")
    
    # Access details
    user_id: str = Field(..., description="User who accessed the system")
    user_role: str = Field(..., description="Role of the accessing user")
    access_type: str = Field(..., description="Type of access (READ, WRITE, EXPORT, DELETE)")
    resource_accessed: str = Field(..., description="Resource that was accessed")
    
    # Access context
    ip_address: Optional[str] = Field(None, description="IP address of the accessor")
    user_agent: Optional[str] = Field(None, description="User agent string")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # Access result
    access_granted: bool = Field(..., description="Whether access was granted")
    denial_reason: Optional[str] = Field(None, description="Reason for access denial")
    
    # Timing
    accessed_at: datetime = Field(default_factory=datetime.utcnow, description="Access timestamp")
    session_duration_minutes: Optional[int] = Field(None, description="Session duration in minutes")
    
    # Security flags
    suspicious_activity: bool = Field(False, description="Whether activity was flagged as suspicious")
    security_alerts: List[str] = Field(default_factory=list, description="Security alerts triggered")
    
    @validator('access_type')
    def validate_access_type(cls, v):
        """Validate access type is from allowed set."""
        valid_types = ['READ', 'WRITE', 'EXPORT', 'DELETE', 'SEARCH', 'ADMIN']
        if v not in valid_types:
            raise ValueError(f'Access type must be one of: {valid_types}')
        return v


class AuditTrail(BaseEntity):
    """
    Complete audit trail for LangGraph workflow execution.
    
    Contains node execution log, timestamps, and export logs
    as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    workflow_id: str = Field(..., description="LangGraph workflow execution identifier")
    
    # Node execution tracking
    node_execution_log: List[NodeExecution] = Field(default_factory=list, description="Complete node execution log")
    
    # Workflow timing
    workflow_started_at: datetime = Field(..., description="Workflow start timestamp")
    workflow_completed_at: Optional[datetime] = Field(None, description="Workflow completion timestamp")
    total_duration_ms: Optional[int] = Field(None, description="Total workflow duration in milliseconds")
    
    # Export tracking
    export_logs: List[ExportLog] = Field(default_factory=list, description="Export access logs")
    
    # Access tracking
    access_logs: List[AuditAccessLog] = Field(default_factory=list, description="Audit access logs")
    
    # Workflow metadata
    workflow_version: str = Field(..., description="LangGraph workflow version")
    state_schema_version: str = Field(..., description="State schema version")
    
    # Checkpoints and snapshots
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow state checkpoints")
    final_state: Optional[Dict[str, Any]] = Field(None, description="Final workflow state")
    
    # Quality metrics
    execution_quality_score: Optional[float] = Field(None, description="Execution quality assessment")
    completeness_score: float = Field(1.0, ge=0.0, le=1.0, description="Audit completeness score")
    
    # Compliance tracking
    compliance_flags: List[str] = Field(default_factory=list, description="Compliance flags raised")
    retention_until: datetime = Field(..., description="Data retention deadline")
    
    # Error tracking
    errors_encountered: List[str] = Field(default_factory=list, description="Errors encountered during workflow")
    warnings_generated: List[str] = Field(default_factory=list, description="Warnings generated during workflow")
    
    @validator('total_duration_ms')
    def calculate_total_duration(cls, v, values):
        """Calculate total duration if not provided."""
        if v is None and 'workflow_started_at' in values and 'workflow_completed_at' in values:
            started = values['workflow_started_at']
            completed = values['workflow_completed_at']
            if completed and started:
                duration = completed - started
                return int(duration.total_seconds() * 1000)
        return v
    
    @validator('retention_until')
    def validate_retention_period(cls, v, values):
        """Validate retention period is in the future."""
        if v <= datetime.utcnow():
            raise ValueError('Retention deadline must be in the future')
        return v
    
    def add_node_execution(self, execution: NodeExecution) -> None:
        """Add a node execution record to the audit trail."""
        self.node_execution_log.append(execution)
        
        # Update workflow completion if this is the last node
        if execution.status == 'SUCCESS' and execution.completed_at:
            self.workflow_completed_at = execution.completed_at
            self._calculate_total_duration()
        
        # Track errors
        if execution.status == 'FAILED' and execution.error_message:
            self.errors_encountered.append(f"{execution.node_name}: {execution.error_message}")
        
        self.updated_at = datetime.utcnow()
    
    def add_export_log(self, export_log: ExportLog) -> None:
        """Add an export log record."""
        self.export_logs.append(export_log)
        self.updated_at = datetime.utcnow()
    
    def add_access_log(self, access_log: AuditAccessLog) -> None:
        """Add an access log record."""
        self.access_logs.append(access_log)
        
        # Flag suspicious activity
        if access_log.suspicious_activity:
            self.compliance_flags.append(f"SUSPICIOUS_ACCESS_{access_log.access_id}")
        
        self.updated_at = datetime.utcnow()
    
    def add_checkpoint(self, checkpoint_name: str, state_data: Dict[str, Any]) -> None:
        """Add a workflow state checkpoint."""
        checkpoint = {
            'name': checkpoint_name,
            'timestamp': datetime.utcnow().isoformat(),
            'state': state_data
        }
        self.checkpoints.append(checkpoint)
        self.updated_at = datetime.utcnow()
    
    def mark_workflow_completed(self, final_state: Dict[str, Any]) -> None:
        """Mark the workflow as completed with final state."""
        self.workflow_completed_at = datetime.utcnow()
        self.final_state = final_state
        self._calculate_total_duration()
        self._calculate_completeness_score()
        self.updated_at = datetime.utcnow()
    
    def _calculate_total_duration(self) -> None:
        """Calculate total workflow duration."""
        if self.workflow_completed_at:
            duration = self.workflow_completed_at - self.workflow_started_at
            self.total_duration_ms = int(duration.total_seconds() * 1000)
    
    def _calculate_completeness_score(self) -> None:
        """Calculate audit completeness score."""
        # Base score
        score = 1.0
        
        # Deduct for missing data
        if not self.workflow_completed_at:
            score -= 0.2
        
        if not self.final_state:
            score -= 0.1
        
        if not self.node_execution_log:
            score -= 0.3
        
        # Deduct for errors
        error_penalty = min(0.2, len(self.errors_encountered) * 0.05)
        score -= error_penalty
        
        self.completeness_score = max(0.0, score)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of workflow execution."""
        successful_nodes = [n for n in self.node_execution_log if n.status == 'SUCCESS']
        failed_nodes = [n for n in self.node_execution_log if n.status == 'FAILED']
        
        return {
            'case_id': self.case_id,
            'workflow_id': self.workflow_id,
            'total_nodes': len(self.node_execution_log),
            'successful_nodes': len(successful_nodes),
            'failed_nodes': len(failed_nodes),
            'total_duration_ms': self.total_duration_ms,
            'errors_count': len(self.errors_encountered),
            'warnings_count': len(self.warnings_generated),
            'exports_count': len(self.export_logs),
            'access_logs_count': len(self.access_logs),
            'completeness_score': self.completeness_score,
            'compliance_flags': self.compliance_flags,
            'workflow_completed': self.workflow_completed_at is not None
        }
    
    def get_node_performance_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for each node type."""
        metrics = {}
        
        for execution in self.node_execution_log:
            node_name = execution.node_name
            if node_name not in metrics:
                metrics[node_name] = {
                    'executions': 0,
                    'total_duration_ms': 0,
                    'successes': 0,
                    'failures': 0,
                    'avg_duration_ms': 0
                }
            
            metrics[node_name]['executions'] += 1
            if execution.duration_ms:
                metrics[node_name]['total_duration_ms'] += execution.duration_ms
            
            if execution.status == 'SUCCESS':
                metrics[node_name]['successes'] += 1
            elif execution.status == 'FAILED':
                metrics[node_name]['failures'] += 1
        
        # Calculate averages
        for node_name, data in metrics.items():
            if data['executions'] > 0:
                data['avg_duration_ms'] = data['total_duration_ms'] / data['executions']
                data['success_rate'] = data['successes'] / data['executions']
        
        return metrics
    
    def is_compliant(self) -> bool:
        """Check if audit trail meets compliance requirements."""
        return (
            len(self.compliance_flags) == 0 and
            self.completeness_score >= 0.9 and
            self.workflow_completed_at is not None and
            len(self.errors_encountered) == 0
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "workflow_id": "WF-2024-001234-001",
                "workflow_version": "v1.0.0",
                "state_schema_version": "v1.0.0",
                "completeness_score": 1.0,
                "compliance_flags": [],
                "errors_encountered": [],
                "warnings_generated": [],
                "retention_until": "2031-01-15T00:00:00Z"
            }
        }
