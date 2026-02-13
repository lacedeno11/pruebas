"""
Database models module for PEI Platform.
Uses SQLAlchemy ORM with declarative base.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the declarative base for all models
Base = declarative_base()

# Import all models to register them with Base
from backend.models.asignacion import Asignacion
from backend.models.cliente import Cliente
from backend.models.cuadrilla import Cuadrilla
from backend.models.log_agente import LogAgente
from backend.models.login import Login
from backend.models.ot import OrdenTrabajo
from backend.models.proyecto import Proyecto
from backend.models.tarea import Tarea

__all__ = [
    "Base",
    "Cliente",
    "Login",
    "Proyecto",
    "OrdenTrabajo",
    "Cuadrilla",
    "Tarea",
    "Asignacion",
    "LogAgente",
]

