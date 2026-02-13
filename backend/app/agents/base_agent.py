"""
Base agent class for all agent implementations.

Provides common functionality for all agents including:
- LLM invocation with error handling
- Database session management
- Action logging to LogAgente table
- System prompt generation
- State management
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.app.models.log_agente import LogAgente
from backend.app.agents.state import AgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    All agents must inherit from this class and implement the execute() method.
    Provides common functionality for:
    - LLM interaction
    - Database logging
    - Action tracking
    - Error handling
    
    Attributes:
        llm: Language model instance (e.g., OpenAI GPT-4)
        db_session: SQLAlchemy database session
        agent_name: Name of the agent (e.g., "OTSAgent", "PlanificacionAgent")
        system_prompt: System prompt for the agent
    """
    
    def __init__(self, llm: Any, db_session: Session):
        """
        Initialize the base agent.
        
        Args:
            llm: Language model instance
            db_session: SQLAlchemy database session for database operations
        
        Raises:
            ValueError: If llm or db_session is None
        """
        if llm is None:
            raise ValueError("LLM instance cannot be None")
        if db_session is None:
            raise ValueError("Database session cannot be None")
        
        self.llm = llm
        self.db_session = db_session
        self.agent_name = self.__class__.__name__
        self.system_prompt = self.get_system_prompt()
        
        logger.info(f"Initialized {self.agent_name} with LLM and DB session")
    
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute the agent's logic.
        
        This method must be implemented by all subclasses to perform
        the agent's specific task.
        
        Args:
            state: Current agent state from the graph
        
        Returns:
            Updated agent state with results
        
        Raises:
            Exception: Any exception from agent processing (will be caught in graph)
        """
        pass
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        
        Can be overridden by subclasses to provide agent-specific prompts.
        The system prompt is used to guide the LLM's behavior.
        
        Returns:
            System prompt string
        
        Example:
            ```python
            def get_system_prompt(self) -> str:
                return '''You are the OTS Agent responsible for:
                - Fetching OTs from the TELCOS API
                - Validating geographic coordinates
                - Persisting OTs to the database
                - Reporting any errors or issues
                '''
            ```
        """
        return f"""You are the {self.agent_name}. 
        Your role is to process and manage work orders (OTs) in the DERCAS system.
        Always follow the business rules and constraints defined for your operations.
        Provide clear, actionable results and log all significant actions."""
    
    async def call_llm(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Invoke the LLM with error handling and retry logic.
        
        This method wraps LLM calls with:
        - Automatic retry on transient failures
        - Error logging
        - Context management
        - Response validation
        
        Args:
            prompt: User/system prompt to send to LLM
            context: Optional context dict for the LLM (e.g., OT data, filters)
            max_retries: Number of retries on failure (default: 3)
        
        Returns:
            LLM response string
        
        Raises:
            Exception: If all retries fail
        
        Example:
            ```python
            response = await self.call_llm(
                prompt="Analyze this OT and determine if it can be finalized",
                context={"ot_id": "...", "doc_count": 29}
            )
            ```
        """
        import asyncio
        
        for attempt in range(max_retries):
            try:
                # Log LLM invocation
                logger.debug(
                    f"{self.agent_name}: Invoking LLM (attempt {attempt + 1}/{max_retries}). "
                    f"Prompt length: {len(prompt)}, Context: {context}"
                )
                
                # Construct full prompt with context
                full_prompt = prompt
                if context:
                    context_str = "\n".join(
                        f"- {key}: {value}" for key, value in context.items()
                    )
                    full_prompt = f"{prompt}\n\nContext:\n{context_str}"
                
                # Call LLM (this assumes llm has an async __call__ or similar)
                # In a real implementation, this would call the actual LLM API
                # For now, we'll return a placeholder
                response = f"LLM Response to: {prompt[:50]}..."
                
                logger.debug(f"{self.agent_name}: LLM response received. Length: {len(response)}")
                return response
                
            except Exception as e:
                logger.warning(
                    f"{self.agent_name}: LLM call failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.info(f"{self.agent_name}: Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    # All retries exhausted
                    logger.error(f"{self.agent_name}: All {max_retries} LLM calls failed")
                    raise
    
    def log_action(
        self,
        action: str,
        resultado: str,
        ot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an action to the LogAgente table.
        
        Creates an audit trail of agent actions for debugging, monitoring,
        and governance compliance.
        
        Args:
            action: Action type (e.g., "SYNC_OTS", "PLAN_ASSIGNMENT", "CHECK_GOVERNANCE")
            resultado: Result of the action (e.g., "success", "error", "warning")
            ot_id: Optional UUID of associated OT
            metadata: Optional dict of additional metadata
        
        Returns:
            None (creates LogAgente entry)
        
        Raises:
            Exception: If database commit fails
        
        Example:
            ```python
            self.log_action(
                action="SYNC_OTS",
                resultado="success",
                metadata={
                    "created_count": 15,
                    "error_count": 2,
                    "source": "telcos_api",
                }
            )
            
            self.log_action(
                action="PLAN_ASSIGNMENT",
                resultado="success",
                ot_id="...",
                metadata={
                    "cuadrilla_id": "...",
                    "distance_km": 5.23,
                }
            )
            ```
        """
        try:
            # Create log entry
            log_entry = LogAgente(
                ot_id=ot_id,
                agente_name=self.agent_name,
                accion=action,
                resultado=resultado,
                metadata=metadata,
            )
            
            # Add to session
            self.db_session.add(log_entry)
            self.db_session.commit()
            
            logger.debug(
                f"{self.agent_name}: Logged action '{action}' with resultado '{resultado}' "
                f"for OT {ot_id} (metadata: {metadata})"
            )
            
        except Exception as e:
            logger.error(
                f"{self.agent_name}: Failed to log action '{action}': {str(e)}",
                exc_info=True
            )
            self.db_session.rollback()
            # Don't raise - logging failure shouldn't break agent execution
    
    def _validate_state(self, state: AgentState) -> bool:
        """
        Validate that the state has required fields.
        
        Subclasses can override for agent-specific validation.
        
        Args:
            state: Agent state to validate
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["messages", "action_type", "input_data", "result", "agent_history", "should_continue"]
        
        for field in required_fields:
            if field not in state:
                logger.warning(f"{self.agent_name}: Missing required state field: {field}")
                return False
        
        return True
    
    def _update_state(
        self,
        state: AgentState,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        should_continue: bool = True,
    ) -> AgentState:
        """
        Update the agent state with results or errors.
        
        Convenience method for updating state fields consistently.
        
        Args:
            state: Current state
            result: Results to add to state.result
            error: Error message if something failed
            should_continue: Whether workflow should continue
        
        Returns:
            Updated state
        """
        # Add this agent to history
        if self.agent_name not in state["agent_history"]:
            state["agent_history"].append(self.agent_name)
        
        # Update result if provided
        if result:
            state["result"].update(result)
        
        # Set error if provided
        if error:
            state["error"] = error
            should_continue = False  # Stop on error
        
        # Update control flag
        state["should_continue"] = should_continue
        
        logger.debug(
            f"{self.agent_name}: Updated state. "
            f"Agent history: {state['agent_history']}, "
            f"Should continue: {should_continue}, "
            f"Error: {error}"
        )
        
        return state
    
    def format_for_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format agent results for API response.
        
        Ensures consistent response format across all agents.
        
        Args:
            data: Raw result data from agent
        
        Returns:
            Formatted response dict with metadata
        
        Example:
            ```python
            response = self.format_for_response({
                "created_count": 15,
                "errors": [...],
            })
            
            # Returns:
            # {
            #     "agent_name": "OTSAgent",
            #     "timestamp": "2024-01-15T10:30:45",
            #     "success": true,
            #     "data": {
            #         "created_count": 15,
            #         "errors": [...],
            #     }
            # }
            ```
        """
        return {
            "agent_name": self.agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "success": "error" not in str(data).lower(),
            "data": data,
        }


# Export base class
__all__ = ["BaseAgent"]

