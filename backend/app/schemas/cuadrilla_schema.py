from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class CuadrillaType(str, Enum):
    PRINCIPAL = "PRINCIPAL"
    RESERVA = "RESERVA"


class CuadrillaBase(BaseModel):
    name: str
    type: CuadrillaType
    capacity_daily: int = 10


class CuadrillaCreate(CuadrillaBase):
    pass


class CuadrillaUpdate(BaseModel):
    is_active: Optional[bool] = None
    current_load: Optional[int] = None


class CuadrillaResponse(CuadrillaBase):
    id: str
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None
    current_load: int = 0
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class CuadrillaWithOTs(CuadrillaResponse):
    ots: List = []  # List of OT IDs or OTResponse objects

