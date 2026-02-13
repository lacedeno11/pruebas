"""
Agent state definition for LangGraph.

Defines the AgentState TypedDict that is shared across all agent nodes
in the planning and governance workflow graph.
"""

from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    Shared state across all agent nodes in the LangGraph workflow.
    
    This TypedDict defines the structure of state that flows through
    the agent graph, allowing agents to:
    - Access user input and messages
    - Share results across agents
    - Maintain execution history
    - Control workflow continuation
    
    Attributes:
        messages: List of conversation messages (ChatMessage-like dicts)
            Each message should have: role (user/agent), content (str), timestamp (str optional)
        
        current_ot_id: Optional UUID of the OT being processed
            Set by Router Agent based on input
            Used by subsequent agents to focus on specific OT
        
        action_type: Classification of the user's intent
            Possible values: INGEST_OT, PLAN_OT, UPDATE_STATUS, QUERY_STATUS, GOVERNANCE_CHECK, CHAT
            Set by Router Agent to route to appropriate handler
        
        input_data: User input and parameters
            Contains the original user request and any parameters
            Example: {"user_message": "Plan all OTs", "filters": {...}}
        
        result: Output from agents
            Agents populate this with their results
            Example: {"created_ots": 15, "errors": [...], "assignments": [...]}
        
        error: Optional error message if something fails
            Set by agents if they encounter issues
            Propagates to end node for error handling
        
        agent_history: List of agent names that have executed
            Tracks execution path through graph
            Example: ["RouterAgent", "PlanificacionAgent", "ComunicacionAgent"]
        
        should_continue: Whether workflow should continue
            Set by agents to control graph flow
            False stops execution and goes to end node
    """
    
    # Input/Message Management
    messages: List[Dict[str, Any]]
    """List of messages in the conversation. Each message is a dict with:
    - role: "user" | "assistant" | "system"
    - content: message text
    - timestamp: ISO format datetime (optional)
    - agent_name: name of agent if from assistant (optional)
    """
    
    # OT Context
    current_ot_id: Optional[str]
    """UUID of the OT being processed. None if processing multiple OTs or no specific OT."""
    
    # Action Classification
    action_type: str
    """
    Intent classification for routing. Values:
    - INGEST_OT: Fetch OTs from TELCOS API
    - PLAN_OT: Plan/assign OTs to cuadrillas
    - UPDATE_STATUS: Update OT status
    - QUERY_STATUS: Query OT status/details
    - GOVERNANCE_CHECK: Check governance rules
    - CHAT: General chat/query
    - UNKNOWN: Could not classify
    """
    
    # Input Data
    input_data: Dict[str, Any]
    """
    User input and parameters:
    - user_message: original user input
    - parameters: action-specific parameters
    - filters: optional filtering criteria
    Example:
    {
        "user_message": "Plan all outstanding OTs",
        "action_type": "PLAN_OT",
        "parameters": {
            "strategy": "balanced",
            "cuadrillas": ["cuad1", "cuad2"],
        },
        "filters": {
            "status": "PREPLANIFICADA",
            "limit": 50,
        }
    }
    """
    
    # Results
    result: Dict[str, Any]
    """
    Output from agent execution. Structure varies by agent:
    
    OTSAgent result:
    {
        "created_ots": 15,
        "errors": [],
        "created_ot_ids": ["id1", "id2", ...],
    }
    
    PlanificacionAgent result:
    {
        "assignments": [
            {"ot_id": "...", "cuadrilla_id": "...", "distance": 5.2},
        ],
        "total_assigned": 10,
        "total_failed": 2,
        "phase_1_results": {...},
        "phase_2_results": {...},
        "phase_3_results": {...},
    }
    
    GobernanzaAgent result:
    {
        "issues_found": 5,
        "alerts_triggered": 3,
        "auto_cancelled": 2,
        "issues": [...],
    }
    
    ComunicacionAgent result:
    {
        "notifications_sent": 3,
        "notifications_failed": 0,
        "delivery_status": "success",
    }
    """
    
    # Error Handling
    error: Optional[str]
    """Error message if agent encountered an issue. None if no error."""
    
    # Execution Tracking
    agent_history: List[str]
    """
    List of agent names that have executed in order.
    Example: ["RouterAgent", "PlanificacionAgent", "ComunicacionAgent"]
    Used to:
    - Track execution path
    - Prevent infinite loops
    - Log agent sequence
    - Debug workflow issues
    """
    
    # Flow Control
    should_continue: bool
    """
    Whether to continue graph execution or jump to end node.
    - True: Continue to next node
    - False: Go directly to end node
    Used by agents to exit early if errors occur.
    """


# Type alias for easier imports
StateDict = AgentState

