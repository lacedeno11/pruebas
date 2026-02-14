"""
Pydantic schemas for Cuadrilla (Crew/OPU) operations.
Provides request/response models with ORM mode support for crew management.

A Cuadrilla is a technical crew that executes Orders of Work (OTs).
- PRINCIPAL crews: Handle standard workload (50% of total crews)
- RESERVA crews: Handle overflow and long-distance assignments (50% of total crews)
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# ENUMS
# ============================================================================


class CuadrillaType(str, Enum):
    """
    Crew types with different responsibilities.
    
    PRINCIPAL: Main crews handling standard daily workload
    RESERVA: Reserve crews for overflow and critical distances
    """

    PRINCIPAL = "PRINCIPAL"
    """Main crew: handles standard daily assignments"""

    RESERVA = "RESERVA"
    """Reserve crew: activated for overflow or distance constraints"""


# ============================================================================
# BASE SCHEMAS
# ============================================================================


class CuadrillaBase(BaseModel):
    """
    Base Cuadrilla schema with core fields.
    
    Attributes:
        name: Unique crew identifier/name
        type: Crew type (PRINCIPAL or RESERVA)
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique crew name identifier",
        example="Cuadrilla Quito-01",
    )

    type: CuadrillaType = Field(
        ...,
        description="Crew type: PRINCIPAL (standard) or RESERVA (overflow/distance)",
    )

    class Config:
        """Pydantic configuration for CuadrillaBase"""
        from_attributes = True


# ============================================================================
# CREATE SCHEMA
# ============================================================================


class CuadrillaCreate(CuadrillaBase):
    """
    Schema for creating a new Cuadrilla.
    Inherits name and type from CuadrillaBase, adds daily_capacity.
    Used for POST /api/v1/cuadrillas endpoint.
    
    Attributes:
        daily_capacity: Maximum number of OTs crew can handle per day
                       Default is 10, configurable per crew based on team size
    
    Example:
        {
            "name": "Cuadrilla Quito-01",
            "type": "PRINCIPAL",
            "daily_capacity": 10
        }
    """

    daily_capacity: int = Field(
        default=10,
        gt=0,
        le=50,
        description="Maximum daily capacity (OTs per day)",
    )

    @field_validator("daily_capacity")
    @classmethod
    def validate_daily_capacity(cls, v: int) -> int:
        """
        Validate daily_capacity is a positive integer within reasonable bounds.
        
        Args:
            v: Daily capacity value
            
        Returns:
            int: Validated capacity
            
        Raises:
            ValueError: If capacity <= 0 or > 50
        """
        if v <= 0:
            raise ValueError("daily_capacity must be greater than 0")
        if v > 50:
            raise ValueError("daily_capacity cannot exceed 50")
        return v

    class Config:
        """Pydantic configuration for CuadrillaCreate"""
        from_attributes = True


# ============================================================================
# UPDATE SCHEMA
# ============================================================================


