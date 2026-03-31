"""
SQLAlchemy ORM models for DERCAS system.

All models are imported here to ensure they're registered with Base.metadata
for proper Alembic migration generation.
"""

from backend.app.models.ot import OrdenTrabajo, OTStatus, ProjectType
from backend.app.models.cuadrilla import Cuadrilla, CuadrillaType
from backend.app.models.log_agente import LogAgente, AGENT_NAMES, ACTION_TYPES, RESULT_STATUSES
from backend.app.models.asignacion import Asignacion, AssignmentResult, calculate_assignment_stats

__all__ = [
    # OT models and enums
    "OrdenTrabajo",
    "OTStatus",
    "ProjectType",
    
    # Cuadrilla models and enums
    "Cuadrilla",
    "CuadrillaType",
    
    # Log models and constants
    "LogAgente",
    "AGENT_NAMES",
    "ACTION_TYPES",
    "RESULT_STATUSES",
    
    # Asignacion models and helpers
    "Asignacion",
    "AssignmentResult",
    "calculate_assignment_stats",
]

