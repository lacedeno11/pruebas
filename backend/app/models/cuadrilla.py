from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class Cuadrilla(Base):
    """Cuadrilla (Work Crew) model"""
    __tablename__ = "cuadrillas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(
        Enum("Principal", "Reserva", name="cuadrilla_type"),
        nullable=False
    )
    last_centroid_lat = Column(Float, nullable=True)
    last_centroid_long = Column(Float, nullable=True)
    capacity = Column(Integer, default=10)
    current_load = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asignaciones = relationship("Asignacion", back_populates="cuadrilla")
    log_agentes = relationship("LogAgente", back_populates="cuadrilla")

