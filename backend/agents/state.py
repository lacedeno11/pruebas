"""
Shared state definitions for LangGraph agents.
Defines the data structures used to communicate between agents.
"""

from typing import TypedDict, Optional, Any, List, Dict
from datetime import datetime


class AgentState(TypedDict):
    """
    Base state for all agents in the orchestration.
    
    This TypedDict defines the structure of messages passed between agents
    in the LangGraph state machine.
    """
    messages: List[Dict[str, Any]]  # Message history
    current_task: str  # Current task being executed
    ot_id: Optional[int]  # OT ID (if applicable)
    cuadrilla_id: Optional[int]  # Cuadrilla ID (if applicable)
    status: str  # Current status (idle, running, completed, error)
    context: Dict[str, Any]  # Additional context data
    error: Optional[str]  # Error message (if any)
    result: Optional[Dict[str, Any]]  # Result of agent execution


class RouterState(AgentState):
    """
    State for RouterAgent.
    
    Used to classify user input and route to appropriate specialized agent.
    Extends AgentState with routing-specific fields.
    """
    classification: Optional[str] = None  # Input classification (ots_ingestion, planning, governance, communication, query)
    next_agent: Optional[str] = None  # Next agent to execute
    confidence: Optional[float] = None  # Confidence score for classification


class OTSState(AgentState):
    """
    State for OTSAgent (OT Synchronization and Ingestion).
    
    Used for fetching OTs from MockApiService and registering them in database.
    """
    fetched_ots: List[Dict[str, Any]] = []  # OTs fetched from API
    validated_ots: List[Dict[str, Any]] = []  # OTs that passed validation
    invalid_ots: List[Dict[str, Any]] = []  # OTs with validation errors
    geo_error_ots: List[Dict[str, Any]] = []  # OTs with missing/invalid coordinates
    total_processed: int = 0
    notifications_sent: int = 0


class PlanificacionState(AgentState):
    """
    State for PlanificacionAgent (Planning and Assignment).
    
    Used for 3-phase planning algorithm and manual assignments.
    """
    unassigned_ots: List[Dict[str, Any]] = []  # OTs needing assignment
    available_cuadrillas: List[Dict[str, Any]] = []  # Available cuadrillas
    phase: Optional[str] = None  # Current planning phase (1, 2, 3)
    assignments_made: List[Dict[str, Any]] = []  # Assignments created
    validation_errors: List[str] = []  # Validation errors encountered
    trigger_type: Optional[str] = None  # auto or manual


class GobernanzaState(AgentState):
    """
    State for GobernanzaAgent (Governance and Compliance).
    
    Used for state transition validation and inactivity monitoring.
    """
    ots_to_check: List[Dict[str, Any]] = []  # OTs to check for inactivity
    alerts_generated: List[Dict[str, Any]] = []  # Governance alerts
    ots_to_cancel: List[Dict[str, Any]] = []  # OTs eligible for auto-cancellation
    cancelled_count: int = 0
    validation_reason: Optional[str] = None  # Reason for state transition validation


class ComunicacionState(AgentState):
    """
    State for ComunicacionAgent (Communication and Notifications).
    
    Used for sending notifications via Telegram and Email.
    """
    channel: Optional[str] = None  # Notification channel (telegram, email)
    recipient: Optional[str] = None  # Recipient identifier (chat_id or email)
    message_template: Optional[str] = None  # Template for message formatting
    formatted_message: Optional[str] = None  # Final formatted message
    notifications_queued: int = 0
    notifications_sent: int = 0

