"""
LangGraph state definition for PEI Platform agentic system.
Defines the state dictionary structure that flows through all agent nodes.
"""

from typing import Dict, List, Optional
from typing_extensions import TypedDict


class PEIGraphState(TypedDict):
    """
    TypedDict defining the state structure that flows through LangGraph nodes.
    
    This state is passed from agent to agent through the LangGraph StateGraph.
    Each agent reads from the state, performs its logic, and updates relevant
    fields before passing the state to the next agent.
    
    Fields:
        user_input (str): User's input text or request
        event_type (str): Type of event triggering the graph execution
        ot_data (dict): Dictionary containing OT-specific data for operations
        current_ot_id (int or None): ID of the current OT being processed
        cuadrilla_id (int or None): ID of the current Cuadrilla being processed
        action_result (str): Result description of the last executed action
        error_message (str or None): Error message if any operation failed
        agent_logs (list): List of agent execution logs (LogAgente records)
        next_agent (str or None): Name of the next agent to execute
    """

    user_input: str
    """
    User's input text or request.
    
    Examples:
    - "Download new OTs from TELCOS"
    - "Plan assignments for all unassigned OTs"
    - "Check for inactive or detained OTs"
    - "Send notifications to teams"
    
    Used by RouterAgent to classify intent and determine next agent.
    """

    event_type: str
    """
    Type of event that triggered the graph execution.
    
    Possible values:
    - 'user_input': User initiated request (via chat or API)
    - 'scheduled_governance': Hourly governance check from scheduler
    - 'nightly_normalization': Nightly centroid recalculation
    - 'system_event': System-generated event
    - 'api_request': API endpoint request
    
    Helps agents understand context and adjust behavior accordingly.
    """

    ot_data: dict
    """
    Dictionary containing OT-specific data for operations.
    
    Structure (varies by operation):
    {
        'ot_id': int,                    # ID of OT
        'external_id': str,              # External ID from TELCOS
        'status': str,                   # Current status
        'project_type': str,             # PUBLICO, PRIVADO, or TERCERIZADO
        'lat': float,                    # Latitude
        'long': float,                   # Longitude
        'cuadrilla_id': int or None,     # Assigned cuadrilla
        'detencion_motivo': str or None, # Detention reason
        ...other OT fields...
    }
    
    Used by OTSAgent, PlanificacionAgent, and GobernanzaAgent for
    operations on specific OTs.
    """

    current_ot_id: Optional[int]
    """
    ID of the current OT being processed.
    
    Set by agents when they start processing a specific OT.
    Used for logging and tracking which OT is being worked on.
    None if no specific OT is being processed (e.g., during bulk operations).
    """

    cuadrilla_id: Optional[int]
    """
    ID of the current Cuadrilla being processed.
    
    Set by PlanificacionAgent when assigning OTs to cuadrillas.
    Used for tracking which team is being assigned work.
    None if no specific cuadrilla is being processed.
    """

    action_result: str
    """
    Result description of the last executed action.
    
    Set by agents after completing their logic.
    
    Examples:
    - "Successfully downloaded 18 OTs from TELCOS"
    - "Assigned 12 OTs to 3 cuadrillas"
    - "Auto-cancelled 2 OTs due to timeout"
    - "Document validation failed for 1 PUBLICO project"
    
    Used for logging and user feedback.
    """

    error_message: Optional[str]
    """
    Error message if any operation failed.
    
    Set by agents when they encounter errors.
    Used for error handling and user notification.
    
    Examples:
    - "TELCOS API returned 500 error"
    - "Database transaction failed"
    - "Missing required coordinates for OT"
    
    None if no error occurred.
    """

    agent_logs: List[Dict]
    """
    List of agent execution logs.
    
    Each agent appends its execution logs to this list.
    Used for audit trail and debugging.
    
    Structure of each log entry:
    {
        'id': int,                          # LogAgente ID from database
        'ot_id': int or None,               # Associated OT ID
        'agente_name': str,                 # Agent name (e.g., 'OTSAgent')
        'accion': str,                      # Action performed
        'resultado': str,                   # SUCCESS, FAILURE, or PENDING
        'raw_llm_response': str or None,    # Raw LLM response if applicable
        'metadata': dict or None,           # Additional context
        'created_at': str,                  # ISO format timestamp
    }
    
    Initialized as empty list, accumulated through agent execution.
    """

    next_agent: Optional[str]
    """
    Name of the next agent to execute in the graph.
    
    Set by RouterAgent or conditional edge logic.
    Determines which agent node to route to next.
    
    Possible values:
    - 'ots': Route to OTSAgent
    - 'planificacion': Route to PlanificacionAgent
    - 'gobernanza': Route to GobernanzaAgent
    - 'comunicacion': Route to ComunicacionAgent
    - 'end': Terminate graph execution
    - None: Use conditional edges to determine next agent
    
    RouterAgent analyzes user_input and event_type to set this field.
    """


# Alternative state definitions for specific agent workflows (future use)


class OTSAgentState(TypedDict):
    """
    Specialized state for OTSAgent execution.
    
    Extends PEIGraphState with OTS-specific fields.
    """

    user_input: str
    event_type: str
    ot_data: dict
    current_ot_id: Optional[int]
    cuadrilla_id: Optional[int]
    action_result: str
    error_message: Optional[str]
    agent_logs: List[Dict]
    next_agent: Optional[str]
    # OTS-specific fields
    ots_fetched: int  # Number of OTs fetched
    ots_with_errors: int  # Number of OTs with geo errors


class PlanificacionAgentState(TypedDict):
    """
    Specialized state for PlanificacionAgent execution.
    
    Extends PEIGraphState with planning-specific fields.
    """

    user_input: str
    event_type: str
    ot_data: dict
    current_ot_id: Optional[int]
    cuadrilla_id: Optional[int]
    action_result: str
    error_message: Optional[str]
    agent_logs: List[Dict]
    next_agent: Optional[str]
    # Planning-specific fields
    ots_assigned: int  # Number of OTs assigned
    cuadrillas_updated: int  # Number of cuadrillas with updated centroids
    unassigned_ots: List[int]  # OT IDs that couldn't be assigned


class GobernanzaAgentState(TypedDict):
    """
    Specialized state for GobernanzaAgent execution.
    
    Extends PEIGraphState with governance-specific fields.
    """

    user_input: str
    event_type: str
    ot_data: dict
    current_ot_id: Optional[int]
    cuadrilla_id: Optional[int]
    action_result: str
    error_message: Optional[str]
    agent_logs: List[Dict]
    next_agent: Optional[str]
    # Governance-specific fields
    inactivity_alerts: int  # Number of inactivity alerts
    detention_alerts: int  # Number of detention alerts
    auto_cancellations: int  # Number of auto-cancelled OTs
    document_warnings: int  # Number of document validation warnings

