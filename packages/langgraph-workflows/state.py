"""
DERCAS-ONCO-XAI V1 - LangGraph State Management

Base GraphState and state management utilities for AI workflows.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union
from uuid import UUID

from pydantic import BaseModel, Field


class BaseGraphState(TypedDict):
    """Base state for all LangGraph workflows."""
    
    # Workflow identification
    workflow_id: str
    workflow_type: str
    workflow_version: str
    
    # Context
    correlation_id: Optional[str]
    case_id: Optional[str]
    user_id: Optional[str]
    
    # Timing
    started_at: datetime
    updated_at: datetime
    
    # Status tracking
    current_node: str
    completed_nodes: List[str]
    failed_nodes: List[str]
    
    # Error handling
    errors: List[Dict[str, Any]]
    retry_count: int
    max_retries: int
    
    # Metadata
    metadata: Dict[str, Any]


class ImageAnalysisState(BaseGraphState):
    """State for image analysis workflow."""
    
    # Input
    image_id: str
    image_path: Optional[str]
    image_metadata: Optional[Dict[str, Any]]
    
    # Processing parameters
    model_config: Dict[str, Any]
    confidence_thresholds: Dict[str, float]
    
    # Intermediate results
    loaded_image: Optional[Any]  # Image tensor/array
    preprocessing_results: Optional[Dict[str, Any]]
    
    # Pattern analysis results
    pattern_predictions: Optional[List[Dict[str, Any]]]
    pattern_confidences: Optional[Dict[str, float]]
    
    # Genetic analysis results
    genetic_predictions: Optional[List[Dict[str, Any]]]
    genetic_confidences: Optional[Dict[str, float]]
    
    # XAI artifacts
    attention_maps: Optional[List[str]]  # Paths to attention maps
    heatmaps: Optional[List[str]]  # Paths to heatmaps
    feature_importance: Optional[Dict[str, float]]
    
    # Final results
    result_bundle: Optional[Dict[str, Any]]
    requires_review: bool
    review_reasons: List[str]
    
    # Quality metrics
    quality_scores: Optional[Dict[str, float]]
    confidence_assessment: Optional[str]


class EHRProcessingState(BaseGraphState):
    """State for EHR processing workflow."""
    
    # Input
    ehr_id: str
    document_content: str
    document_type: str
    document_metadata: Optional[Dict[str, Any]]
    
    # Processing configuration
    extraction_config: Dict[str, Any]
    ontology_config: Dict[str, Any]
    
    # Normalization results
    normalized_content: Optional[str]
    normalization_metadata: Optional[Dict[str, Any]]
    
    # Entity extraction results
    extracted_entities: Optional[List[Dict[str, Any]]]
    entity_confidences: Optional[Dict[str, float]]
    extraction_metadata: Optional[Dict[str, Any]]
    
    # Ontology mapping
    ontology_candidates: Optional[Dict[str, List[Dict[str, Any]]]]
    selected_mappings: Optional[List[Dict[str, Any]]]
    mapping_confidences: Optional[Dict[str, float]]
    
    # Evidence and validation
    evidence_pack: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    
    # Final results
    processed_entities: Optional[List[Dict[str, Any]]]
    ontology_mappings: Optional[List[Dict[str, Any]]]
    processing_summary: Optional[Dict[str, Any]]


class GraphAssemblyState(BaseGraphState):
    """State for graph assembly workflow."""
    
    # Input
    case_id: str
    source_components: List[str]  # List of data sources to include
    
    # Configuration
    graph_config: Dict[str, Any]
    layout_config: Dict[str, Any]
    
    # Data gathering
    case_findings: Optional[Dict[str, Any]]
    image_results: Optional[List[Dict[str, Any]]]
    ehr_entities: Optional[List[Dict[str, Any]]]
    ontology_mappings: Optional[List[Dict[str, Any]]]
    
    # Graph construction
    nodes: Optional[List[Dict[str, Any]]]
    edges: Optional[List[Dict[str, Any]]]
    subgraph_data: Optional[Dict[str, Any]]
    
    # Provenance and annotation
    provenance_data: Optional[Dict[str, Any]]
    annotations: Optional[Dict[str, Any]]
    
    # Layout and visualization
    layout_data: Optional[Dict[str, Any]]
    visualization_config: Optional[Dict[str, Any]]
    
    # Final results
    graph_snapshot: Optional[Dict[str, Any]]
    snapshot_metadata: Optional[Dict[str, Any]]


class ExplanationState(BaseGraphState):
    """State for explanation generation workflow."""
    
    # Input
    case_id: str
    explanation_type: str
    target_audience: str  # clinician, patient, researcher
    
    # Configuration
    explanation_config: Dict[str, Any]
    guardrails_config: Dict[str, Any]
    
    # Evidence gathering
    image_evidence: Optional[List[Dict[str, Any]]]
    ehr_evidence: Optional[List[Dict[str, Any]]]
    graph_evidence: Optional[Dict[str, Any]]
    literature_evidence: Optional[List[Dict[str, Any]]]
    
    # Conflict detection
    conflicts: Optional[List[Dict[str, Any]]]
    conflict_resolution: Optional[Dict[str, Any]]
    
    # Explanation drafting
    draft_sections: Optional[Dict[str, str]]
    draft_metadata: Optional[Dict[str, Any]]
    
    # Validation and guardrails
    guardrail_checks: Optional[Dict[str, bool]]
    compliance_issues: Optional[List[str]]
    
    # Final report
    explanation_report: Optional[Dict[str, Any]]
    report_metadata: Optional[Dict[str, Any]]
    
    # Quality assessment
    explanation_quality: Optional[Dict[str, float]]
    clinical_review_required: bool


class OntologyUpdateState(BaseGraphState):
    """State for ontology update workflow."""
    
    # Input
    ontology_name: str
    update_source: str  # manual, automated, scheduled
    update_config: Dict[str, Any]
    
    # Source discovery
    available_sources: Optional[List[Dict[str, Any]]]
    selected_sources: Optional[List[str]]
    
    # Ontology fetching
    current_ontology: Optional[Dict[str, Any]]
    new_ontology: Optional[Dict[str, Any]]
    fetch_metadata: Optional[Dict[str, Any]]
    
    # Validation and parsing
    validation_results: Optional[Dict[str, Any]]
    parsing_results: Optional[Dict[str, Any]]
    integrity_check: Optional[Dict[str, bool]]
    
    # Diff computation
    ontology_diff: Optional[Dict[str, Any]]
    change_summary: Optional[Dict[str, Any]]
    
    # LLM mapping suggestions
    llm_suggestions: Optional[List[Dict[str, Any]]]
    suggestion_confidences: Optional[Dict[str, float]]
    
    # Reasoner validation
    reasoner_results: Optional[Dict[str, Any]]
    consistency_check: Optional[Dict[str, bool]]
    
    # Impact analysis
    impact_assessment: Optional[Dict[str, Any]]
    affected_mappings: Optional[List[str]]
    risk_assessment: Optional[Dict[str, str]]
    
    # Proposal creation
    update_proposal: Optional[Dict[str, Any]]
    proposal_metadata: Optional[Dict[str, Any]]
    
    # Human approval
    approval_status: Optional[str]
    approval_metadata: Optional[Dict[str, Any]]
    
    # Publication/rollback
    publication_results: Optional[Dict[str, Any]]
    rollback_plan: Optional[Dict[str, Any]]


# State management utilities
class StateManager:
    """Utility class for managing workflow state."""
    
    @staticmethod
    def create_base_state(
        workflow_type: str,
        workflow_version: str = "1.0",
        correlation_id: Optional[str] = None,
        case_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> BaseGraphState:
        """Create base state for a workflow."""
        now = datetime.utcnow()
        
        return BaseGraphState(
            workflow_id=f"{workflow_type}_{now.strftime('%Y%m%d_%H%M%S')}",
            workflow_type=workflow_type,
            workflow_version=workflow_version,
            correlation_id=correlation_id,
            case_id=case_id,
            user_id=user_id,
            started_at=now,
            updated_at=now,
            current_node="start",
            completed_nodes=[],
            failed_nodes=[],
            errors=[],
            retry_count=0,
            max_retries=max_retries,
            metadata={}
        )
    
    @staticmethod
    def update_state(
        state: BaseGraphState,
        current_node: str,
        completed_node: Optional[str] = None,
        error: Optional[Dict[str, Any]] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> BaseGraphState:
        """Update workflow state."""
        state["current_node"] = current_node
        state["updated_at"] = datetime.utcnow()
        
        if completed_node and completed_node not in state["completed_nodes"]:
            state["completed_nodes"].append(completed_node)
        
        if error:
            state["errors"].append(error)
            if current_node not in state["failed_nodes"]:
                state["failed_nodes"].append(current_node)
        
        if metadata_update:
            state["metadata"].update(metadata_update)
        
        return state
    
    @staticmethod
    def should_retry(state: BaseGraphState) -> bool:
        """Check if workflow should retry on failure."""
        return state["retry_count"] < state["max_retries"]
    
    @staticmethod
    def increment_retry(state: BaseGraphState) -> BaseGraphState:
        """Increment retry count."""
        state["retry_count"] += 1
        state["updated_at"] = datetime.utcnow()
        return state
    
    @staticmethod
    def is_completed(state: BaseGraphState, required_nodes: List[str]) -> bool:
        """Check if workflow is completed."""
        return all(node in state["completed_nodes"] for node in required_nodes)
    
    @staticmethod
    def has_failed(state: BaseGraphState) -> bool:
        """Check if workflow has failed."""
        return len(state["failed_nodes"]) > 0 and not StateManager.should_retry(state)
    
    @staticmethod
    def get_execution_time(state: BaseGraphState) -> float:
        """Get workflow execution time in seconds."""
        return (state["updated_at"] - state["started_at"]).total_seconds()


# State validation utilities
class StateValidator:
    """Utility class for validating workflow state."""
    
    @staticmethod
    def validate_image_analysis_state(state: ImageAnalysisState) -> List[str]:
        """Validate image analysis state."""
        errors = []
        
        if not state.get("image_id"):
            errors.append("image_id is required")
        
        if state.get("current_node") == "load_image" and not state.get("image_path"):
            errors.append("image_path is required for load_image node")
        
        if state.get("current_node") == "run_pattern_model" and not state.get("loaded_image"):
            errors.append("loaded_image is required for run_pattern_model node")
        
        return errors
    
    @staticmethod
    def validate_ehr_processing_state(state: EHRProcessingState) -> List[str]:
        """Validate EHR processing state."""
        errors = []
        
        if not state.get("ehr_id"):
            errors.append("ehr_id is required")
        
        if not state.get("document_content"):
            errors.append("document_content is required")
        
        if state.get("current_node") == "extract_entities" and not state.get("normalized_content"):
            errors.append("normalized_content is required for extract_entities node")
        
        return errors
    
    @staticmethod
    def validate_graph_assembly_state(state: GraphAssemblyState) -> List[str]:
        """Validate graph assembly state."""
        errors = []
        
        if not state.get("case_id"):
            errors.append("case_id is required")
        
        if not state.get("source_components"):
            errors.append("source_components is required")
        
        return errors


# State persistence utilities
class StatePersistence:
    """Utility class for persisting workflow state."""
    
    @staticmethod
    def serialize_state(state: BaseGraphState) -> Dict[str, Any]:
        """Serialize state for persistence."""
        serialized = dict(state)
        
        # Convert datetime objects to ISO strings
        if isinstance(serialized.get("started_at"), datetime):
            serialized["started_at"] = serialized["started_at"].isoformat()
        
        if isinstance(serialized.get("updated_at"), datetime):
            serialized["updated_at"] = serialized["updated_at"].isoformat()
        
        return serialized
    
    @staticmethod
    def deserialize_state(data: Dict[str, Any], state_type: type) -> BaseGraphState:
        """Deserialize state from persistence."""
        # Convert ISO strings back to datetime objects
        if isinstance(data.get("started_at"), str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        return state_type(**data)


# Context managers for state management
class WorkflowContext:
    """Context manager for workflow execution."""
    
    def __init__(self, state: BaseGraphState, node_name: str):
        self.state = state
        self.node_name = node_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.state = StateManager.update_state(
            self.state,
            current_node=self.node_name
        )
        return self.state
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type is None:
            # Success
            self.state = StateManager.update_state(
                self.state,
                current_node=f"{self.node_name}_completed",
                completed_node=self.node_name,
                metadata_update={
                    f"{self.node_name}_execution_time": execution_time
                }
            )
        else:
            # Error
            error_info = {
                "node": self.node_name,
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time": execution_time
            }
            
            self.state = StateManager.update_state(
                self.state,
                current_node=f"{self.node_name}_failed",
                error=error_info
            )
        
        return False  # Don't suppress exceptions
