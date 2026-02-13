from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class OT(Base):
    """Orden de Trabajo (Work Order) model"""
    __tablename__ = "ots"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(
        Enum(
            "PREPLANIFICADA",
            "PLANIFICADA",
            "ASIGNADO_TAREA",
            "DETENIDA",
            "ANULADA",
            "FINALIZADA",
            name="ot_status"
        ),
        default="PREPLANIFICADA",
        nullable=False
    )
    project_type = Column(
        Enum(
            "PUBLICO",
            "PRIVADO",
            "TERCERIZADO",
            name="project_type"
        ),
        nullable=False
    )
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    cliente_id = Column(String, nullable=False)
    login_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    geo_error = Column(Boolean, default=False)
    detention_reason = Column(String, nullable=True)

    # Relationships
    asignaciones = relationship("Asignacion", back_populates="ot")
    log_agentes = relationship("LogAgente", back_populates="ot")

