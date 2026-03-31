from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class PlanificationStrategy(str, Enum):
    BALANCE = "balance"
    PROXIMITY = "proximity"
    CAPACITY = "capacity"
    OPTIMIZED = "optimized"


class AgentInput(BaseModel):
    action_type: str
    ot_id: Optional[str] = None
    parameters: Dict[str, Any] = {}


class AgentResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = {}
    agent_name: str
    timestamp: datetime


class PlanificationRequest(BaseModel):
    ot_ids: List[str]
    cuadrilla_id: Optional[str] = None
    strategy: PlanificationStrategy = PlanificationStrategy.OPTIMIZED


class ChatMessage(BaseModel):
    role: AgentRole
    content: str
    timestamp: datetime
    agent_name: Optional[str] = None

