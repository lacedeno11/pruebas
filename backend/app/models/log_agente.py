from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class LogAgente(Base):
    """
    LogAgente (Agent Action Log) SQLAlchemy model.
    Tracks all actions performed by agents for audit and debugging purposes.
    """
    __tablename__ = "logs_agentes"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key to OT (nullable for system-level actions not tied to specific OT)
    ot_id = Column(Integer, ForeignKey("ots.id"), nullable=True)

    # Agent action details
    agente_name = Column(String, nullable=False)
    accion = Column(String, nullable=False)
    resultado = Column(String, nullable=False)

    # Raw LLM response for debugging (nullable)
    raw_llm_response = Column(Text, nullable=True)

    # Timestamp of action
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ot = relationship("OT", back_populates="logs")

    def __repr__(self):
        return f"<LogAgente(id={self.id}, agente_name={self.agente_name}, accion={self.accion}, ot_id={self.ot_id}, timestamp={self.timestamp})>"

