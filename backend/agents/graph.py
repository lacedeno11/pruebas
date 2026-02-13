"""LangGraph state graph for PEI agent orchestration"""

import logging
from typing import TypedDict, List, Optional

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class PEIState(TypedDict):
    """State schema for PEI platform agent graph"""

    # Data collections
    ots: List[dict]  # List of OT objects from database or API
    cuadrillas: List[dict]  # List of Cuadrilla objects

    # Control flow
    current_action: str  # Current action: ingest_ots, plan_ots, check_governance, send_notification, query
    user_input: Optional[str]  # User input for routing decisions

    # Results and errors
    validation_result: Optional[dict]  # Result of validation operations
    error: Optional[str]  # Error message if operation fails

    # Audit trail
    agent_logs: List[dict]  # Log entries from agent operations


def route_action(state: PEIState) -> str:
    """
    Route action based on current_action in state.

    Maps current_action to appropriate graph node for execution.

    Args:
        state: Current PEI state

    Returns:
        Node name to execute next
    """
    current_action = state.get("current_action", "").lower()

    logger.info(f"Routing action: {current_action}")

    # Route to appropriate node based on current_action
    if current_action == "ingest_ots":
        return "ots_ingestion_node"
    elif current_action == "plan_ots":
        return "planning_node"
    elif current_action == "check_governance":
        return "governance_node"
    elif current_action == "send_notification":
        return "communication_node"
    elif current_action == "query":
        return "end_node"
    else:
        logger.warning(f"Unknown action: {current_action}, routing to end")
        return "end_node"


def router_node(state: PEIState) -> PEIState:
    """
    Router node: classify user input and set current_action.

    This is the entry point for user requests. The router extracts intent from
    user_input and sets current_action for downstream agents.

    Args:
        state: Current PEI state

    Returns:
        Updated state with current_action set
    """
    logger.info("Router node: Classifying user intent")

    user_input = state.get("user_input", "").lower()

    # Simple keyword-based routing (replace with LLM in production)
    if "ingest" in user_input or "fetch" in user_input:
        state["current_action"] = "ingest_ots"
    elif "plan" in user_input or "assign" in user_input:
        state["current_action"] = "plan_ots"
    elif "governance" in user_input or "check" in user_input or "cancel" in user_input:
        state["current_action"] = "check_governance"
    elif "notify" in user_input or "alert" in user_input or "send" in user_input:
        state["current_action"] = "send_notification"
    else:
        state["current_action"] = "query"

    logger.info(f"Classified action: {state['current_action']}")

    # Add log entry
    state["agent_logs"].append(
        {
            "agent": "router",
            "action": "classify_intent",
            "user_input": user_input,
            "classified_as": state["current_action"],
        }
    )

    return state


def ots_ingestion_node(state: PEIState) -> PEIState:
    """
    OT Ingestion node: placeholder for OTS Agent integration.

    In production, this calls OTSAgent.execute(state).
    The agent will:
    1. Fetch OTs from TELCOS API via TelcosService
    2. Validate coordinates
    3. Create OT records in database
    4. Return IngestionResult

    Args:
        state: Current PEI state

    Returns:
        Updated state with ingestion results
    """
    logger.info("OT Ingestion node: Triggered")

    # Placeholder - in production, this would call OTSAgent
    # from backend.agents.ots_agent import OTSAgent
    # agent = OTSAgent(db_session, telcos_service)
    # state = await agent.execute(state)

    state["agent_logs"].append(
        {
            "agent": "ots_ingestion",
            "action": "ingest_ots",
            "status": "placeholder",
        }
    )

    return state


def planning_node(state: PEIState) -> PEIState:
    """
    Planning node: placeholder for Planning Agent integration.

    In production, this calls PlanificacionAgent.execute(state).
    The agent will implement the 3-phase planning algorithm:
    1. Balance Phase: Assign 1 OT to each cuadrilla
    2. Proximity Phase: Assign remaining OTs to nearest cuadrilla
    3. Normalization: Optimize routes and recalculate centroids

    Args:
        state: Current PEI state

    Returns:
        Updated state with planning results
    """
    logger.info("Planning node: Triggered")

    # Placeholder - in production, this would call PlanificacionAgent
    # from backend.agents.planificacion_agent import PlanificacionAgent
    # agent = PlanificacionAgent(db_session, llm_client)
    # state = await agent.execute(state)

    state["agent_logs"].append(
        {
            "agent": "planning",
            "action": "plan_ots",
            "status": "placeholder",
        }
    )

    return state


