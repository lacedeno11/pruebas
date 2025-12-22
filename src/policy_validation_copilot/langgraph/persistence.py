"""
State persistence utilities for LangGraph state management.

This module provides utilities for persisting and retrieving PolicyValidationState
instances to/from various storage backends.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..models.state import PolicyValidationState, StateTransition

logger = logging.getLogger(__name__)


class StatePersistenceBackend(ABC):
    """Abstract base class for state persistence backends."""
    
    @abstractmethod
    async def save_state(self, state: PolicyValidationState) -> bool:
        """Save a state to the backend."""
        pass
    
    @abstractmethod
    async def load_state(self, state_id: str) -> Optional[PolicyValidationState]:
        """Load a state from the backend."""
        pass
    
    @abstractmethod
    async def delete_state(self, state_id: str) -> bool:
        """Delete a state from the backend."""
        pass
    
    @abstractmethod
    async def list_states(
        self,
        case_id: Optional[str] = None,
        workflow_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List states with optional filtering."""
        pass


class InMemoryStatePersistence(StatePersistenceBackend):
    """In-memory state persistence for development and testing."""
    
    def __init__(self):
        self._states: Dict[str, PolicyValidationState] = {}
        self._transitions: Dict[str, List[StateTransition]] = {}
    
    async def save_state(self, state: PolicyValidationState) -> bool:
        """Save a state to memory."""
        try:
            logger.debug(f"Saving state {state.state_id} to memory")
            self._states[state.state_id] = state
            return True
        except Exception as e:
            logger.error(f"Error saving state to memory: {e}")
            return False
    
    async def load_state(self, state_id: str) -> Optional[PolicyValidationState]:
        """Load a state from memory."""
        try:
            logger.debug(f"Loading state {state_id} from memory")
            return self._states.get(state_id)
        except Exception as e:
            logger.error(f"Error loading state from memory: {e}")
            return None
    
    async def delete_state(self, state_id: str) -> bool:
        """Delete a state from memory."""
        try:
            logger.debug(f"Deleting state {state_id} from memory")
            if state_id in self._states:
                del self._states[state_id]
            if state_id in self._transitions:
                del self._transitions[state_id]
            return True
        except Exception as e:
            logger.error(f"Error deleting state from memory: {e}")
            return False
    
    async def list_states(
        self,
        case_id: Optional[str] = None,
        workflow_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List states from memory with optional filtering."""
        try:
            states = list(self._states.values())
            
            # Apply filters
            if case_id:
                states = [s for s in states if s.case.case_id == case_id]
            
            if workflow_status:
                states = [s for s in states if s.workflow_status == workflow_status]
            
            # Sort by creation time (newest first)
            states.sort(key=lambda s: s.created_at, reverse=True)
            
            # Apply pagination
            paginated_states = states[offset:offset + limit]
            
            # Return summary information
            return [state.to_summary() for state in paginated_states]
            
        except Exception as e:
            logger.error(f"Error listing states from memory: {e}")
            return []
    
    def save_transition(self, transition: StateTransition) -> bool:
        """Save a state transition to memory."""
        try:
            if transition.state_id not in self._transitions:
                self._transitions[transition.state_id] = []
            self._transitions[transition.state_id].append(transition)
            return True
        except Exception as e:
            logger.error(f"Error saving transition to memory: {e}")
            return False
    
    def get_transitions(self, state_id: str) -> List[StateTransition]:
        """Get all transitions for a state."""
        return self._transitions.get(state_id, [])


class FileSystemStatePersistence(StatePersistenceBackend):
    """File system-based state persistence."""
    
    def __init__(self, base_path: str = "./state_storage"):
        self.base_path = base_path
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Ensure the storage directory exists."""
        import os
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_state_file_path(self, state_id: str) -> str:
        """Get the file path for a state."""
        import os
        return os.path.join(self.base_path, f"{state_id}.json")
    
    async def save_state(self, state: PolicyValidationState) -> bool:
        """Save a state to the file system."""
        try:
            logger.debug(f"Saving state {state.state_id} to file system")
            
            file_path = self._get_state_file_path(state.state_id)
            state_data = state.dict()
            
            # Add metadata
            state_data["_persistence_metadata"] = {
                "saved_at": datetime.utcnow().isoformat(),
                "backend": "filesystem",
                "version": "1.0.0",
            }
            
            with open(file_path, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving state to file system: {e}")
            return False
    
    async def load_state(self, state_id: str) -> Optional[PolicyValidationState]:
        """Load a state from the file system."""
        try:
            logger.debug(f"Loading state {state_id} from file system")
            
            file_path = self._get_state_file_path(state_id)
            
            import os
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r') as f:
                state_data = json.load(f)
            
            # Remove metadata
            state_data = {k: v for k, v in state_data.items() if not k.startswith("_")}
            
            return PolicyValidationState(**state_data)
            
        except Exception as e:
            logger.error(f"Error loading state from file system: {e}")
            return None
    
    async def delete_state(self, state_id: str) -> bool:
        """Delete a state from the file system."""
        try:
            logger.debug(f"Deleting state {state_id} from file system")
            
            file_path = self._get_state_file_path(state_id)
            
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting state from file system: {e}")
            return False
    
    async def list_states(
        self,
        case_id: Optional[str] = None,
        workflow_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List states from the file system with optional filtering."""
        try:
            import os
            import glob
            
            state_files = glob.glob(os.path.join(self.base_path, "*.json"))
            states = []
            
            for file_path in state_files:
                try:
                    with open(file_path, 'r') as f:
                        state_data = json.load(f)
                    
                    # Remove metadata
                    state_data = {k: v for k, v in state_data.items() if not k.startswith("_")}
                    state = PolicyValidationState(**state_data)
                    
                    # Apply filters
                    if case_id and state.case.case_id != case_id:
                        continue
                    
                    if workflow_status and state.workflow_status != workflow_status:
                        continue
                    
                    states.append(state)
                    
                except Exception as e:
                    logger.warning(f"Error loading state file {file_path}: {e}")
                    continue
            
            # Sort by creation time (newest first)
            states.sort(key=lambda s: s.created_at, reverse=True)
            
            # Apply pagination
            paginated_states = states[offset:offset + limit]
            
            # Return summary information
            return [state.to_summary() for state in paginated_states]
            
        except Exception as e:
            logger.error(f"Error listing states from file system: {e}")
            return []


class StatePersistenceManager:
    """Manager for state persistence operations."""
    
    def __init__(self, backend: StatePersistenceBackend):
        self.backend = backend
        self._auto_save_enabled = True
    
    def enable_auto_save(self):
        """Enable automatic state saving."""
        self._auto_save_enabled = True
    
    def disable_auto_save(self):
        """Disable automatic state saving."""
        self._auto_save_enabled = False
    
    async def save_state(self, state: PolicyValidationState) -> bool:
        """Save a state using the configured backend."""
        if not self._auto_save_enabled:
            logger.debug("Auto-save disabled, skipping state save")
            return True
        
        return await self.backend.save_state(state)
    
    async def load_state(self, state_id: str) -> Optional[PolicyValidationState]:
        """Load a state using the configured backend."""
        return await self.backend.load_state(state_id)
    
    async def delete_state(self, state_id: str) -> bool:
        """Delete a state using the configured backend."""
        return await self.backend.delete_state(state_id)
    
    async def list_states(
        self,
        case_id: Optional[str] = None,
        workflow_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List states using the configured backend."""
        return await self.backend.list_states(case_id, workflow_status, limit, offset)
    
    async def cleanup_old_states(self, max_age_days: int = 30) -> int:
        """Clean up old states based on age."""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            states = await self.list_states(limit=1000)  # Get more states for cleanup
            
            deleted_count = 0
            for state_summary in states:
                created_at = datetime.fromisoformat(state_summary.get("created_at", ""))
                if created_at < cutoff_date:
                    state_id = state_summary.get("state_id")
                    if state_id and await self.delete_state(state_id):
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old states")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during state cleanup: {e}")
            return 0
    
    async def backup_states(self, backup_path: str) -> bool:
        """Create a backup of all states."""
        try:
            import os
            import json
            from datetime import datetime
            
            os.makedirs(backup_path, exist_ok=True)
            
            states = await self.list_states(limit=10000)  # Get all states
            backup_data = {
                "backup_created_at": datetime.utcnow().isoformat(),
                "backup_version": "1.0.0",
                "state_count": len(states),
                "states": []
            }
            
            for state_summary in states:
                state_id = state_summary.get("state_id")
                if state_id:
                    state = await self.load_state(state_id)
                    if state:
                        backup_data["states"].append(state.dict())
            
            backup_file = os.path.join(backup_path, f"states_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            logger.info(f"Created backup with {len(backup_data['states'])} states at {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    async def restore_states(self, backup_file: str) -> int:
        """Restore states from a backup file."""
        try:
            import json
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            restored_count = 0
            for state_data in backup_data.get("states", []):
                try:
                    state = PolicyValidationState(**state_data)
                    if await self.save_state(state):
                        restored_count += 1
                except Exception as e:
                    logger.warning(f"Error restoring state: {e}")
                    continue
            
            logger.info(f"Restored {restored_count} states from backup")
            return restored_count
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return 0


# Default persistence manager with in-memory backend
default_persistence_manager = StatePersistenceManager(InMemoryStatePersistence())


def create_file_persistence_manager(base_path: str = "./state_storage") -> StatePersistenceManager:
    """Create a persistence manager with file system backend."""
    return StatePersistenceManager(FileSystemStatePersistence(base_path))


def create_memory_persistence_manager() -> StatePersistenceManager:
    """Create a persistence manager with in-memory backend."""
    return StatePersistenceManager(InMemoryStatePersistence())
