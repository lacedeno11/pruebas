"""
Pydantic schemas for Cuadrilla (Work Team) entities.
Used for request/response validation and serialization.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CuadrillaBase(BaseModel):
    """Base schema for Cuadrilla with minimal required fields."""
    name: str = Field(..., description="Unique name identifier for the cuadrilla")
    type: str = Field(..., description="Cuadrilla type: PRINCIPAL or RESERVA")


class CuadrillaCreate(CuadrillaBase):
    """Schema for creating a new Cuadrilla."""
    daily_capacity: Optional[int] = Field(None, description="Daily OT capacity for this cuadrilla")


class CuadrillaResponse(BaseModel):
    """Schema for Cuadrilla response with all fields including database-generated ones."""
    id: int = Field(..., description="Primary key")
    name: str = Field(..., description="Cuadrilla name")
    type: str = Field(..., description="Cuadrilla type: PRINCIPAL or RESERVA")
    last_centroid_lat: Optional[float] = Field(None, description="Last calculated centroid latitude")
    last_centroid_long: Optional[float] = Field(None, description="Last calculated centroid longitude")
    current_load: int = Field(default=0, description="Current number of assigned OTs")
    daily_capacity: int = Field(..., description="Maximum OTs per day")
    is_active: bool = Field(default=True, description="Whether cuadrilla is active")

    class Config:
        from_attributes = True


class CuadrillaWithOTs(CuadrillaResponse):
    """Extended Cuadrilla schema including list of assigned OTs."""
    assigned_ots: List[dict] = Field(default_factory=list, description="List of assigned OT objects")

    class Config:
        from_attributes = True

