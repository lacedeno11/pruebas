"""
LogAgente (Agent Log) model - Audit trail for AI agent actions.
Persists agent decisions, actions, and raw LLM responses for compliance and debugging.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class LogAgente(Base):
    """
    LogAgente (Agent Log) model.
    Tracks all AI agent actions with raw LLM responses for audit and analysis.
    Enables compliance tracking and troubleshooting of agent decisions.
    """

    __tablename__ = "logs_agentes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ot_id = Column(UUID(as_uuid=True), ForeignKey("ordenes_trabajo.id"), nullable=True)
    agente_name = Column(String(255), nullable=False)
    accion = Column(String(255), nullable=False)
    resultado = Column(String(255), nullable=False)
    raw_llm_response = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    orden_trabajo = relationship("OrdenTrabajo", back_populates="logs")

    def __repr__(self) -> str:
        return f"<LogAgente(id={self.id}, agente_name={self.agente_name}, accion={self.accion})>"