class CuadrillaUpdate(BaseModel):
    """
    Schema for updating an existing Cuadrilla.
    All fields are optional (partial updates supported).
    Used for PUT /api/v1/cuadrillas/{cuadrilla_id} endpoint.
    
    Note:
        - name can be updated (with unique constraint check)
        - type is typically read-only after creation (business rule)
        - daily_capacity can be adjusted based on team changes
        - active controls whether crew accepts new assignments
    
    Example:
        {
            "name": "Cuadrilla Quito-01-Updated",
            "daily_capacity": 12,
            "active": false
        }
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated crew name (must be unique)",
    )

    daily_capacity: Optional[int] = Field(
        default=None,
        gt=0,
        le=50,
        description="Updated maximum daily capacity",
    )

    active: Optional[bool] = Field(
        default=None,
        description="Whether crew is active and accepting assignments",
    )

    @field_validator("daily_capacity")
    @classmethod
    def validate_daily_capacity(cls, v: Optional[int]) -> Optional[int]:
        """Validate daily_capacity if provided."""
        if v is None:
            return v
        if v <= 0:
            raise ValueError("daily_capacity must be greater than 0")
        if v > 50:
            raise ValueError("daily_capacity cannot exceed 50")
        return v

    class Config:
        """Pydantic configuration for CuadrillaUpdate"""
        from_attributes = True


# ============================================================================
# DATABASE SCHEMA (WITH ID AND FIELDS)
# ============================================================================


class CuadrillaInDB(CuadrillaBase):
    """
    Cuadrilla schema as stored in database.
    Includes auto-generated id, centroid coordinates, current load, and timestamps.
    Internal use (not exposed in API responses directly).
    
    Attributes:
        id: UUID primary key (auto-generated)
        last_centroid_lat: Last calculated centroid latitude from assigned OTs
        last_centroid_long: Last calculated centroid longitude from assigned OTs
        current_load: Number of currently assigned OTs
        daily_capacity: Maximum daily capacity (inherited from CuadrillaBase or set at creation)
        active: Whether crew is active and accepting assignments
        created_at: Timestamp when crew was created
    
    The centroid represents the geographic center of all OTs assigned to this crew.
    It's used in Phase 2 of the planning algorithm to validate the 10km distance constraint.
    """

    id: str = Field(
        ...,
        description="Unique UUID identifier",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    last_centroid_lat: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Last calculated centroid latitude",
    )

    last_centroid_long: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Last calculated centroid longitude",
    )

    current_load: int = Field(
        default=0,
        ge=0,
        description="Current number of assigned OTs",
    )

    daily_capacity: int = Field(
        default=10,
        gt=0,
        description="Maximum daily capacity",
    )

    active: bool = Field(
        default=True,
        description="Whether crew is active and accepting assignments",
    )

    created_at: datetime = Field(
        ...,
        description="Timestamp when crew was created",
    )

    class Config:
        """Pydantic configuration for CuadrillaInDB"""
        from_attributes = True


# ============================================================================
# RESPONSE SCHEMA (WITH RELATIONSHIPS)
# ============================================================================


class OTResponseMinimal(BaseModel):
    """
    Minimal OT information included in Cuadrilla responses.
    
    This is a forward reference to OTResponse to avoid circular imports.
    Includes essential OT details for crew assignment listing.
    """

    id: str = Field(description="OT UUID")
    external_id: str = Field(description="External TELCOS identifier")
    status: str = Field(description="OT status")
    project_type: str = Field(description="Project type: PUBLICO, PRIVADO, or TERCERIZADO")
    cliente_id: str = Field(description="Customer ID")
    lat: Optional[float] = Field(default=None)
    long: Optional[float] = Field(default=None)
    geo_error: bool = Field(default=False)
    created_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class CuadrillaResponse(CuadrillaInDB):
    """
    Cuadrilla schema for API responses.
    Includes all database fields plus relationships.
    Returned by GET endpoints.
    
    This schema includes the list of assigned OTs to show which work
    orders are assigned to this crew. Used in crew detail views and
    planning algorithm visualization.
    
    Example response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Cuadrilla Quito-01",
            "type": "PRINCIPAL",
            "last_centroid_lat": -0.22,
            "last_centroid_long": -78.51,
            "current_load": 8,
            "daily_capacity": 10,
            "active": true,
            "created_at": "2024-02-13T15:30:45.123456",
            "assigned_ots": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "external_id": "OT-2024-001234",
                    "status": "ASIGNADO_TAREA",
                    "project_type": "PUBLICO",
                    "cliente_id": "CLI-12345",
                    "lat": -0.22,
                    "long": -78.51,
                    "geo_error": false,
                    "created_at": "2024-02-13T15:30:45.123456"
                },
                ...
            ]
        }
    """

    assigned_ots: List[OTResponseMinimal] = Field(
        default_factory=list,
        description="List of OTs assigned to this crew",
    )

    class Config:
        """Pydantic configuration for CuadrillaResponse"""
        from_attributes = True


# ============================================================================
# LIST RESPONSE SCHEMA
# ============================================================================


class CuadrillaListResponse(BaseModel):
    """
    Paginated list response for Cuadrilla queries.
    
    Used by GET /api/v1/cuadrillas with pagination support.
    
    Example:
        {
            "items": [
                { ... cuadrilla response 1 ... },
                { ... cuadrilla response 2 ... }
            ],
            "total": 10,
            "page": 1,
            "page_size": 10,
            "total_pages": 1
        }
    """

    items: List[CuadrillaResponse] = Field(description="Cuadrillas in current page")
    total: int = Field(description="Total number of cuadrillas")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# CAPACITY & LOAD SCHEMAS
# ============================================================================


class CuadrillaCapacityInfo(BaseModel):
    """
    Capacity utilization information for a Cuadrilla.
    
    Used by GET /api/v1/cuadrillas/{cuadrilla_id}/capacity endpoint
    and for dashboard statistics.
    
    Example:
        {
            "cuadrilla_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Cuadrilla Quito-01",
            "current_load": 8,
            "daily_capacity": 10,
            "available_slots": 2,
            "utilization_percentage": 80.0,
            "available": true
        }
    """

    cuadrilla_id: str = Field(description="Crew UUID")
    name: str = Field(description="Crew name")
    current_load: int = Field(description="Current number of assigned OTs")
    daily_capacity: int = Field(description="Maximum daily capacity")

    @property
    def available_slots(self) -> int:
        """Calculate available slots."""
        return max(0, self.daily_capacity - self.current_load)

    @property
    def utilization_percentage(self) -> float:
        """Calculate utilization percentage."""
        if self.daily_capacity == 0:
            return 0.0
        return (self.current_load / self.daily_capacity) * 100

    @property
    def available(self) -> bool:
        """Whether crew has available capacity."""
        return self.current_load < self.daily_capacity

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class CuadrillaCentroidInfo(BaseModel):
    """
    Centroid information for a Cuadrilla.
    
    Used by GET /api/v1/cuadrillas/{cuadrilla_id}/centroid endpoint.
    The centroid is the geographic center of all assigned OTs.
    
    Example:
        {
            "cuadrilla_id": "550e8400-e29b-41d4-a716-446655440000",
            "lat": -0.22,
            "long": -78.51,
            "calculated_at": "2024-02-13T16:45:30.654321",
            "assigned_ot_count": 8,
            "radius_km": 10.0
        }
    """

    cuadrilla_id: str = Field(description="Crew UUID")
    lat: Optional[float] = Field(
        default=None,
        description="Centroid latitude",
    )
    long: Optional[float] = Field(
        default=None,
        description="Centroid longitude",
    )
    calculated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when centroid was last calculated",
    )
    assigned_ot_count: int = Field(
        description="Number of OTs used in centroid calculation",
    )
    radius_km: float = Field(
        default=10.0,
        description="Assignment radius constraint in kilometers",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# FILTER SCHEMA FOR LIST QUERIES
# ============================================================================


class CuadrillaFilters(BaseModel):
    """
    Query filters for listing Cuadrillas.
    
    Used by GET /api/v1/cuadrillas?type=PRINCIPAL&active=true&page=1
    
    Attributes:
        type: Filter by crew type (PRINCIPAL or RESERVA)
        active_only: If True, return only active crews
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        sort_by: Sort field (name, capacity, load, created_at)
        sort_order: Sort direction (asc or desc)
    """

    type: Optional[CuadrillaType] = Field(
        default=None,
        description="Filter by crew type",
    )

    active_only: bool = Field(
        default=True,
        description="If True, return only active crews",
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

    sort_by: str = Field(
        default="name",
        description="Sort field: name, capacity, load, or created_at",
    )

    sort_order: str = Field(
        default="asc",
        description="Sort direction: asc or desc",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================


class CuadrillaStatistics(BaseModel):
    """
    Statistics about Cuadrillas.
    
    Used by dashboard and planning endpoints.
    
    Example:
        {
            "total_cuadrillas": 10,
            "principal_count": 5,
            "reserva_count": 5,
            "active_count": 9,
            "total_capacity": 100,
            "total_load": 72,
            "average_utilization": 72.0,
            "fully_loaded": 2,
            "available": 8
        }
    """

    total_cuadrillas: int = Field(description="Total number of crews")
    principal_count: int = Field(description="Number of PRINCIPAL crews")
    reserva_count: int = Field(description="Number of RESERVA crews")
    active_count: int = Field(description="Number of active crews")
    inactive_count: int = Field(description="Number of inactive crews")

    total_capacity: int = Field(description="Sum of all daily capacities")
    total_load: int = Field(description="Sum of all current loads")
    average_utilization: float = Field(description="Average utilization percentage")

    fully_loaded: int = Field(
        description="Number of crews at max capacity",
    )
    available: int = Field(
        description="Number of crews with available slots",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# ASSIGNMENT STATISTICS
# ============================================================================


class CuadrillaAssignmentStats(BaseModel):
    """
    Assignment statistics for a specific Cuadrilla.
    
    Used in crew detail pages showing assignment metrics.
    
    Example:
        {
            "cuadrilla_id": "550e8400-e29b-41d4-a716-446655440000",
            "total_assigned": 8,
            "by_status": {
                "ASIGNADO_TAREA": 7,
                "DETENIDA": 1
            },
            "by_project_type": {
                "PUBLICO": 4,
                "PRIVADO": 3,
                "TERCERIZADO": 1
            },
            "average_distance_km": 5.3,
            "max_distance_km": 9.8,
            "total_assignments_all_time": 156
        }
    """

    cuadrilla_id: str = Field(description="Crew UUID")
    total_assigned: int = Field(description="Current assigned OTs")
    by_status: dict = Field(description="Count by OT status")
    by_project_type: dict = Field(description="Count by project type")

    average_distance_km: Optional[float] = Field(
        default=None,
        description="Average distance from centroid to assigned OTs",
    )
    max_distance_km: Optional[float] = Field(
        default=None,
        description="Maximum distance from centroid to any assigned OT",
    )

    total_assignments_all_time: int = Field(
        default=0,
        description="Total assignments in system history",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# VALIDATORS
# ============================================================================


@field_validator("name", mode="before")
def validate_name(cls, v):
    """
    Validate crew name format.
    Should be alphanumeric with hyphens/underscores/spaces.
    """
    if not v:
        raise ValueError("name cannot be empty")

    # Allow alphanumeric, hyphens, underscores, spaces
    if not all(c.isalnum() or c in "-_ " for c in v):
        raise ValueError(
            "name can only contain letters, numbers, hyphens, underscores, and spaces"
        )

    return v.strip()

