"""LangGraph state definition for PEI Agéntico platform."""

from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    """Enumeration of possible agent actions in the workflow."""
    INGEST = "ingest"
    PLAN = "plan"
    VALIDATE = "validate"
    NOTIFY = "notify"
    GOVERNANCE = "governance"
    CHAT = "chat"


class PEIState(TypedDict, total=False):
    """
    State structure for LangGraph workflow in PEI Agéntico.
    
    This TypedDict defines the state that flows through the LangGraph
    state graph, carrying information between agents and nodes.
    """
    
    # OT identification and data
    ot_id: str
    """The ID or external_id of the work order being processed."""
    
    ot_data: Dict[str, Any]
    """Complete OT data including status, coordinates, project type, etc."""
    
    # Status tracking
    current_status: str
    """Current status of the OT (PREPLANIFICADA, PLANIFICADA, etc.)."""
    
    # Workflow action
    action: str
    """
    Current action being executed by the workflow.
    Values: 'ingest', 'plan', 'validate', 'notify', 'governance', 'chat'
    """
    
    # Crew assignment
    cuadrilla_id: Optional[str]
    """ID of the assigned crew (Cuadrilla), if applicable."""
    
    # Validation
    validation_result: Dict[str, Any]
    """
    Result of validation checks.
    Format: {valid: bool, error_message: str, warnings: [str]}
    """
    
    # Error handling
    error: Optional[str]
    """Error message if workflow execution fails."""
    
    # Agent responses
    agent_responses: List[Dict[str, Any]]
    """
    List of responses from executed agents.
    Each entry: {agent_name: str, response: Any, timestamp: str}
    """
    
    # Conversational state
    messages: List[Dict[str, Any]]
    """
    Conversation history for chat agent.
    Each entry: {role: 'user'|'assistant', content: str, timestamp: str}
    """


def create_initial_state(
    action: str,
    ot_id: Optional[str] = None,
    ot_data: Optional[Dict[str, Any]] = None,
) -> PEIState:
    """
    Create an initial PEIState for starting a workflow.
    
    Args:
        action: The action to perform (INGEST, PLAN, VALIDATE, NOTIFY, GOVERNANCE, CHAT)
        ot_id: Optional OT ID for OT-specific workflows
        ot_data: Optional OT data dictionary
    
    Returns:
        PEIState: Initialized state ready for workflow execution
    
    Example:
        >>> state = create_initial_state(
        ...     action="plan",
        ...     ot_id="OT-12345",
        ...     ot_data={"status": "PREPLANIFICADA", "project_type": "PUBLICO"}
        ... )
    """
    state: PEIState = {
        "action": action,
        "ot_id": ot_id or "",
        "ot_data": ot_data or {},
        "current_status": ot_data.get("status", "") if ot_data else "",
        "cuadrilla_id": None,
        "validation_result": {},
        "error": None,
        "agent_responses": [],
        "messages": [],
    }
    return state


def add_agent_response(
    state: PEIState,
    agent_name: str,
    response: Any,
    timestamp: Optional[str] = None,
) -> PEIState:
    """
    Add an agent's response to the state.
    
    Args:
        state: The current PEIState
        agent_name: Name of the agent that generated the response
        response: The response data/message from the agent
        timestamp: Optional timestamp (auto-generated if not provided)
    
    Returns:
        PEIState: Updated state with the new agent response
    
    Example:
        >>> state = add_agent_response(
        ...     state,
        ...     agent_name="Planificación Agent",
        ...     response={"assignments": 5, "pending": 2}
        ... )
    """
    from datetime import datetime
    
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    
    agent_response = {
        "agent_name": agent_name,
        "response": response,
        "timestamp": timestamp,
    }
    
    if "agent_responses" not in state:
        state["agent_responses"] = []
    
    state["agent_responses"].append(agent_response)
    return state


def add_message(
    state: PEIState,
    role: str,
    content: str,
    timestamp: Optional[str] = None,
) -> PEIState:
    """
    Add a message to the conversation history in state.
    
    Args:
        state: The current PEIState
        role: Role of the message sender ('user' or 'assistant')
        content: The message content
        timestamp: Optional timestamp (auto-generated if not provided)
    
    Returns:
        PEIState: Updated state with the new message
    
    Example:
        >>> state = add_message(
        ...     state,
        ...     role="assistant",
        ...     content="Planning has been completed successfully"
        ... )
    """
    from datetime import datetime
    
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    
    message = {
        "role": role,
        "content": content,
        "timestamp": timestamp,
    }
    
    if "messages" not in state:
        state["messages"] = []
    
    state["messages"].append(message)
    return state


def update_validation_result(
    state: PEIState,
    valid: bool,
    error_message: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> PEIState:
    """
    Update the validation result in state.
    
    Args:
        state: The current PEIState
        valid: Whether validation passed
        error_message: Optional error message if validation failed
        warnings: Optional list of warning messages
    
    Returns:
        PEIState: Updated state with validation result
    
    Example:
        >>> state = update_validation_result(
        ...     state,
        ...     valid=True,
        ...     warnings=["Document count is exactly 29, no buffer"]
        ... )
    """
    state["validation_result"] = {
        "valid": valid,
        "error_message": error_message,
        "warnings": warnings or [],
    }
    return state


def get_agent_response(state: PEIState, agent_name: str) -> Optional[Any]:
    """
    Retrieve a specific agent's response from state.
    
    Args:
        state: The current PEIState
        agent_name: Name of the agent to retrieve response from
    
    Returns:
        Optional[Any]: The agent's response, or None if not found
    
    Example:
        >>> planning_response = get_agent_response(state, "Planificación Agent")
    """
    for response in state.get("agent_responses", []):
        if response.get("agent_name") == agent_name:
            return response.get("response")
    return None


def get_last_message(state: PEIState, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get the last message in conversation history.
    
    Args:
        state: The current PEIState
        role: Optional role filter ('user' or 'assistant')
    
    Returns:
        Optional[Dict]: The last matching message, or None if not found
    
    Example:
        >>> last_user_msg = get_last_message(state, role="user")
    """
    messages = state.get("messages", [])
    
    if not messages:
        return None
    
    if role is None:
        return messages[-1]
    
    for message in reversed(messages):
        if message.get("role") == role:
            return message
    
    return None

