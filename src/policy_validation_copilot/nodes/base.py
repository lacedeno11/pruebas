"""
Base node utilities for LangGraph workflow.

Provides common functionality for all nodes.
"""

import logging
from datetime import datetime
from functools import wraps
from typing import Callable, Any
from uuid import uuid4

from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.models.audit import NodeExecution, NodeType

logger = logging.getLogger(__name__)


def create_node_execution(
    case_id: str,
    node_type: NodeType,
    node_name: str,
    input_state: PolicyValidationState,
) -> NodeExecution:
    """Create a new node execution record."""
    import hashlib
    import json

    # Hash the input state for reproducibility
    state_dict = input_state.model_dump(mode="json", exclude={"node_executions"})
    state_json = json.dumps(state_dict, sort_keys=True, default=str)
    input_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]

    return NodeExecution(
        execution_id=str(uuid4()),
        case_id=case_id,
        node_type=node_type,
        node_name=node_name,
        input_state_hash=input_hash,
        status="RUNNING",
    )


def complete_node_execution(
    execution: NodeExecution,
    output_state: PolicyValidationState,
    status: str = "SUCCESS",
    error_message: str | None = None,
) -> NodeExecution:
    """Complete a node execution record."""
    import hashlib
    import json

    execution.completed_at = datetime.utcnow()
    execution.status = status
    execution.error_message = error_message

    if execution.started_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()
        execution.duration_ms = int(duration * 1000)

    # Hash output state
    state_dict = output_state.model_dump(mode="json", exclude={"node_executions"})
    state_json = json.dumps(state_dict, sort_keys=True, default=str)
    execution.output_state_hash = hashlib.sha256(state_json.encode()).hexdigest()[:16]

    return execution


def node_wrapper(
    node_type: NodeType,
    node_name: str,
) -> Callable:
    """
    Decorator that wraps a node function with execution tracking.

    Handles:
    - Creating execution record
    - Error handling
    - Completing execution record
    - Adding to audit trail
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: PolicyValidationState) -> dict[str, Any]:
            case_id = state.case.case_id if state.case else "UNKNOWN"

            # Create execution record
            execution = create_node_execution(
                case_id=case_id,
                node_type=node_type,
                node_name=node_name,
                input_state=state,
            )

            # Update current node
            state.current_node = node_name
            state.workflow_status = "RUNNING"

            try:
                logger.info(f"Starting node {node_name} for case {case_id}")

                # Execute the actual node function
                result = await func(state)

                # Complete execution
                complete_node_execution(execution, state, status="SUCCESS")

                logger.info(
                    f"Completed node {node_name} for case {case_id} "
                    f"in {execution.duration_ms}ms"
                )

                # Add execution to result
                if "node_executions" not in result:
                    result["node_executions"] = []
                result["node_executions"].append(execution)

                return result

            except Exception as e:
                logger.error(f"Error in node {node_name}: {e}")

                # Complete with error
                complete_node_execution(
                    execution, state, status="FAILED", error_message=str(e)
                )

                # Add error to state
                state.add_error("NODE_ERROR", str(e), node_name)

                # Return state with error and execution
                return {
                    "errors": state.errors,
                    "last_error": state.last_error,
                    "workflow_status": "FAILED",
                    "node_executions": [execution],
                }

        return wrapper

    return decorator
