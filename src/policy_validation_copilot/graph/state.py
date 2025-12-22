"""
LangGraph state management for Policy Validation Copilot workflow.

This module provides state management functionality specifically for LangGraph
workflow orchestration, including state persistence, transition logging,
checkpoint management, and workflow recovery.

This complements the data models in models/state.py by providing the operational
state management layer for the LangGraph workflow execution.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from uuid import UUID, uuid4
from contextlib import asynccontextmanager

from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from ..models.state import (
    PolicyValidationState,
    reduce_policy_validation_state,
    validate_state_transition,
    validate_state_completeness,
    serialize_state_for_persistence,
    deserialize_state_from_persistence,
    log_state_transition
)
from ..models.audit import NodeExecutionLog, ExecutionStatus, AuditEventType


logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Raised when state transition validation fails."""
    pass


class StateCheckpointError(Exception):
    """Raised when state checkpoint operations fail."""
    pass


class StatePersistenceError(Exception):
    """Raised when state persistence operations fail."""
    pass


class PolicyValidationStateManager:
    """
    State manager for Policy Validation Copilot LangGraph workflow.
    
    Provides comprehensive state management including:
    - State persistence and checkpointing
    - State transition validation and logging
    - Workflow recovery and rollback
    - State monitoring and metrics
    - Concurrent state access management
    """
    
    def __init__(
        self,
        checkpoint_saver: Optional[BaseCheckpointSaver] = None,
        enable_persistence: bool = True,
        enable_validation: bool = True,
        enable_logging: bool = True,
        checkpoint_interval: int = 5,  # Save checkpoint every N state changes
        max_checkpoints: int = 100,
        state_ttl_hours: int = 168  # 7 days
    ):
        """
        Initialize state manager.
        
        Args:
            checkpoint_saver: LangGraph checkpoint saver implementation
            enable_persistence: Whether to persist state to storage
            enable_validation: Whether to validate state transitions
            enable_logging: Whether to log state transitions
            checkpoint_interval: Number of state changes between checkpoints
            max_checkpoints: Maximum number of checkpoints to retain
            state_ttl_hours: Hours to retain state data
        """
        self.checkpoint_saver = checkpoint_saver or MemorySaver()
        self.enable_persistence = enable_persistence
        self.enable_validation = enable_validation
        self.enable_logging = enable_logging
        self.checkpoint_interval = checkpoint_interval
        self.max_checkpoints = max_checkpoints
        self.state_ttl_hours = state_ttl_hours
        
        # State tracking
        self._active_states: Dict[UUID, PolicyValidationState] = {}
        self._state_locks: Dict[UUID, asyncio.Lock] = {}
        self._checkpoint_counters: Dict[UUID, int] = {}
        self._state_history: Dict[UUID, List[Dict[str, Any]]] = {}
        
        # Metrics
        self._transition_count = 0
        self._validation_errors = 0
        self._persistence_errors = 0
        
        logger.info("PolicyValidationStateManager initialized")

    async def create_workflow_state(
        self,
        workflow_id: UUID,
        initial_state: Optional[PolicyValidationState] = None
    ) -> PolicyValidationState:
        """
        Create a new workflow state.
        
        Args:
            workflow_id: Unique workflow identifier
            initial_state: Initial state data
            
        Returns:
            Created workflow state
        """
        if workflow_id in self._active_states:
            raise StateTransitionError(f"Workflow {workflow_id} already exists")
        
        # Create lock for this workflow
        self._state_locks[workflow_id] = asyncio.Lock()
        
        async with self._state_locks[workflow_id]:
            # Initialize state
            if initial_state is None:
                state = PolicyValidationState(
                    workflow_id=workflow_id,
                    workflow_version="1.0.0",
                    current_node="start",
                    workflow_status="RUNNING",
                    config_version="1.0.0",
                    feature_flags={},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    persisted=False,
                    persistence_version=1,
                    case={},
                    evidence_pack={},
                    checklist={},
                    ml={},
                    decision={},
                    guardrails={},
                    hitl={},
                    audit={}
                )
            else:
                state = initial_state.copy()
                state['workflow_id'] = workflow_id
                state['created_at'] = datetime.utcnow()
                state['updated_at'] = datetime.utcnow()
            
            # Store state
            self._active_states[workflow_id] = state
            self._checkpoint_counters[workflow_id] = 0
            self._state_history[workflow_id] = []
            
            # Create initial checkpoint
            if self.enable_persistence:
                await self._create_checkpoint(workflow_id, state, "workflow_created")
            
            # Log creation
            if self.enable_logging:
                await self._log_state_event(
                    workflow_id, "workflow_created", 
                    {"initial_node": state.get('current_node')}
                )
            
            logger.info(f"Created workflow state for {workflow_id}")
            return state

    async def get_workflow_state(self, workflow_id: UUID) -> Optional[PolicyValidationState]:
        """
        Get current workflow state.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Current state or None if not found
        """
        if workflow_id not in self._active_states:
            # Try to load from checkpoint
            if self.enable_persistence:
                state = await self._load_from_checkpoint(workflow_id)
                if state:
                    self._active_states[workflow_id] = state
                    self._state_locks[workflow_id] = asyncio.Lock()
                    return state
            return None
        
        return self._active_states[workflow_id].copy()

    async def update_workflow_state(
        self,
        workflow_id: UUID,
        state_update: PolicyValidationState,
        node_name: Optional[str] = None,
        transition_metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Update workflow state with validation and persistence.
        
        Args:
            workflow_id: Workflow identifier
            state_update: State updates to apply
            node_name: Name of node making the update
            transition_metadata: Additional transition metadata
            
        Returns:
            Updated state
            
        Raises:
            StateTransitionError: If state transition is invalid
        """
        if workflow_id not in self._active_states:
            raise StateTransitionError(f"Workflow {workflow_id} not found")
        
        if workflow_id not in self._state_locks:
            self._state_locks[workflow_id] = asyncio.Lock()
        
        async with self._state_locks[workflow_id]:
            current_state = self._active_states[workflow_id]
            
            # Apply state reducer
            new_state = reduce_policy_validation_state(current_state, state_update)
            
            # Validate transition if enabled
            if self.enable_validation:
                validation_errors = validate_state_transition(current_state, new_state)
                if validation_errors:
                    self._validation_errors += 1
                    error_msg = f"State transition validation failed: {validation_errors}"
                    logger.error(error_msg)
                    raise StateTransitionError(error_msg)
            
            # Update state
            self._active_states[workflow_id] = new_state
            self._transition_count += 1
            
            # Increment checkpoint counter
            self._checkpoint_counters[workflow_id] += 1
            
            # Create checkpoint if needed
            if (self.enable_persistence and 
                self._checkpoint_counters[workflow_id] % self.checkpoint_interval == 0):
                await self._create_checkpoint(workflow_id, new_state, node_name or "state_update")
            
            # Log transition
            if self.enable_logging:
                transition_log = log_state_transition(
                    current_state, new_state, node_name or "unknown", transition_metadata
                )
                await self._log_state_event(
                    workflow_id, "state_transition", 
                    {
                        "node": node_name,
                        "transition_log": transition_log.dict(),
                        "metadata": transition_metadata
                    }
                )
            
            # Add to history
            self._state_history[workflow_id].append({
                "timestamp": datetime.utcnow().isoformat(),
                "node": node_name,
                "changes": self._calculate_state_changes(current_state, new_state),
                "metadata": transition_metadata
            })
            
            # Limit history size
            if len(self._state_history[workflow_id]) > 1000:
                self._state_history[workflow_id] = self._state_history[workflow_id][-500:]
            
            logger.debug(f"Updated workflow state for {workflow_id} from node {node_name}")
            return new_state

    async def complete_workflow(
        self,
        workflow_id: UUID,
        completion_metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Mark workflow as completed and finalize state.
        
        Args:
            workflow_id: Workflow identifier
            completion_metadata: Additional completion metadata
            
        Returns:
            Final workflow state
        """
        if workflow_id not in self._active_states:
            raise StateTransitionError(f"Workflow {workflow_id} not found")
        
        async with self._state_locks[workflow_id]:
            current_state = self._active_states[workflow_id]
            
            # Create completion update
            completion_update = PolicyValidationState(
                workflow_status="COMPLETED",
                updated_at=datetime.utcnow(),
                **current_state
            )
            
            # Apply update
            final_state = reduce_policy_validation_state(current_state, completion_update)
            self._active_states[workflow_id] = final_state
            
            # Create final checkpoint
            if self.enable_persistence:
                await self._create_checkpoint(workflow_id, final_state, "workflow_completed")
            
            # Log completion
            if self.enable_logging:
                await self._log_state_event(
                    workflow_id, "workflow_completed", 
                    {"completion_metadata": completion_metadata}
                )
            
            logger.info(f"Completed workflow {workflow_id}")
            return final_state

    async def fail_workflow(
        self,
        workflow_id: UUID,
        error: Exception,
        error_metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Mark workflow as failed and record error state.
        
        Args:
            workflow_id: Workflow identifier
            error: Exception that caused failure
            error_metadata: Additional error metadata
            
        Returns:
            Failed workflow state
        """
        if workflow_id not in self._active_states:
            raise StateTransitionError(f"Workflow {workflow_id} not found")
        
        async with self._state_locks[workflow_id]:
            current_state = self._active_states[workflow_id]
            
            # Create failure update
            error_state = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_timestamp": datetime.utcnow().isoformat(),
                "error_metadata": error_metadata or {}
            }
            
            failure_update = PolicyValidationState(
                workflow_status="FAILED",
                error_state=error_state,
                updated_at=datetime.utcnow(),
                **current_state
            )
            
            # Apply update
            failed_state = reduce_policy_validation_state(current_state, failure_update)
            self._active_states[workflow_id] = failed_state
            
            # Create failure checkpoint
            if self.enable_persistence:
                await self._create_checkpoint(workflow_id, failed_state, "workflow_failed")
            
            # Log failure
            if self.enable_logging:
                await self._log_state_event(
                    workflow_id, "workflow_failed", 
                    {"error": str(error), "error_metadata": error_metadata}
                )
            
            logger.error(f"Failed workflow {workflow_id}: {error}")
            return failed_state

    async def pause_workflow(
        self,
        workflow_id: UUID,
        pause_reason: str,
        pause_metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Pause workflow execution.
        
        Args:
            workflow_id: Workflow identifier
            pause_reason: Reason for pausing
            pause_metadata: Additional pause metadata
            
        Returns:
            Paused workflow state
        """
        if workflow_id not in self._active_states:
            raise StateTransitionError(f"Workflow {workflow_id} not found")
        
        async with self._state_locks[workflow_id]:
            current_state = self._active_states[workflow_id]
            
            pause_update = PolicyValidationState(
                workflow_status="PAUSED",
                updated_at=datetime.utcnow(),
                **current_state
            )
            
            paused_state = reduce_policy_validation_state(current_state, pause_update)
            self._active_states[workflow_id] = paused_state
            
            if self.enable_persistence:
                await self._create_checkpoint(workflow_id, paused_state, "workflow_paused")
            
            if self.enable_logging:
                await self._log_state_event(
                    workflow_id, "workflow_paused", 
                    {"reason": pause_reason, "metadata": pause_metadata}
                )
            
            logger.info(f"Paused workflow {workflow_id}: {pause_reason}")
            return paused_state

    async def resume_workflow(
        self,
        workflow_id: UUID,
        resume_metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Resume paused workflow execution.
        
        Args:
            workflow_id: Workflow identifier
            resume_metadata: Additional resume metadata
            
        Returns:
            Resumed workflow state
        """
        if workflow_id not in self._active_states:
            raise StateTransitionError(f"Workflow {workflow_id} not found")
        
        async with self._state_locks[workflow_id]:
            current_state = self._active_states[workflow_id]
            
            if current_state.get('workflow_status') != 'PAUSED':
                raise StateTransitionError(f"Workflow {workflow_id} is not paused")
            
            resume_update = PolicyValidationState(
                workflow_status="RUNNING",
                updated_at=datetime.utcnow(),
                **current_state
            )
            
            resumed_state = reduce_policy_validation_state(current_state, resume_update)
            self._active_states[workflow_id] = resumed_state
            
            if self.enable_persistence:
                await self._create_checkpoint(workflow_id, resumed_state, "workflow_resumed")
            
            if self.enable_logging:
                await self._log_state_event(
                    workflow_id, "workflow_resumed", 
                    {"metadata": resume_metadata}
                )
            
            logger.info(f"Resumed workflow {workflow_id}")
            return resumed_state

    async def rollback_to_checkpoint(
        self,
        workflow_id: UUID,
        checkpoint_id: Optional[str] = None
    ) -> PolicyValidationState:
        """
        Rollback workflow to a previous checkpoint.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Specific checkpoint ID, or None for latest
            
        Returns:
            Rolled back workflow state
        """
        if not self.enable_persistence:
            raise StatePersistenceError("Persistence not enabled, cannot rollback")
        
        # Load checkpoint
        checkpoint_state = await self._load_from_checkpoint(workflow_id, checkpoint_id)
        if not checkpoint_state:
            raise StateCheckpointError(f"Checkpoint not found for workflow {workflow_id}")
        
        if workflow_id not in self._state_locks:
            self._state_locks[workflow_id] = asyncio.Lock()
        
        async with self._state_locks[workflow_id]:
            # Restore state
            self._active_states[workflow_id] = checkpoint_state
            
            # Log rollback
            if self.enable_logging:
                await self._log_state_event(
                    workflow_id, "workflow_rollback", 
                    {"checkpoint_id": checkpoint_id}
                )
            
            logger.info(f"Rolled back workflow {workflow_id} to checkpoint {checkpoint_id}")
            return checkpoint_state

    async def get_workflow_history(
        self,
        workflow_id: UUID,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get workflow state change history.
        
        Args:
            workflow_id: Workflow identifier
            limit: Maximum number of history entries
            
        Returns:
            List of state change history entries
        """
        if workflow_id not in self._state_history:
            return []
        
        history = self._state_history[workflow_id]
        if limit:
            history = history[-limit:]
        
        return history

    async def validate_workflow_state(
        self,
        workflow_id: UUID
    ) -> Tuple[bool, List[str]]:
        """
        Validate current workflow state completeness and consistency.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        state = await self.get_workflow_state(workflow_id)
        if not state:
            return False, [f"Workflow {workflow_id} not found"]
        
        # Check state completeness
        completeness_errors = validate_state_completeness(state)
        
        # Additional workflow-specific validations
        workflow_errors = []
        
        # Check workflow status consistency
        status = state.get('workflow_status')
        if status == 'COMPLETED':
            if not state.get('decision', {}).get('decision'):
                workflow_errors.append("Completed workflow missing decision")
        
        # Check node progression
        current_node = state.get('current_node')
        if not current_node:
            workflow_errors.append("Missing current node")
        
        all_errors = completeness_errors + workflow_errors
        return len(all_errors) == 0, all_errors

    async def cleanup_expired_states(self) -> int:
        """
        Clean up expired workflow states.
        
        Returns:
            Number of states cleaned up
        """
        cleanup_count = 0
        cutoff_time = datetime.utcnow() - timedelta(hours=self.state_ttl_hours)
        
        expired_workflows = []
        for workflow_id, state in self._active_states.items():
            if state.get('updated_at', datetime.utcnow()) < cutoff_time:
                expired_workflows.append(workflow_id)
        
        for workflow_id in expired_workflows:
            await self._cleanup_workflow_state(workflow_id)
            cleanup_count += 1
        
        logger.info(f"Cleaned up {cleanup_count} expired workflow states")
        return cleanup_count

    async def get_state_metrics(self) -> Dict[str, Any]:
        """
        Get state management metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "active_workflows": len(self._active_states),
            "total_transitions": self._transition_count,
            "validation_errors": self._validation_errors,
            "persistence_errors": self._persistence_errors,
            "average_history_length": (
                sum(len(h) for h in self._state_history.values()) / 
                len(self._state_history) if self._state_history else 0
            ),
            "checkpoint_interval": self.checkpoint_interval,
            "persistence_enabled": self.enable_persistence,
            "validation_enabled": self.enable_validation
        }

    # Private methods

    async def _create_checkpoint(
        self,
        workflow_id: UUID,
        state: PolicyValidationState,
        checkpoint_name: str
    ) -> None:
        """Create a state checkpoint."""
        try:
            checkpoint_data = {
                "workflow_id": str(workflow_id),
                "checkpoint_name": checkpoint_name,
                "timestamp": datetime.utcnow().isoformat(),
                "state": serialize_state_for_persistence(state)
            }
            
            # Use LangGraph checkpoint saver
            config = {"configurable": {"thread_id": str(workflow_id)}}
            checkpoint = {
                "v": 1,
                "ts": datetime.utcnow().isoformat(),
                "channel_values": checkpoint_data,
                "channel_versions": {},
                "versions_seen": {}
            }
            
            await self.checkpoint_saver.aput(config, checkpoint, {})
            
            logger.debug(f"Created checkpoint for workflow {workflow_id}: {checkpoint_name}")
            
        except Exception as e:
            self._persistence_errors += 1
            logger.error(f"Failed to create checkpoint for {workflow_id}: {e}")
            raise StateCheckpointError(f"Checkpoint creation failed: {e}")

    async def _load_from_checkpoint(
        self,
        workflow_id: UUID,
        checkpoint_id: Optional[str] = None
    ) -> Optional[PolicyValidationState]:
        """Load state from checkpoint."""
        try:
            config = {"configurable": {"thread_id": str(workflow_id)}}
            checkpoint = await self.checkpoint_saver.aget(config)
            
            if not checkpoint:
                return None
            
            checkpoint_data = checkpoint.get("channel_values", {})
            state_data = checkpoint_data.get("state")
            
            if not state_data:
                return None
            
            return deserialize_state_from_persistence(state_data)
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint for {workflow_id}: {e}")
            return None

    async def _log_state_event(
        self,
        workflow_id: UUID,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """Log a state management event."""
        try:
            log_entry = {
                "workflow_id": str(workflow_id),
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": event_data
            }
            
            # In a real implementation, this would write to a logging system
            logger.info(f"State event: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Failed to log state event: {e}")

    def _calculate_state_changes(
        self,
        old_state: PolicyValidationState,
        new_state: PolicyValidationState
    ) -> List[str]:
        """Calculate what changed between states."""
        changes = []
        
        # Check top-level changes
        for key in new_state.keys():
            if key in old_state:
                if old_state[key] != new_state[key]:
                    changes.append(f"Updated {key}")
            else:
                changes.append(f"Added {key}")
        
        # Check for removed keys
        for key in old_state.keys():
            if key not in new_state:
                changes.append(f"Removed {key}")
        
        return changes

    async def _cleanup_workflow_state(self, workflow_id: UUID) -> None:
        """Clean up all data for a workflow."""
        # Remove from active states
        if workflow_id in self._active_states:
            del self._active_states[workflow_id]
        
        # Remove lock
        if workflow_id in self._state_locks:
            del self._state_locks[workflow_id]
        
        # Remove counters and history
        if workflow_id in self._checkpoint_counters:
            del self._checkpoint_counters[workflow_id]
        
        if workflow_id in self._state_history:
            del self._state_history[workflow_id]
        
        logger.debug(f"Cleaned up workflow state for {workflow_id}")

    @asynccontextmanager
    async def workflow_context(self, workflow_id: UUID):
        """Context manager for workflow state operations."""
        if workflow_id not in self._state_locks:
            self._state_locks[workflow_id] = asyncio.Lock()
        
        async with self._state_locks[workflow_id]:
            try:
                yield self._active_states.get(workflow_id)
            except Exception as e:
                logger.error(f"Error in workflow context for {workflow_id}: {e}")
                raise


# Global state manager instance
_state_manager: Optional[PolicyValidationStateManager] = None


def get_state_manager() -> PolicyValidationStateManager:
    """Get the global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = PolicyValidationStateManager()
    return _state_manager


def initialize_state_manager(
    checkpoint_saver: Optional[BaseCheckpointSaver] = None,
    **kwargs
) -> PolicyValidationStateManager:
    """Initialize the global state manager."""
    global _state_manager
    _state_manager = PolicyValidationStateManager(
        checkpoint_saver=checkpoint_saver,
        **kwargs
    )
    return _state_manager


# Utility functions for LangGraph integration

async def create_workflow_state(
    workflow_id: UUID,
    initial_state: Optional[PolicyValidationState] = None
) -> PolicyValidationState:
    """Create a new workflow state."""
    manager = get_state_manager()
    return await manager.create_workflow_state(workflow_id, initial_state)


async def get_workflow_state(workflow_id: UUID) -> Optional[PolicyValidationState]:
    """Get current workflow state."""
    manager = get_state_manager()
    return await manager.get_workflow_state(workflow_id)


async def update_workflow_state(
    workflow_id: UUID,
    state_update: PolicyValidationState,
    node_name: Optional[str] = None,
    transition_metadata: Optional[Dict[str, Any]] = None
) -> PolicyValidationState:
    """Update workflow state."""
    manager = get_state_manager()
    return await manager.update_workflow_state(
        workflow_id, state_update, node_name, transition_metadata
    )


async def complete_workflow(
    workflow_id: UUID,
    completion_metadata: Optional[Dict[str, Any]] = None
) -> PolicyValidationState:
    """Complete workflow."""
    manager = get_state_manager()
    return await manager.complete_workflow(workflow_id, completion_metadata)


async def fail_workflow(
    workflow_id: UUID,
    error: Exception,
    error_metadata: Optional[Dict[str, Any]] = None
) -> PolicyValidationState:
    """Fail workflow."""
    manager = get_state_manager()
    return await manager.fail_workflow(workflow_id, error, error_metadata)


# State decorator for LangGraph nodes
def with_state_management(node_name: str):
    """
    Decorator for LangGraph nodes to add automatic state management.
    
    Args:
        node_name: Name of the node for logging
    """
    def decorator(func: Callable):
        async def wrapper(state: PolicyValidationState, **kwargs) -> PolicyValidationState:
            workflow_id = state.get('workflow_id')
            if not workflow_id:
                raise StateTransitionError("Missing workflow_id in state")
            
            try:
                # Log node start
                start_time = datetime.utcnow()
                logger.info(f"Starting node {node_name} for workflow {workflow_id}")
                
                # Execute node function
                result = await func(state, **kwargs)
                
                # Calculate execution time
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                # Update state with execution log
                execution_log = NodeExecutionLog(
                    node_name=node_name,
                    node_type="node",
                    status=ExecutionStatus.COMPLETED,
                    started_at=start_time,
                    completed_at=end_time,
                    duration_ms=duration_ms,
                    input_data=serialize_state_for_persistence(state),
                    output_data=serialize_state_for_persistence(result)
                )
                
                # Add to audit trail
                if 'audit' not in result:
                    result['audit'] = {}
                if 'node_execution_log' not in result['audit']:
                    result['audit']['node_execution_log'] = []
                
                result['audit']['node_execution_log'].append(execution_log)
                result['current_node'] = node_name
                result['updated_at'] = end_time
                
                # Update state through manager
                updated_state = await update_workflow_state(
                    workflow_id, result, node_name, 
                    {"duration_ms": duration_ms, "status": "completed"}
                )
                
                logger.info(f"Completed node {node_name} for workflow {workflow_id} in {duration_ms:.2f}ms")
                return updated_state
                
            except Exception as e:
                # Log node failure
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                execution_log = NodeExecutionLog(
                    node_name=node_name,
                    node_type="node",
                    status=ExecutionStatus.FAILED,
                    started_at=start_time,
                    completed_at=end_time,
                    duration_ms=duration_ms,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                
                # Update state with error
                error_state = state.copy()
                if 'audit' not in error_state:
                    error_state['audit'] = {}
                if 'node_execution_log' not in error_state['audit']:
                    error_state['audit']['node_execution_log'] = []
                
                error_state['audit']['node_execution_log'].append(execution_log)
                
                # Fail workflow
                await fail_workflow(
                    workflow_id, e, 
                    {"node": node_name, "duration_ms": duration_ms}
                )
                
                logger.error(f"Failed node {node_name} for workflow {workflow_id}: {e}")
                raise
        
        return wrapper
    return decorator


__all__ = [
    "PolicyValidationStateManager",
    "StateTransitionError",
    "StateCheckpointError", 
    "StatePersistenceError",
    "get_state_manager",
    "initialize_state_manager",
    "create_workflow_state",
    "get_workflow_state",
    "update_workflow_state",
    "complete_workflow",
    "fail_workflow",
    "with_state_management"
]
