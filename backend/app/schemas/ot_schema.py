from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class OTStatus(str, Enum):
    """Enumeration for OT (Orden de Trabajo) statuses."""
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(str, Enum):
    """Enumeration for project types."""
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class OTBase(BaseModel):
    """Base OT schema with common fields."""
    external_id: str = Field(..., description="External ID from TELCOS system")
    status: OTStatus = Field(default=OTStatus.PREPLANIFICADA, description="Current OT status")
    project_type: ProjectType = Field(..., description="Type of project")
    cliente_id: str = Field(..., description="Customer ID from BSS")
    login_id: str = Field(..., description="Login/Service point ID")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    long: Optional[float] = Field(None, description="Longitude coordinate")
    error_geo: bool = Field(default=False, description="Flag if geographic data is missing")
    cuadrilla_id: Optional[int] = Field(None, description="Assigned team ID")


class OTCreate(OTBase):
    """Schema for creating a new OT."""
    pass


class OTUpdate(BaseModel):
    """Schema for updating OT fields (all optional)."""
    status: Optional[OTStatus] = None
    project_type: Optional[ProjectType] = None
    cliente_id: Optional[str] = None
    login_id: Optional[str] = None
    lat: Optional[float] = None
    long: Optional[float] = None
    error_geo: Optional[bool] = None
    cuadrilla_id: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class OTInDB(OTBase):
    """Schema for OT data as stored in database."""
    id: int = Field(..., description="Primary key")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class CuadrillaInfo(BaseModel):
    """Simplified cuadrilla info for OT responses."""
    id: int
    name: str
    type: str

    model_config = ConfigDict(from_attributes=True)


class OTResponse(OTInDB):
    """Schema for API responses with cuadrilla information."""
    cuadrilla: Optional[CuadrillaInfo] = Field(None, description="Assigned cuadrilla details")

    model_config = ConfigDict(from_attributes=True)