def governance_node(state: PEIState) -> PEIState:
    """
    Governance node: placeholder for Governance Agent integration.

    In production, this calls GobernanzaAgent.execute(state).
    The agent will:
    1. Check inactive OTs in DETENIDA status
    2. Send alerts at 20, 25, 29 days
    3. Auto-cancel OTs after 30 days
    4. Check PREPLANIFICADA inactivity (>48 hours)

    Args:
        state: Current PEI state

    Returns:
        Updated state with governance results
    """
    logger.info("Governance node: Triggered")

    # Placeholder - in production, this would call GobernanzaAgent
    # from backend.agents.gobernanza_agent import GobernanzaAgent
    # agent = GobernanzaAgent(db_session, notification_service)
    # state = await agent.execute(state)

    state["agent_logs"].append(
        {
            "agent": "governance",
            "action": "check_inactivity",
            "status": "placeholder",
        }
    )

    return state


def communication_node(state: PEIState) -> PEIState:
    """
    Communication node: placeholder for Communication Agent integration.

    In production, this calls ComunicacionAgent.execute(state).
    The agent will:
    1. Format notification messages
    2. Route to EMAIL or TELEGRAM
    3. Handle batching and rate limiting
    4. Log all sent notifications

    Args:
        state: Current PEI state

    Returns:
        Updated state with communication results
    """
    logger.info("Communication node: Triggered")

    # Placeholder - in production, this would call ComunicacionAgent
    # from backend.agents.comunicacion_agent import ComunicacionAgent
    # agent = ComunicacionAgent(notification_service)
    # state = await agent.execute(state)

    state["agent_logs"].append(
        {
            "agent": "communication",
            "action": "send_notifications",
            "status": "placeholder",
        }
    )

    return state


def end_node(state: PEIState) -> PEIState:
    """
    End node: finalize and return results.

    This node is called when the workflow completes.
    It ensures all results are properly formatted.

    Args:
        state: Current PEI state

    Returns:
        Final state with all results
    """
    logger.info("End node: Workflow completed")

    state["agent_logs"].append(
        {
            "agent": "system",
            "action": "workflow_completed",
            "total_logs": len(state.get("agent_logs", [])),
        }
    )

    return state


# Create and compile the StateGraph
def create_graph():
    """
    Create and compile the PEI agent graph.

    Returns:
        Compiled LangGraph StateGraph for agent orchestration
    """
    logger.info("Creating PEI agent graph")

    # Create StateGraph with PEIState
    graph = StateGraph(PEIState)

    # Add nodes
    graph.add_node("router_node", router_node)
    graph.add_node("ots_ingestion_node", ots_ingestion_node)
    graph.add_node("planning_node", planning_node)
    graph.add_node("governance_node", governance_node)
    graph.add_node("communication_node", communication_node)
    graph.add_node("end_node", end_node)

    # Set entry point
    graph.set_entry_point("router_node")

    # Add conditional edges from router to appropriate nodes
    graph.add_conditional_edges(
        "router_node",
        route_action,
        {
            "ots_ingestion_node": "ots_ingestion_node",
            "planning_node": "planning_node",
            "governance_node": "governance_node",
            "communication_node": "communication_node",
            "end_node": "end_node",
        },
    )

    # Add edges from each agent node to end_node
    graph.add_edge("ots_ingestion_node", "end_node")
    graph.add_edge("planning_node", "end_node")
    graph.add_edge("governance_node", "end_node")
    graph.add_edge("communication_node", "end_node")

    # End node finishes execution
    graph.add_edge("end_node", END)

    # Compile the graph
    app = graph.compile()

    logger.info("PEI agent graph compiled successfully")

    return app


# Create the app instance
app = create_graph()

# Export for use in main.py and API routes
__all__ = ["PEIState", "app", "route_action", "create_graph"]

