"""
Asignacion (Assignment) model - Tracks OT-to-Crew assignments.
Records assignment details including distance from centroid for the 10km proximity rule.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class Asignacion(Base):
    """
    Asignacion (Assignment) model.
    Records assignment of work orders to crews with geographical and temporal tracking.
    Stores distance from crew centroid for proximity validation (<10km rule).
    """

    __tablename__ = "asignaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ot_id = Column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"), nullable=False)
    cuadrilla_id = Column(
        UUID(as_uuid=True), ForeignKey("cuadrillas.id"), nullable=False
    )
    assigned_by_agent = Column(String(255), nullable=False)
    distancia_centroide_km = Column(Float, nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unassigned_at = Column(DateTime, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)

    # Relationships
    orden_trabajo = relationship("OrdenTrabajo", back_populates="asignaciones")
    cuadrilla = relationship("Cuadrilla", back_populates="asignaciones")

    def __repr__(self) -> str:
        return f"<Asignacion(id={self.id}, ot_id={self.ot_id}, cuadrilla_id={self.cuadrilla_id})>"

