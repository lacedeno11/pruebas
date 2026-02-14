"""
PEI LangGraph Workflow Definition.

This module defines the complete multi-agent workflow using LangGraph.
The graph orchestrates 5 specialized agents that work together to manage
the OT (work order) lifecycle:

1. RouterAgent: Classifies user intent and routes to appropriate agent
2. OTSAgent: Ingests new OTs from external API
3. PlanificacionAgent: Assigns OTs to cuadrillas
4. GobernanzaAgent: Enforces governance rules and validates transitions
5. ComunicacionAgent: Sends notifications to stakeholders

The workflow follows a conditional routing pattern where the RouterAgent
determines which specialized agent should handle the request.
"""

import logging
from typing import Callable

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_agent import BaseAgent
from src.agents.comunicacion_agent import ComunicacionAgent
from src.agents.gobernanza_agent import GobernanzaAgent
from src.agents.ots_agent import OTSAgent
from src.agents.planificacion_agent import PlanificacionAgent
from src.agents.router_agent import RouterAgent
from src.agents.state import PEIState

logger = logging.getLogger(__name__)


async def create_pei_graph(db: AsyncSession) -> StateGraph:
    """
    Create and return the compiled PEI agent workflow graph.

    This function sets up the complete multi-agent workflow with:
    - 5 agent nodes (router, ots, planificacion, gobernanza, comunicacion)
    - Conditional routing based on RouterAgent classification
    - Proper state management with PEIState TypedDict
    - Error handling and logging throughout

    Args:
        db (AsyncSession): Database session for all agents

    Returns:
        StateGraph: Compiled graph ready for execution

    Workflow Diagram:
        START
         ↓
        router (RouterAgent)
         ↓
        [conditional routing based on metadata['route']]
         ├─→ ingest_ots → ots (OTSAgent) → comunicacion (ComunicacionAgent) → END
         ├─→ plan_ots → planificacion (PlanificacionAgent) → END
         ├─→ check_governance → gobernanza (GobernanzaAgent) → comunicacion → END
         └─→ manual_transition → gobernanza (GobernanzaAgent) → comunicacion → END
    """
    try:
        logger.info("Creating PEI LangGraph workflow")

        # Instantiate all 5 agents with database session
        router_agent = RouterAgent(db)
        ots_agent = OTSAgent(db)
        planificacion_agent = PlanificacionAgent(db)
        gobernanza_agent = GobernanzaAgent(db)
        comunicacion_agent = ComunicacionAgent(db)

        logger.info("Instantiated all 5 agents")

        # Create StateGraph with PEIState schema
        graph = StateGraph(PEIState)

        # Add agent nodes
        graph.add_node("router", router_agent.process)
        graph.add_node("ots", ots_agent.process)
        graph.add_node("planificacion", planificacion_agent.process)
        graph.add_node("gobernanza", gobernanza_agent.process)
        graph.add_node("comunicacion", comunicacion_agent.process)

        logger.info("Added 5 agent nodes to graph")

        # Define conditional routing function
        def route_after_router(state: PEIState) -> str:
            """
            Determine which agent should process based on RouterAgent's classification.

            Args:
                state (PEIState): Current workflow state with routing decision

            Returns:
                str: Name of next node to execute
            """
            route = state.get("metadata", {}).get("route", "query_status")

            # Route to appropriate agent based on classification
            if route == "ingest_ots":
                logger.debug("Routing to OTSAgent for OT ingestion")
                return "ots"
            elif route == "plan_ots":
                logger.debug("Routing to PlanificacionAgent for planning")
                return "planificacion"
            elif route == "check_governance":
                logger.debug("Routing to GobernanzaAgent for governance check")
                return "gobernanza"
            elif route == "manual_transition":
                logger.debug("Routing to GobernanzaAgent for transition validation")
                return "gobernanza"
            else:
                # query_status or unknown: end workflow (would be dashboard endpoint)
                logger.debug(f"Route '{route}' - ending workflow (query handled by API)")
                return END

        logger.info("Defined conditional routing function")

        # Add edges (connections between nodes)
        # START → router (entry point)
        graph.add_edge(START, "router")
        logger.debug("Added edge: START → router")

        # router → conditional routing
        graph.add_conditional_edges(
            "router",
            route_after_router,
            {
                "ots": "ots",
                "planificacion": "planificacion",
                "gobernanza": "gobernanza",
                END: END,
            },
        )
        logger.debug("Added conditional edges from router")

        # OTSAgent → ComunicacionAgent (notify about ingestion)
        graph.add_edge("ots", "comunicacion")
        logger.debug("Added edge: ots → comunicacion")

        # ComunicacionAgent → END
        graph.add_edge("comunicacion", END)
        logger.debug("Added edge: comunicacion → END")

        # PlanificacionAgent → END (no additional notifications needed)
        graph.add_edge("planificacion", END)
        logger.debug("Added edge: planificacion → END")

        # GobernanzaAgent → ComunicacionAgent (notify about governance actions)
        graph.add_edge("gobernanza", "comunicacion")
        logger.debug("Added edge: gobernanza → comunicacion")

        # Compile the graph
        compiled_graph = graph.compile()
        logger.info("Successfully compiled PEI LangGraph workflow")

        return compiled_graph

    except Exception as e:
        logger.error(f"Error creating PEI graph: {str(e)}", exc_info=True)
        raise


