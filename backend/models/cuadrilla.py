"""Pydantic models for Cuadrilla (work team) entities"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from backend.utils.constants import CUADRILLA_TYPES


class CuadrillaBase(BaseModel):
    """Base Cuadrilla model with common fields"""

    name: str = Field(..., description="Cuadrilla name")
    type: str = Field(..., description="Cuadrilla type (Principal/Reserva)")
    capacity: Optional[int] = Field(
        default=10, description="Maximum number of OTs"
    )
    last_centroid_lat: Optional[float] = Field(
        default=None, description="Last centroid latitude"
    )
    last_centroid_long: Optional[float] = Field(
        default=None, description="Last centroid longitude"
    )
    active: Optional[bool] = Field(
        default=True, description="Whether cuadrilla is active"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        """Validate cuadrilla type"""
        if v not in CUADRILLA_TYPES.values():
            raise ValueError(
                f"Invalid type. Allowed: {list(CUADRILLA_TYPES.values())}"
            )
        return v


class CuadrillaCreate(CuadrillaBase):
    """Model for creating a new Cuadrilla"""

    pass


class CuadrillaUpdate(BaseModel):
    """Model for updating a Cuadrilla"""

    name: Optional[str] = None
    type: Optional[str] = None
    capacity: Optional[int] = None
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None
    active: Optional[bool] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        """Validate cuadrilla type"""
        if v is not None and v not in CUADRILLA_TYPES.values():
            raise ValueError(
                f"Invalid type. Allowed: {list(CUADRILLA_TYPES.values())}"
            )
        return v


class CuadrillaInDB(CuadrillaBase):
    """Model for Cuadrilla retrieved from database"""

    id: int = Field(..., description="Cuadrilla ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True  # ORM mode for SQLAlchemy compatibility


class CuadrillaWithWorkload(CuadrillaInDB):
    """Cuadrilla with current workload information"""

    current_workload: int = Field(
        default=0, description="Number of currently assigned OTs"
    )
    assigned_ots: List = Field(
        default_factory=list, description="List of assigned OT objects"
    )

