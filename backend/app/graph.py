import logging
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.app.agents import (
    RouterAgent,
    OTSAgent,
    PlanificacionAgent,
    GobernanzaAgent,
    ComunicacionAgent
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """
    TypedDict defining the state schema for the LangGraph state machine.
    
    This state is passed between nodes in the graph and represents the current
    context of an OT processing workflow or chat interaction.
    
    Fields:
    - input: User message or system input triggering the workflow
    - ots: List of OT dictionaries being processed
    - cuadrillas: List of Cuadrilla dictionaries for reference
    - action: Current action/agent to execute (e.g., 'OTS_AGENT', 'PLANIFICACION_AGENT')
    - result: Result dictionary from the last executed node
    - messages: List of all messages in the conversation
    - errors: List of error messages accumulated during execution
    """
    input: str
    ots: List[Dict[str, Any]]
    cuadrillas: List[Dict[str, Any]]
    action: str
    result: Dict[str, Any]
    messages: List[str]
    errors: List[str]


# Initialize agents
router_agent = RouterAgent()
ots_agent = OTSAgent()
planificacion_agent = PlanificacionAgent()
gobernanza_agent = GobernanzaAgent()
comunicacion_agent = ComunicacionAgent()


async def route_node(state: AgentState) -> AgentState:
    """
    Router Node: Classifies user input and routes to appropriate agent.
    
    Uses RouterAgent to determine which specialized agent should handle the request.
    
    Args:
        state: Current AgentState
    
    Returns:
        Updated state with action field set to target agent
    """
    logger.info(f"Route node: Processing input: {state['input'][:50]}...")
    
    try:
        updated_state = await router_agent.route(state)
        logger.info(f"Route node: Routing to {updated_state.get('action', 'ERROR')}")
        return updated_state
    except Exception as e:
        error_msg = f"Error in routing: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "action": "ERROR",
            "errors": state.get("errors", []) + [error_msg]
        }


async def ots_ingestion_node(state: AgentState) -> AgentState:
    """
    OTS Ingestion Node: Fetches OTs from TELCOS and persists to database.
    
    Executed when action is 'OTS_AGENT'. Fetches OTs, validates coordinates,
    and stores in database.
    
    Args:
        state: Current AgentState
    
    Returns:
        Updated state with OT ingestion results
    """
    logger.info("OTS Ingestion node: Starting OT ingestion")
    
    try:
        updated_state = await ots_agent.ingest_ots(state)
        logger.info(f"OTS Ingestion node: Completed with result {updated_state.get('result', {})}")
        return updated_state
    except Exception as e:
        error_msg = f"Error in OTS ingestion: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "action": "INGEST_ERROR",
            "errors": state.get("errors", []) + [error_msg]
        }


async def planificacion_node(state: AgentState) -> AgentState:
    """
    Planificación Node: Assigns OTs to cuadrillas using 3-phase algorithm.
    
    Executed after OTS_AGENT. Implements:
    - Phase 1: Balanced assignment (1 OT per cuadrilla)
    - Phase 2: Proximity-based assignment (<10km from centroid)
    - Phase 3: Nocturnal optimization (stub)
    
    Args:
        state: Current AgentState
    
    Returns:
        Updated state with assignment results
    """
    logger.info("Planificación node: Starting OT assignment")
    
    try:
        updated_state = await planificacion_agent.assign_ots(state)
        logger.info(f"Planificación node: Completed with result {updated_state.get('result', {})}")
        return updated_state
    except Exception as e:
        error_msg = f"Error in planificación: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "action": "ASSIGNMENT_ERROR",
            "errors": state.get("errors", []) + [error_msg]
        }


async def gobernanza_node(state: AgentState) -> AgentState:
    """
    Gobernanza Node: Performs governance checks and compliance validation.
    
    Checks for:
    - Detained OTs and triggers alerts (days 20, 25, 29)
    - Auto-cancellation of OTs detained >30 days
    - PREPLANIFICADA alerts (>48 hours)
    - Document validation for PUBLICO projects
    
    Args:
        state: Current AgentState
    
    Returns:
        Updated state with governance check results
    """
    logger.info("Gobernanza node: Starting governance checks")
    
    try:
        # For now, check detained OTs
        updated_state = await gobernanza_agent.check_detained_ots(state)
        logger.info(f"Gobernanza node: Completed with result {updated_state.get('result', {})}")
        return updated_state
    except Exception as e:
        error_msg = f"Error in gobernanza checks: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "action": "GOVERNANCE_ERROR",
            "errors": state.get("errors", []) + [error_msg]
        }


