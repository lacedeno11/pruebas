"""
Tarea (Task) model - Represents specific activities within an OT.
Tasks track detailed work breakdown with completion status.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class Tarea(Base):
    """
    Tarea (Task) model.
    Represents specific activities within a work order.
    Examples: Fiber laying (Tendido de fibra), Splicing (Fusión), Equipment configuration (Configuración de equipo)
    """

    __tablename__ = "tareas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ot_id = Column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    completada = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    orden_trabajo = relationship("OrdenTrabajo", back_populates="tareas")

    def __repr__(self) -> str:
        return f"<Tarea(id={self.id}, nombre={self.nombre}, completada={self.completada})>"

