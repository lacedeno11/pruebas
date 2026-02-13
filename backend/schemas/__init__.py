"""
Schema module for PEI Platform.
Centralizes exports of all Pydantic schemas for easy importing.
"""

from backend.schemas.ot_schema import (
    OTBase,
    OTCreate,
    OTUpdate,
    OTResponse,
    OTStatusUpdate,
)

from backend.schemas.cuadrilla_schema import (
    CuadrillaBase,
    CuadrillaCreate,
    CuadrillaResponse,
    CuadrillaWithOTs,
)

from backend.schemas.log_schema import (
    LogAgenteBase,
    LogAgenteCreate,
    LogAgenteResponse,
)

__all__ = [
    # OT Schemas
    "OTBase",
    "OTCreate",
    "OTUpdate",
    "OTResponse",
    "OTStatusUpdate",
    # Cuadrilla Schemas
    "CuadrillaBase",
    "CuadrillaCreate",
    "CuadrillaResponse",
    "CuadrillaWithOTs",
    # LogAgente Schemas
    "LogAgenteBase",
    "LogAgenteCreate",
    "LogAgenteResponse",
]


