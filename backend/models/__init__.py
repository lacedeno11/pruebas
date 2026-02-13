"""
Models package for PEI Platform.
Exports all SQLAlchemy models for easy importing throughout the application.
"""

from backend.db.database import Base
from backend.models.ot import OT, OTStatus, ProjectType
from backend.models.cuadrilla import Cuadrilla, CuadrillaType
from backend.models.log_agente import LogAgente, ActionResult

__all__ = [
    # Database base
    "Base",
    # OT model and enums
    "OT",
    "OTStatus",
    "ProjectType",
    # Cuadrilla model and enums
    "Cuadrilla",
    "CuadrillaType",
    # LogAgente model and enums
    "LogAgente",
    "ActionResult",
]

