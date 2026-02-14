from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class Asignacion(Base):
    """OT-to-Cuadrilla assignment tracking model"""
    __tablename__ = "asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ots.id"), nullable=False)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by_agent = Column(String, nullable=False)
    distance_to_centroid = Column(Float, nullable=True)
    priority = Column(Integer, default=0)

    # Relationships
    ot = relationship("OT", back_populates="asignaciones")
    cuadrilla = relationship("Cuadrilla", back_populates="asignaciones")

