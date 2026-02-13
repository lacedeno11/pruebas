"""
Cuadrilla (Crew/OPU) model - Represents work crews and their capacity.
Crews are divided into PRINCIPAL (50%) and RESERVA (50%) for load balancing.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class Cuadrilla(Base):
    """
    Cuadrilla (Work Crew/OPU) model.
    Represents human and technical resources for OT execution.
    Types: PRINCIPAL (base workload) and RESERVA (overflow/long-distance activation)
    """

    __tablename__ = "cuadrillas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(255), unique=True, nullable=False)
    tipo = Column(
        Enum("PRINCIPAL", "RESERVA", name="cuadrilla_tipo_enum"),
        nullable=False,
    )
    capacidad_diaria = Column(Integer, default=5, nullable=False)
    last_centroid_lat = Column(Float, nullable=True)
    last_centroid_long = Column(Float, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asignaciones = relationship(
        "Asignacion", back_populates="cuadrilla", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Cuadrilla(id={self.id}, nombre={self.nombre}, tipo={self.tipo})>"

