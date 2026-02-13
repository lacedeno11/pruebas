from langgraph.graph import StateGraph, START, END
from app.agents.state import PEIState
from app.agents.router_agent import RouterAgent
from app.agents.ots_agent import OTSAgent
from app.agents.planificacion_agent import PlanificacionAgent
from app.agents.gobernanza_agent import GobernanzaAgent
from app.agents.comunicacion_agent import ComunicacionAgent


def create_pei_graph():
    """
    Create and compile the PEI LangGraph workflow
    
    Workflow structure:
    START -> router_node -> (ots_node | planificacion_node | gobernanza_node | comunicacion_node) -> comunicacion_node -> END
    
    The router agent classifies user intent and routes to appropriate agents.
    All non-comunicacion agents eventually feed into comunicacion agent for notifications.
    
    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    
    # Initialize agents
    router_agent = RouterAgent()
    ots_agent = OTSAgent()
    planificacion_agent = PlanificacionAgent()
    gobernanza_agent = GobernanzaAgent()
    comunicacion_agent = ComunicacionAgent()
    
    # Create state graph
    workflow = StateGraph(PEIState)
    
    # Add agent nodes
    workflow.add_node("router", router_agent.classify_input)
    workflow.add_node("ots", ots_agent.process_ots)
    workflow.add_node("planificacion", planificacion_agent.assign_ots)
    workflow.add_node("gobernanza", gobernanza_agent.check_governance_rules)
    workflow.add_node("comunicacion", comunicacion_agent.send_notifications)
    
    # Add edges from START to router
    workflow.add_edge(START, "router")
    
    # Add conditional edges from router to other agents based on action
    def route_action(state: PEIState) -> str:
        """
        Route to appropriate agent based on classified action
        """
        action = state.get("action", "").lower()
        
        if action == "sync_ots":
            return "ots"
        elif action == "plan_assignment":
            return "planificacion"
        elif action == "check_governance":
            return "gobernanza"
        elif action == "send_notification":
            return "comunicacion"
        elif action == "query_status":
            # For query_status, send to comunicacion to format response
            return "comunicacion"
        else:
            # Default to comunicacion if action not recognized
            return "comunicacion"
    
    workflow.add_conditional_edges("router", route_action)
    
    # Add edges from all agents to comunicacion (for notification sending)
    workflow.add_edge("ots", "comunicacion")
    workflow.add_edge("planificacion", "comunicacion")
    workflow.add_edge("gobernanza", "comunicacion")
    
    # Add edge from comunicacion to END
    workflow.add_edge("comunicacion", END)
    
    # Compile the graph
    graph = workflow.compile()
    
    return graph


def should_continue_to_communication(state: PEIState) -> bool:
    """
    Determine if workflow should continue to communication agent
    Always true - all agents should eventually notify
    """
    return True


def should_route_to_ots(state: PEIState) -> bool:
    """Check if action is sync_ots"""
    return state.get("action", "").lower() == "sync_ots"


def should_route_to_planificacion(state: PEIState) -> bool:
    """Check if action is plan_assignment"""
    return state.get("action", "").lower() == "plan_assignment"


def should_route_to_gobernanza(state: PEIState) -> bool:
    """Check if action is check_governance"""
    return state.get("action", "").lower() == "check_governance"


def should_route_to_comunicacion(state: PEIState) -> bool:
    """Check if action is send_notification or query_status"""
    action = state.get("action", "").lower()
    return action in ["send_notification", "query_status"]

