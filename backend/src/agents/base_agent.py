"""
Base agent class for PEI Platform agent hierarchy.

This module defines the BaseAgent abstract class that all specialized agents
inherit from. It provides common functionality for LLM initialization, state
management, and action logging.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.state import PEIState
from src.config.settings import settings
from src.models import AgentLog

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all PEI agents.

    All agents (RouterAgent, OTSAgent, PlanificacionAgent, GobernanzaAgent,
    ComunicacionAgent) inherit from this class and implement the abstract
    process() method.

    Attributes:
        db (AsyncSession): Database session for persistence
        llm: Language model instance (ChatOpenAI by default)
        agent_name (str): Name of the agent (set by subclasses)
    """

    def __init__(
        self,
        db: AsyncSession,
        llm=None,
        agent_name: str = "BaseAgent",
    ):
        """
        Initialize the base agent.

        Args:
            db (AsyncSession): Database session for this agent
            llm (optional): Language model instance. If None, initializes
                ChatOpenAI(model='gpt-4', temperature=0)
            agent_name (str): Name of the agent (overridden in subclasses)
        """
        self.db = db
        self.agent_name = agent_name
        logger.info(f"Initializing {agent_name}")

        # Initialize LLM if not provided
        if llm is None:
            try:
                from langchain_openai import ChatOpenAI

                self.llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=0,
                    openai_api_key=settings.openai_api_key,
                )
                logger.info(f"{agent_name}: ChatOpenAI LLM initialized")
            except ImportError:
                logger.warning(
                    f"{agent_name}: langchain_openai not available, LLM will be None"
                )
                self.llm = None
            except Exception as e:
                logger.error(
                    f"{agent_name}: Error initializing ChatOpenAI: {str(e)}"
                )
                self.llm = None
        else:
            self.llm = llm

    @abstractmethod
    async def process(self, state: PEIState) -> PEIState:
        """
        Process the workflow state.

        This is the main method that agents implement. It receives the current
        state, processes it according to the agent's logic, and returns the
        modified state.

        Args:
            state (PEIState): Current workflow state

        Returns:
            PEIState: Modified state to pass to next agent

        Example implementation in subclass:
            async def process(self, state: PEIState) -> PEIState:
                # Process state
                state['agent_messages'].append({
                    'agent': self.agent_name,
                    'content': 'Processing...'
                })
                # Return modified state
                return state
        """
        pass

    async def log_action(
        self,
        ot_id: Optional[int] = None,
        accion: str = "",
        resultado: str = "SUCCESS",
        raw_llm_response: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> AgentLog:
        """
        Log an agent action to the database.

        Creates an AgentLog entry to track what the agent did, the result,
        and any relevant metadata for debugging and audit purposes.

        Args:
            ot_id (int, optional): ID of the OT being processed (if applicable)
            accion (str): Description of the action performed
            resultado (str): Result of the action (SUCCESS, FAILURE, WARNING)
            raw_llm_response (dict, optional): Raw response from LLM if used
            metadata (dict, optional): Additional metadata to store

        Returns:
            AgentLog: Created log entry

        Example:
            await agent.log_action(
                ot_id=1,
                accion="Asignación exitosa - Centroide: 2.5 km",
                resultado="SUCCESS",
                metadata={"centroid_distance": 2.5}
            )
        """
        try:
            log_entry = AgentLog(
                ot_id=ot_id,
                agent_name=self.agent_name,
                accion=accion,
                resultado=resultado,
                raw_llm_response=raw_llm_response,
                metadata=metadata or {},
                timestamp=datetime.utcnow(),
            )

            self.db.add(log_entry)
            await self.db.commit()

            logger.info(
                f"{self.agent_name}: Logged action - "
                f"OT {ot_id}, Result: {resultado}"
            )
            return log_entry

        except Exception as e:
            logger.error(
                f"{self.agent_name}: Error logging action: {str(e)}"
            )
            await self.db.rollback()
            raise

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for this agent's LLM.

        Subclasses should override this method to provide agent-specific
        system instructions that guide the LLM behavior.

        Returns:
            str: System prompt text

        Example implementation in subclass:
            def _create_system_prompt(self) -> str:
                return '''You are the OTS Agent for the PEI system.
                Your responsibility is to:
                1. Fetch OTs from the external API
                2. Validate geographic coordinates
                3. Create OT records in the database
                Always ensure 100% field mapping.'''
        """
        return f"""You are the {self.agent_name} for the PEI Agent Platform.
You are part of a multi-agent system for managing work orders (OTs).
Process the input state and return the modified state.
Be precise and follow the business rules strictly."""

    async def validate_state(self, state: PEIState) -> bool:
        """
        Validate that the state has the necessary information for this agent.

        Subclasses can override this to check for required state fields
        before processing.

        Args:
            state (PEIState): State to validate

        Returns:
            bool: True if state is valid for this agent, False otherwise
        """
        if not isinstance(state, dict):
            logger.error(f"{self.agent_name}: Invalid state type: {type(state)}")
            return False

        required_fields = ["input", "agent_messages", "metadata"]
        for field in required_fields:
            if field not in state:
                logger.error(f"{self.agent_name}: Missing required field: {field}")
                return False

        return True

    async def handle_error(
        self, state: PEIState, error_msg: str
    ) -> PEIState:
        """
        Handle errors that occur during processing.

        Logs the error and sets the error state.

        Args:
            state (PEIState): Current state
            error_msg (str): Error message

        Returns:
            PEIState: Updated state with error information
        """
        logger.error(f"{self.agent_name}: Error - {error_msg}")

        state["error"] = error_msg
        state["action_result"] = {
            "success": False,
            "message": error_msg,
        }

        # Log error action
        await self.log_action(
            accion=f"Error: {error_msg}",
            resultado="FAILURE",
        )

        return state

    def __repr__(self) -> str:
        """String representation of agent instance."""
        return f"<{self.__class__.__name__}(agent_name={self.agent_name})>"

