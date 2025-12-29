"""Image Analysis LangGraph workflow.

Nodes: ValidateInput → LoadImage → RunPatternModel → RunMutationModel →
       GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
"""

from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_execution
from langgraph_workflows.tools.model import get_model_client
from langgraph_workflows.tools.storage import get_storage_tool


async def validate_input(state: GraphState) -> GraphState:
    """Validate input parameters."""
    state = update_execution(state, status="running", progress=0.0, current_node="validate_input")

    inputs = state.get("inputs", {})

    if not inputs.get("image_id") and not inputs.get("image_uri"):
        state = update_execution(
            state,
            error={"code": "VALIDATION_ERROR", "message": "image_id or image_uri required"},
        )
        state["execution"]["status"] = "failed"

    return state


async def load_image(state: GraphState) -> GraphState:
    """Load image from storage."""
    state = update_execution(state, progress=0.1, current_node="load_image")

    if state["execution"]["status"] == "failed":
        return state

    inputs = state.get("inputs", {})
    image_uri = inputs.get("image_uri")

    if image_uri:
        try:
            storage = get_storage_tool()
            key = storage.key_from_uri(image_uri)
            image_data = storage.download_file(key)
            state["_current_image"] = image_data
        except Exception as e:
            state = update_execution(
                state,
                error={"code": "IMAGE_LOAD_ERROR", "message": str(e)},
            )
            state["execution"]["status"] = "failed"
    else:
        # Mock image data for testing
        state["_current_image"] = b"mock_image_data"

    return state


async def run_pattern_model(state: GraphState) -> GraphState:
    """Run pattern segmentation model."""
    state = update_execution(state, progress=0.3, current_node="run_pattern_model")

    if state["execution"]["status"] == "failed":
        return state

    image_data = state.get("_current_image", b"")
    policies = state.get("policies", {})
    thresholds = policies.get("thresholds", {})

    try:
        model_client = get_model_client()
        pattern_results = await model_client.predict_patterns(image_data, thresholds)

        outputs = state.get("outputs", {})
        outputs["pattern_outputs"] = pattern_results
        state["outputs"] = outputs

    except Exception as e:
        state = update_execution(
            state,
            error={"code": "MODEL_ERROR", "message": str(e)},
        )
        state["execution"]["status"] = "failed"

    return state


async def run_mutation_model(state: GraphState) -> GraphState:
    """Run mutation prediction model."""
    state = update_execution(state, progress=0.5, current_node="run_mutation_model")

    if state["execution"]["status"] == "failed":
        return state

    image_data = state.get("_current_image", b"")
    policies = state.get("policies", {})
    thresholds = policies.get("thresholds", {})

    try:
        model_client = get_model_client()
        mutation_results = await model_client.predict_mutations(image_data, thresholds)

        outputs = state.get("outputs", {})
        outputs["genetic_outputs"] = mutation_results
        state["outputs"] = outputs

    except Exception as e:
        state = update_execution(
            state,
            error={"code": "MODEL_ERROR", "message": str(e)},
        )
        state["execution"]["status"] = "failed"

    return state


async def generate_xai(state: GraphState) -> GraphState:
    """Generate XAI artifacts."""
    state = update_execution(state, progress=0.7, current_node="generate_xai")

    if state["execution"]["status"] == "failed":
        return state

    image_data = state.get("_current_image", b"")
    outputs = state.get("outputs", {})

    predictions = {
        "patterns": outputs.get("pattern_outputs", []),
        "mutations": outputs.get("genetic_outputs", []),
    }

    try:
        model_client = get_model_client()
        xai_artifacts = await model_client.generate_xai_artifacts(image_data, predictions)

        outputs["xai_artifacts"] = xai_artifacts
        state["outputs"] = outputs

    except Exception as e:
        state = update_execution(
            state,
            error={"code": "XAI_ERROR", "message": str(e)},
        )
        # XAI failure is not fatal

    return state


