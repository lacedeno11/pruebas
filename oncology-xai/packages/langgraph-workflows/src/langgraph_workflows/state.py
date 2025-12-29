"""Common state definitions for LangGraph workflows."""

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class Identity(BaseModel):
    """Identity context for the workflow."""

    correlation_id: str
    user_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class Context(BaseModel):
    """Clinical context for the workflow."""

    patient_id: str | None = None
    case_id: str | None = None


class Inputs(BaseModel):
    """Workflow inputs."""

    image_id: str | None = None
    image_uri: str | None = None
    ehr_id: str | None = None
    ehr_uri: str | None = None
    ehr_text: str | None = None
    ontology_versions: dict[str, str] = Field(default_factory=dict)


class Execution(BaseModel):
    """Execution state."""

    job_id: str | None = None
    status: str = "pending"
    progress: float = 0.0
    current_node: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class Outputs(BaseModel):
    """Workflow outputs."""

    # Inference outputs
    pattern_outputs: list[dict[str, Any]] = Field(default_factory=list)
    genetic_outputs: list[dict[str, Any]] = Field(default_factory=list)
    xai_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    result_bundle_id: str | None = None

    # EHR outputs
    ehr_entities: list[dict[str, Any]] = Field(default_factory=list)
    ehr_mappings: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)

    # Graph outputs
    graph_snapshot_id: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)

    # Report outputs
    explanation_report_id: str | None = None
    report_uri: str | None = None


class Policies(BaseModel):
    """Policy configuration for guardrails."""

    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "lepidic": 0.55,
            "acinar": 0.55,
            "papillary": 0.55,
            "micropapillary": 0.55,
            "solid": 0.55,
            "EGFR": 0.60,
            "KRAS": 0.60,
            "TP53": 0.60,
        }
    )
    hitl_policy: str = "auto"  # auto, always, never
    guardrails_enabled: bool = True
    max_retries: int = 3


class GraphState(TypedDict, total=False):
    """Complete workflow state.

    This TypedDict is used by LangGraph to track state across nodes.
    """

    identity: dict[str, Any]
    context: dict[str, Any]
    inputs: dict[str, Any]
    execution: dict[str, Any]
    outputs: dict[str, Any]
    policies: dict[str, Any]

    # Transient data (not persisted between nodes)
    _current_image: bytes | None
    _current_ehr_text: str | None
    _intermediate_results: dict[str, Any]


def create_initial_state(
    correlation_id: str,
    user_id: str | None = None,
    roles: list[str] | None = None,
    case_id: str | None = None,
    patient_id: str | None = None,
    thresholds: dict[str, float] | None = None,
) -> GraphState:
    """Create an initial graph state."""
    return GraphState(
        identity=Identity(
            correlation_id=correlation_id,
            user_id=user_id,
            roles=roles or [],
        ).model_dump(),
        context=Context(
            patient_id=patient_id,
            case_id=case_id,
        ).model_dump(),
        inputs=Inputs().model_dump(),
        execution=Execution().model_dump(),
        outputs=Outputs().model_dump(),
        policies=Policies(
            thresholds=thresholds or Policies().thresholds
        ).model_dump(),
    )


def update_execution(
    state: GraphState,
    status: str | None = None,
    progress: float | None = None,
    current_node: str | None = None,
    error: dict[str, Any] | None = None,
) -> GraphState:
    """Update execution state."""
    execution = state.get("execution", {})

    if status is not None:
        execution["status"] = status
    if progress is not None:
        execution["progress"] = progress
    if current_node is not None:
        execution["current_node"] = current_node
    if error is not None:
        errors = execution.get("errors", [])
        errors.append(error)
        execution["errors"] = errors

    state["execution"] = execution
    return state
