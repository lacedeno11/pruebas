"""
Pydantic schemas for LogAgente (Agent Log) models.

This module defines request/response schemas for logging agent actions:

ResultadoEnum:
    SUCCESS: Operation completed successfully
    FAILURE: Operation failed with error
    PENDING: Operation is in progress or awaiting processing

AgenteEnum:
    ROUTER: Router agent that classifies intents
    OTS: OTS agent that ingests work orders
    PLANIFICACION: Planning agent that assigns OTs to crews
    GOBERNANZA: Governance agent that monitors state and alerts
    COMUNICACION: Communication agent that sends notifications

Schema Classes:
    LogAgenteBase: Common fields for all log schemas
    LogAgenteCreate: Request body for creating logs
    LogAgenteResponse: Response body for retrieving logs
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ResultadoEnum(str, Enum):
    """Agent operation result enumeration."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


class AgenteEnum(str, Enum):
    """Agent type enumeration."""

    ROUTER = "ROUTER"
    OTS = "OTS"
    PLANIFICACION = "PLANIFICACION"
    GOBERNANZA = "GOBERNANZA"
    COMUNICACION = "COMUNICACION"


class LogAgenteBase(BaseModel):
    """
    Base schema with common fields for all LogAgente operations.

    Fields:
        agente_name: Agent that performed the action (AgenteEnum value)
        accion: Description of the action performed
        resultado: Result status of the operation (SUCCESS, FAILURE, PENDING)
    """

    agente_name: str = Field(
        ...,
        description="Agent name (ROUTER, OTS, PLANIFICACION, GOBERNANZA, COMUNICACION)",
        example="PLANIFICACION",
    )
    accion: str = Field(
        ...,
        description="Description of the action performed",
        example="Phase 1: Assigned OT-2024-001 to crew Cuadrilla Norte A",
    )
    resultado: ResultadoEnum = Field(
        ...,
        description="Result status of the operation",
        example=ResultadoEnum.SUCCESS,
    )


class LogAgenteCreate(LogAgenteBase):
    """
    Schema for creating agent logs (typically called internally by agents).

    Extends LogAgenteBase with optional fields for additional context:
    - ot_id: Associated OT (null for system-level logs)
    - raw_llm_response: Raw response from LLM if using AI
    - error_details: Error message/stack trace if failure occurred

    Example:
        {
            "agente_name": "PLANIFICACION",
            "accion": "Phase 1: Assigned OT-2024-001 to crew Cuadrilla Norte A",
            "resultado": "SUCCESS",
            "ot_id": 1,
            "raw_llm_response": null,
            "error_details": null
        }

        {
            "agente_name": "OTS",
            "accion": "Ingestion attempt for OT with missing coordinates",
            "resultado": "FAILURE",
            "ot_id": 5,
            "raw_llm_response": {
                "reasoning": "Coordinates missing for location validation",
                "decision": "set_error_geo_status"
            },
            "error_details": "Missing latitude/longitude for OT-2024-005"
        }
    """

    ot_id: Optional[int] = Field(
        None,
        description="Associated OT ID (null for system-level logs)",
        example=1,
    )
    raw_llm_response: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw response from LLM if using AI (JSON)",
        example={
            "reasoning": "OT within 8.5km of crew centroid",
            "decision": "assign_to_crew"
        },
    )
    error_details: Optional[str] = Field(
        None,
        description="Error message or stack trace if failure occurred",
        example="HTTPError: 503 Service Unavailable from external API",
    )


class LogAgenteResponse(LogAgenteBase):
    """
    Schema for agent log responses (GET /system/logs).

    Extends LogAgenteBase with database-generated fields and metadata.
    Uses ConfigDict(from_attributes=True) for SQLAlchemy ORM mapping.

    Fields (from LogAgenteBase):
        agente_name, accion, resultado

    Additional Fields:
        id: Database primary key
        ot_id: Associated OT ID (null for system-level logs)
        raw_llm_response: Raw LLM response if applicable
        error_details: Error details if operation failed
        created_at: Timestamp when log was created (UTC)

    Example:
        {
            "id": 1,
            "agente_name": "PLANIFICACION",
            "accion": "Phase 1: Assigned OT-2024-001 to crew Cuadrilla Norte A",
            "resultado": "SUCCESS",
            "ot_id": 1,
            "raw_llm_response": null,
            "error_details": null,
            "created_at": "2024-01-15T10:30:00Z"
        }

        {
            "id": 2,
            "agente_name": "GOBERNANZA",
            "accion": "Inactivity alert: OT in PREPLANIFICADA for 52h",
            "resultado": "PENDING",
            "ot_id": 10,
            "raw_llm_response": {
                "alert_type": "inactivity",
                "severity": "HIGH",
                "notification_queued": true
            },
            "error_details": null,
            "created_at": "2024-01-15T14:45:00Z"
        }
    """

    id: int = Field(
        ...,
        description="Database primary key",
        example=1,
    )
    ot_id: Optional[int] = Field(
        None,
        description="Associated OT ID (null for system-level logs)",
        example=1,
    )
    raw_llm_response: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw response from LLM if using AI (JSON)",
    )
    error_details: Optional[str] = Field(
        None,
        description="Error message or stack trace if failure occurred",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when log was created (UTC)",
        example="2024-01-15T10:30:00Z",
    )

    # Enable ORM mode for SQLAlchemy model mapping
    model_config = ConfigDict(from_attributes=True)


