"""Pydantic models for OT (Orden de Trabajo) entities"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from backend.utils.constants import OT_STATUS, PROJECT_TYPES


class OTBase(BaseModel):
    """Base OT model with common fields"""

    external_id: str = Field(..., description="External OT ID from TELCOS")
    cliente_id: str = Field(..., description="Client ID")
    login_id: str = Field(..., description="Login ID (service point)")
    status: str = Field(
        default="PREPLANIFICADA", description="OT status"
    )
    project_type: str = Field(..., description="Project type")
    lat: Optional[float] = Field(
        default=None, description="Latitude coordinate"
    )
    long: Optional[float] = Field(
        default=None, description="Longitude coordinate"
    )
    detalle_detencion: Optional[str] = Field(
        default=None, description="Details if OT is stopped"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status is one of allowed values"""
        if v not in OT_STATUS.values():
            raise ValueError(
                f"Invalid status. Allowed: {list(OT_STATUS.values())}"
            )
        return v

    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v):
        """Validate project type is one of allowed values"""
        if v not in PROJECT_TYPES.values():
            raise ValueError(
                f"Invalid project_type. Allowed: {list(PROJECT_TYPES.values())}"
            )
        return v


class OTCreate(OTBase):
    """Model for creating a new OT"""

    pass


class OTUpdate(BaseModel):
    """Model for updating an OT"""

    external_id: Optional[str] = None
    cliente_id: Optional[str] = None
    login_id: Optional[str] = None
    status: Optional[str] = None
    project_type: Optional[str] = None
    lat: Optional[float] = None
    long: Optional[float] = None
    detalle_detencion: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status is one of allowed values"""
        if v is not None and v not in OT_STATUS.values():
            raise ValueError(
                f"Invalid status. Allowed: {list(OT_STATUS.values())}"
            )
        return v

    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v):
        """Validate project type is one of allowed values"""
        if v is not None and v not in PROJECT_TYPES.values():
            raise ValueError(
                f"Invalid project_type. Allowed: {list(PROJECT_TYPES.values())}"
            )
        return v


class OTInDB(OTBase):
    """Model for OT retrieved from database"""

    id: int = Field(..., description="OT ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_status_change: datetime = Field(
        ..., description="Last status change timestamp"
    )
    cuadrilla_id: Optional[int] = Field(
        default=None, description="Assigned cuadrilla ID"
    )

    class Config:
        from_attributes = True  # ORM mode for SQLAlchemy compatibility

