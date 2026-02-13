"""LangGraph state graph definition for PEI Agéntico workflow orchestration."""

from langgraph.graph import StateGraph, END
from backend.graph.state import PEIState, ActionType
import logging

# Configure logging
logger = logging.getLogger(__name__)


# Define node functions (these will be imported from agent modules once created)
# For now, we use stub implementations to allow workflow compilation

async def router_node(state: PEIState) -> PEIState:
    """
    Router node that classifies incoming requests into actions.
    
    TODO: Replace with actual implementation from backend.agents.router_agent
    
    Args:
        state: Current PEIState
    
    Returns:
        Updated PEIState with action classified
    """
    logger.info(f"Router node processing: action={state.get('action')}")
    # Stub implementation - will be replaced with LLM-based routing
    return state


async def ots_ingest_node(state: PEIState) -> PEIState:
    """
    OTS ingestion node that fetches and validates work orders.
    
    TODO: Replace with actual implementation from backend.agents.ots_agent
    
    Responsibilities:
    - Fetch OTs from TELCOS API (or mock service)
    - Validate geographic coordinates
    - Check for duplicates
    - Create OT records in database
    - Log errors and notify PM
    
    Args:
        state: Current PEIState with INGEST action
    
    Returns:
        Updated PEIState with ingestion results
    """
    logger.info("OTS Ingest node processing")
    # Stub implementation - will be replaced with actual ingestion logic
    return state


async def planning_node(state: PEIState) -> PEIState:
    """
    Planning node that implements 3-phase assignment algorithm.
    
    TODO: Replace with actual implementation from backend.agents.planificacion_agent
    
    Responsibilities:
    - Phase 1: Initial Balance (assign 1 OT per crew, prioritize PUBLICO)
    - Phase 2: Centroid Proximity (assign within 10km, max capacity)
    - Phase 3: Route Optimization (nightly centroid recalculation)
    
    Args:
        state: Current PEIState with PLAN action
    
    Returns:
        Updated PEIState with assignment results
    """
    logger.info("Planning node processing")
    # Stub implementation - will be replaced with actual planning algorithm
    return state


async def validation_node(state: PEIState) -> PEIState:
    """
    Validation node that checks business rules and constraints.
    
    TODO: Implement validation node
    
    Responsibilities:
    - Validate state transitions
    - Check crew capacity and distance
    - Validate PUBLICO document requirements
    - Update validation_result in state
    
    Args:
        state: Current PEIState with VALIDATE action
    
    Returns:
        Updated PEIState with validation results
    """
    logger.info("Validation node processing")
    # Stub implementation - validation happens in route handlers for now
    return state


async def governance_node(state: PEIState) -> PEIState:
    """
    Governance node that enforces business rules.
    
    TODO: Replace with actual implementation from backend.agents.gobernanza_agent
    
    Responsibilities:
    - 48h PREPLANIFICADA alert
    - 30-day DETENIDA auto-cancellation
    - Progressive escalating alerts (20d, 25d, 29d)
    - Log governance actions
    
    Args:
        state: Current PEIState with GOVERNANCE action
    
    Returns:
        Updated PEIState with governance actions executed
    """
    logger.info("Governance node processing")
    # Stub implementation - will be replaced with governance checks
    return state


async def communication_node(state: PEIState) -> PEIState:
    """
    Communication node that sends notifications.
    
    TODO: Replace with actual implementation from backend.agents.comunicacion_agent
    
    Responsibilities:
    - Parse agent_responses to determine notification type
    - Send Telegram notifications with emoji indicators
    - Send HTML email notifications
    - Log all sent notifications
    - Implement retry logic (max 3 attempts)
    
    Args:
        state: Current PEIState with NOTIFY action
    
    Returns:
        Updated PEIState with notifications sent
    """
    logger.info("Communication node processing")
    # Stub implementation - will be replaced with notification logic
    return state


async def end_node(state: PEIState) -> PEIState:
    """
    End node that finalizes workflow execution.
    
    Logs workflow completion and error state if applicable.
    
    Args:
        state: Final PEIState after workflow execution
    
    Returns:
        Unchanged PEIState (terminal node)
    """
    if state.get("error"):
        logger.error(f"Workflow ended with error: {state['error']}")
    else:
        logger.info("Workflow completed successfully")
    return state


def _route_on_action(state: PEIState) -> str:
    """
    Conditional edge function that routes based on action.
    
    Args:
        state: Current PEIState
    
    Returns:
        str: Next node name to execute
    """
    action = state.get("action", "")
    
    if action == ActionType.INGEST.value:
        return "ots_ingest"
    elif action == ActionType.PLAN.value:
        return "planning"
    elif action == ActionType.VALIDATE.value:
        return "validation"
    elif action == ActionType.GOVERNANCE.value:
        return "governance"
    elif action == ActionType.NOTIFY.value:
        return "communication"
    elif action == ActionType.CHAT.value:
        # Chat actions go directly to communication for response
        return "communication"
    else:
        logger.warning(f"Unknown action: {action}")
        return "end"


def create_workflow():
    """
    Create and compile the LangGraph state graph.
    
    The workflow follows this pattern:
    
    START → router → [branching based on action]
                    ├→ ots_ingest → end
                    ├→ planning → end
                    ├→ validation → end
                    ├→ governance → communication → end
                    └→ communication → end
    
    All paths eventually reach the 'end' node which logs completion.
    
    Returns:
        Compiled LangGraph graph for workflow execution
    """
    # Create state graph
    workflow = StateGraph(PEIState)
    
    # Define all nodes
    workflow.add_node("router", router_node)
    workflow.add_node("ots_ingest", ots_ingest_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("governance", governance_node)
    workflow.add_node("communication", communication_node)
    workflow.add_node("end", end_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Add conditional edges from router based on action
    workflow.add_conditional_edges(
        "router",
        _route_on_action,
        {
            "ots_ingest": "ots_ingest",
            "planning": "planning",
            "validation": "validation",
            "governance": "governance",
            "communication": "communication",
            "end": "end",
        }
    )
    
    # Add edges from processing nodes to end
    workflow.add_edge("ots_ingest", "end")
    workflow.add_edge("planning", "end")
    workflow.add_edge("validation", "end")
    workflow.add_edge("governance", "communication")
    workflow.add_edge("communication", "end")
    
    # Compile the graph
    graph = workflow.compile()
    
    return graph


# Create and export the compiled workflow
pei_workflow = create_workflow()


def visualize_workflow(output_path: str = "backend/graph/workflow.png"):
    """
    Generate a visualization of the workflow graph.
    
    Args:
        output_path: Path where to save the PNG image
    
    Returns:
        bool: True if visualization succeeded, False otherwise
    """
    try:
        # Try to generate visualization using graphviz
        # This requires graphviz to be installed: pip install graphviz
        png_data = pei_workflow.get_graph().draw_mermaid_png()
        
        with open(output_path, "wb") as f:
            f.write(png_data)
        
        logger.info(f"Workflow visualization saved to {output_path}")
        return True
    except Exception as e:
        logger.warning(f"Could not generate workflow visualization: {e}")
        logger.info("Install graphviz for visualization: pip install graphviz")
        return False


# Optionally generate visualization on import
if __name__ == "__main__":
    # Generate visualization if run as main
    visualize_workflow()