async def comunicacion_node(state: AgentState) -> AgentState:
    """
    Comunicación Node: Sends notifications based on events.
    
    Routes notifications to team managers via:
    - Telegram (for urgent alerts and status updates)
    - Email (for formal notifications and completions)
    
    Args:
        state: Current AgentState
    
    Returns:
        Updated state with notification results
    """
    logger.info("Comunicación node: Starting notifications")
    
    try:
        # For now, this is a logging/stub step
        # In production, would send actual notifications based on state
        logger.info("Comunicación node: Notifications processed")
        return {
            **state,
            "action": "COMUNICACION_COMPLETE",
            "result": {
                "notifications_sent": 0,
                "messages": ["Notification system initialized (stub)"]
            }
        }
    except Exception as e:
        error_msg = f"Error in comunicación: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "action": "COMUNICACION_ERROR",
            "errors": state.get("errors", []) + [error_msg]
        }


def should_route_to_ots(state: AgentState) -> bool:
    """Conditional edge: Check if should route to OTS agent."""
    return state.get("action") == "OTS_AGENT"


def should_route_to_planificacion(state: AgentState) -> bool:
    """Conditional edge: Check if should route to Planificación agent."""
    return state.get("action") == "PLANIFICACION_AGENT"


def should_route_to_gobernanza(state: AgentState) -> bool:
    """Conditional edge: Check if should route to Gobernanza agent."""
    return state.get("action") == "GOBERNANZA_AGENT"


def should_route_to_comunicacion(state: AgentState) -> bool:
    """Conditional edge: Check if should route to Comunicación agent."""
    return state.get("action") == "COMUNICACION_AGENT"


def create_graph() -> StateGraph:
    """
    Create and compile the LangGraph state machine.
    
    Graph structure:
    - router (entry point)
      ├─ OTS_AGENT → ots_ingestion → planificacion → end
      ├─ PLANIFICACION_AGENT → planificacion → end
      ├─ GOBERNANZA_AGENT → gobernanza → comunicacion → end
      ├─ COMUNICACION_AGENT → comunicacion → end
      └─ ERROR → end
    
    Returns:
        Compiled StateGraph with MemorySaver checkpoint
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", route_node)
    graph.add_node("ots_ingestion", ots_ingestion_node)
    graph.add_node("planificacion", planificacion_node)
    graph.add_node("gobernanza", gobernanza_node)
    graph.add_node("comunicacion", comunicacion_node)

    # Set entry point
    graph.set_entry_point("router")

    # Add conditional edges from router based on action
    graph.add_conditional_edges(
        "router",
        lambda state: state.get("action", "ERROR"),
        {
            "OTS_AGENT": "ots_ingestion",
            "PLANIFICACION_AGENT": "planificacion",
            "GOBERNANZA_AGENT": "gobernanza",
            "COMUNICACION_AGENT": "comunicacion",
            "ERROR": END,
        }
    )

    # OTS workflow: ots_ingestion → planificacion → end
    graph.add_edge("ots_ingestion", "planificacion")
    graph.add_edge("planificacion", END)

    # Gobernanza workflow: gobernanza → comunicacion → end
    graph.add_edge("gobernanza", "comunicacion")
    graph.add_edge("comunicacion", END)

    # Direct endpoints
    # PLANIFICACION_AGENT → planificacion → end (already added above)
    # COMUNICACION_AGENT → comunicacion → end

    # Compile with MemorySaver for state persistence
    checkpointer = MemorySaver()
    compiled_graph = graph.compile(checkpointer=checkpointer)

    logger.info("LangGraph state machine compiled successfully")
    return compiled_graph


# Create the global graph instance
graph = create_graph()


async def execute_workflow(
    user_input: str,
    thread_id: str = "default"
) -> Dict[str, Any]:
    """
    Execute the workflow graph with user input.
    
    Invokes the graph with initial state and returns final state.
    
    Args:
        user_input: User message or system command
        thread_id: Thread ID for state persistence (for future use)
    
    Returns:
        Final state after workflow execution
    """
    # Initialize state
    initial_state: AgentState = {
        "input": user_input,
        "ots": [],
        "cuadrillas": [],
        "action": "",
        "result": {},
        "messages": [user_input],
        "errors": []
    }

    try:
        logger.info(f"Executing workflow for input: {user_input[:50]}...")
        
        # Invoke graph
        final_state = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}
        )

        logger.info(f"Workflow completed with action: {final_state.get('action')}")
        return final_state

    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}"
        logger.error(error_msg)
        
        return {
            **initial_state,
            "action": "ERROR",
            "errors": [error_msg]
        }


__all__ = ["AgentState", "graph", "execute_workflow"]

