"""
Pydantic schemas for agent logs and audit trail.
Provides request/response models for persisting and querying agent operations.

Agent logs track all operations performed by the LangGraph agents:
- Agent name and action taken
- Result of the operation (SUCCESS, FAILED, SKIPPED)
- OT affected (if applicable)
- Raw LLM response for debugging
- Correlation ID for request tracing across multi-agent flows
- Timestamp for activity timeline
- Metadata for additional context
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================


class LogResult(str, Enum):
    """
    Result status of an agent operation.
    
    SUCCESS: Operation completed as expected
    FAILED: Operation encountered an error
    SKIPPED: Operation was skipped (e.g., no OTs to process)
    """

    SUCCESS = "SUCCESS"
    """Operation completed successfully"""

    FAILED = "FAILED"
    """Operation failed with error"""

    SKIPPED = "SKIPPED"
    """Operation was skipped"""


class AgentAction(str, Enum):
    """
    Types of actions agents can perform.
    
    Used to categorize and search agent logs.
    """

    # Router Agent actions
    ROUTE_REQUEST = "ROUTE_REQUEST"
    CLASSIFY_INTENT = "CLASSIFY_INTENT"

    # OTS Agent actions
    INGEST_OTS = "INGEST_OTS"
    VALIDATE_COORDINATES = "VALIDATE_COORDINATES"
    MARK_GEO_ERROR = "MARK_GEO_ERROR"

    # Planificacion Agent actions
    PLAN_OTS = "PLAN_OTS"
    ASSIGN_OT = "ASSIGN_OT"
    CALCULATE_CENTROID = "CALCULATE_CENTROID"
    CHECK_DISTANCE = "CHECK_DISTANCE"
    NIGHTLY_NORMALIZATION = "NIGHTLY_NORMALIZATION"

    # Gobernanza Agent actions
    VALIDATE_STATUS_TRANSITION = "VALIDATE_STATUS_TRANSITION"
    CHECK_DOCUMENTS = "CHECK_DOCUMENTS"
    CHECK_INACTIVITY = "CHECK_INACTIVITY"
    AUTO_CANCEL_OT = "AUTO_CANCEL_OT"

    # Comunicacion Agent actions
    SEND_NOTIFICATION = "SEND_NOTIFICATION"
    SEND_TELEGRAM = "SEND_TELEGRAM"
    SEND_EMAIL = "SEND_EMAIL"
    CREATE_ALERT = "CREATE_ALERT"


# ============================================================================
# BASE SCHEMAS
# ============================================================================


class LogBase(BaseModel):
    """
    Base log schema with core fields common to all agent logs.
    
    Attributes:
        agente_name: Which agent performed the action
        accion: Type of action taken
        resultado: Result status (SUCCESS, FAILED, SKIPPED)
    """

    agente_name: str = Field(
        ...,
        description="Agent name: RouterAgent, OTSAgent, PlanificacionAgent, GobernanzaAgent, ComunicacionAgent",
        example="PlanificacionAgent",
    )

    accion: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Action taken by the agent",
        example="ASSIGN_OT",
    )

    resultado: LogResult = Field(
        ...,
        description="Result of the operation: SUCCESS, FAILED, or SKIPPED",
    )

    class Config:
        """Pydantic configuration for LogBase"""
        from_attributes = True


# ============================================================================
# CREATE SCHEMA
# ============================================================================


class LogCreate(LogBase):
    """
    Schema for creating a new agent log entry.
    Inherits core fields from LogBase, adds detailed operation context.
    Used when agents execute operations and need to log results.
    
    Attributes:
        ot_id: Optional OT affected by this operation
        raw_llm_response: Raw response from LLM (for debugging agent reasoning)
        correlation_id: Request tracing ID across multi-agent flows
    
    Example:
        {
            "agente_name": "PlanificacionAgent",
            "accion": "ASSIGN_OT",
            "resultado": "SUCCESS",
            "ot_id": "550e8400-e29b-41d4-a716-446655440000",
            "correlation_id": "req-12345",
            "raw_llm_response": "{\\"thoughts\\": \\"OT-001 assigned to crew 1\\", ...}"
        }
    """

    ot_id: Optional[str] = Field(
        default=None,
        description="OT affected by this operation (if applicable)",
    )

    raw_llm_response: Optional[str] = Field(
        default=None,
        description="Raw LLM response for debugging agent reasoning",
    )

    correlation_id: str = Field(
        ...,
        description="Request correlation ID for tracing across agents",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    class Config:
        """Pydantic configuration for LogCreate"""
        from_attributes = True


# ============================================================================
# DATABASE SCHEMA
# ============================================================================


class LogInDB(LogBase):
    """
    Log schema as stored in database.
    Includes auto-generated id, timestamp, and additional context.
    Internal use (not exposed in API responses directly).
    
    Attributes:
        id: UUID primary key (auto-generated)
        timestamp: When log entry was created
        ot_id: Optional OT affected
        raw_llm_response: Raw LLM response (nullable)
        correlation_id: Request tracing ID
        metadata: Additional context as JSON (structured dict)
    """

    id: str = Field(
        ...,
        description="Unique UUID identifier",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp when log entry was created",
    )

    ot_id: Optional[str] = Field(
        default=None,
        description="OT affected by this operation",
    )

    raw_llm_response: Optional[str] = Field(
        default=None,
        description="Raw LLM response (nullable)",
    )

    correlation_id: str = Field(
        ...,
        description="Request correlation ID for tracing",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context as JSON object",
        example={
            "distance_km": 5.3,
            "crew_load": "8/10",
            "phase": "PROXIMITY",
        },
    )

    class Config:
        """Pydantic configuration for LogInDB"""
        from_attributes = True


# ============================================================================
# RESPONSE SCHEMA
# ============================================================================


class LogResponse(LogInDB):
    """
    Log schema for API responses.
    Includes all database fields, formatted for client consumption.
    Returned by GET endpoints for log retrieval.
    
    Example response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "agente_name": "PlanificacionAgent",
            "accion": "ASSIGN_OT",
            "resultado": "SUCCESS",
            "timestamp": "2024-02-13T16:45:30.654321",
            "ot_id": "550e8400-e29b-41d4-a716-446655440001",
            "correlation_id": "req-12345",
            "raw_llm_response": "{\\"thoughts\\": ...}",
            "metadata": {
                "distance_km": 5.3,
                "crew_load": "8/10",
                "crew_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
            }
        }
    """

    class Config:
        """Pydantic configuration for LogResponse"""
        from_attributes = True


# ============================================================================
# LIST RESPONSE SCHEMA
# ============================================================================


class LogListResponse(BaseModel):
    """
    Paginated list response for log queries.
    
    Used by GET /api/v1/agents/logs with pagination support.
    
    Example:
        {
            "items": [
                { ... log entry 1 ... },
                { ... log entry 2 ... }
            ],
            "total": 1250,
            "page": 1,
            "page_size": 50,
            "total_pages": 25
        }
    """

    items: list[LogResponse] = Field(description="Logs in current page")
    total: int = Field(description="Total number of logs")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# FILTER SCHEMA
# ============================================================================


class LogFilters(BaseModel):
    """
    Query filters for retrieving agent logs.
    
    Used by GET /api/v1/agents/logs endpoint.
    
    Attributes:
        agent_name: Filter by agent (RouterAgent, OTSAgent, etc.)
        accion: Filter by action type
        resultado: Filter by result (SUCCESS, FAILED, SKIPPED)
        ot_id: Filter by affected OT
        correlation_id: Filter by request trace ID (multi-agent tracing)
        from_timestamp: Start of date range
        to_timestamp: End of date range
        page: Page number (1-indexed)
        page_size: Items per page (max 500)
    """

    agent_name: Optional[str] = Field(
        default=None,
        description="Filter by agent name",
    )

    accion: Optional[str] = Field(
        default=None,
        description="Filter by action type",
    )

    resultado: Optional[LogResult] = Field(
        default=None,
        description="Filter by result: SUCCESS, FAILED, or SKIPPED",
    )

    ot_id: Optional[str] = Field(
        default=None,
        description="Filter by affected OT",
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Filter by correlation ID for tracing multi-agent flows",
    )

    from_timestamp: Optional[datetime] = Field(
        default=None,
        description="Start of date range",
    )

    to_timestamp: Optional[datetime] = Field(
        default=None,
        description="End of date range",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )

    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Items per page (max 500)",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# STATISTICS SCHEMA
# ============================================================================


class LogStatistics(BaseModel):
    """
    Statistics about agent operations.
    
    Used for dashboard and monitoring.
    
    Example:
        {
            "total_logs": 5234,
            "by_agent": {
                "RouterAgent": 1020,
                "OTSAgent": 950,
                "PlanificacionAgent": 1500,
                "GobernanzaAgent": 1200,
                "ComunicacionAgent": 564
            },
            "by_result": {
                "SUCCESS": 4950,
                "FAILED": 200,
                "SKIPPED": 84
            },
            "success_rate": 94.58,
            "average_operation_time_ms": 245.3,
            "operations_today": 312
        }
    """

    total_logs: int = Field(description="Total number of logs")
    by_agent: Dict[str, int] = Field(description="Count by agent name")
    by_result: Dict[str, int] = Field(description="Count by result status")
    success_rate: float = Field(description="Percentage of successful operations")
    average_operation_time_ms: float = Field(description="Average operation duration")
    operations_today: int = Field(description="Operations logged today")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# EXPORT SCHEMAS
# ============================================================================

__all__ = [
    "LogBase",
    "LogCreate",
    "LogInDB",
    "LogResponse",
    "LogListResponse",
    "LogFilters",
    "LogStatistics",
    "LogResult",
    "AgentAction",
]

