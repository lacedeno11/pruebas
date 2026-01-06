# DERCAS-ONCO-XAI V1 - LangGraph Utilities
# Common utility functions for workflows

import uuid
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid7

from .state import BaseGraphState, IdentityContext, ClinicalContext, InputContext, ExecutionContext, OutputContext, PolicyContext

logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """Generate a new correlation ID using UUID7 for time-ordering."""
    return str(uuid7.uuid7())


def generate_workflow_id() -> str:
    """Generate a new workflow execution ID."""
    return str(uuid7.uuid7())


def generate_job_id() -> str:
    """Generate a new job ID."""
    return str(uuid7.uuid7())


def create_job_context(
    user_id: Optional[str] = None,
    case_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None
) -> BaseGraphState:
    """
    Create a basic job context for workflow execution.
    
    Args:
        user_id: User executing the workflow
        case_id: Associated case ID
        patient_id: Associated patient ID
        correlation_id: Request correlation ID
        roles: User roles
        permissions: User permissions
    
    Returns:
        BaseGraphState with populated context
    """
    identity = IdentityContext(
        correlation_id=correlation_id or generate_correlation_id(),
        user_id=user_id,
        roles=roles or [],
        permissions=permissions or []
    )
    
    clinical = ClinicalContext(
        patient_id=patient_id,
        case_id=case_id
    )
    
    inputs = InputContext()
    execution = ExecutionContext()
    outputs = OutputContext()
    policies = PolicyContext()
    
    return BaseGraphState(
        identity=identity,
        clinical=clinical,
        inputs=inputs,
        execution=execution,
        outputs=outputs,
        policies=policies
    )


def validate_clinical_guardrails(content: str, strict: bool = True) -> List[str]:
    """
    Validate content against clinical guardrails.
    
    Args:
        content: Content to validate
        strict: Whether to use strict validation rules
    
    Returns:
        List of guardrail violations
    """
    violations = []
    
    # Definitive diagnosis patterns (prohibited)
    definitive_patterns = [
        r'\bdiagnosis\s+is\b',
        r'\bpatient\s+has\b',
        r'\bconfirmed\s+diagnosis\b',
        r'\bdefinitive\s+diagnosis\b',
        r'\bcertain\s+that\b',
        r'\bwithout\s+doubt\b',
        r'\bpositively\s+diagnosed\b',
        r'\bwe\s+can\s+conclude\b',
        r'\bit\s+is\s+certain\b',
        r'\bundoubtedly\b',
        r'\bguaranteed\s+to\s+be\b'
    ]
    
    for pattern in definitive_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            violations.append(f"Definitive diagnosis language detected: {pattern}")
    
    # Required disclaimer patterns
    disclaimer_patterns = [
        r'\blimitations\b',
        r'\bfor\s+research\s+use\s+only\b',
        r'\bnot\s+for\s+diagnostic\s+use\b',
        r'\bassistive\s+tool\b',
        r'\bshould\s+be\s+validated\b',
        r'\bqualified\s+medical\s+professional\b',
        r'\bresearch\s+purposes\b',
        r'\bnot\s+a\s+substitute\b'
    ]
    
    has_disclaimer = any(
        re.search(pattern, content, re.IGNORECASE)
        for pattern in disclaimer_patterns
    )
    
    if not has_disclaimer:
        violations.append("Required clinical disclaimer not found")
    
    # Required uncertainty language
    uncertainty_patterns = [
        r'\bsuggests?\b',
        r'\bindicates?\b',
        r'\bmay\s+be\b',
        r'\bcould\s+be\b',
        r'\bpossible\b',
        r'\blikely\b',
        r'\bprobable\b',
        r'\bappears?\s+to\s+be\b',
        r'\bconsistent\s+with\b',
        r'\bcompatible\s+with\b'
    ]
    
    has_uncertainty = any(
        re.search(pattern, content, re.IGNORECASE)
        for pattern in uncertainty_patterns
    )
    
    if strict and not has_uncertainty:
        violations.append("Content lacks appropriate uncertainty language")
    
    # Prohibited absolute statements
    absolute_patterns = [
        r'\balways\b',
        r'\bnever\b',
        r'\b100%\b',
        r'\bcompletely\s+certain\b',
        r'\babsolutely\b',
        r'\bguaranteed\b'
    ]
    
    for pattern in absolute_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            violations.append(f"Absolute statement detected: {pattern}")
    
    return violations


