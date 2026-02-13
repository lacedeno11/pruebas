from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CuadrillaBase(BaseModel):
    """Base schema for Cuadrilla"""
    name: str = Field(..., description="Cuadrilla name")
    type: str = Field(..., description="Cuadrilla type: Principal or Reserva")
    capacity: int = Field(default=10, description="Cuadrilla capacity")
    is_active: bool = Field(default=True, description="Whether cuadrilla is active")


class CuadrillaCreate(CuadrillaBase):
    """Schema for creating a new Cuadrilla"""
    pass


class CuadrillaResponse(CuadrillaBase):
    """Schema for Cuadrilla response"""
    id: int = Field(..., description="Cuadrilla ID")
    current_load: int = Field(default=0, description="Current workload")
    last_centroid_lat: Optional[float] = Field(None, description="Last centroid latitude")
    last_centroid_long: Optional[float] = Field(None, description="Last centroid longitude")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {
        "from_attributes": True
    }

