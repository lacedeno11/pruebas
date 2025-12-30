# DERCAS-ONCO-XAI V1 - LangGraph State Management
# Base GraphState and context classes for workflows

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid7


class IdentityContext(BaseModel):
    """Identity and authentication context for workflows."""
    
    correlation_id: str = Field(default_factory=lambda: str(uuid7.uuid7()), description="Request correlation ID")
    user_id: Optional[str] = Field(None, description="User executing the workflow")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: Optional[str] = Field(None, description="User session ID")
    
    class Config:
        frozen = True


class ClinicalContext(BaseModel):
    """Clinical context for workflows."""
    
    patient_id: Optional[str] = Field(None, description="Associated patient ID")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    encounter_id: Optional[str] = Field(None, description="Associated encounter ID")
    clinical_unit: Optional[str] = Field(None, description="Clinical unit/department")
    
    class Config:
        frozen = True


class InputContext(BaseModel):
    """Input context for workflows."""
    
    image_id: Optional[str] = Field(None, description="Input image ID")
    image_uri: Optional[str] = Field(None, description="Input image URI")
    ehr_id: Optional[str] = Field(None, description="Input EHR document ID")
    ehr_uri: Optional[str] = Field(None, description="Input EHR document URI")
    ehr_text: Optional[str] = Field(None, description="Input EHR text content")
    ontology_versions: Dict[str, str] = Field(default_factory=dict, description="Active ontology versions")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")
    
    class Config:
        frozen = True


