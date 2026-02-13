from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Schema for agent request"""
    action: str = Field(..., description="Action to perform")
    ot_id: Optional[int] = Field(None, description="OT ID if applicable")
    cuadrilla_id: Optional[int] = Field(None, description="Cuadrilla ID if applicable")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class AgentResponse(BaseModel):
    """Schema for agent response"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    agent_name: str = Field(..., description="Name of the agent")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PlanningRequest(BaseModel):
    """Schema for planning request"""
    ot_ids: List[int] = Field(..., description="List of OT IDs to plan")
    force_balance: bool = Field(default=False, description="Force balance phase")


class PlanningResponse(BaseModel):
    """Schema for planning response"""
    assigned_count: int = Field(..., description="Number of OTs assigned")
    failed_count: int = Field(..., description="Number of failed assignments")
    assignments: List[Dict[str, Any]] = Field(..., description="List of assignments")
    errors: List[str] = Field(default_factory=list, description="List of errors")

