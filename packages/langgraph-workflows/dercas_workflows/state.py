"""
DERCAS-ONCO-XAI LangGraph State Management

Base GraphState and state management utilities for LangGraph workflows.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class NodeStatus(str, Enum):
    """Individual node execution status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowContext(BaseModel):
    """Workflow execution context."""
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_type: str = Field(..., description="Type of workflow")
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    user_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: Set[str] = Field(default_factory=set)
    
    # Clinical context
    patient_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    
    # Execution context
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Environment
    environment: str = "development"
    debug_mode: bool = False
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            set: lambda v: list(v)
        }


class NodeExecution(BaseModel):
    """Individual node execution tracking."""
    node_name: str
    status: NodeStatus = NodeStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowResult(BaseModel):
    """Workflow execution result."""
    workflow_id: str
    status: WorkflowStatus
    result: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    nodes_executed: List[NodeExecution] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowError(Exception):
    """Workflow execution error."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "WORKFLOW_ERROR",
        node_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.node_name = node_name
        self.details = details or {}
        super().__init__(message)


class BaseGraphState(BaseModel):
    """Base state for all DERCAS LangGraph workflows."""
    
    # Identity and correlation
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    user_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: Set[str] = Field(default_factory=set)
    
    # Clinical context
    patient_id: Optional[UUID] = None
    case_id: Optional[UUID] = None
    
    # Workflow inputs
    image_id: Optional[UUID] = None
    image_uri: Optional[str] = None
    ehr_id: Optional[UUID] = None
    ehr_text: Optional[str] = None
    ehr_uri: Optional[str] = None
    ontology_versions: Dict[str, str] = Field(default_factory=dict)
    
    # Execution tracking
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: Optional[UUID] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_node: Optional[str] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    node_executions: List[NodeExecution] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # Workflow outputs
    result_bundle_id: Optional[UUID] = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    mappings: List[Dict[str, Any]] = Field(default_factory=list)
    graph_snapshot_id: Optional[UUID] = None
    report_id: Optional[UUID] = None
    xai_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Configuration and policies
    thresholds: Dict[str, float] = Field(default_factory=dict)
    hitl_policy: Dict[str, Any] = Field(default_factory=dict)
    guardrails_policy: Dict[str, Any] = Field(default_factory=dict)
    model_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Tool configurations
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    model_backend_config: Dict[str, Any] = Field(default_factory=dict)
    storage_config: Dict[str, Any] = Field(default_factory=dict)
    sparql_config: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            set: lambda v: list(v)
        }
    
    def add_error(self, error_code: str, message: str, node_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Add an error to the workflow state."""
        self.errors.append({
            "error_code": error_code,
            "message": message,
            "node_name": node_name,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        self.status = WorkflowStatus.FAILED
        self.updated_at = datetime.utcnow()
    
    def add_warning(self, warning_code: str, message: str, node_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a warning to the workflow state."""
        self.warnings.append({
            "warning_code": warning_code,
            "message": message,
            "node_name": node_name,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()
    
    def start_node(self, node_name: str, inputs: Optional[Dict[str, Any]] = None) -> None:
        """Mark a node as started."""
        # Find existing node execution or create new one
        node_exec = None
        for exec in self.node_executions:
            if exec.node_name == node_name:
                node_exec = exec
                break
        
        if not node_exec:
            node_exec = NodeExecution(node_name=node_name)
            self.node_executions.append(node_exec)
        
        node_exec.status = NodeStatus.RUNNING
        node_exec.started_at = datetime.utcnow()
        node_exec.inputs = inputs or {}
        
        self.current_node = node_name
        self.status = WorkflowStatus.RUNNING
        self.updated_at = datetime.utcnow()
    
    def complete_node(self, node_name: str, outputs: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mark a node as completed."""
        for exec in self.node_executions:
            if exec.node_name == node_name:
                exec.status = NodeStatus.COMPLETED
                exec.completed_at = datetime.utcnow()
                exec.outputs = outputs or {}
                exec.metadata = metadata or {}
                
                if exec.started_at:
                    exec.duration_seconds = (exec.completed_at - exec.started_at).total_seconds()
                
                break
        
        self.updated_at = datetime.utcnow()
    
    def fail_node(self, node_name: str, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark a node as failed."""
        for exec in self.node_executions:
            if exec.node_name == node_name:
                exec.status = NodeStatus.FAILED
                exec.completed_at = datetime.utcnow()
                exec.error_message = error_message
                exec.error_details = error_details or {}
                
                if exec.started_at:
                    exec.duration_seconds = (exec.completed_at - exec.started_at).total_seconds()
                
                break
        
        self.add_error("NODE_FAILED", error_message, node_name, error_details)
    
    def update_progress(self, progress: float) -> None:
        """Update workflow progress."""
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.utcnow()
    
    def complete_workflow(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.progress = 1.0
        self.current_node = None
        self.updated_at = datetime.utcnow()
        
        if result:
            # Update state with final results
            for key, value in result.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        completed_nodes = [exec for exec in self.node_executions if exec.status == NodeStatus.COMPLETED]
        failed_nodes = [exec for exec in self.node_executions if exec.status == NodeStatus.FAILED]
        
        total_duration = 0.0
        for exec in self.node_executions:
            if exec.duration_seconds:
                total_duration += exec.duration_seconds
        
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "progress": self.progress,
            "total_nodes": len(self.node_executions),
            "completed_nodes": len(completed_nodes),
            "failed_nodes": len(failed_nodes),
            "total_duration_seconds": total_duration,
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class StateManager:
    """State management utilities for workflows."""
    
    @staticmethod
    def create_workflow_state(
        workflow_type: str,
        correlation_id: str,
        context: Optional[WorkflowContext] = None,
        **kwargs
    ) -> BaseGraphState:
        """Create a new workflow state."""
        state = BaseGraphState(
            correlation_id=correlation_id,
            **kwargs
        )
        
        if context:
            state.user_id = context.user_id
            state.roles = context.roles
            state.permissions = context.permissions
            state.patient_id = context.patient_id
            state.case_id = context.case_id
        
        return state
    
    @staticmethod
    def update_workflow_state(state: BaseGraphState, updates: Dict[str, Any]) -> BaseGraphState:
        """Update workflow state with new values."""
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        state.updated_at = datetime.utcnow()
        return state
    
    @staticmethod
    def get_workflow_progress(state: BaseGraphState) -> Dict[str, Any]:
        """Get workflow progress information."""
        return {
            "workflow_id": state.workflow_id,
            "status": state.status,
            "progress": state.progress,
            "current_node": state.current_node,
            "nodes_completed": len([exec for exec in state.node_executions if exec.status == NodeStatus.COMPLETED]),
            "nodes_total": len(state.node_executions),
            "errors": state.errors,
            "warnings": state.warnings
        }
    
    @staticmethod
    def handle_workflow_error(
        state: BaseGraphState,
        error: Exception,
        node_name: Optional[str] = None
    ) -> BaseGraphState:
        """Handle workflow error and update state."""
        if isinstance(error, WorkflowError):
            state.add_error(error.error_code, error.message, node_name or error.node_name, error.details)
        else:
            state.add_error("UNEXPECTED_ERROR", str(error), node_name)
        
        if node_name:
            state.fail_node(node_name, str(error))
        
        return state


# Utility functions
def create_workflow_state(
    workflow_type: str,
    correlation_id: str,
    context: Optional[WorkflowContext] = None,
    **kwargs
) -> BaseGraphState:
    """Create a new workflow state."""
    return StateManager.create_workflow_state(workflow_type, correlation_id, context, **kwargs)


def update_workflow_state(state: BaseGraphState, updates: Dict[str, Any]) -> BaseGraphState:
    """Update workflow state with new values."""
    return StateManager.update_workflow_state(state, updates)


def get_workflow_progress(state: BaseGraphState) -> Dict[str, Any]:
    """Get workflow progress information."""
    return StateManager.get_workflow_progress(state)


def handle_workflow_error(
    state: BaseGraphState,
    error: Exception,
    node_name: Optional[str] = None
) -> BaseGraphState:
    """Handle workflow error and update state."""
    return StateManager.handle_workflow_error(state, error, node_name)


# Workflow-specific state classes
class ImageAnalysisState(BaseGraphState):
    """State for image analysis workflow."""
    
    # Image-specific inputs
    image_format: Optional[str] = None
    image_size_bytes: Optional[int] = None
    image_checksum: Optional[str] = None
    roi: Optional[Dict[str, Any]] = None
    tiling_params: Optional[Dict[str, Any]] = None
    
    # Model configuration
    pattern_model_profile: str = "lung_patterns_v3"
    mutation_model_profile: str = "genetic_mutations_v2"
    xai_model_profile: str = "explainability_v1"
    
    # Results
    pattern_results: List[Dict[str, Any]] = Field(default_factory=list)
    genetic_results: List[Dict[str, Any]] = Field(default_factory=list)
    overlay_uris: List[str] = Field(default_factory=list)
    heatmap_uris: List[str] = Field(default_factory=list)


class EHRAnalysisState(BaseGraphState):
    """State for EHR analysis workflow."""
    
    # EHR-specific inputs
    ehr_version: Optional[int] = None
    ehr_source: Optional[str] = None
    ehr_checksum: Optional[str] = None
    
    # Processing configuration
    extraction_method: str = "llm"
    mapping_method: str = "sparql_lookup"
    conflict_detection_enabled: bool = True
    
    # Results
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    ontology_mappings: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_packs: List[Dict[str, Any]] = Field(default_factory=list)


class GraphAssemblyState(BaseGraphState):
    """State for graph assembly workflow."""
    
    # Graph configuration
    include_inferred: bool = True
    max_depth: int = 3
    layout_algorithm: str = "force_directed"
    
    # Results
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    layout: Dict[str, Any] = Field(default_factory=dict)
    triplestore_graph_iri: Optional[str] = None


class OntologyUpdateState(BaseGraphState):
    """State for ontology update workflow."""
    
    # Update configuration
    targets: List[str] = Field(default_factory=list)  # NCIt, MONDO, SO
    mode: str = "offline"  # online, offline
    sources_policy_id: Optional[str] = None
    
    # Processing results
    fetched_ontologies: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    diff_reports: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    reasoner_reports: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    impact_analysis: Dict[str, Any] = Field(default_factory=dict)
    proposal_id: Optional[UUID] = None
    
    # Approval tracking
    requires_approval: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class ExplanationState(BaseGraphState):
    """State for explanation generation workflow."""
    
    # Input sources
    include_image_analysis: bool = True
    include_ehr_analysis: bool = True
    include_graph_analysis: bool = True
    
    # Generation configuration
    report_format: str = "html"  # html, pdf, json
    template: Optional[str] = None
    llm_model: Optional[str] = None
    
    # Evidence gathering
    evidence_sources: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts_found: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Guardrails validation
    guardrails_passed: bool = True
    guardrails_violations: List[str] = Field(default_factory=list)
    
    # Final report
    report_uri: Optional[str] = None
    report_hash: Optional[str] = None