class ExecutionContext(BaseModel):
    """Execution context for workflows."""
    
    job_id: Optional[str] = Field(None, description="Associated job ID")
    workflow_id: str = Field(default_factory=lambda: str(uuid7.uuid7()), description="Workflow execution ID")
    status: str = Field("PENDING", description="Workflow status")
    progress: float = Field(0.0, description="Workflow progress (0.0-1.0)")
    current_node: Optional[str] = Field(None, description="Current workflow node")
    started_at: Optional[datetime] = Field(None, description="Workflow start time")
    ended_at: Optional[datetime] = Field(None, description="Workflow end time")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow errors")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics")
    retry_count: int = Field(0, description="Number of retries")
    
    def add_error(self, error_code: str, error_message: str, node: Optional[str] = None) -> None:
        """Add an error to the execution context."""
        error = {
            "error_code": error_code,
            "error_message": error_message,
            "node": node or self.current_node,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.errors.append(error)
    
    def update_progress(self, progress: float, node: Optional[str] = None) -> None:
        """Update workflow progress."""
        self.progress = max(0.0, min(1.0, progress))
        if node:
            self.current_node = node
    
    def start_execution(self) -> None:
        """Mark workflow as started."""
        self.status = "RUNNING"
        self.started_at = datetime.utcnow()
    
    def complete_execution(self) -> None:
        """Mark workflow as completed."""
        self.status = "COMPLETED"
        self.ended_at = datetime.utcnow()
        self.progress = 1.0
    
    def fail_execution(self, error_code: str, error_message: str) -> None:
        """Mark workflow as failed."""
        self.status = "FAILED"
        self.ended_at = datetime.utcnow()
        self.add_error(error_code, error_message)


class OutputContext(BaseModel):
    """Output context for workflows."""
    
    result_bundle_id: Optional[str] = Field(None, description="Generated result bundle ID")
    pattern_outputs: List[Dict[str, Any]] = Field(default_factory=list, description="Pattern analysis outputs")
    genetic_outputs: List[Dict[str, Any]] = Field(default_factory=list, description="Genetic analysis outputs")
    xai_artifacts: List[str] = Field(default_factory=list, description="XAI artifact IDs")
    ehr_entities: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted EHR entities")
    ehr_mappings: List[Dict[str, Any]] = Field(default_factory=list, description="EHR ontology mappings")
    graph_snapshot_id: Optional[str] = Field(None, description="Generated graph snapshot ID")
    explanation_report_id: Optional[str] = Field(None, description="Generated explanation report ID")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="Generated artifacts (name -> URI)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Output metadata")
    
    def add_artifact(self, name: str, uri: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an artifact to the output context."""
        self.artifacts[name] = uri
        if metadata:
            self.metadata[f"{name}_metadata"] = metadata
    
    def add_pattern_result(self, pattern: str, score: float, **kwargs) -> None:
        """Add a pattern analysis result."""
        result = {
            "pattern": pattern,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.pattern_outputs.append(result)
    
    def add_genetic_result(self, mutation: str, score: float, status: str, **kwargs) -> None:
        """Add a genetic analysis result."""
        result = {
            "mutation": mutation,
            "score": score,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.genetic_outputs.append(result)
    
    def add_ehr_entity(self, text: str, entity_type: str, confidence: float, **kwargs) -> None:
        """Add an extracted EHR entity."""
        entity = {
            "text": text,
            "type": entity_type,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.ehr_entities.append(entity)
    
    def add_ehr_mapping(self, entity_text: str, ontology: str, iri: str, confidence: float, **kwargs) -> None:
        """Add an EHR ontology mapping."""
        mapping = {
            "entity_text": entity_text,
            "ontology": ontology,
            "iri": iri,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.ehr_mappings.append(mapping)


class PolicyContext(BaseModel):
    """Policy and guardrails context for workflows."""
    
    thresholds: Dict[str, float] = Field(default_factory=dict, description="Confidence thresholds")
    hitl_policy: Dict[str, Any] = Field(default_factory=dict, description="Human-in-the-loop policies")
    guardrails_policy: Dict[str, Any] = Field(default_factory=dict, description="Clinical guardrails policies")
    model_versions: Dict[str, str] = Field(default_factory=dict, description="Model versions to use")
    timeout_seconds: int = Field(300, description="Workflow timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    enable_clinical_guardrails: bool = Field(True, description="Whether to enforce clinical guardrails")
    require_disclaimers: bool = Field(True, description="Whether to require disclaimers")
    prevent_definitive_diagnosis: bool = Field(True, description="Whether to prevent definitive diagnosis")
    
    def get_threshold(self, key: str, default: float = 0.5) -> float:
        """Get threshold value with default."""
        return self.thresholds.get(key, default)
    
    def should_trigger_hitl(self, scores: Dict[str, float]) -> bool:
        """Check if human-in-the-loop should be triggered."""
        if not self.hitl_policy:
            return False
        
        # Check if any score is below threshold
        for key, score in scores.items():
            threshold = self.get_threshold(key)
            if score < threshold:
                return True
        
        return False
    
    def validate_guardrails(self, content: str) -> List[str]:
        """Validate content against clinical guardrails."""
        violations = []
        
        if not self.enable_clinical_guardrails:
            return violations
        
        # Check for definitive diagnosis language
        if self.prevent_definitive_diagnosis:
            definitive_patterns = [
                r'\bdiagnosis\s+is\b',
                r'\bpatient\s+has\b',
                r'\bconfirmed\s+diagnosis\b',
                r'\bdefinitive\s+diagnosis\b',
                r'\bcertain\s+that\b',
                r'\bwithout\s+doubt\b'
            ]
            
            import re
            for pattern in definitive_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"Definitive diagnosis language detected: {pattern}")
        
        # Check for required disclaimers
        if self.require_disclaimers:
            disclaimer_patterns = [
                r'\blimitations\b',
                r'\bfor\s+research\s+use\s+only\b',
                r'\bnot\s+for\s+diagnostic\s+use\b',
                r'\bassistive\s+tool\b'
            ]
            
            has_disclaimer = any(
                re.search(pattern, content, re.IGNORECASE)
                for pattern in disclaimer_patterns
            )
            
            if not has_disclaimer:
                violations.append("Required disclaimer not found")
        
        return violations


class BaseGraphState(BaseModel):
    """
    Base state class for all LangGraph workflows in the oncology platform.
    
    This state provides a consistent structure across all workflows with:
    - Identity and authentication context
    - Clinical context (patient, case, etc.)
    - Input context (images, EHR, etc.)
    - Execution context (job tracking, progress, errors)
    - Output context (results, artifacts)
    - Policy context (thresholds, guardrails)
    """
    
    # Core contexts
    identity: IdentityContext = Field(default_factory=IdentityContext, description="Identity context")
    clinical: ClinicalContext = Field(default_factory=ClinicalContext, description="Clinical context")
    inputs: InputContext = Field(default_factory=InputContext, description="Input context")
    execution: ExecutionContext = Field(default_factory=ExecutionContext, description="Execution context")
    outputs: OutputContext = Field(default_factory=OutputContext, description="Output context")
    policies: PolicyContext = Field(default_factory=PolicyContext, description="Policy context")
    
    # Workflow-specific data
    workflow_data: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific data")
    
    class Config:
        arbitrary_types_allowed = True
    
    def get_correlation_id(self) -> str:
        """Get correlation ID for tracing."""
        return self.identity.correlation_id
    
    def get_case_id(self) -> Optional[str]:
        """Get case ID if available."""
        return self.clinical.case_id
    
    def get_user_id(self) -> Optional[str]:
        """Get user ID if available."""
        return self.identity.user_id
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.identity.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.identity.permissions
    
    def start_workflow(self, node: Optional[str] = None) -> None:
        """Start workflow execution."""
        self.execution.start_execution()
        if node:
            self.execution.current_node = node
    
    def complete_workflow(self) -> None:
        """Complete workflow execution."""
        self.execution.complete_execution()
    
    def fail_workflow(self, error_code: str, error_message: str) -> None:
        """Fail workflow execution."""
        self.execution.fail_execution(error_code, error_message)
    
    def update_progress(self, progress: float, node: Optional[str] = None) -> None:
        """Update workflow progress."""
        self.execution.update_progress(progress, node)
    
    def add_error(self, error_code: str, error_message: str, node: Optional[str] = None) -> None:
        """Add an error to the workflow."""
        self.execution.add_error(error_code, error_message, node)
    
    def should_trigger_hitl(self, scores: Dict[str, float]) -> bool:
        """Check if human-in-the-loop should be triggered."""
        return self.policies.should_trigger_hitl(scores)
    
    def validate_guardrails(self, content: str) -> List[str]:
        """Validate content against clinical guardrails."""
        return self.policies.validate_guardrails(content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseGraphState":
        """Create state from dictionary."""
        return cls(**data)
    
    def copy_with_updates(self, **updates) -> "BaseGraphState":
        """Create a copy of the state with updates."""
        data = self.dict()
        data.update(updates)
        return self.__class__(**data)


# Specialized state classes for specific workflows

class ImageAnalysisState(BaseGraphState):
    """State for image analysis workflows."""
    
    # Image-specific data
    image_metadata: Dict[str, Any] = Field(default_factory=dict, description="Image metadata")
    preprocessing_results: Dict[str, Any] = Field(default_factory=dict, description="Preprocessing results")
    model_results: Dict[str, Any] = Field(default_factory=dict, description="Model inference results")
    xai_results: Dict[str, Any] = Field(default_factory=dict, description="XAI generation results")
    
    def set_image_metadata(self, width: int, height: int, format: str, **kwargs) -> None:
        """Set image metadata."""
        self.image_metadata.update({
            "width": width,
            "height": height,
            "format": format,
            **kwargs
        })
    
    def add_model_result(self, model_name: str, results: Dict[str, Any]) -> None:
        """Add model inference results."""
        self.model_results[model_name] = results


class EHRAnalysisState(BaseGraphState):
    """State for EHR analysis workflows."""
    
    # EHR-specific data
    ehr_metadata: Dict[str, Any] = Field(default_factory=dict, description="EHR metadata")
    normalization_results: Dict[str, Any] = Field(default_factory=dict, description="Text normalization results")
    extraction_results: Dict[str, Any] = Field(default_factory=dict, description="Entity extraction results")
    mapping_results: Dict[str, Any] = Field(default_factory=dict, description="Ontology mapping results")
    conflict_analysis: Dict[str, Any] = Field(default_factory=dict, description="Conflict analysis results")
    
    def set_ehr_metadata(self, length: int, source: str, version: int, **kwargs) -> None:
        """Set EHR metadata."""
        self.ehr_metadata.update({
            "length": length,
            "source": source,
            "version": version,
            **kwargs
        })
    
    def add_extraction_result(self, extractor_name: str, entities: List[Dict[str, Any]]) -> None:
        """Add entity extraction results."""
        self.extraction_results[extractor_name] = entities
    
    def add_mapping_result(self, ontology: str, mappings: List[Dict[str, Any]]) -> None:
        """Add ontology mapping results."""
        self.mapping_results[ontology] = mappings


class GraphAssemblyState(BaseGraphState):
    """State for graph assembly workflows."""
    
    # Graph-specific data
    graph_metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph metadata")
    findings_data: Dict[str, Any] = Field(default_factory=dict, description="Case findings data")
    subgraph_data: Dict[str, Any] = Field(default_factory=dict, description="Subgraph data")
    layout_data: Dict[str, Any] = Field(default_factory=dict, description="Graph layout data")
    provenance_data: Dict[str, Any] = Field(default_factory=dict, description="Provenance data")
    
    def set_graph_metadata(self, node_count: int, edge_count: int, **kwargs) -> None:
        """Set graph metadata."""
        self.graph_metadata.update({
            "node_count": node_count,
            "edge_count": edge_count,
            **kwargs
        })
    
    def add_findings(self, source: str, findings: List[Dict[str, Any]]) -> None:
        """Add case findings from a source."""
        self.findings_data[source] = findings
    
    def set_layout(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
        """Set graph layout data."""
        self.layout_data = {
            "nodes": nodes,
            "edges": edges,
            "timestamp": datetime.utcnow().isoformat()
        }
