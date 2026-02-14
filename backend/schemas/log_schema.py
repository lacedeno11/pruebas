"""
Pydantic schemas for LogAgente (Agent Execution Log) entities.
Used for request/response validation and serialization.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class LogAgenteBase(BaseModel):
    """Base schema for LogAgente with minimal required fields."""
    agente_name: str = Field(..., description="Name of the agent that executed the action")
    accion: str = Field(..., description="Description of the action performed")
    resultado: str = Field(..., description="Result of the action: SUCCESS, FAILURE, or PENDING")


class LogAgenteCreate(LogAgenteBase):
    """Schema for creating a new LogAgente entry."""
    ot_id: Optional[int] = Field(None, description="Associated OT ID if applicable")
    raw_llm_response: Optional[str] = Field(None, description="Raw response from LLM if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")


class LogAgenteResponse(BaseModel):
    """Schema for LogAgente response with all fields including database-generated ones."""
    id: int = Field(..., description="Primary key")
    ot_id: Optional[int] = Field(None, description="Associated OT ID")
    agente_name: str = Field(..., description="Agent name")
    accion: str = Field(..., description="Action performed")
    resultado: str = Field(..., description="Action result")
    raw_llm_response: Optional[str] = Field(None, description="Raw LLM response")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True

