from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class PEIState(TypedDict, total=False):
    """
    LangGraph state management for PEI platform
    Defines the shared state passed between all agents in the workflow
    """
    # Communication and routing
    messages: List[Dict[str, Any]]  # Chat history: {role, content, timestamp}
    current_agent: str  # Name of current agent in execution
    action: str  # Classified action from RouterAgent
    user_input: str  # Original user input/command
    
    # OT and Cuadrilla management
    ot_ids: List[int]  # IDs of OTs being processed
    cuadrilla_ids: List[int]  # IDs of cuadrillas involved
    
    # Processing results
    validation_result: Optional[Dict[str, Any]]  # Results from OTSAgent validation
    assignments: List[Dict[str, Any]]  # Assignment results from PlanificacionAgent
    errors: List[str]  # Error messages during processing
    notifications: List[Dict[str, Any]]  # Notifications to send from GobernanzaAgent
    
    # Database and context
    db_session: Optional[Any]  # SQLAlchemy session for database access
    
    # Agent-specific flags
    force_balance: bool  # Flag to force balance phase in planning
    is_complete: bool  # Flag indicating workflow completion


def create_initial_state(user_input: str, db_session: Optional[Any] = None) -> PEIState:
    """
    Create an initial state for a new workflow execution
    
    Args:
        user_input: The user's natural language command
        db_session: Optional SQLAlchemy session for database operations
    
    Returns:
        Initialized PEIState dictionary
    """
    return {
        "messages": [
            {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
        "current_agent": "router",
        "action": None,
        "user_input": user_input,
        "ot_ids": [],
        "cuadrilla_ids": [],
        "validation_result": None,
        "assignments": [],
        "errors": [],
        "notifications": [],
        "db_session": db_session,
        "force_balance": False,
        "is_complete": False,
    }


def add_message(state: PEIState, role: str, content: str) -> PEIState:
    """
    Add a message to the state's message history
    
    Args:
        state: Current PEIState
        role: Message role ('user' or 'agent')
        content: Message content
    
    Returns:
        Updated state with new message
    """
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }
    state["messages"].append(message)
    return state


def add_error(state: PEIState, error: str) -> PEIState:
    """
    Add an error message to the state
    
    Args:
        state: Current PEIState
        error: Error message
    
    Returns:
        Updated state with error
    """
    state["errors"].append(error)
    return state


def set_action(state: PEIState, action: str) -> PEIState:
    """
    Set the action to be executed
    
    Args:
        state: Current PEIState
        action: Action name (sync_ots, plan_assignment, check_governance, send_notification, query_status)
    
    Returns:
        Updated state with action
    """
    state["action"] = action
    return state


def set_current_agent(state: PEIState, agent_name: str) -> PEIState:
    """
    Set the current agent in execution
    
    Args:
        state: Current PEIState
        agent_name: Name of the agent (router, ots, planificacion, gobernanza, comunicacion)
    
    Returns:
        Updated state with current agent
    """
    state["current_agent"] = agent_name
    return state


def add_notification(state: PEIState, notification: Dict[str, Any]) -> PEIState:
    """
    Add a notification to the state
    
    Args:
        state: Current PEIState
        notification: Notification dict with type, recipient, message, etc.
    
    Returns:
        Updated state with notification
    """
    state["notifications"].append(notification)
    return state


def add_assignment(state: PEIState, assignment: Dict[str, Any]) -> PEIState:
    """
    Add an assignment result to the state
    
    Args:
        state: Current PEIState
        assignment: Assignment dict with ot_id, cuadrilla_id, distance, etc.
    
    Returns:
        Updated state with assignment
    """
    state["assignments"].append(assignment)
    return state


def get_last_message(state: PEIState) -> Optional[Dict[str, Any]]:
    """
    Get the last message from the message history
    
    Args:
        state: Current PEIState
    
    Returns:
        Last message dict or None if no messages
    """
    if state.get("messages"):
        return state["messages"][-1]
    return None


def get_messages_by_role(state: PEIState, role: str) -> List[Dict[str, Any]]:
    """
    Get all messages by a specific role
    
    Args:
        state: Current PEIState
        role: Message role to filter by
    
    Returns:
        List of messages matching the role
    """
    return [msg for msg in state.get("messages", []) if msg.get("role") == role]


def get_user_messages(state: PEIState) -> List[Dict[str, Any]]:
    """Get all user messages from state"""
    return get_messages_by_role(state, "user")


def get_agent_messages(state: PEIState) -> List[Dict[str, Any]]:
    """Get all agent messages from state"""
    return get_messages_by_role(state, "agent")


def has_errors(state: PEIState) -> bool:
    """Check if state contains any errors"""
    return len(state.get("errors", [])) > 0


def has_assignments(state: PEIState) -> bool:
    """Check if state contains any assignments"""
    return len(state.get("assignments", [])) > 0


def has_notifications(state: PEIState) -> bool:
    """Check if state contains any notifications"""
    return len(state.get("notifications", [])) > 0


def clear_errors(state: PEIState) -> PEIState:
    """Clear all errors from state"""
    state["errors"] = []
    return state


def clear_assignments(state: PEIState) -> PEIState:
    """Clear all assignments from state"""
    state["assignments"] = []
    return state


def clear_notifications(state: PEIState) -> PEIState:
    """Clear all notifications from state"""
    state["notifications"] = []
    return state


def mark_complete(state: PEIState) -> PEIState:
    """Mark workflow as complete"""
    state["is_complete"] = True
    return state

