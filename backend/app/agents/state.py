"""
LangGraph Agent State Schema Definition

Defines the AgentState TypedDict that is passed between all agent nodes
in the LangGraph workflow for DERCAS PEI backend.

The state carries:
- User intent and input for routing
- Operation parameters and results
- Error tracking and logging
- Database session for persistence
"""

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """
    State dictionary passed between LangGraph agent nodes.
    
    Fields:
        user_input: Original user request or system event
        intent: Classified intent (ingest, plan, govern, notify, etc.)
        ot_ids: List of OT IDs affected by operation
        cuadrilla_ids: List of crew IDs affected by operation
        operation: Operation type (ingest, plan, govern, notify)
        parameters: Additional request parameters
        result: Operation result/output
        errors: List of error messages
        agent_logs: List of agent action logs
        session: Database session (Any type to avoid circular imports)
    """

    user_input: str
    intent: str
    ot_ids: List[int]
    cuadrilla_ids: List[int]
    operation: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    errors: List[str]
    agent_logs: List[Dict[str, Any]]
    session: Any


__all__ = ["AgentState"]

