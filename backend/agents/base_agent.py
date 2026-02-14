"""
Base agent class for PEI Platform agentic system.
Provides abstract base class for all agents to inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.models import LogAgente
from backend.models.log_agente import ActionResult


class BaseAgent(ABC):
    """
    Abstract base class for all PEI Platform agents.
    
    All agents (RouterAgent, OTSAgent, PlanificacionAgent, GobernanzaAgent, ComunicacionAgent)
    inherit from this class and implement the execute() method.
    
    Provides common functionality:
    - LLM access for all agents
    - Database session management
    - Action logging via _log_action() helper method
    
    Attributes:
        llm: ChatOpenAI LLM instance for language model operations
        db_session: SQLAlchemy database session for ORM operations
        agent_name: Name of the agent (set by subclasses)
    """

    def __init__(self, llm: ChatOpenAI, db_session: Session):
        """
        Initialize the BaseAgent with LLM and database session.
        
        Args:
            llm: ChatOpenAI instance for LLM operations (routing, analysis, etc.)
            db_session: SQLAlchemy Session for database operations
        """
        self.llm = llm
        self.db_session = db_session
        self.agent_name = self.__class__.__name__

    @abstractmethod
    async def execute(self, state: Dict) -> Dict:
        """
        Execute the agent's main logic.
        
        This method is implemented by all subclasses to define agent-specific behavior.
        
        Args:
            state: Dictionary containing the current state flowing through LangGraph.
                   Common fields:
                   - user_input (str): User input text
                   - event_type (str): Type of event (e.g., 'user_input', 'scheduled_governance')
                   - ot_data (dict): OT-related data
                   - current_ot_id (int or None): Current OT being processed
                   - cuadrilla_id (int or None): Current Cuadrilla being processed
                   - action_result (str): Result of action
                   - error_message (str or None): Error message if any
                   - agent_logs (list): List of agent execution logs
                   - next_agent (str or None): Next agent to execute
        
        Returns:
            Dictionary containing updated state with results of agent execution.
            Must include at least:
            - action_result (str): Description of action result
            - agent_logs (list): Updated logs from execution
        
        Raises:
            NotImplementedError: If not overridden by subclass
        """
        raise NotImplementedError(
            f"Agent {self.agent_name} must implement execute() method"
        )

    def _log_action(
        self,
        agente_name: str,
        accion: str,
        resultado: ActionResult,
        ot_id: Optional[int] = None,
        raw_response: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> LogAgente:
        """
        Log an agent action to the database.
        
        Creates a LogAgente record documenting the action taken by the agent.
        Used to track agent execution history, debugging, and audit trail.
        
        Args:
            agente_name: Name of the agent performing the action (e.g., 'OTSAgent')
            accion: Description of the action (e.g., 'fetch_ots', 'assign_ot_to_cuadrilla')
            resultado: Result status (ActionResult.SUCCESS, ActionResult.FAILURE, ActionResult.PENDING)
            ot_id: Optional ID of the OT being processed
            raw_response: Optional raw LLM response or API response for debugging
            metadata: Optional dictionary with additional context (e.g., assignment details)
        
        Returns:
            LogAgente instance that was persisted to the database
            
        Example:
            >>> log = agent._log_action(
            ...     agente_name='OTSAgent',
            ...     accion='fetch_ots_from_telcos',
            ...     resultado=ActionResult.SUCCESS,
            ...     ot_id=None,
            ...     metadata={'ot_count': 18, 'geo_errors': 2}
            ... )
        """
        # Create new LogAgente record
        log_entry = LogAgente(
            ot_id=ot_id,
            agente_name=agente_name,
            accion=accion,
            resultado=resultado,
            raw_llm_response=raw_response,
            metadata=metadata,
        )

        # Persist to database
        self.db_session.add(log_entry)
        try:
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            print(f"⚠️ Error logging action: {str(e)}")
            raise

        return log_entry

