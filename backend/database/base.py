"""SQLAlchemy declarative base for all ORM models"""

from sqlalchemy.ext.declarative import declarative_base

# Create the declarative base class for all models
Base = declarative_base()

# Import all models to ensure they are registered with the Base
# This is important for Alembic migrations and SQLAlchemy's metadata tracking
from backend.database.models import OT, Cuadrilla, LogAgente, Asignacion, Alerta

__all__ = ["Base", "OT", "Cuadrilla", "LogAgente", "Asignacion", "Alerta"]