def format_workflow_error(
    error_code: str,
    error_message: str,
    node: Optional[str] = None,
    correlation_id: Optional[str] = None,
    additional_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a workflow error for consistent error handling.
    
    Args:
        error_code: Error code
        error_message: Error message
        node: Workflow node where error occurred
        correlation_id: Request correlation ID
        additional_details: Additional error details
    
    Returns:
        Formatted error dictionary
    """
    error = {
        "error_code": error_code,
        "error_message": error_message,
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": correlation_id,
        "node": node,
        "details": additional_details or {}
    }
    
    return error


def calculate_workflow_progress(
    current_node: str,
    total_nodes: List[str],
    node_weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate workflow progress based on current node.
    
    Args:
        current_node: Current workflow node
        total_nodes: List of all workflow nodes
        node_weights: Optional weights for nodes (default: equal weight)
    
    Returns:
        Progress as float between 0.0 and 1.0
    """
    if not total_nodes:
        return 0.0
    
    try:
        current_index = total_nodes.index(current_node)
    except ValueError:
        return 0.0
    
    if node_weights:
        # Calculate weighted progress
        total_weight = sum(node_weights.get(node, 1.0) for node in total_nodes)
        completed_weight = sum(
            node_weights.get(node, 1.0) 
            for node in total_nodes[:current_index + 1]
        )
        return completed_weight / total_weight
    else:
        # Calculate simple progress
        return (current_index + 1) / len(total_nodes)


def extract_confidence_scores(results: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract confidence scores from workflow results.
    
    Args:
        results: Workflow results dictionary
    
    Returns:
        Dictionary of confidence scores
    """
    scores = {}
    
    # Extract pattern scores
    if "patterns" in results:
        for pattern in results["patterns"]:
            if "pattern" in pattern and "score" in pattern:
                scores[pattern["pattern"]] = pattern["score"]
    
    # Extract mutation scores
    if "mutations" in results:
        for mutation in results["mutations"]:
            if "mutation" in mutation and "score" in mutation:
                scores[mutation["mutation"]] = mutation["score"]
    
    # Extract entity scores
    if "entities" in results:
        for entity in results["entities"]:
            if "type" in entity and "confidence" in entity:
                scores[f"entity_{entity['type']}"] = entity["confidence"]
    
    # Extract mapping scores
    if "mappings" in results:
        for mapping in results["mappings"]:
            if "ontology" in mapping and "confidence" in mapping:
                scores[f"mapping_{mapping['ontology']}"] = mapping["confidence"]
    
    return scores


def should_trigger_hitl(
    scores: Dict[str, float],
    thresholds: Dict[str, float],
    require_all: bool = False
) -> bool:
    """
    Determine if human-in-the-loop should be triggered based on scores.
    
    Args:
        scores: Confidence scores
        thresholds: Threshold values
        require_all: If True, all scores must be below threshold
    
    Returns:
        True if HITL should be triggered
    """
    if not scores or not thresholds:
        return False
    
    below_threshold = []
    
    for key, score in scores.items():
        threshold = thresholds.get(key, 0.5)  # Default threshold
        if score < threshold:
            below_threshold.append(key)
    
    if require_all:
        # All scores must be below threshold
        return len(below_threshold) == len(scores)
    else:
        # Any score below threshold triggers HITL
        return len(below_threshold) > 0


def create_clinical_disclaimer(
    model_versions: Optional[Dict[str, str]] = None,
    ontology_versions: Optional[Dict[str, str]] = None,
    processing_time: Optional[float] = None,
    confidence_scores: Optional[Dict[str, float]] = None
) -> str:
    """
    Create a standard clinical disclaimer for AI-generated content.
    
    Args:
        model_versions: Model versions used
        ontology_versions: Ontology versions used
        processing_time: Processing time in seconds
        confidence_scores: Confidence scores
    
    Returns:
        Formatted clinical disclaimer
    """
    disclaimer_parts = [
        "## Clinical Disclaimer",
        "",
        "**IMPORTANT: This analysis is for research and educational purposes only.**",
        "",
        "### Limitations",
        "- This is an assistive AI tool and should not be used for definitive diagnosis",
        "- Results should be validated by qualified medical professionals",
        "- AI predictions may contain errors or biases",
        "- Clinical context and patient history must be considered",
        "",
        "### Technical Details"
    ]
    
    if model_versions:
        disclaimer_parts.append("**Model Versions:**")
        for model, version in model_versions.items():
            disclaimer_parts.append(f"- {model}: {version}")
        disclaimer_parts.append("")
    
    if ontology_versions:
        disclaimer_parts.append("**Ontology Versions:**")
        for ontology, version in ontology_versions.items():
            disclaimer_parts.append(f"- {ontology}: {version}")
        disclaimer_parts.append("")
    
    if confidence_scores:
        disclaimer_parts.append("**Confidence Scores:**")
        for item, score in confidence_scores.items():
            disclaimer_parts.append(f"- {item}: {score:.3f}")
        disclaimer_parts.append("")
    
    if processing_time:
        disclaimer_parts.append(f"**Processing Time:** {processing_time:.2f} seconds")
        disclaimer_parts.append("")
    
    disclaimer_parts.extend([
        "### Usage Guidelines",
        "- Use as a supplementary tool in clinical decision-making",
        "- Always verify findings with additional diagnostic methods",
        "- Consider patient-specific factors not captured in the analysis",
        "- Consult with specialists for complex cases",
        "",
        f"*Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
    ])
    
    return "\n".join(disclaimer_parts)


def validate_workflow_state(state: BaseGraphState) -> List[str]:
    """
    Validate workflow state for completeness and consistency.
    
    Args:
        state: Workflow state to validate
    
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check required identity fields
    if not state.identity.correlation_id:
        errors.append("Missing correlation ID in identity context")
    
    # Check execution context
    if state.execution.status not in ["PENDING", "RUNNING", "COMPLETED", "FAILED"]:
        errors.append(f"Invalid execution status: {state.execution.status}")
    
    if not (0.0 <= state.execution.progress <= 1.0):
        errors.append(f"Invalid progress value: {state.execution.progress}")
    
    # Check clinical context consistency
    if state.clinical.case_id and not state.clinical.patient_id:
        errors.append("Case ID provided without patient ID")
    
    # Check input context
    if state.inputs.image_id and not state.inputs.image_uri:
        errors.append("Image ID provided without image URI")
    
    if state.inputs.ehr_id and not (state.inputs.ehr_uri or state.inputs.ehr_text):
        errors.append("EHR ID provided without EHR content")
    
    # Check policy context
    for threshold_key, threshold_value in state.policies.thresholds.items():
        if not (0.0 <= threshold_value <= 1.0):
            errors.append(f"Invalid threshold value for {threshold_key}: {threshold_value}")
    
    return errors


def merge_workflow_states(
    primary_state: BaseGraphState,
    secondary_state: BaseGraphState,
    merge_strategy: str = "primary_wins"
) -> BaseGraphState:
    """
    Merge two workflow states.
    
    Args:
        primary_state: Primary state (takes precedence)
        secondary_state: Secondary state
        merge_strategy: Strategy for merging ("primary_wins", "secondary_wins", "merge")
    
    Returns:
        Merged workflow state
    """
    if merge_strategy == "primary_wins":
        # Use primary state, only fill missing fields from secondary
        merged_data = primary_state.dict()
        secondary_data = secondary_state.dict()
        
        # Merge workflow_data
        merged_workflow_data = secondary_data.get("workflow_data", {})
        merged_workflow_data.update(merged_data.get("workflow_data", {}))
        merged_data["workflow_data"] = merged_workflow_data
        
        return BaseGraphState(**merged_data)
    
    elif merge_strategy == "secondary_wins":
        # Use secondary state, only fill missing fields from primary
        return merge_workflow_states(secondary_state, primary_state, "primary_wins")
    
    elif merge_strategy == "merge":
        # Merge all fields intelligently
        merged_data = secondary_state.dict()
        primary_data = primary_state.dict()
        
        # Merge specific contexts
        for context_key in ["identity", "clinical", "inputs", "execution", "outputs", "policies"]:
            if context_key in primary_data and context_key in merged_data:
                primary_context = primary_data[context_key]
                secondary_context = merged_data[context_key]
                
                # Merge context fields
                for field_key, field_value in primary_context.items():
                    if field_value is not None:
                        secondary_context[field_key] = field_value
                
                merged_data[context_key] = secondary_context
        
        # Merge workflow_data
        merged_workflow_data = merged_data.get("workflow_data", {})
        merged_workflow_data.update(primary_data.get("workflow_data", {}))
        merged_data["workflow_data"] = merged_workflow_data
        
        return BaseGraphState(**merged_data)
    
    else:
        raise ValueError(f"Unknown merge strategy: {merge_strategy}")


def create_workflow_summary(state: BaseGraphState) -> Dict[str, Any]:
    """
    Create a summary of workflow execution.
    
    Args:
        state: Workflow state
    
    Returns:
        Workflow summary dictionary
    """
    summary = {
        "workflow_id": state.execution.workflow_id,
        "correlation_id": state.identity.correlation_id,
        "status": state.execution.status,
        "progress": state.execution.progress,
        "started_at": state.execution.started_at.isoformat() if state.execution.started_at else None,
        "ended_at": state.execution.ended_at.isoformat() if state.execution.ended_at else None,
        "current_node": state.execution.current_node,
        "error_count": len(state.execution.errors),
        "retry_count": state.execution.retry_count,
        "case_id": state.clinical.case_id,
        "patient_id": state.clinical.patient_id,
        "user_id": state.identity.user_id,
        "outputs": {
            "result_bundle_id": state.outputs.result_bundle_id,
            "pattern_count": len(state.outputs.pattern_outputs),
            "genetic_count": len(state.outputs.genetic_outputs),
            "entity_count": len(state.outputs.ehr_entities),
            "mapping_count": len(state.outputs.ehr_mappings),
            "artifact_count": len(state.outputs.artifacts),
            "graph_snapshot_id": state.outputs.graph_snapshot_id,
            "explanation_report_id": state.outputs.explanation_report_id
        }
    }
    
    # Calculate duration if both timestamps are available
    if state.execution.started_at and state.execution.ended_at:
        duration = (state.execution.ended_at - state.execution.started_at).total_seconds()
        summary["duration_seconds"] = duration
    
    return summary
