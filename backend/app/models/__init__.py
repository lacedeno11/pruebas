"""
SQLAlchemy Models Package

This module provides centralized imports for all ORM models used in the DERCAS PEI system.

Models:
    - OT: Work Order model with status lifecycle and crew assignment
    - Cuadrilla: Work Crew model with capacity and centroid tracking
    - LogAgente: Agent Action Log model for audit trail
    - Asignacion: Assignment History model for tracking OT-to-crew assignments

Usage:
    from app.models import OT, Cuadrilla, LogAgente, Asignacion
    
    # Or import individually
    from app.models import OT
    
Integration:
    - Used by database migrations (Alembic)
    - Used by FastAPI endpoints for CRUD operations
    - Used by agent services for business logic
    - All models inherit from Base (app.core.database.Base)
"""

from app.models.asignacion import Asignacion
from app.models.cuadrilla import Cuadrilla
from app.models.log_agente import LogAgente
from app.models.ot import OT

__all__ = [
    "OT",
    "Cuadrilla",
    "LogAgente",
    "Asignacion",
]

