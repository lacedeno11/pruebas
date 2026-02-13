"""
Pydantic schemas for OT (Orden de Trabajo) entities.
Used for request/response validation and serialization.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class OTBase(BaseModel):
    """Base schema for OT with minimal required fields."""
    external_id: str = Field(..., description="External ID from TELCOS system")
    cliente_id: str = Field(..., description="Client identifier")
    login_id: str = Field(..., description="Login identifier for the technician")
    project_type: str = Field(..., description="Project type: PUBLICO, PRIVADO, or TERCERIZADO")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    long: Optional[float] = Field(None, description="Longitude coordinate")


class OTCreate(OTBase):
    """Schema for creating a new OT."""
    pass


class OTUpdate(BaseModel):
    """Schema for updating an existing OT."""
    status: Optional[str] = Field(None, description="OT status: PREPLANIFICADA, PLANIFICADA, etc.")
    cuadrilla_id: Optional[int] = Field(None, description="Assigned cuadrilla ID")
    detencion_motivo: Optional[str] = Field(None, description="Reason for detention if status is DETENIDA")


class OTStatusUpdate(BaseModel):
    """Schema for status updates via drag-drop operations."""
    status: str = Field(..., description="New status for the OT")


class OTResponse(BaseModel):
    """Schema for OT response with all fields including database-generated ones."""
    id: int = Field(..., description="Primary key")
    external_id: str = Field(..., description="External ID from TELCOS system")
    cliente_id: str = Field(..., description="Client identifier")
    login_id: str = Field(..., description="Login identifier")
    status: str = Field(..., description="Current OT status")
    project_type: str = Field(..., description="Project type")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    long: Optional[float] = Field(None, description="Longitude coordinate")
    cuadrilla_id: Optional[int] = Field(None, description="Assigned cuadrilla ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    geo_error: bool = Field(default=False, description="Flag indicating geographic data error")
    detencion_motivo: Optional[str] = Field(None, description="Reason for detention")

    class Config:
        from_attributes = True

