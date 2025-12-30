"""
DERCAS-ONCO-XAI V1 - LangGraph Tools

Common tools interfaces and utilities for AI workflows in the oncology platform.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """Result from a tool execution."""
    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[Any] = Field(None, description="Tool output data")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    execution_time_seconds: Optional[float] = Field(None, description="Execution time")


class BaseTool(ABC):
    """Base class for all workflow tools."""
    
    def __init__(self, tool_name: str, timeout_seconds: int = 30):
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with timeout and error handling."""
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Executing tool: {self.tool_name}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_impl(**kwargs),
                timeout=self.timeout_seconds
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(f"Tool {self.tool_name} completed successfully")
            
            return ToolResult(
                success=True,
                data=result,
                execution_time_seconds=execution_time
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Tool {self.tool_name} timed out after {self.timeout_seconds} seconds"
            
            self.logger.error(error_msg)
            
            return ToolResult(
                success=False,
                error=error_msg,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Tool {self.tool_name} failed: {str(e)}"
            
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                error=error_msg,
                execution_time_seconds=execution_time,
                metadata={"exception_type": type(e).__name__}
            )
    
    @abstractmethod
    async def _execute_impl(self, **kwargs) -> Any:
        """Implement the tool logic."""
        pass


class HTTPClientTool(BaseTool):
    """Tool for making HTTP requests to internal services."""
    
    def __init__(
        self,
        tool_name: str,
        base_url: str,
        timeout_seconds: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(tool_name, timeout_seconds)
        self.base_url = base_url.rstrip('/')
        self.default_headers = headers or {}
    
    async def _execute_impl(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute HTTP request."""
        url = f"{self.base_url}{path}"
        
        # Merge headers
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout_seconds
            )
            
            response.raise_for_status()
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response.json() if response.content else None
            }


class DatabaseTool(BaseTool):
    """Tool for database operations."""
    
    def __init__(
        self,
        tool_name: str,
        connection_string: str,
        timeout_seconds: int = 30
    ):
        super().__init__(tool_name, timeout_seconds)
        self.connection_string = connection_string
    
    async def _execute_impl(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        fetch_mode: str = "all"  # all, one, none
    ) -> Any:
        """Execute database query."""
        # This is a placeholder - in real implementation, use asyncpg or similar
        self.logger.info(f"Executing database query: {query[:100]}...")
        
        # Mock implementation
        if fetch_mode == "all":
            return []
        elif fetch_mode == "one":
            return None
        else:
            return {"affected_rows": 0}


class FileStorageTool(BaseTool):
    """Tool for file storage operations."""
    
    def __init__(
        self,
        tool_name: str,
        storage_config: Dict[str, Any],
        timeout_seconds: int = 60
    ):
        super().__init__(tool_name, timeout_seconds)
        self.storage_config = storage_config
    
    async def _execute_impl(
        self,
        operation: str,  # upload, download, delete, list
        file_path: str,
        data: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute file storage operation."""
        self.logger.info(f"Executing storage operation: {operation} on {file_path}")
        
        # Mock implementation
        if operation == "upload":
            return {
                "file_path": file_path,
                "size": len(data) if data else 0,
                "checksum": "mock_checksum",
                "url": f"https://storage.example.com/{file_path}"
            }
        elif operation == "download":
            return {
                "file_path": file_path,
                "data": b"mock_file_content",
                "metadata": metadata or {}
            }
        elif operation == "delete":
            return {"deleted": True}
        elif operation == "list":
            return {"files": []}
        else:
            raise ValueError(f"Unknown operation: {operation}")


class ModelInferenceTool(BaseTool):
    """Tool for ML model inference."""
    
    def __init__(
        self,
        tool_name: str,
        model_config: Dict[str, Any],
        timeout_seconds: int = 120
    ):
        super().__init__(tool_name, timeout_seconds)
        self.model_config = model_config
    
    async def _execute_impl(
        self,
        model_name: str,
        input_data: Any,
        inference_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute model inference."""
        self.logger.info(f"Running inference with model: {model_name}")
        
        # Mock implementation for MVP
        if "pattern" in model_name.lower():
            return {
                "predictions": [
                    {"pattern": "lepidic", "confidence": 0.85},
                    {"pattern": "acinar", "confidence": 0.12},
                    {"pattern": "papillary", "confidence": 0.03}
                ],
                "model_version": "pattern_model_v1.0",
                "inference_time_ms": 150
            }
        elif "mutation" in model_name.lower():
            return {
                "predictions": [
                    {"mutation": "EGFR", "status": "positive", "confidence": 0.92},
                    {"mutation": "KRAS", "status": "negative", "confidence": 0.88},
                    {"mutation": "TP53", "status": "uncertain", "confidence": 0.45}
                ],
                "model_version": "mutation_model_v1.0",
                "inference_time_ms": 200
            }
        else:
            return {
                "predictions": [],
                "model_version": "unknown_model",
                "inference_time_ms": 50
            }


class OntologyTool(BaseTool):
    """Tool for ontology operations."""
    
    def __init__(
        self,
        tool_name: str,
        ontology_config: Dict[str, Any],
        timeout_seconds: int = 30
    ):
        super().__init__(tool_name, timeout_seconds)
        self.ontology_config = ontology_config
    
    async def _execute_impl(
        self,
        operation: str,  # search, map, validate, diff
        query: Optional[str] = None,
        entities: Optional[List[str]] = None,
        ontology_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute ontology operation."""
        self.logger.info(f"Executing ontology operation: {operation}")
        
        # Mock implementation
        if operation == "search":
            return {
                "results": [
                    {
                        "code": "C3512",
                        "term": "Lung Adenocarcinoma",
                        "ontology": "NCIt",
                        "confidence": 0.95
                    }
                ]
            }
        elif operation == "map":
            return {
                "mappings": [
                    {
                        "entity": entities[0] if entities else "unknown",
                        "mapped_code": "C3512",
                        "mapped_term": "Lung Adenocarcinoma",
                        "ontology": "NCIt",
                        "confidence": 0.90
                    }
                ] if entities else []
            }
        elif operation == "validate":
            return {"valid": True, "issues": []}
        elif operation == "diff":
            return {"changes": [], "additions": [], "deletions": []}
        else:
            raise ValueError(f"Unknown operation: {operation}")


class EventPublisherTool(BaseTool):
    """Tool for publishing events."""
    
    def __init__(
        self,
        tool_name: str,
        event_bus_config: Dict[str, Any],
        timeout_seconds: int = 10
    ):
        super().__init__(tool_name, timeout_seconds)
        self.event_bus_config = event_bus_config
    
    async def _execute_impl(
        self,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        case_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish an event."""
        self.logger.info(f"Publishing event: {event_type}")
        
        # Mock implementation
        return {
            "event_id": f"evt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "published": True,
            "timestamp": datetime.utcnow().isoformat()
        }


class ValidationTool(BaseTool):
    """Tool for data validation."""
    
    def __init__(self, tool_name: str, validation_config: Dict[str, Any]):
        super().__init__(tool_name, timeout_seconds=10)
        self.validation_config = validation_config
    
    async def _execute_impl(
        self,
        data: Any,
        validation_type: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate data."""
        self.logger.info(f"Validating data with type: {validation_type}")
        
        # Mock implementation
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }


class ToolRegistry:
    """Registry for managing tool instances."""
    
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool):
        """Register a tool."""
        cls._tools[tool.tool_name] = tool
        logger.info(f"Registered tool: {tool.tool_name}")
    
    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return cls._tools.get(tool_name)
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tools."""
        return list(cls._tools.keys())
    
    @classmethod
    async def execute_tool(
        cls,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """Execute a tool by name."""
        tool = cls.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}"
            )
        
        return await tool.execute(**kwargs)


class ToolChain:
    """Chain multiple tools together."""
    
    def __init__(self, chain_name: str):
        self.chain_name = chain_name
        self.tools: List[tuple[str, Dict[str, Any]]] = []
        self.logger = logging.getLogger(f"{__name__}.{chain_name}")
    
    def add_tool(self, tool_name: str, **kwargs):
        """Add a tool to the chain."""
        self.tools.append((tool_name, kwargs))
    
    async def execute(self, initial_data: Any = None) -> List[ToolResult]:
        """Execute all tools in the chain."""
        results = []
        current_data = initial_data
        
        self.logger.info(f"Executing tool chain: {self.chain_name}")
        
        for tool_name, kwargs in self.tools:
            # Pass previous result as input if available
            if current_data is not None:
                kwargs["input_data"] = current_data
            
            result = await ToolRegistry.execute_tool(tool_name, **kwargs)
            results.append(result)
            
            if not result.success:
                self.logger.error(f"Tool chain failed at {tool_name}: {result.error}")
                break
            
            # Use result data for next tool
            current_data = result.data
        
        return results


# Utility functions for common tool patterns
async def execute_parallel_tools(
    tool_configs: List[tuple[str, Dict[str, Any]]]
) -> List[ToolResult]:
    """Execute multiple tools in parallel."""
    tasks = []
    
    for tool_name, kwargs in tool_configs:
        task = ToolRegistry.execute_tool(tool_name, **kwargs)
        tasks.append(task)
    
    return await asyncio.gather(*tasks, return_exceptions=True)


async def execute_conditional_tool(
    condition_func: callable,
    true_tool: tuple[str, Dict[str, Any]],
    false_tool: tuple[str, Dict[str, Any]],
    condition_data: Any
) -> ToolResult:
    """Execute tool based on condition."""
    if condition_func(condition_data):
        tool_name, kwargs = true_tool
    else:
        tool_name, kwargs = false_tool
    
    return await ToolRegistry.execute_tool(tool_name, **kwargs)


def create_retry_tool(
    base_tool_name: str,
    max_retries: int = 3,
    delay_seconds: float = 1.0
) -> BaseTool:
    """Create a retryable version of a tool."""
    
    class RetryTool(BaseTool):
        def __init__(self):
            super().__init__(f"{base_tool_name}_retry")
            self.base_tool_name = base_tool_name
            self.max_retries = max_retries
            self.delay_seconds = delay_seconds
        
        async def _execute_impl(self, **kwargs) -> Any:
            for attempt in range(self.max_retries + 1):
                result = await ToolRegistry.execute_tool(self.base_tool_name, **kwargs)
                
                if result.success:
                    return result.data
                
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Tool {self.base_tool_name} failed (attempt {attempt + 1}), retrying..."
                    )
                    await asyncio.sleep(self.delay_seconds * (2 ** attempt))
                else:
                    raise Exception(f"Tool failed after {self.max_retries} retries: {result.error}")
    
    return RetryTool()


# Decorators for tool functions
def tool(tool_name: str, timeout_seconds: int = 30):
    """Decorator to convert a function into a tool."""
    def decorator(func):
        class FunctionTool(BaseTool):
            def __init__(self):
                super().__init__(tool_name, timeout_seconds)
                self.func = func
            
            async def _execute_impl(self, **kwargs) -> Any:
                if asyncio.iscoroutinefunction(self.func):
                    return await self.func(**kwargs)
                else:
                    return self.func(**kwargs)
        
        # Register the tool
        tool_instance = FunctionTool()
        ToolRegistry.register(tool_instance)
        
        return func
    
    return decorator


# Common tool configurations
def create_service_http_tool(service_name: str, base_url: str) -> HTTPClientTool:
    """Create HTTP tool for a service."""
    return HTTPClientTool(
        tool_name=f"{service_name}_http",
        base_url=base_url,
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"langgraph-workflow/{service_name}"
        }
    )


def create_model_inference_tool(model_name: str, model_config: Dict[str, Any]) -> ModelInferenceTool:
    """Create model inference tool."""
    return ModelInferenceTool(
        tool_name=f"{model_name}_inference",
        model_config=model_config,
        timeout_seconds=120
    )


def create_storage_tool(storage_type: str, config: Dict[str, Any]) -> FileStorageTool:
    """Create file storage tool."""
    return FileStorageTool(
        tool_name=f"{storage_type}_storage",
        storage_config=config,
        timeout_seconds=60
    )