class LogAgentePaginatedResponse(BaseModel):
    """
    Schema for paginated agent log list responses (GET /system/logs with pagination).

    Fields:
        items: List of LogAgenteResponse objects
        total: Total number of logs matching filters
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    items: list[LogAgenteResponse] = Field(
        default_factory=list,
        description="List of agent logs",
    )
    total: int = Field(
        ...,
        description="Total number of logs matching the filters",
        example=500,
    )
    page: int = Field(
        default=1,
        description="Current page number (1-indexed)",
        example=1,
    )
    page_size: int = Field(
        default=50,
        description="Number of items per page",
        example=50,
    )
    total_pages: int = Field(
        ...,
        description="Total number of pages",
        example=10,
    )


class LogAgenteFilter(BaseModel):
    """
    Schema for filtering agent logs (GET /system/logs query parameters).

    Fields:
        agente_name: Filter by agent (optional)
        resultado: Filter by result status (optional)
        ot_id: Filter by OT ID (optional)
        date_from: Start date for date range filter (ISO format)
        date_to: End date for date range filter (ISO format)
        page: Page number for pagination (default=1)
        page_size: Items per page (default=50)
    """

    agente_name: Optional[str] = Field(
        None,
        description="Filter by agent name",
        example="PLANIFICACION",
    )
    resultado: Optional[str] = Field(
        None,
        description="Filter by result status",
        example="SUCCESS",
    )
    ot_id: Optional[int] = Field(
        None,
        description="Filter by associated OT ID",
        example=1,
    )
    date_from: Optional[datetime] = Field(
        None,
        description="Start date for date range filter (ISO format)",
        example="2024-01-15T00:00:00Z",
    )
    date_to: Optional[datetime] = Field(
        None,
        description="End date for date range filter (ISO format)",
        example="2024-01-15T23:59:59Z",
    )
    page: int = Field(
        default=1,
        description="Page number for pagination (1-indexed)",
        ge=1,
    )
    page_size: int = Field(
        default=50,
        description="Number of items per page",
        ge=1,
        le=500,
    )


class AgentActionSummary(BaseModel):
    """
    Schema for summarizing agent actions for a specific operation.

    Used by agent responses to provide a summary of what was executed.

    Fields:
        agent_name: Name of the agent that executed
        action: Description of the action performed
        result: SUCCESS, FAILURE, or PENDING
        duration_ms: Time taken to complete (milliseconds)
        affected_ots: List of OT IDs affected
        affected_crews: List of crew IDs affected
        metadata: Additional context as key-value pairs
    """

    agent_name: str = Field(
        ...,
        description="Agent that executed the action",
        example="PLANIFICACION",
    )
    action: str = Field(
        ...,
        description="Description of the action",
        example="Phase 1: Initial Balance - Assigned 5 OTs",
    )
    result: ResultadoEnum = Field(
        ...,
        description="Result status",
        example=ResultadoEnum.SUCCESS,
    )
    duration_ms: int = Field(
        ...,
        description="Time taken to complete in milliseconds",
        example=1250,
    )
    affected_ots: List[int] = Field(
        default_factory=list,
        description="List of OT IDs affected by this action",
        example=[1, 2, 3, 4, 5],
    )
    affected_crews: List[int] = Field(
        default_factory=list,
        description="List of crew IDs affected by this action",
        example=[1, 2, 3],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context as key-value pairs",
        example={
            "phase": "BALANCE",
            "crews_processed": 5,
            "warnings": 0
        },
    )


class AgentExecutionTrace(BaseModel):
    """
    Schema for detailed execution trace of an agent workflow.

    Used for debugging and understanding agent decision-making process.

    Fields:
        workflow_id: Unique workflow identifier
        started_at: When the workflow started
        completed_at: When the workflow completed
        status: Overall workflow status
        agent_logs: List of all agent actions in sequence
        errors: List of any errors that occurred
        total_duration_ms: Total time for entire workflow
    """

    workflow_id: str = Field(
        ...,
        description="Unique workflow identifier (UUID or trace ID)",
        example="workflow_abc123def456",
    )
    started_at: datetime = Field(
        ...,
        description="When the workflow started (UTC)",
        example="2024-01-15T10:30:00Z",
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When the workflow completed (UTC)",
        example="2024-01-15T10:35:00Z",
    )
    status: str = Field(
        ...,
        description="Overall workflow status",
        example="COMPLETED",
    )
    agent_logs: List[LogAgenteResponse] = Field(
        default_factory=list,
        description="List of all agent actions in sequence",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of any errors that occurred",
        example=[],
    )
    total_duration_ms: int = Field(
        ...,
        description="Total time for entire workflow in milliseconds",
        example=5000,
    )

