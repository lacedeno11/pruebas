from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class OTStatus(str, Enum):
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(str, Enum):
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class OTBase(BaseModel):
    external_id: str
    status: OTStatus
    project_type: ProjectType
    lat: Optional[float] = None
    long: Optional[float] = None
    cliente_id: str
    login_id: str


class OTCreate(OTBase):
    pass


class OTUpdate(BaseModel):
    status: Optional[OTStatus] = None
    cuadrilla_id: Optional[str] = None


class OTResponse(OTBase):
    id: str
    cuadrilla_id: Optional[str] = None
    error_geo: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OTListResponse(BaseModel):
    items: List[OTResponse]
    total: int

