from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class LogAgente(Base):
    """Agent action logging model"""
    __tablename__ = "logs_agentes"

    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ots.id"), nullable=True, index=True)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=True, index=True)
    agente_name = Column(String, index=True, nullable=False)
    accion = Column(String, nullable=False)
    resultado = Column(String, nullable=False)
    raw_llm_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ot = relationship("OT", back_populates="log_agentes")
    cuadrilla = relationship("Cuadrilla", back_populates="log_agentes")

