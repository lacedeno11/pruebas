"""
OrdenTrabajo (OT) model - Core operational entity.
Represents work orders with state machine transitions and timestamps.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class OrdenTrabajo(Base):
    """
    OrdenTrabajo (Work Order) model.
    Central operational entity with state machine:
    PREPLANIFICADA -> PLANIFICADA -> ASIGNADO_TAREA -> [DETENIDA | FINALIZADA | ANULADA]
    """

    __tablename__ = "ordenes_trabajo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    login_id = Column(UUID(as_uuid=True), ForeignKey("logins.id"), nullable=False)
    proyecto_id = Column(
        UUID(as_uuid=True), ForeignKey("proyectos.id"), nullable=True
    )
    status = Column(
        Enum(
            "PREPLANIFICADA",
            "PLANIFICADA",
            "ASIGNADO_TAREA",
            "DETENIDA",
            "ANULADA",
            "FINALIZADA",
            name="ot_status_enum",
        ),
        default="PREPLANIFICADA",
        nullable=False,
    )
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    geo_error = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    detenida_at = Column(DateTime, nullable=True)
    finalizada_at = Column(DateTime, nullable=True)

    # Relationships
    cliente = relationship("Cliente", back_populates="ordenes_trabajo")
    login = relationship("Login", back_populates="ordenes_trabajo")
    proyecto = relationship("Proyecto", back_populates="ordenes_trabajo")
    tareas = relationship(
        "Tarea", back_populates="orden_trabajo", cascade="all, delete-orphan"
    )
    asignaciones = relationship(
        "Asignacion", back_populates="orden_trabajo", cascade="all, delete-orphan"
    )
    logs = relationship(
        "LogAgente", back_populates="orden_trabajo", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OrdenTrabajo(id={self.id}, external_id={self.external_id}, status={self.status})>"

