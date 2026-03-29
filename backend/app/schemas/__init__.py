"""
Pydantic schemas module for DERCAS PEI.

This module aggregates all schema definitions for request/response validation,
enabling convenient imports throughout the application.

Schemas are organized by domain:
- OT (Work Order) schemas: OTCreate, OTUpdate, OTResponse, OTTransitionRequest
- Cuadrilla (Crew) schemas: CuadrillaCreate, CuadrillaUpdate, CuadrillaResponse, CuadrillaWithOTs
- LogAgente (Agent Log) schemas: LogAgenteCreate, LogAgenteResponse

Enumerations:
- OTStatus: Work order statuses
- ProjectType: Project type classifications
- CuadrillaType: Crew type classifications
- AgenteEnum: Agent identifiers
- ResultadoEnum: Operation result statuses

Usage:
    from app.schemas import OTCreate, OTResponse, CuadrillaCreate
    from app.schemas import OTStatus, ProjectType, CuadrillaType
"""

# OT (Work Order) schemas
from .ot import (
    OTCreate,
    OTResponse,
    OTStatus,
    OTTransitionRequest,
    OTUpdate,
    ProjectType,
)

# Cuadrilla (Crew) schemas
from .cuadrilla import (
    CuadrillaCreate,
    CuadrillaResponse,
    CuadrillaType,
    CuadrillaUpdate,
    CuadrillaWithOTs,
)

# LogAgente (Agent Log) schemas
from .log_agente import (
    AgenteEnum,
    LogAgenteCreate,
    LogAgenteResponse,
    ResultadoEnum,
)

__all__ = [
    # OT schemas
    "OTCreate",
    "OTUpdate",
    "OTResponse",
    "OTTransitionRequest",
    "OTStatus",
    "ProjectType",
    # Cuadrilla schemas
    "CuadrillaCreate",
    "CuadrillaUpdate",
    "CuadrillaResponse",
    "CuadrillaWithOTs",
    "CuadrillaType",
    # LogAgente schemas
    "LogAgenteCreate",
    "LogAgenteResponse",
    "AgenteEnum",
    "ResultadoEnum",
]

