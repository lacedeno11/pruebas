"""
Shared state definition for PEI LangGraph workflow.

This module defines the PEIState TypedDict which is the shared state
that flows through all agent nodes in the LangGraph workflow.
All agents receive and modify this state as they process information.
"""

from typing import Any, TypedDict


class PEIState(TypedDict, total=False):
    """
    Shared state for PEI agent workflow in LangGraph.

    This TypedDict defines the structure of state that is passed through
    the agent graph. Each agent receives this state, processes it, and
    returns a modified version.

    Attributes:
        input (str): User input or command that triggered the workflow
            Example: "Plan all PUBLICO project OTs"

        agent_messages (list[dict]): Chronological list of agent messages
            Each message: {"agent": str, "content": str, "timestamp": str}
            Used for conversation history and debugging

        current_ot_id (int | None): Currently processing OT ID
            Set by agents when focusing on specific OT

        ots_to_process (list[dict]): List of OTs to process in workflow
            Contains OT data with: id, external_id, status, etc.

        action_result (dict): Result of last agent action
            Contains: success (bool), message (str), data (optional dict)
            Flows from one agent to the next

        error (str | None): Error message if workflow fails
            Set when an agent encounters an error
            Allows downstream agents to handle failures

        metadata (dict): Flexible metadata for workflow control
            Common keys:
            - "route": Routing decision from RouterAgent
                Values: "ingest_ots", "plan_ots", "check_governance", etc.
            - "confidence": Confidence score of routing decision (0-1)
            - "notification_type": Type of notification to send
                Values: "alert", "status_change", "geo_error", "governance_alert"
            - "agent_logs": List of logged actions by agents
            - "planning_strategy": Strategy for planning agent
                Values: "balanced", "proximity", "nightly"
            - Any custom metadata agents need to pass to each other
    """

    input: str
    agent_messages: list[dict]
    current_ot_id: int | None
    ots_to_process: list[dict]
    action_result: dict
    error: str | None
    metadata: dict


def create_initial_state(input_text: str) -> PEIState:
    """
    Create an initial PEIState for starting a new workflow.

    Args:
        input_text (str): User input or command

    Returns:
        PEIState: Initial state with default values
    """
    return PEIState(
        input=input_text,
        agent_messages=[],
        current_ot_id=None,
        ots_to_process=[],
        action_result={},
        error=None,
        metadata={},
    )


def add_agent_message(
    state: PEIState, agent_name: str, content: str, timestamp: str
) -> PEIState:
    """
    Add an agent message to the state's message history.

    Args:
        state (PEIState): Current state
        agent_name (str): Name of agent sending message
        content (str): Message content
        timestamp (str): ISO format timestamp

    Returns:
        PEIState: Updated state with new message
    """
    new_message = {
        "agent": agent_name,
        "content": content,
        "timestamp": timestamp,
    }
    state["agent_messages"].append(new_message)
    return state


def set_action_result(
    state: PEIState, success: bool, message: str, data: dict | None = None
) -> PEIState:
    """
    Set the action result in the state.

    Args:
        state (PEIState): Current state
        success (bool): Whether action succeeded
        message (str): Result message
        data (dict | None): Optional result data

    Returns:
        PEIState: Updated state with action result
    """
    state["action_result"] = {
        "success": success,
        "message": message,
        "data": data or {},
    }
    return state


def set_error(state: PEIState, error_message: str) -> PEIState:
    """
    Set an error in the state and mark action as failed.

    Args:
        state (PEIState): Current state
        error_message (str): Error message

    Returns:
        PEIState: Updated state with error
    """
    state["error"] = error_message
    state["action_result"] = {
        "success": False,
        "message": error_message,
        "data": {},
    }
    return state


def set_metadata(state: PEIState, key: str, value: Any) -> PEIState:
    """
    Set a metadata value in the state.

    Args:
        state (PEIState): Current state
        key (str): Metadata key
        value (Any): Metadata value

    Returns:
        PEIState: Updated state with metadata
    """
    state["metadata"][key] = value
    return state


def get_metadata(state: PEIState, key: str, default: Any = None) -> Any:
    """
    Get a metadata value from the state.

    Args:
        state (PEIState): Current state
        key (str): Metadata key
        default (Any): Default value if key not found

    Returns:
        Any: Metadata value or default
    """
    return state["metadata"].get(key, default)


def to_dict(state: PEIState) -> dict[str, Any]:
    """
    Convert PEIState TypedDict to a regular dictionary for serialization.

    Args:
        state (PEIState): State to serialize

    Returns:
        dict: Serializable dictionary
    """
    return dict(state)


def from_dict(data: dict[str, Any]) -> PEIState:
    """
    Create a PEIState TypedDict from a regular dictionary (deserialization).

    Args:
        data (dict): Dictionary with state data

    Returns:
        PEIState: Reconstructed state
    """
    return PEIState(
        input=data.get("input", ""),
        agent_messages=data.get("agent_messages", []),
        current_ot_id=data.get("current_ot_id"),
        ots_to_process=data.get("ots_to_process", []),
        action_result=data.get("action_result", {}),
        error=data.get("error"),
        metadata=data.get("metadata", {}),
    )

