"""Pydantic models for LogAgente (Agent Logs) entities"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LogAgenteBase(BaseModel):
    """Base LogAgente model with common fields"""

    ot_id: Optional[int] = Field(default=None, description="OT ID")
    agente_name: str = Field(..., description="Name of the agent")
    accion: str = Field(..., description="Action performed")
    resultado: str = Field(..., description="Result (SUCCESS/ERROR/WARNING)")
    raw_llm_response: Optional[str] = Field(
        default=None, description="Raw LLM response"
    )
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata"
    )


class LogAgenteCreate(LogAgenteBase):
    """Model for creating a new LogAgente"""

    pass


class LogAgenteInDB(LogAgenteBase):
    """Model for LogAgente retrieved from database"""

    id: int = Field(..., description="Log ID")
    timestamp: datetime = Field(..., description="When the log was created")

    class Config:
        from_attributes = True  # ORM mode for SQLAlchemy compatibility

