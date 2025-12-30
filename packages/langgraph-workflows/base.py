"""
DERCAS-ONCO-XAI V1 - LangGraph Base Components

Base workflow classes and utilities for AI workflows in the oncology platform.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from .state import BaseGraphState, StateManager, WorkflowContext

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseGraphState)


class BaseWorkflow(ABC):
    """Base class for all LangGraph workflows in the platform."""
    
    def __init__(
        self,
        workflow_name: str,
        workflow_version: str = "1.0",
        max_retries: int = 3,
        timeout_seconds: int = 300
    ):
        self.workflow_name = workflow_name
        self.workflow_version = workflow_version
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.graph: Optional[CompiledGraph] = None
        self._compiled = False
    
    @abstractmethod
    def get_state_type(self) -> Type[T]:
        """Return the state type for this workflow."""
        pass
    
    @abstractmethod
    def define_nodes(self) -> Dict[str, callable]:
        """Define the workflow nodes."""
        pass
    
    @abstractmethod
    def define_edges(self) -> List[tuple]:
        """Define the workflow edges."""
        pass
    
    @abstractmethod
    def get_entry_point(self) -> str:
        """Get the entry point node name."""
        pass
    
    @abstractmethod
    def get_finish_point(self) -> str:
        """Get the finish point node name."""
        pass
    
    def create_initial_state(
        self,
        correlation_id: Optional[str] = None,
        case_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> T:
        """Create initial state for the workflow."""
        base_state = StateManager.create_base_state(
            workflow_type=self.workflow_name,
            workflow_version=self.workflow_version,
            correlation_id=correlation_id,
            case_id=case_id,
            user_id=user_id,
            max_retries=self.max_retries
        )
        
        # Merge with workflow-specific state
        state_type = self.get_state_type()
        state_data = {**base_state, **kwargs}
        
        return state_type(**state_data)
    
    def compile_graph(self) -> CompiledGraph:
        """Compile the workflow graph."""
        if self._compiled and self.graph:
            return self.graph
        
        # Create state graph
        graph = StateGraph(self.get_state_type())
        
        # Add nodes
        nodes = self.define_nodes()
        for node_name, node_func in nodes.items():
            graph.add_node(node_name, node_func)
        
        # Add edges
        edges = self.define_edges()
        for edge in edges:
            if len(edge) == 2:
                # Simple edge
                from_node, to_node = edge
                graph.add_edge(from_node, to_node)
            elif len(edge) == 3:
                # Conditional edge
                from_node, condition_func, mapping = edge
                graph.add_conditional_edges(from_node, condition_func, mapping)
        
        # Set entry and finish points
        graph.set_entry_point(self.get_entry_point())
        graph.set_finish_point(self.get_finish_point())
        
        # Compile graph
        self.graph = graph.compile()
        self._compiled = True
        
        logger.info(f"Compiled workflow graph for {self.workflow_name}")
        return self.graph
    
    async def execute(
        self,
        initial_state: T,
        config: Optional[Dict[str, Any]] = None
    ) -> T:
        """Execute the workflow."""
        if not self._compiled:
            self.compile_graph()
        
        logger.info(
            f"Starting workflow execution: {self.workflow_name}",
            extra={
                "workflow_id": initial_state["workflow_id"],
                "correlation_id": initial_state.get("correlation_id"),
                "case_id": initial_state.get("case_id")
            }
        )
        
        try:
            # Execute the graph
            result = await self.graph.ainvoke(initial_state, config=config)
            
            logger.info(
                f"Workflow execution completed: {self.workflow_name}",
                extra={
                    "workflow_id": initial_state["workflow_id"],
                    "correlation_id": initial_state.get("correlation_id"),
                    "execution_time": StateManager.get_execution_time(result)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Workflow execution failed: {self.workflow_name}: {e}",
                extra={
                    "workflow_id": initial_state["workflow_id"],
                    "correlation_id": initial_state.get("correlation_id"),
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Update state with error
            error_info = {
                "node": initial_state.get("current_node", "unknown"),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = StateManager.update_state(
                initial_state,
                current_node="failed",
                error=error_info
            )
            
            return result
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information."""
        nodes = self.define_nodes()
        edges = self.define_edges()
        
        return {
            "name": self.workflow_name,
            "version": self.workflow_version,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "nodes": list(nodes.keys()),
            "edges": [
                {"from": edge[0], "to": edge[1] if len(edge) == 2 else "conditional"}
                for edge in edges
            ],
            "entry_point": self.get_entry_point(),
            "finish_point": self.get_finish_point(),
            "state_type": self.get_state_type().__name__
        }


class WorkflowNode:
    """Base class for workflow nodes."""
    
    def __init__(self, node_name: str):
        self.node_name = node_name
        self.logger = logging.getLogger(f"{__name__}.{node_name}")
    
    async def execute(self, state: BaseGraphState) -> BaseGraphState:
        """Execute the node logic."""
        with WorkflowContext(state, self.node_name) as context_state:
            try:
                result = await self._execute_impl(context_state)
                self.logger.info(f"Node {self.node_name} completed successfully")
                return result
            except Exception as e:
                self.logger.error(f"Node {self.node_name} failed: {e}", exc_info=True)
                raise
    
    @abstractmethod
    async def _execute_impl(self, state: BaseGraphState) -> BaseGraphState:
        """Implement the node logic."""
        pass


class ConditionalNode(WorkflowNode):
    """Base class for conditional workflow nodes."""
    
    @abstractmethod
    def get_next_node(self, state: BaseGraphState) -> str:
        """Determine the next node based on state."""
        pass


