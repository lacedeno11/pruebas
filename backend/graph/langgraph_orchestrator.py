"""
LangGraph orchestrator - Multi-agent workflow orchestration.
Defines StateGraph with all agents and conditional routing logic.
"""

import logging
from typing import Any, Dict, Optional

from backend.agents.router_agent import RouterAgent
from backend.agents.ots_agent import OTSAgent
from backend.agents.planificacion_agent import PlanificacionAgent
from backend.agents.gobernanza_agent import GobernanzaAgent
from backend.agents.comunicacion_agent import ComunicacionAgent
from backend.config import Settings
from backend.graph.state import AgentState

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Multi-agent workflow orchestrator using LangGraph StateGraph.
    
    Orchestration Flow:
    1. RouterAgent classifies input
    2. Conditional routing to specialized agents
    3. Agents execute and return results
    4. ComunicacionAgent handles notifications
    5. Return final results to user
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_session: Optional[Any] = None,
    ):
        """
        Initialize orchestrator with settings and database session.

        Args:
            settings: Application settings
            db_session: AsyncSession for database operations
        """
        self.settings = settings or Settings()
        self.db_session = db_session
        self.router_agent = RouterAgent()
        # Additional agent instances would be initialized here

    async def run_workflow(self, user_input: str) -> Dict[str, Any]:
        """
        Execute complete agent workflow for user input.
        
        Args:
            user_input: User message or system event
            
        Returns:
            Dictionary with workflow results
        """
        logger.info(f"AgentOrchestrator: Starting workflow for input: {user_input[:50]}...")
        
        try:
            # Step 1: Classify input
            classification = await self.router_agent.classify_input(user_input)
            logger.info(f"AgentOrchestrator: Input classified as {classification}")

            # Step 2: Route to appropriate agent
            result = await self.route_to_agent(classification, user_input)

            # Step 3: Prepare response
            response = {
                "status": "success",
                "classification": classification,
                "result": result,
                "message": self.format_response(classification, result),
            }

            return response

        except Exception as e:
            logger.error(f"AgentOrchestrator: Error in workflow: {str(e)}")
            return {
                "status": "error",
                "classification": "UNKNOWN",
                "result": None,
                "message": f"Workflow error: {str(e)}",
                "error": str(e),
            }

    async def route_to_agent(self, classification: str, user_input: str) -> Dict[str, Any]:
        """
        Route to appropriate agent based on classification.
        
        Args:
            classification: Router classification
            user_input: User input message
            
        Returns:
            Result from specialized agent
        """
        logger.info(f"AgentOrchestrator: Routing to {classification} agent")
        
        try:
            if classification == "INGEST_OT":
                # Trigger OTSAgent
                ots_agent = OTSAgent(
                    telcos_client=None,  # Would be injected
                    db_session=self.db_session,
                )
                return await ots_agent.ingest_ots()

            elif classification == "PLAN_OTS":
                # Trigger PlanificacionAgent
                planning_agent = PlanificacionAgent(
                    db_session=self.db_session,
                )
                return await planning_agent.plan_ots()

            elif classification == "CHECK_STATUS":
                # Trigger GobernanzaAgent
                governance_agent = GobernanzaAgent(
                    db_session=self.db_session,
                )
                return await governance_agent.check_inactive_ots()

            elif classification == "MANUAL_ASSIGNMENT":
                # Parse input for OT and crew IDs, then trigger assignment
                return {
                    "status": "pending",
                    "message": "Manual assignment requires OT ID and Crew ID",
                }

            else:  # QUERY or unknown
                return {
                    "status": "success",
                    "message": f"Query response for: {user_input[:100]}",
                }

        except Exception as e:
            logger.error(f"AgentOrchestrator: Error routing to agent: {str(e)}")
            return {
                "status": "error",
                "message": f"Agent execution failed: {str(e)}",
            }

    def format_response(self, classification: str, result: Dict[str, Any]) -> str:
        """
        Format agent result into user-friendly message.
        
        Args:
            classification: Agent classification
            result: Agent result dictionary
            
        Returns:
            Formatted message string
        """
        if isinstance(result, dict) and "summary" in result:
            return result["summary"]
        elif isinstance(result, dict) and "message" in result:
            return result["message"]
        else:
            return f"Completed {classification}"


# Global orchestrator instance (would be initialized with settings/db_session)
_orchestrator = None


async def get_orchestrator(
    settings: Optional[Settings] = None,
    db_session: Optional[Any] = None,
) -> AgentOrchestrator:
    """
    Get or create global orchestrator instance.
    
    Args:
        settings: Application settings
        db_session: Database session
        
    Returns:
        AgentOrchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator(settings=settings, db_session=db_session)
    
    return _orchestrator


async def run_agent_workflow(
    user_input: str,
    settings: Optional[Settings] = None,
    db_session: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main entry point for running agent workflow.
    
    Args:
        user_input: User message
        settings: Application settings
        db_session: Database session
        
    Returns:
        Workflow result dictionary
    """
    orchestrator = await get_orchestrator(settings, db_session)
    return await orchestrator.run_workflow(user_input)


def create_agent_graph():
    """
    Create LangGraph StateGraph with all agents.
    
    This is a placeholder for full LangGraph integration.
    Currently returns simplified orchestrator.
    
    Returns:
        AgentOrchestrator instance (would return compiled StateGraph)
    """
    logger.info("Creating agent graph")
    # TODO: Implement full LangGraph StateGraph
    # from langgraph.graph import StateGraph, END
    # graph = StateGraph(AgentState)
    # ... add nodes and edges ...
    # return graph.compile()
    return AgentOrchestrator()

