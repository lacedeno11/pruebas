"""
Agent state definition for LangGraph orchestrator.
Defines shared state across all agents in the workflow.
"""

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict):
    """
    Shared state for all agents in the LangGraph workflow.

    Tracks input, agent classifications, execution results, and errors.
    """

    input: str
    """User input or system event message"""

    classification: Optional[str]
    """Router classification: INGEST_OT, PLAN_OTS, CHECK_STATUS, etc."""

    ots_ingested: List[Dict[str, Any]]
    """List of OTs ingested by OTSAgent"""

    planning_result: Dict[str, Any]
    """Result from PlanificacionAgent execution"""

    governance_result: Dict[str, Any]
    """Result from GobernanzaAgent execution"""

    notifications_sent: List[Dict[str, Any]]
    """List of notifications sent by ComunicacionAgent"""

    error: Optional[str]
    """Error message if any agent fails"""

    current_agent: str
    """Name of agent currently executing"""

