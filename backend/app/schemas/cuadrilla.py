"""
Pydantic schemas for Cuadrilla (Crew) models.

This module defines request/response schemas for Cuadrilla operations:

CuadrillaType Enum:
    PRINCIPAL: Primary crew with base load capacity
    RESERVA: Reserve/backup crew activated for overflow or distance constraints

Schema Classes:
    CuadrillaBase: Common fields shared across all Cuadrilla schemas
    CuadrillaCreate: Request body for POST /cuadrillas
    CuadrillaUpdate: Request body for PATCH /cuadrillas/{id}
    CuadrillaResponse: Response body for GET /cuadrillas and crew operations
    CuadrillaWithOTs: Extended response including list of assigned OTs
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from .ot import OTResponse


class CuadrillaType(str, Enum):
    """Crew type enumeration."""

    PRINCIPAL = "PRINCIPAL"
    RESERVA = "RESERVA"


class CuadrillaBase(BaseModel):
    """
    Base schema with common fields for all Cuadrilla operations.

    Fields:
        name: Unique name/identifier for the crew
        type: Crew type (PRINCIPAL or RESERVA)
        max_capacity: Maximum number of OTs crew can handle (default=10)
    """

    name: str = Field(
        ...,
        description="Unique crew name/identifier",
        example="Cuadrilla Norte A",
    )
    type: CuadrillaType = Field(
        ...,
        description="Crew type (PRINCIPAL for base load, RESERVA for overflow)",
        example=CuadrillaType.PRINCIPAL,
    )
    max_capacity: int = Field(
        default=10,
        description="Maximum number of OTs crew can handle",
        example=10,
        ge=1,  # Greater than or equal to 1
        le=100,  # Less than or equal to 100
    )


class CuadrillaCreate(CuadrillaBase):
    """
    Schema for creating new crews (POST /cuadrillas).

    Extends CuadrillaBase with all required fields. Inherits validation
    from CuadrillaBase to ensure type is valid and capacity is in range.

    Example:
        {
            "name": "Cuadrilla Norte A",
            "type": "PRINCIPAL",
            "max_capacity": 10
        }
    """

    pass


class CuadrillaUpdate(BaseModel):
    """
    Schema for updating crews (PATCH /cuadrillas/{id}).

    All fields are optional. Only provided fields will be updated.
    Allows selective updates without requiring all fields.

    Fields:
        name: Optional update to crew name
        type: Optional update to crew type
        max_capacity: Optional update to crew capacity
    """

    name: Optional[str] = Field(
        None,
        description="Update crew name",
    )
    type: Optional[CuadrillaType] = Field(
        None,
        description="Update crew type",
    )
    max_capacity: Optional[int] = Field(
        None,
        description="Update maximum crew capacity",
        ge=1,
        le=100,
    )


class CuadrillaResponse(CuadrillaBase):
    """
    Schema for crew responses (GET /cuadrillas, POST /cuadrillas, PATCH /cuadrillas/{id}).

    Extends CuadrillaBase with database-generated fields and computed values.
    Uses ConfigDict(from_attributes=True) for SQLAlchemy ORM mapping.

    Fields (from CuadrillaBase):
        name, type, max_capacity

    Additional Fields:
        id: Database primary key
        last_centroid_lat: Last calculated centroid latitude (from Phase 3)
        last_centroid_long: Last calculated centroid longitude (from Phase 3)
        assigned_ots_count: Current number of assigned OTs (computed)
        created_at: Timestamp when crew was created
        updated_at: Timestamp of last update

    Example:
        {
            "id": 1,
            "name": "Cuadrilla Norte A",
            "type": "PRINCIPAL",
            "max_capacity": 10,
            "last_centroid_lat": -0.1807,
            "last_centroid_long": -78.4678,
            "assigned_ots_count": 8,
            "created_at": "2024-01-10T09:00:00Z",
            "updated_at": "2024-01-15T14:30:00Z"
        }
    """

    id: int = Field(
        ...,
        description="Database primary key",
        example=1,
    )
    last_centroid_lat: Optional[float] = Field(
        None,
        description="Last calculated centroid latitude from Phase 3 optimization",
        example=-0.1807,
    )
    last_centroid_long: Optional[float] = Field(
        None,
        description="Last calculated centroid longitude from Phase 3 optimization",
        example=-78.4678,
    )
    assigned_ots_count: int = Field(
        default=0,
        description="Current number of assigned OTs (computed)",
        example=8,
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when crew was created (UTC)",
        example="2024-01-10T09:00:00Z",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of last update (UTC)",
        example="2024-01-15T14:30:00Z",
    )

    # Enable ORM mode for SQLAlchemy model mapping
    model_config = ConfigDict(from_attributes=True)


class CuadrillaWithOTs(CuadrillaResponse):
    """
    Extended crew response including list of assigned OT details.

    Used by endpoints that need to return crew information along with
    all currently assigned work orders for comprehensive crew view.

    Fields (from CuadrillaResponse):
        id, name, type, max_capacity, last_centroid_lat, last_centroid_long,
        assigned_ots_count, created_at, updated_at

    Additional Fields:
        assigned_ots: List of OTResponse objects for OTs assigned to this crew

    Example:
        {
            "id": 1,
            "name": "Cuadrilla Norte A",
            "type": "PRINCIPAL",
            "max_capacity": 10,
            "last_centroid_lat": -0.1807,
            "last_centroid_long": -78.4678,
            "assigned_ots_count": 2,
            "created_at": "2024-01-10T09:00:00Z",
            "updated_at": "2024-01-15T14:30:00Z",
            "assigned_ots": [
                {
                    "id": 1,
                    "external_id": "OT-2024-001",
                    "status": "PLANIFICADA",
                    "project_type": "PUBLICO",
                    "cliente_id": "CLIENTE-123",
                    "login": "user@example.com",
                    "lat": -0.1900,
                    "long": -78.4700,
                    "cuadrilla_id": 1,
                    "detention_reason": null,
                    "detention_date": null,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:35:00Z"
                },
                {
                    "id": 2,
                    "external_id": "OT-2024-002",
                    "status": "ASIGNADO_TAREA",
                    "project_type": "PRIVADO",
                    "cliente_id": "CLIENTE-456",
                    "login": "tech@example.com",
                    "lat": -0.1750,
                    "long": -78.4650,
                    "cuadrilla_id": 1,
                    "detention_reason": null,
                    "detention_date": null,
                    "created_at": "2024-01-14T11:00:00Z",
                    "updated_at": "2024-01-15T11:45:00Z"
                }
            ]
        }
    """

    # Import OTResponse type - using string to avoid circular imports
    assigned_ots: list["OTResponse"] = Field(
        default_factory=list,
        description="List of OT responses for OTs assigned to this crew",
    )

    # Maintain ORM compatibility
    model_config = ConfigDict(from_attributes=True)


class CuadrillaCapacityInfo(BaseModel):
    """
    Crew capacity and utilization information.

    Used by dashboard and crew management endpoints to show
    capacity status and utilization metrics.

    Fields:
        cuadrilla_id: ID of the crew
        name: Crew name
        type: Crew type
        max_capacity: Maximum capacity
        assigned_count: Current assigned OTs
        available_capacity: Remaining available slots (max - assigned)
        utilization_percent: Percentage of capacity used (0-100)
        is_at_capacity: Boolean indicating if crew is fully utilized
    """

    cuadrilla_id: int = Field(
        ...,
        description="Crew ID",
        example=1,
    )
    name: str = Field(
        ...,
        description="Crew name",
        example="Cuadrilla Norte A",
    )
    type: CuadrillaType = Field(
        ...,
        description="Crew type",
        example=CuadrillaType.PRINCIPAL,
    )
    max_capacity: int = Field(
        ...,
        description="Maximum capacity",
        example=10,
    )
    assigned_count: int = Field(
        ...,
        description="Current number of assigned OTs",
        example=8,
    )
    available_capacity: int = Field(
        ...,
        description="Remaining available slots",
        example=2,
    )
    utilization_percent: float = Field(
        ...,
        description="Percentage of capacity utilized (0-100)",
        example=80.0,
    )
    is_at_capacity: bool = Field(
        ...,
        description="Whether crew is at or above max capacity",
        example=False,
    )


class CuadrillaLocationUpdate(BaseModel):
    """
    Schema for updating crew centroid location.

    Used by POST /cuadrillas/{id}/recalculate-centroid endpoint
    to explicitly trigger centroid recalculation.

    Fields:
        recalculate: Boolean flag to trigger recalculation
        reason: Optional reason for manual recalculation
    """

    recalculate: bool = Field(
        default=True,
        description="Trigger centroid recalculation",
    )
    reason: Optional[str] = Field(
        None,
        description="Optional reason for manual recalculation",
        example="Manual optimization requested by user",
    )

