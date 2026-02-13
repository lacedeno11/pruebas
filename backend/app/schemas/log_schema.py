from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LogAgenteBase(BaseModel):
    """Base LogAgente schema with common fields."""
    agente_name: str = Field(..., description="Name of the agent performing the action")
    accion: str = Field(..., description="Action performed by the agent")
    resultado: str = Field(..., description="Result of the action")
    ot_id: Optional[int] = Field(None, description="Related OT ID if applicable")
    raw_llm_response: Optional[str] = Field(None, description="Raw LLM response data if applicable")


class LogAgenteCreate(LogAgenteBase):
    """Schema for creating a new LogAgente entry."""
    pass


class LogAgenteResponse(LogAgenteBase):
    """Schema for API responses with database fields."""
    id: int = Field(..., description="Primary key")
    timestamp: datetime = Field(..., description="Log entry timestamp")

    model_config = ConfigDict(from_attributes=True)

