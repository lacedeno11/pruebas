"""
PEIGraphRunner class for executing the LangGraph agentic system.
Handles LLM initialization, graph creation, and state management.
"""

import asyncio
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI

from backend.agents.pei_graph import create_pei_graph
from backend.db.database import SessionLocal
from backend.config import get_settings
from backend.models import LogAgente


class PEIGraphRunner:
    """
    Main orchestrator for executing the PEI Platform agentic system.

    Responsible for:
    1. Initializing the LLM (ChatOpenAI)
    2. Creating the LangGraph StateGraph with all 5 agents
    3. Running the graph with initial state
    4. Managing database sessions
    5. Error handling and logging

    The runner can be used in both async and sync contexts:
    - Async: await runner.run_graph(initial_state)
    - Sync: runner.run_sync(initial_state)

    Example:
        >>> from backend.config import get_settings
        >>> settings = get_settings()
        >>> runner = PEIGraphRunner(settings)
        >>> result = await runner.run_graph({"user_input": "Download new OTs"})
    """

    def __init__(self, config_settings=None):
        """
        Initialize PEIGraphRunner with LLM and configuration.

        Args:
            config_settings: Settings object from pydantic-settings (default: get_settings())
                            Contains OPENAI_API_KEY and other configuration

        Raises:
            ValueError: If OPENAI_API_KEY is not configured
        """
        # Get settings if not provided
        if config_settings is None:
            config_settings = get_settings()

        self.config = config_settings

        # Initialize LLM with OpenAI API key
        if not self.config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not configured. Please set OPENAI_API_KEY in .env"
            )

        self.llm = ChatOpenAI(
            api_key=self.config.OPENAI_API_KEY,
            model="gpt-3.5-turbo",  # Use gpt-3.5-turbo for cost efficiency
            temperature=0.3,  # Lower temperature for more deterministic behavior
            max_tokens=1000,  # Limit token usage for routing/classification
        )

    async def run_graph(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the PEI Platform agentic workflow asynchronously.

        This method:
        1. Gets a database session
        2. Creates the LangGraph with all 5 agents
        3. Invokes the graph with the initial state
        4. Handles exceptions and logs errors
        5. Returns the final state

        Args:
            initial_state: Initial state dictionary containing:
                - user_input (str): User request or trigger
                - event_type (str): Type of event ('user_input', 'scheduled_governance', etc.)
                - ot_data (dict, optional): OT data for context
                - current_ot_id (int, optional): Current OT being processed
                - cuadrilla_id (int, optional): Current cuadrilla being processed

        Returns:
            Final state dictionary containing:
                - action_result (str): Result of the execution
                - error_message (str, optional): Error message if execution failed
                - agent_logs (list): List of log entries from executed agents
                - next_agent (str): Name of next agent (usually 'end' on completion)

        Example:
            >>> runner = PEIGraphRunner()
            >>> state = {
            ...     "user_input": "Download new OTs from TELCOS",
            ...     "event_type": "user_input",
            ... }
            >>> result = await runner.run_graph(state)
            >>> print(result["action_result"])
        """
        # Get database session
        db_session = SessionLocal()

        try:
            # Create the compiled LangGraph
            graph = create_pei_graph(self.llm, db_session)

            # Invoke the graph with initial state
            # The graph will flow through agents based on routing
            final_state = await graph.ainvoke(initial_state)

            return final_state

        except Exception as e:
            # Log the error
            error_message = f"Graph execution failed: {str(e)}"
            print(f"❌ {error_message}")

            # Try to log the error to database
            try:
                log_entry = LogAgente(
                    agente_name="PEIGraphRunner",
                    accion="run_graph",
                    resultado="FAILURE",
                    raw_llm_response=None,
                    metadata={"error": str(e)},
                )
                db_session.add(log_entry)
                db_session.commit()
            except Exception as log_error:
                print(f"⚠️ Failed to log error: {log_error}")

            # Return state with error
            return {
                "action_result": "failed",
                "error_message": error_message,
                "agent_logs": [],
                "next_agent": "end",
            }

        finally:
            # Always close the database session
            db_session.close()

    def run_sync(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the PEI Platform agentic workflow synchronously.

        This is a wrapper around run_graph() for use in non-async contexts
        (e.g., FastAPI endpoints that cannot be async, or external integrations).

        The method:
        1. Creates a new event loop if needed
        2. Runs the async run_graph() method
        3. Returns the result

        Args:
            initial_state: Initial state dictionary (same as run_graph())

        Returns:
            Final state dictionary (same as run_graph())

        Example:
            >>> runner = PEIGraphRunner()
            >>> state = {
            ...     "user_input": "Check governance rules",
            ...     "event_type": "scheduled_governance",
            ... }
            >>> result = runner.run_sync(state)
        """
        try:
            # Get or create event loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No event loop in current thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # Run the async method in the event loop
            return loop.run_until_complete(self.run_graph(initial_state))
        except Exception as e:
            print(f"❌ Sync run failed: {str(e)}")
            return {
                "action_result": "failed",
                "error_message": f"Sync execution failed: {str(e)}",
                "agent_logs": [],
                "next_agent": "end",
            }

    def create_graph(self):
        """
        Create and return the compiled LangGraph without executing it.

        Useful for testing or advanced scenarios where you need to interact
        with the graph directly.

        Returns:
            Compiled LangGraph StateGraph instance

        Example:
            >>> runner = PEIGraphRunner()
            >>> graph = runner.create_graph()
            >>> result = await graph.ainvoke(initial_state)
        """
        db_session = SessionLocal()
        try:
            return create_pei_graph(self.llm, db_session)
        finally:
            db_session.close()

