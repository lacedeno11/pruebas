"""
PEI Agent Executor for LangGraph Workflow Execution.

This module provides the PEIAgentExecutor class which manages the execution of
the complete multi-agent workflow. It handles:

1. User-initiated workflow execution (via API)
2. Scheduled job execution (via APScheduler)
3. Error handling and recovery
4. State management and persistence
5. Alert routing for critical failures

The executor acts as the orchestration layer between FastAPI endpoints/scheduler
and the LangGraph agent workflow.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import create_pei_graph
from src.agents.state import PEIState, create_initial_state
from src.models import AgentLog
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class PEIAgentExecutor:
    """
    Executor for PEI agent workflows.

    Manages the execution of the multi-agent system, including:
    - User-initiated requests via API
    - Scheduled governance checks (every 6 hours)
    - Scheduled nightly normalization (daily at 00:00 UTC)
    - Error handling and recovery
    - Alert routing for critical issues

    All executions are tracked in agent_logs for audit trail and debugging.
    """

    def __init__(self):
        """Initialize the executor."""
        logger.info("Initializing PEIAgentExecutor")
        self.notification_service = NotificationService()

    async def execute(
        self,
        input_text: str,
        db: AsyncSession,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the PEI agent workflow with user input.

        This method:
        1. Creates initial workflow state from user input
        2. Creates and configures the LangGraph workflow
        3. Executes the workflow with error handling
        4. Logs execution results
        5. Returns final state

        Args:
            input_text (str): User input/command for the workflow
                Example: "Plan all PUBLICO project OTs"
            db (AsyncSession): Database session for agent access
            config (Optional[Dict[str, Any]]): Additional execution configuration
                - thread_id: For state persistence across calls
                - recursion_limit: Max agent steps (default 25)
                - timeout: Execution timeout in seconds

        Returns:
            Dict[str, Any]: Final workflow state containing:
                - input: Original user input
                - metadata['route']: Routing decision from RouterAgent
                - action_result: Result of final agent
                - agent_messages: Conversation history
                - error: Any error that occurred (if applicable)

        Example:
            ```python
            executor = PEIAgentExecutor()
            result = await executor.execute("Plan OTs for PUBLICO", db)
            if result.get('action_result', {}).get('success'):
                print(f"Success: {result['action_result']['message']}")
            ```
        """
        try:
            logger.info(f"Executor: Starting workflow execution")
            logger.info(f"  Input: {input_text[:100]}")

            # Create initial state
            state = create_initial_state(input_text)
            logger.debug(f"Executor: Created initial state")

            # Create the workflow graph
            graph = await create_pei_graph(db)
            logger.debug(f"Executor: Created PEI workflow graph")

            # Set default config if not provided
            if config is None:
                config = {}
            config.setdefault("recursion_limit", 25)

            # Execute the workflow
            logger.info(f"Executor: Executing workflow with recursion_limit={config['recursion_limit']}")
            final_state = await graph.ainvoke(state, config)
            logger.info(f"Executor: Workflow execution completed")

            # Log execution result
            route = final_state.get("metadata", {}).get("route", "unknown")
            action_result = final_state.get("action_result", {})
            success = action_result.get("success", False)

            await self._log_execution(
                db,
                input_text=input_text,
                route=route,
                success=success,
                result_message=action_result.get("message", "No message"),
                agent_messages_count=len(final_state.get("agent_messages", [])),
            )

            logger.info(
                f"Executor: Execution result - route={route}, success={success}, "
                f"messages={len(final_state.get('agent_messages', []))}"
            )

            return final_state

        except Exception as e:
            logger.error(f"Executor: Workflow execution failed: {str(e)}", exc_info=True)

            # Create error state
            error_state = create_initial_state(input_text)
            error_state["error"] = str(e)
            error_state["action_result"] = {
                "success": False,
                "message": f"Workflow execution failed: {str(e)}",
            }

            # Log the execution error
            await self._log_execution(
                db,
                input_text=input_text,
                route="error",
                success=False,
                result_message=str(e),
                error=True,
            )

            # Send alert for critical errors
            try:
                await self.notification_service.send_alert(
                    alert_type="system_error",
                    ot_id=None,
                    recipients=["admin@telconet.ec"],
                    message=f"PEI Agent Executor error: {str(e)}",
                )
            except Exception as alert_error:
                logger.warning(f"Executor: Failed to send error alert: {str(alert_error)}")

            return error_state

    async def execute_scheduled(
        self, task_type: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Execute a scheduled job (governance check or nightly normalization).

        This method is called by APScheduler for background tasks:
        - Governance checks: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
        - Nightly normalization: Daily at 00:00 UTC

        Args:
            task_type (str): Type of scheduled task
                - 'governance': Run GobernanzaAgent governance check
                - 'normalization': Run PlanificacionAgent nightly optimization
            db (AsyncSession): Database session for agents

        Returns:
            Dict[str, Any]: Execution result with:
                - status: 'success' or 'error'
                - task_type: The task that was executed
                - timestamp: When the task ran
                - result: Task-specific results

        Example:
            ```python
            executor = PEIAgentExecutor()
            result = await executor.execute_scheduled('governance', db)
            if result['status'] == 'success':
                print(f"Governance check completed")
            ```
        """
        try:
            logger.info(f"Executor: Starting scheduled task: {task_type}")
            start_time = datetime.utcnow()

            if task_type == "governance":
                # Run governance check
                result = await self.execute(
                    "Check governance alerts and auto-cancellations",
                    db,
                    config={"recursion_limit": 25},
                )
                task_result = {
                    "status": "success" if result.get("action_result", {}).get("success") else "error",
                    "task_type": "governance",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": result.get("action_result", {}),
                }

            elif task_type == "normalization":
                # Run nightly normalization
                result = await self.execute(
                    "Run nightly route normalization and optimization",
                    db,
                    config={"recursion_limit": 25},
                )
                task_result = {
                    "status": "success" if result.get("action_result", {}).get("success") else "error",
                    "task_type": "normalization",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": result.get("action_result", {}),
                }

            else:
                logger.warning(f"Executor: Unknown scheduled task type: {task_type}")
                task_result = {
                    "status": "error",
                    "task_type": task_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": f"Unknown task type: {task_type}",
                }

            # Log scheduled execution
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Executor: Scheduled task '{task_type}' completed in {duration:.2f}s - "
                f"Status: {task_result['status']}"
            )

            return task_result

        except Exception as e:
            logger.error(
                f"Executor: Scheduled task '{task_type}' failed: {str(e)}", exc_info=True
            )

            error_result = {
                "status": "error",
                "task_type": task_type,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

            # Send alert for scheduled task failures
            try:
                await self.notification_service.send_alert(
                    alert_type="scheduled_job_error",
                    ot_id=None,
                    recipients=["admin@telconet.ec"],
                    message=f"Scheduled task '{task_type}' failed: {str(e)}",
                )
            except Exception as alert_error:
                logger.warning(
                    f"Executor: Failed to send scheduled task error alert: {str(alert_error)}"
                )

            return error_result

    async def _log_execution(
        self,
        db: AsyncSession,
        input_text: str,
        route: str,
        success: bool,
        result_message: str,
        agent_messages_count: int = 0,
        error: bool = False,
    ) -> None:
        """
        Log workflow execution to database for audit trail.

        Creates an AgentLog entry tracking the overall workflow execution.
        This is different from individual agent logs - this tracks the
        top-level executor call.

        Args:
            db (AsyncSession): Database session
            input_text (str): Original user input
            route (str): Route classification from RouterAgent
            success (bool): Whether execution succeeded
            result_message (str): Result/error message
            agent_messages_count (int): Number of agent messages/steps
            error (bool): Whether an error occurred

        Returns:
            None
        """
        try:
            log_entry = AgentLog(
                ot_id=None,  # Executor-level logs don't target specific OT
                agent_name="PEIAgentExecutor",
                accion=f"Workflow execution - Route: {route}, Steps: {agent_messages_count}",
                resultado="FAILURE" if error else ("SUCCESS" if success else "WARNING"),
                metadata={
                    "input": input_text[:200],  # Truncate for storage
                    "route": route,
                    "success": success,
                    "agent_messages_count": agent_messages_count,
                    "result_message": result_message[:500],  # Truncate message
                },
                timestamp=datetime.utcnow(),
            )

            db.add(log_entry)
            await db.commit()

            logger.debug(f"Executor: Logged execution to agent_logs")

        except Exception as e:
            logger.error(f"Executor: Error logging execution: {str(e)}")
            try:
                await db.rollback()
            except Exception:
                pass


# Global executor singleton (optional, for convenience)
_executor_instance: Optional[PEIAgentExecutor] = None


def get_executor() -> PEIAgentExecutor:
    """
    Get or create the global PEIAgentExecutor singleton.

    This provides a convenient way to access the executor
    without creating new instances.

    Returns:
        PEIAgentExecutor: The executor instance

    Example:
        ```python
        executor = get_executor()
        result = await executor.execute("Plan OTs", db)
        ```
    """
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = PEIAgentExecutor()
    return _executor_instance


async def reset_executor() -> None:
    """
    Reset the global executor singleton.

    Useful for testing or when you need to create a fresh executor.
    """
    global _executor_instance
    _executor_instance = None

