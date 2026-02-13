"""
Pydantic schemas for Order of Work (OT) operations.
Provides request/response models with ORM mode support for database integration.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS
# ============================================================================


class OTStatus(str, Enum):
    """
    OT workflow states.
    
    State transitions:
    PREPLANIFICADA -> PLANIFICADA -> ASIGNADO_TAREA -> DETENIDA/FINALIZADA
    DETENIDA -> ANULADA (after 30 days)
    Any state can transition to ANULADA manually
    """

    PREPLANIFICADA = "PREPLANIFICADA"
    """Initial state: OT received but not yet planned"""

    PLANIFICADA = "PLANIFICADA"
    """Planning agent has processed but not assigned to crew"""

    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    """Assigned to a crew and waiting for execution"""

    DETENIDA = "DETENIDA"
    """Temporarily stopped (waiting for materials, client, weather, permits)"""

    ANULADA = "ANULADA"
    """Cancelled (manually or by governance after 30-day inactivity)"""

    FINALIZADA = "FINALIZADA"
    """Completed successfully"""


class ProjectType(str, Enum):
    """
    Project types with different business rules.
    
    PUBLICO: Requires 29 mandatory documents in TelcoDrive before finalization
    PRIVADO: Standard process with photo evidence and digital signatures
    TERCERIZADO: External company management with SLA constraints
    """

    PUBLICO = "PUBLICO"
    """Public/government project: strictest governance (29 docs required)"""

    PRIVADO = "PRIVADO"
    """Private client: standard process"""

    TERCERIZADO = "TERCERIZADO"
    """Third-party/outsourced: external company SLAs apply"""


# ============================================================================
# BASE SCHEMAS
# ============================================================================


class OTBase(BaseModel):
    """
    Base OT schema with core fields common to all OT operations.
    
    Attributes:
        external_id: Unique identifier from TELCOS BSS system
        status: Current workflow state
        project_type: Project classification (PUBLICO, PRIVADO, TERCERIZADO)
        cliente_id: Customer ID from BSS
        login_id: Service point ID with coordinates
        lat: Latitude coordinate (optional, marks as geo_error if missing)
        long: Longitude coordinate (optional, marks as geo_error if missing)
    """

    external_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique identifier from TELCOS/BSS system",
        example="OT-2024-001234",
    )

    status: OTStatus = Field(
        default=OTStatus.PREPLANIFICADA,
        description="Current OT workflow state",
    )

    project_type: ProjectType = Field(
        ...,
        description="Project classification for business rules",
    )

    cliente_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Customer ID from BSS",
        example="CLI-12345",
    )

    login_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Service point ID where installation occurs",
        example="LOGIN-67890",
    )

    lat: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (-90 to 90)",
        example=-0.22,
    )

    long: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (-180 to 180)",
        example=-78.51,
    )

    class Config:
        """Pydantic configuration for OTBase"""
        from_attributes = True


# ============================================================================
# CREATE SCHEMA
# ============================================================================


class OTCreate(OTBase):
    """
    Schema for creating a new OT.
    Inherits all required fields from OTBase.
    Used for POST /api/v1/ots endpoint.
    
    Example:
        {
            "external_id": "OT-2024-001234",
            "project_type": "PUBLICO",
            "cliente_id": "CLI-12345",
            "login_id": "LOGIN-67890",
            "lat": -0.22,
            "long": -78.51
        }
    """

    pass


# ============================================================================
# UPDATE SCHEMA
# ============================================================================


class OTUpdate(BaseModel):
    """
    Schema for updating an existing OT.
    All fields are optional (partial updates supported).
    Used for PUT /api/v1/ots/{ot_id} endpoint.
    
    Note:
        - external_id cannot be updated (primary identifier)
        - For status changes, use POST /api/v1/ots/{ot_id}/change-status
    
    Example:
        {
            "status": "PLANIFICADA",
            "project_type": "PRIVADO",
            "lat": -0.25,
            "long": -78.48
        }
    """

    status: Optional[OTStatus] = Field(
        default=None,
        description="New OT status",
    )

    project_type: Optional[ProjectType] = Field(
        default=None,
        description="New project type",
    )

    cliente_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Updated customer ID",
    )

    login_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Updated service point ID",
    )

    lat: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Updated latitude",
    )

    long: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Updated longitude",
    )

    class Config:
        """Pydantic configuration for OTUpdate"""
        from_attributes = True


# ============================================================================
# DATABASE SCHEMA (WITH ID AND TIMESTAMPS)
# ============================================================================


class OTInDB(OTBase):
    """
    OT schema as stored in database.
    Includes auto-generated id, timestamps, and derived fields.
    Internal use (not exposed in API responses directly).
    
    Attributes:
        id: UUID primary key (auto-generated)
        created_at: Timestamp when OT was created
        updated_at: Timestamp when OT was last updated
        cuadrilla_id: Assigned crew UUID (nullable, may be None if unassigned)
        geo_error: True if coordinates are invalid or missing
    """

    id: str = Field(
        ...,
        description="Unique UUID identifier",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    created_at: datetime = Field(
        ...,
        description="Timestamp when OT was created",
    )

    updated_at: datetime = Field(
        ...,
        description="Timestamp when OT was last updated",
    )

    cuadrilla_id: Optional[str] = Field(
        default=None,
        description="Assigned crew UUID (None if unassigned)",
    )

    geo_error: bool = Field(
        default=False,
        description="True if coordinates are invalid or missing",
    )

    class Config:
        """Pydantic configuration for OTInDB"""
        from_attributes = True


# ============================================================================
# RESPONSE SCHEMA (WITH RELATED DATA)
# ============================================================================


class OTResponse(OTInDB):
    """
    OT schema for API responses.
    Includes all database fields plus relationships.
    Returned by GET endpoints.
    
    This schema includes optional cuadrilla information to show which crew
    is assigned to this OT. The cuadrilla field is populated only if the OT
    has been assigned (cuadrilla_id is not None).
    
    Example response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "external_id": "OT-2024-001234",
            "status": "ASIGNADO_TAREA",
            "project_type": "PUBLICO",
            "cliente_id": "CLI-12345",
            "login_id": "LOGIN-67890",
            "lat": -0.22,
            "long": -78.51,
            "created_at": "2024-02-13T15:30:45.123456",
            "updated_at": "2024-02-13T16:45:30.654321",
            "cuadrilla_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "geo_error": false,
            "cuadrilla": {
                "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "name": "Cuadrilla Quito-01",
                "type": "PRINCIPAL",
                "current_load": 8,
                "daily_capacity": 10,
                "active": true
            }
        }
    """

    # Import here to avoid circular dependency
    cuadrilla: Optional["CuadrillaResponse"] = Field(
        default=None,
        description="Assigned crew details (if OT is assigned)",
    )

    class Config:
        """Pydantic configuration for OTResponse"""
        from_attributes = True


# ============================================================================
# MINIMAL CUADRILLA RESPONSE (to avoid circular imports)
# ============================================================================


class CuadrillaResponse(BaseModel):
    """
    Minimal crew information included in OT responses.
    
    This is a forward declaration to avoid circular imports.
    The full CuadrillaResponse model is defined in schemas/cuadrilla.py
    
    Attributes:
        id: Crew UUID
        name: Crew name (unique)
        type: Crew type (PRINCIPAL or RESERVA)
        last_centroid_lat: Last calculated centroid latitude
        last_centroid_long: Last calculated centroid longitude
        current_load: Number of currently assigned OTs
        daily_capacity: Maximum OTs crew can handle per day
        active: Whether crew is active
        created_at: Timestamp when crew was created
    """

    id: str = Field(description="Crew UUID")
    name: str = Field(description="Crew name")
    type: str = Field(description="Crew type: PRINCIPAL or RESERVA")
    last_centroid_lat: Optional[float] = Field(default=None)
    last_centroid_long: Optional[float] = Field(default=None)
    current_load: int = Field(description="Current number of assigned OTs")
    daily_capacity: int = Field(description="Maximum daily capacity")
    active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# LIST RESPONSE SCHEMA
# ============================================================================


class OTListResponse(BaseModel):
    """
    Paginated list response for OT queries.
    
    Used by GET /api/v1/ots with pagination support.
    
    Example:
        {
            "items": [
                { ... OT response 1 ... },
                { ... OT response 2 ... }
            ],
            "total": 150,
            "page": 1,
            "page_size": 10,
            "total_pages": 15
        }
    """

    items: List[OTResponse] = Field(description="OTs in current page")
    total: int = Field(description="Total number of OTs")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# FILTER SCHEMA FOR LIST QUERIES
# ============================================================================


class OTFilters(BaseModel):
    """
    Query filters for listing OTs.
    
    Used by GET /api/v1/ots?status=ASIGNADO_TAREA&project_type=PUBLICO&page=1
    
    Attributes:
        status: Filter by OT status
        project_type: Filter by project type
        cuadrilla_id: Filter by assigned crew
        geo_error_only: If True, return only OTs with geo_error=True
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
    """

    status: Optional[OTStatus] = Field(
        default=None,
        description="Filter by OT status",
    )

    project_type: Optional[ProjectType] = Field(
        default=None,
        description="Filter by project type",
    )

    cuadrilla_id: Optional[str] = Field(
        default=None,
        description="Filter OTs assigned to specific crew",
    )

    geo_error_only: bool = Field(
        default=False,
        description="If True, return only OTs with geo_error=True",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )

    page_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# STATUS CHANGE SCHEMA
# ============================================================================


class StatusChangeRequest(BaseModel):
    """
    Request body for status change operation.
    Used by POST /api/v1/ots/{ot_id}/change-status
    
    This is used for drag-and-drop status changes via the Kanban board,
    requiring validation by RouterAgent and GobernanzaAgent.
    
    Attributes:
        new_status: Target OT status
        reason: Required reason if moving to DETENIDA status
    
    Example:
        {
            "new_status": "DETENIDA",
            "reason": "FALTA_MATERIAL"
        }
    """

    new_status: OTStatus = Field(
        ...,
        description="Target OT status",
    )

    reason: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Reason for status change (required if moving to DETENIDA)",
        example="Cliente no disponible",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class StatusChangeResponse(BaseModel):
    """
    Response for status change operation.
    Returned by POST /api/v1/ots/{ot_id}/change-status
    
    Attributes:
        success: Whether status change was successful
        message: User-friendly message about the operation
        rollback: If True, client should revert the visual change
        validation_details: Details about any validation failures
    
    Example success:
        {
            "success": true,
            "message": "OT status changed to DETENIDA",
            "rollback": false,
            "validation_details": {}
        }
    
    Example failure:
        {
            "success": false,
            "message": "Cannot finalize PUBLIC project without 29 documents",
            "rollback": true,
            "validation_details": {
                "required_documents": 29,
                "completed_documents": 25,
                "missing_documents": ["Doc1", "Doc2", "Doc3", "Doc4"]
            }
        }
    """

    success: bool = Field(
        ...,
        description="Whether status change was successful",
    )

    message: str = Field(
        ...,
        description="User-friendly message about the operation result",
    )

    rollback: bool = Field(
        ...,
        description="If True, client should revert visual change (operation failed)",
    )

    validation_details: dict = Field(
        default_factory=dict,
        description="Additional validation details if applicable",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# ADDITIONAL UTILITY SCHEMAS
# ============================================================================


class OTStatistics(BaseModel):
    """
    Statistics about OTs grouped by status and project type.
    Used by GET /api/v1/dashboard/stats
    
    Example:
        {
            "total": 150,
            "by_status": {
                "PREPLANIFICADA": 25,
                "PLANIFICADA": 45,
                "ASIGNADO_TAREA": 60,
                "DETENIDA": 15,
                "ANULADA": 3,
                "FINALIZADA": 2
            },
            "by_project_type": {
                "PUBLICO": 80,
                "PRIVADO": 50,
                "TERCERIZADO": 20
            },
            "geo_errors": 5,
            "unassigned": 20
        }
    """

    total: int = Field(description="Total number of OTs")

    by_status: dict = Field(
        description="Count of OTs by status",
        example={
            "PREPLANIFICADA": 25,
            "PLANIFICADA": 45,
        },
    )

    by_project_type: dict = Field(
        description="Count of OTs by project type",
        example={
            "PUBLICO": 80,
            "PRIVADO": 50,
        },
    )

    geo_errors: int = Field(
        description="Count of OTs with invalid coordinates",
    )

    unassigned: int = Field(
        description="Count of OTs not assigned to any crew",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# VALIDATORS
# ============================================================================


@field_validator("external_id", mode="before")
def validate_external_id(cls, v):
    """
    Validate external_id format.
    Should be alphanumeric with hyphens, no special characters.
    """
    if not v:
        raise ValueError("external_id cannot be empty")

    # Allow alphanumeric, hyphens, underscores
    if not all(c.isalnum() or c in "-_" for c in v):
        raise ValueError(
            "external_id can only contain letters, numbers, hyphens, and underscores"
        )

    return v


# ============================================================================
# FORWARD REFERENCE RESOLUTION
# ============================================================================

# Update forward references after all models are defined
OTResponse.model_rebuild()

