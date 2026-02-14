"""
LangGraph StateGraph orchestration for PEI Platform agentic system.
Defines the complete workflow graph connecting all 5 agents with proper routing logic.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.language_model import BaseLanguageModel
from sqlalchemy.orm import Session

from backend.agents.graph_state import PEIGraphState
from backend.agents.base_agent import BaseAgent
from backend.agents.router_agent import RouterAgent
from backend.agents.ots_agent import OTSAgent
from backend.agents.planificacion_agent import PlanificacionAgent
from backend.agents.gobernanza_agent import GobernanzaAgent
from backend.agents.comunicacion_agent import ComunicacionAgent


def create_pei_graph(llm: BaseLanguageModel, db_session: Session):
    """
    Create and compile the PEI Platform LangGraph StateGraph.
    
    This function constructs the complete agentic workflow by:
    1. Instantiating all 5 specialized agents
    2. Creating a StateGraph with PEIGraphState
    3. Adding nodes for each agent
    4. Configuring routing edges between agents
    5. Compiling the graph for execution
    
    The graph follows this flow:
        START
          ↓
        [Router Agent] - Routes incoming requests to appropriate agent
          ↓
        ┌─────────────────────────────────────────┐
        ↓                    ↓          ↓          ↓
    [OTS Agent]    [Planificación]  [Gobernanza]  [Comunicación]
    (sync OTs)       (3-phase plan)  (rules check)  (notifications)
        ↓                    ↓          ↓          ↓
        └─────────────────────────────────────────┘
                          ↓
                  [Comunicación Agent]
                   (send notifications)
                          ↓
                        END
    
    Args:
        llm: ChatOpenAI language model instance for LLM-powered routing
        db_session: SQLAlchemy database session for data persistence
        
    Returns:
        Compiled LangGraph StateGraph instance ready for execution
        
    Raises:
        Exception: If agent instantiation or graph compilation fails
    """
    # Instantiate all 5 agents with LLM and database session
    router_agent = RouterAgent(llm=llm, db_session=db_session)
    ots_agent = OTSAgent(llm=llm, db_session=db_session)
    planificacion_agent = PlanificacionAgent(llm=llm, db_session=db_session)
    gobernanza_agent = GobernanzaAgent(llm=llm, db_session=db_session)
    comunicacion_agent = ComunicacionAgent(llm=llm, db_session=db_session)

    # Create StateGraph with PEIGraphState as state schema
    graph = StateGraph(PEIGraphState)

    # Add nodes for each agent
    # Each node executes the agent's async execute method
    graph.add_node("router", router_agent.execute)
    graph.add_node("ots", ots_agent.execute)
    graph.add_node("planificacion", planificacion_agent.execute)
    graph.add_node("gobernanza", gobernanza_agent.execute)
    graph.add_node("comunicacion", comunicacion_agent.execute)

    # Set entry point: START always routes to Router agent
    graph.set_entry_point("router")

    # Conditional routing from Router Agent
    # Router agent sets state['next_agent'] to one of: 'ots', 'planificacion', 'gobernanza', 'comunicacion', 'end'
    def router_conditional(state: Dict[str, Any]) -> str:
        """
        Route from Router agent to the appropriate agent based on next_agent field.
        
        Args:
            state: Current graph state with next_agent field set by RouterAgent
            
        Returns:
            Next node name to execute: 'ots', 'planificacion', 'gobernanza', 'comunicacion', or END
        """
        next_agent = state.get("next_agent", "end")
        
        # Route to appropriate agent
        if next_agent == "ots":
            return "ots"
        elif next_agent == "planificacion":
            return "planificacion"
        elif next_agent == "gobernanza":
            return "gobernanza"
        elif next_agent == "comunicacion":
            return "comunicacion"
        else:
            # Default to END if no valid next_agent specified
            return END

    # Add conditional edges from router
    # These edges branch based on the router's decision
    graph.add_conditional_edges(
        "router",
        router_conditional,
    )

    # Edges from operational agents to comunicacion agent
    # After each operational agent completes, route to comunicacion for notification handling
    graph.add_edge("ots", "comunicacion")
    graph.add_edge("planificacion", "comunicacion")
    graph.add_edge("gobernanza", "comunicacion")

    # Edge from comunicacion to END
    # After notifications are sent, terminate the workflow
    graph.add_edge("comunicacion", END)

    # Compile the graph into a runnable object
    # Compilation optimizes the graph for execution
    compiled_graph = graph.compile()

    return compiled_graph

