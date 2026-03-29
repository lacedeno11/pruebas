"""
Pydantic schemas for Work Order (OT) models.

This module defines request/response schemas for OT operations:

OTStatus Enum:
    PREPLANIFICADA: Initial state, awaiting planning
    PLANIFICADA: Assigned to crew, ready for execution
    ASIGNADO_TAREA: Task assigned to technician
    DETENIDA: Paused/blocked, requires intervention
    ANULADA: Cancelled, terminal state
    FINALIZADA: Completed successfully, terminal state
    ERROR_GEO: Missing coordinates, blocking state

ProjectType Enum:
    PUBLICO: Public sector project (requires 29 documents for completion)
    PRIVADO: Private sector project
    TERCERIZADO: Outsourced/third-party project

Schema Classes:
    OTBase: Common fields shared across all OT schemas
    OTCreate: Request body for POST /ots
    OTUpdate: Request body for PATCH /ots/{id}
    OTResponse: Response body for GET /ots and transitions
    OTTransitionRequest: Request body for POST /ots/{id}/transition
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class OTStatus(str, Enum):
    """Work Order status enumeration."""

    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"
    ERROR_GEO = "ERROR_GEO"


class ProjectType(str, Enum):
    """Project type enumeration."""

    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class OTBase(BaseModel):
    """
    Base schema with common fields for all OT operations.

    Fields:
        external_id: Unique identifier from external system (TELCOS)
        cliente_id: Client/customer identifier
        login: Associated login or username
        lat: Latitude coordinate (nullable - triggers ERROR_GEO if missing)
        long: Longitude coordinate (nullable - triggers ERROR_GEO if missing)
        project_type: Project type (PUBLICO, PRIVADO, TERCERIZADO)
    """

    external_id: str = Field(
        ...,
        description="Unique OT identifier from external system",
        example="OT-2024-001",
    )
    cliente_id: str = Field(
        ...,
        description="Client/customer identifier",
        example="CLIENTE-123",
    )
    login: str = Field(
        ...,
        description="Associated login or username for the work order",
        example="user@example.com",
    )
    lat: Optional[float] = Field(
        None,
        description="Latitude coordinate in decimal degrees (-90 to 90)",
        example=-0.1807,
    )
    long: Optional[float] = Field(
        None,
        description="Longitude coordinate in decimal degrees (-180 to 180)",
        example=-78.4678,
    )
    project_type: ProjectType = Field(
        ...,
        description="Type of project (PUBLICO requires 29 documents)",
        example=ProjectType.PUBLICO,
    )


class OTCreate(OTBase):
    """
    Schema for creating new work orders (POST /ots).

    Extends OTBase with all required fields. Inherits validation
    from OTBase to ensure coordinates are within valid ranges
    and project_type is one of the allowed values.

    Example:
        {
            "external_id": "OT-2024-001",
            "cliente_id": "CLIENTE-123",
            "login": "user@example.com",
            "lat": -0.1807,
            "long": -78.4678,
            "project_type": "PUBLICO"
        }
    """

    pass


class OTUpdate(BaseModel):
    """
    Schema for updating work orders (PATCH /ots/{id}).

    All fields are optional. Only provided fields will be updated.
    This allows partial updates without requiring all fields.

    Fields:
        external_id: Optional update to external ID
        cliente_id: Optional update to client ID
        login: Optional update to login
        lat: Optional update to latitude
        long: Optional update to longitude
        project_type: Optional update to project type
    """

    external_id: Optional[str] = Field(
        None,
        description="Update OT identifier",
    )
    cliente_id: Optional[str] = Field(
        None,
        description="Update client identifier",
    )
    login: Optional[str] = Field(
        None,
        description="Update login",
    )
    lat: Optional[float] = Field(
        None,
        description="Update latitude coordinate",
    )
    long: Optional[float] = Field(
        None,
        description="Update longitude coordinate",
    )
    project_type: Optional[ProjectType] = Field(
        None,
        description="Update project type",
    )


class OTResponse(OTBase):
    """
    Schema for OT responses (GET /ots, POST /ots, PATCH /ots/{id}).

    Extends OTBase with database-generated fields and additional state.
    Uses ConfigDict(from_attributes=True) for SQLAlchemy ORM mapping.

    Fields (from OTBase):
        external_id, cliente_id, login, lat, long, project_type

    Additional Fields:
        id: Database primary key
        status: Current OT status
        created_at: Timestamp when OT was created
        updated_at: Timestamp of last update
        cuadrilla_id: ID of assigned crew (null if unassigned)
        detention_reason: Reason for DETENIDA status (if applicable)
        detention_date: Timestamp when OT entered DETENIDA status

    Example:
        {
            "id": 1,
            "external_id": "OT-2024-001",
            "cliente_id": "CLIENTE-123",
            "login": "user@example.com",
            "lat": -0.1807,
            "long": -78.4678,
            "project_type": "PUBLICO",
            "status": "PLANIFICADA",
            "cuadrilla_id": 5,
            "detention_reason": null,
            "detention_date": null,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:35:00Z"
        }
    """

    id: int = Field(
        ...,
        description="Database primary key",
        example=1,
    )
    status: OTStatus = Field(
        ...,
        description="Current work order status",
        example=OTStatus.PLANIFICADA,
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when OT was created (UTC)",
        example="2024-01-15T10:30:00Z",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of last update (UTC)",
        example="2024-01-15T10:35:00Z",
    )
    cuadrilla_id: Optional[int] = Field(
        None,
        description="ID of assigned crew (null if unassigned)",
        example=5,
    )
    detention_reason: Optional[str] = Field(
        None,
        description="Reason for DETENIDA status (if applicable)",
        example="Weather conditions - waiting for clearance",
    )
    detention_date: Optional[datetime] = Field(
        None,
        description="Timestamp when OT entered DETENIDA status (UTC)",
        example="2024-01-15T14:00:00Z",
    )

    # Enable ORM mode for SQLAlchemy model mapping
    model_config = ConfigDict(from_attributes=True)


class OTTransitionRequest(BaseModel):
    """
    Schema for state transitions (POST /ots/{id}/transition).

    Handles OT status changes with optional crew assignment and reason.

    Fields:
        new_status: Target status for the transition
        cuadrilla_id: Crew ID (required for PLANIFICADA/ASIGNADO_TAREA)
        reason: Transition reason (required for DETENIDA, optional for others)

    Examples:
        Transition to PLANIFICADA (assign crew):
        {
            "new_status": "PLANIFICADA",
            "cuadrilla_id": 5
        }

        Transition to DETENIDA (with reason):
        {
            "new_status": "DETENIDA",
            "reason": "Weather conditions - waiting for clearance"
        }

        Transition to FINALIZADA:
        {
            "new_status": "FINALIZADA"
        }

        Transition to ANULADA (cancel):
        {
            "new_status": "ANULADA",
            "reason": "Client requested cancellation"
        }
    """

    new_status: OTStatus = Field(
        ...,
        description="Target status for the transition",
        example=OTStatus.PLANIFICADA,
    )
    cuadrilla_id: Optional[int] = Field(
        None,
        description="Crew ID for assignment (required for PLANIFICADA/ASIGNADO_TAREA)",
        example=5,
    )
    reason: Optional[str] = Field(
        None,
        description="Transition reason (required for DETENIDA, optional for others)",
        example="Weather conditions - waiting for clearance",
    )


class OTPaginatedResponse(BaseModel):
    """
    Schema for paginated OT list responses (GET /ots with pagination).

    Fields:
        items: List of OT responses
        total: Total number of OTs matching filters
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    items: list[OTResponse] = Field(
        default_factory=list,
        description="List of work orders",
    )
    total: int = Field(
        ...,
        description="Total number of OTs matching the filters",
        example=150,
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
        example=3,
    )