def get_routing_description(route: str) -> str:
    """
    Get human-readable description of a routing decision.

    Args:
        route (str): Route classification from RouterAgent

    Returns:
        str: Description of what will happen
    """
    descriptions = {
        "ingest_ots": "Download and ingest new work orders from external API",
        "plan_ots": "Assign work orders to cuadrillas using planning algorithm",
        "check_governance": "Review governance alerts and auto-cancellations",
        "manual_transition": "Validate and execute manual status change",
        "query_status": "Query work order status (handled by API)",
    }
    return descriptions.get(route, "Unknown operation")


def get_node_description(node: str) -> str:
    """
    Get human-readable description of an agent node.

    Args:
        node (str): Node name in graph

    Returns:
        str: Description of agent responsibilities
    """
    descriptions = {
        "router": "RouterAgent - Classifies user intent and routes request",
        "ots": "OTSAgent - Fetches and ingests OTs from external API",
        "planificacion": "PlanificacionAgent - Assigns OTs to cuadrillas",
        "gobernanza": "GobernanzaAgent - Enforces business rules and governance",
        "comunicacion": "ComunicacionAgent - Sends notifications to stakeholders",
    }
    return descriptions.get(node, "Unknown node")


# Graph execution reference for documentation
"""
WORKFLOW EXECUTION PATHS:

Path 1: OT Ingestion (UC-PEI-01)
--------------------------------
Input: "Download new OTs" or similar
1. RouterAgent: Classifies as 'ingest_ots' (confidence: 0.9)
2. OTSAgent: Fetches OTs from API, validates coordinates
   - Marks ERROR_GEO for invalid coordinates
   - Creates database records with status=PREPLANIFICADA
   - Updates state.ots_to_process
3. ComunicacionAgent: Sends notifications
   - GEO_ERROR alerts to project managers
4. END: Returns with ingestion results

Path 2: OT Planning (UC-PEI-02)
-------------------------------
Input: "Plan OTs" or similar
1. RouterAgent: Classifies as 'plan_ots' (confidence: 0.9)
2. PlanificacionAgent: Assigns OTs to cuadrillas
   - Phase 1: Balance load across teams
   - Phase 2: Proximity-based assignment (<10km)
   - Phase 3: Nightly normalization (scheduled)
   - Updates status to PLANIFICADA
3. END: Returns with assignment results

Path 3: Governance Check (UC-PEI-08)
------------------------------------
Input: "Check alerts" or similar
1. RouterAgent: Classifies as 'check_governance' (confidence: 0.85)
2. GobernanzaAgent: Monitors OT status
   - Detention monitoring: alerts at days 20, 25, 29; auto-cancel at day 30
   - Preplanificada timeout: alerts for OTs >48 hours
   - Document validation: ensures PUBLICO projects have 29 docs
3. ComunicacionAgent: Sends alerts
   - Detention alerts to coordinator
   - Preplanificada alerts to coordinator
4. END: Returns with governance check results

Path 4: Manual Transition (UC-PEI-13)
-------------------------------------
Input: "Mark OT as detained" with reason
1. RouterAgent: Classifies as 'manual_transition' (confidence: 0.85)
2. GobernanzaAgent: Validates transition
   - Checks state machine rules
   - For DETENIDA: requires reason (min 10 chars)
   - For FINALIZADA: validates 29 documents for PUBLICO
3. ComunicacionAgent: Sends notifications
   - Status change email to project manager
4. END: Returns validation result

Path 5: Query (Dashboard)
------------------------
Input: "Show OT list" or similar
1. RouterAgent: Classifies as 'query_status' (confidence: 0.5-0.75)
2. END: Routes to REST API endpoint for data retrieval
   - Handled by dashboard_endpoints.py
   - Returns filtered/aggregated OT data
"""

