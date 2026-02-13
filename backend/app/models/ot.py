from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


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


class OT(Base):
    """
    OT (Orden de Trabajo) SQLAlchemy model.
    Represents work orders for installation teams (cuadrillas).
    """
    __tablename__ = "ots"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # External identifiers
    external_id = Column(String, unique=True, index=True, nullable=False)
    cliente_id = Column(String, nullable=False)
    login_id = Column(String, nullable=False)

    # Status and type
    status = Column(SQLEnum(OTStatus), default=OTStatus.PREPLANIFICADA, nullable=False)
    project_type = Column(SQLEnum(ProjectType), nullable=False)

    # Geographic coordinates
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    error_geo = Column(Boolean, default=False)

    # Foreign Key to Cuadrilla
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    cuadrilla = relationship("Cuadrilla", back_populates="ots")
    logs = relationship("LogAgente", back_populates="ot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OT(id={self.id}, external_id={self.external_id}, status={self.status}, cuadrilla_id={self.cuadrilla_id})>"