class ValidationNode(WorkflowNode):
    """Base class for validation nodes."""
    
    @abstractmethod
    def validate_input(self, state: BaseGraphState) -> List[str]:
        """Validate input and return list of errors."""
        pass
    
    async def _execute_impl(self, state: BaseGraphState) -> BaseGraphState:
        """Execute validation."""
        errors = self.validate_input(state)
        
        if errors:
            error_message = f"Validation failed: {'; '.join(errors)}"
            raise ValueError(error_message)
        
        self.logger.info(f"Validation passed for node {self.node_name}")
        return state


class RetryableNode(WorkflowNode):
    """Base class for retryable workflow nodes."""
    
    def __init__(self, node_name: str, max_node_retries: int = 3):
        super().__init__(node_name)
        self.max_node_retries = max_node_retries
    
    async def execute(self, state: BaseGraphState) -> BaseGraphState:
        """Execute with retry logic."""
        node_retry_count = state.get("metadata", {}).get(f"{self.node_name}_retry_count", 0)
        
        for attempt in range(self.max_node_retries):
            try:
                with WorkflowContext(state, self.node_name) as context_state:
                    result = await self._execute_impl(context_state)
                    
                    # Reset retry count on success
                    if f"{self.node_name}_retry_count" in result.get("metadata", {}):
                        del result["metadata"][f"{self.node_name}_retry_count"]
                    
                    self.logger.info(f"Retryable node {self.node_name} completed successfully")
                    return result
                    
            except Exception as e:
                node_retry_count += 1
                
                if attempt < self.max_node_retries - 1:
                    self.logger.warning(
                        f"Node {self.node_name} failed (attempt {attempt + 1}/{self.max_node_retries}): {e}"
                    )
                    
                    # Update retry count in metadata
                    if "metadata" not in state:
                        state["metadata"] = {}
                    state["metadata"][f"{self.node_name}_retry_count"] = node_retry_count
                    
                    # Wait before retry (exponential backoff)
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.logger.error(
                        f"Node {self.node_name} failed after {self.max_node_retries} attempts: {e}",
                        exc_info=True
                    )
                    raise


class WorkflowRegistry:
    """Registry for managing workflow instances."""
    
    _workflows: Dict[str, BaseWorkflow] = {}
    
    @classmethod
    def register(cls, workflow: BaseWorkflow):
        """Register a workflow."""
        cls._workflows[workflow.workflow_name] = workflow
        logger.info(f"Registered workflow: {workflow.workflow_name}")
    
    @classmethod
    def get_workflow(cls, workflow_name: str) -> Optional[BaseWorkflow]:
        """Get a workflow by name."""
        return cls._workflows.get(workflow_name)
    
    @classmethod
    def list_workflows(cls) -> List[str]:
        """List all registered workflows."""
        return list(cls._workflows.keys())
    
    @classmethod
    def get_workflow_info(cls, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get workflow information."""
        workflow = cls.get_workflow(workflow_name)
        return workflow.get_workflow_info() if workflow else None


class WorkflowExecutor:
    """Utility class for executing workflows."""
    
    @staticmethod
    async def execute_workflow(
        workflow_name: str,
        initial_state: BaseGraphState,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseGraphState:
        """Execute a workflow by name."""
        workflow = WorkflowRegistry.get_workflow(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")
        
        return await workflow.execute(initial_state, config)
    
    @staticmethod
    async def execute_workflow_with_timeout(
        workflow_name: str,
        initial_state: BaseGraphState,
        timeout_seconds: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseGraphState:
        """Execute a workflow with timeout."""
        import asyncio
        
        workflow = WorkflowRegistry.get_workflow(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")
        
        timeout = timeout_seconds or workflow.timeout_seconds
        
        try:
            return await asyncio.wait_for(
                workflow.execute(initial_state, config),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Workflow {workflow_name} timed out after {timeout} seconds")
            
            # Update state with timeout error
            error_info = {
                "node": initial_state.get("current_node", "unknown"),
                "error_type": "TimeoutError",
                "error_message": f"Workflow timed out after {timeout} seconds",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = StateManager.update_state(
                initial_state,
                current_node="timeout",
                error=error_info
            )
            
            return result


# Utility functions for common workflow patterns
def create_linear_workflow_edges(node_names: List[str]) -> List[tuple]:
    """Create edges for a linear workflow."""
    edges = []
    for i in range(len(node_names) - 1):
        edges.append((node_names[i], node_names[i + 1]))
    return edges


def create_conditional_edge(
    from_node: str,
    condition_func: callable,
    node_mapping: Dict[str, str]
) -> tuple:
    """Create a conditional edge."""
    return (from_node, condition_func, node_mapping)


def create_error_handling_edges(
    main_nodes: List[str],
    error_handler_node: str,
    final_node: str
) -> List[tuple]:
    """Create edges with error handling."""
    edges = create_linear_workflow_edges(main_nodes)
    
    # Add error handling edges
    for node in main_nodes[:-1]:  # Exclude the last node
        edges.append((node, error_handler_node))
    
    # Error handler goes to final node
    edges.append((error_handler_node, final_node))
    
    return edges


# Decorators for workflow nodes
def workflow_node(node_name: str):
    """Decorator to mark a function as a workflow node."""
    def decorator(func):
        func._node_name = node_name
        func._is_workflow_node = True
        return func
    return decorator


def validation_node(node_name: str):
    """Decorator to mark a function as a validation node."""
    def decorator(func):
        func._node_name = node_name
        func._is_validation_node = True
        return func
    return decorator


def conditional_node(node_name: str):
    """Decorator to mark a function as a conditional node."""
    def decorator(func):
        func._node_name = node_name
        func._is_conditional_node = True
        return func
    return decorator