async def assemble_result_bundle(state: GraphState) -> GraphState:
    """Assemble result bundle."""
    state = update_execution(state, progress=0.8, current_node="assemble_result_bundle")

    if state["execution"]["status"] == "failed":
        return state

    outputs = state.get("outputs", {})
    inputs = state.get("inputs", {})
    context = state.get("context", {})
    policies = state.get("policies", {})

    result_bundle_id = f"rb_{uuid4().hex[:16]}"

    intermediate = state.get("_intermediate_results", {})
    intermediate["result_bundle"] = {
        "result_bundle_id": result_bundle_id,
        "case_id": context.get("case_id"),
        "image_id": inputs.get("image_id"),
        "model_profile": "lung_patterns_v1",
        "model_version": "mock_v1.0",
        "thresholds": policies.get("thresholds", {}),
        "pattern_results": outputs.get("pattern_outputs", []),
        "genetic_results": outputs.get("genetic_outputs", []),
        "xai_artifacts": outputs.get("xai_artifacts", []),
    }

    outputs["result_bundle_id"] = result_bundle_id
    state["outputs"] = outputs
    state["_intermediate_results"] = intermediate

    return state


async def policy_check(state: GraphState) -> GraphState:
    """Check for low confidence and policy violations."""
    state = update_execution(state, progress=0.85, current_node="policy_check")

    if state["execution"]["status"] == "failed":
        return state

    outputs = state.get("outputs", {})
    policies = state.get("policies", {})

    # Check for inconclusive results
    inconclusive_patterns = [
        p for p in outputs.get("pattern_outputs", [])
        if not p.get("is_conclusive", True)
    ]

    inconclusive_mutations = [
        m for m in outputs.get("genetic_outputs", [])
        if m.get("status") == "INCONCLUSIVE"
    ]

    if inconclusive_patterns or inconclusive_mutations:
        intermediate = state.get("_intermediate_results", {})
        intermediate["needs_review"] = True
        intermediate["review_reasons"] = {
            "inconclusive_patterns": [p["pattern"] for p in inconclusive_patterns],
            "inconclusive_mutations": [m["mutation"] for m in inconclusive_mutations],
        }
        state["_intermediate_results"] = intermediate

    return state


async def persist_and_audit(state: GraphState) -> GraphState:
    """Persist results and create audit event."""
    state = update_execution(state, progress=0.95, current_node="persist_and_audit")

    if state["execution"]["status"] == "failed":
        return state

    # In real implementation, would persist to database and emit audit event
    # For now, just mark as complete

    return state


async def finalize(state: GraphState) -> GraphState:
    """Finalize workflow."""
    state = update_execution(state, progress=1.0, current_node="finalize")

    if state["execution"]["status"] != "failed":
        state["execution"]["status"] = "completed"

    # Clean up transient data
    state.pop("_current_image", None)

    return state


def should_continue(state: GraphState) -> Literal["continue", "end"]:
    """Check if workflow should continue."""
    if state.get("execution", {}).get("status") == "failed":
        return "end"
    return "continue"


def create_image_analysis_graph() -> StateGraph:
    """Create the image analysis LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("load_image", load_image)
    workflow.add_node("run_pattern_model", run_pattern_model)
    workflow.add_node("run_mutation_model", run_mutation_model)
    workflow.add_node("generate_xai", generate_xai)
    workflow.add_node("assemble_result_bundle", assemble_result_bundle)
    workflow.add_node("policy_check", policy_check)
    workflow.add_node("persist_and_audit", persist_and_audit)
    workflow.add_node("finalize", finalize)

    # Set entry point
    workflow.set_entry_point("validate_input")

    # Add edges
    workflow.add_conditional_edges(
        "validate_input",
        should_continue,
        {"continue": "load_image", "end": "finalize"},
    )
    workflow.add_conditional_edges(
        "load_image",
        should_continue,
        {"continue": "run_pattern_model", "end": "finalize"},
    )
    workflow.add_conditional_edges(
        "run_pattern_model",
        should_continue,
        {"continue": "run_mutation_model", "end": "finalize"},
    )
    workflow.add_conditional_edges(
        "run_mutation_model",
        should_continue,
        {"continue": "generate_xai", "end": "finalize"},
    )
    workflow.add_edge("generate_xai", "assemble_result_bundle")
    workflow.add_edge("assemble_result_bundle", "policy_check")
    workflow.add_edge("policy_check", "persist_and_audit")
    workflow.add_edge("persist_and_audit", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
