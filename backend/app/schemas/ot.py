from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OTBase(BaseModel):
    """Base schema for OT"""
    external_id: str = Field(..., description="External OT identifier")
    status: str = Field(..., description="OT status")
    project_type: str = Field(..., description="Project type: PUBLICO, PRIVADO, TERCERIZADO")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    long: Optional[float] = Field(None, description="Longitude coordinate")
    cliente_id: str = Field(..., description="Client ID")
    login_id: str = Field(..., description="Login ID")
    geo_error: bool = Field(default=False, description="Indicates if there's a geo error")
    detention_reason: Optional[str] = Field(None, description="Reason for detention")


class OTCreate(OTBase):
    """Schema for creating a new OT"""
    pass


class OTUpdate(BaseModel):
    """Schema for updating an OT"""
    external_id: Optional[str] = None
    status: Optional[str] = None
    project_type: Optional[str] = None
    lat: Optional[float] = None
    long: Optional[float] = None
    cliente_id: Optional[str] = None
    login_id: Optional[str] = None
    geo_error: Optional[bool] = None
    detention_reason: Optional[str] = None


class OTResponse(OTBase):
    """Schema for OT response"""
    id: int = Field(..., description="OT ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    
    model_config = {
        "from_attributes": True
    }

