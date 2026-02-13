"""
Pydantic models for API request/response validation.
Provides type safety and automatic documentation for FastAPI endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from backend.database.models import OTStatus, ProjectType, CuadrillaType, ClienteType


# ============================================================================
# Cliente Schemas
# ============================================================================


class ClienteBase(BaseModel):
    """Base schema for Cliente"""
    name: str = Field(..., min_length=1, max_length=255)
    type: ClienteType = Field(default=ClienteType.NATURAL)


class ClienteCreate(ClienteBase):
    """Schema for creating a new Cliente"""
    external_id: str = Field(..., min_length=1, max_length=50)


class ClienteResponse(ClienteBase):
    """Schema for Cliente response"""
    id: int
    external_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Login Schemas
# ============================================================================


class LoginBase(BaseModel):
    """Base schema for Login"""
    address: Optional[str] = Field(None, max_length=500)
    lat: Optional[float] = None
    long: Optional[float] = None


class LoginCreate(LoginBase):
    """Schema for creating a new Login"""
    external_id: str = Field(..., min_length=1, max_length=50)
    cliente_id: int


class LoginResponse(LoginBase):
    """Schema for Login response"""
    id: int
    external_id: str
    cliente_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Orden de Servicio Schemas
# ============================================================================


class OrdenServicioBase(BaseModel):
    """Base schema for OrdenServicio"""
    cliente_id: int


class OrdenServicioCreate(OrdenServicioBase):
    """Schema for creating a new OrdenServicio"""
    external_id: str = Field(..., min_length=1, max_length=50)


class OrdenServicioResponse(OrdenServicioBase):
    """Schema for OrdenServicio response"""
    id: int
    external_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Orden de Trabajo Schemas
# ============================================================================


class OTBase(BaseModel):
    """Base schema for Orden de Trabajo"""
    status: OTStatus = OTStatus.PREPLANIFICADA
    project_type: ProjectType = ProjectType.PRIVADO
    lat: Optional[float] = None
    long: Optional[float] = None


class OTCreate(OTBase):
    """Schema for creating a new Orden de Trabajo"""
    external_id: str = Field(..., min_length=1, max_length=50)
    orden_servicio_id: int
    login_id: int
    cliente_id: int
    pm_email: Optional[str] = None  # For notifications


class OTUpdate(BaseModel):
    """Schema for updating Orden de Trabajo status"""
    new_status: OTStatus
    reason: Optional[str] = None


class OTResponse(OTBase):
    """Schema for Orden de Trabajo response"""
    id: int
    external_id: str
    orden_servicio_id: int
    login_id: int
    cuadrilla_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    geo_error: bool = False

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Cuadrilla Schemas
# ============================================================================


class CuadrillaBase(BaseModel):
    """Base schema for Cuadrilla"""
    name: str = Field(..., min_length=1, max_length=255)
    type: CuadrillaType = CuadrillaType.PRINCIPAL
    capacity: int = Field(default=10, ge=1)


class CuadrillaCreate(CuadrillaBase):
    """Schema for creating a new Cuadrilla"""
    pass


class CuadrillaResponse(CuadrillaBase):
    """Schema for Cuadrilla response"""
    id: int
    current_load: int = 0
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Tarea Schemas
# ============================================================================


class TareaBase(BaseModel):
    """Base schema for Tarea"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "pendiente"


class TareaCreate(TareaBase):
    """Schema for creating a new Tarea"""
    ot_id: int


class TareaResponse(TareaBase):
    """Schema for Tarea response"""
    id: int
    ot_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Log Agente Schemas
# ============================================================================


class LogAgenteCreate(BaseModel):
    """Schema for creating a new LogAgente entry"""
    ot_id: Optional[int] = None
    agente_name: str = Field(..., min_length=1, max_length=100)
    accion: str = Field(..., min_length=1, max_length=255)
    resultado: Optional[str] = None
    raw_llm_response: Optional[str] = None


class LogAgenteResponse(LogAgenteCreate):
    """Schema for LogAgente response"""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Asignacion Schemas
# ============================================================================


class AsignacionCreate(BaseModel):
    """Schema for creating a new Asignacion"""
    ot_id: int
    cuadrilla_id: int
    assigned_by_agent: str = Field(..., min_length=1, max_length=100)
    distance_to_centroid_km: Optional[float] = None


class AsignacionResponse(AsignacionCreate):
    """Schema for Asignacion response"""
    id: int
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Workload and Statistics Schemas
# ============================================================================


class CuadrillaWorkload(BaseModel):
    """Detailed workload information for a Cuadrilla"""
    cuadrilla_id: int
    name: str
    type: CuadrillaType
    current_load: int
    capacity: int
    available_capacity: int
    utilization_percent: float
    assigned_ots_count: int
    assigned_ots: List[OTResponse] = []
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None
    is_available: bool
    created_at: Optional[datetime] = None


class OTStatistics(BaseModel):
    """Aggregated OT statistics"""
    total_ots: int = 0
    by_status: dict = Field(default_factory=dict)
    by_project_type: dict = Field(default_factory=dict)
    geo_error_count: int = 0
    assigned_count: int = 0
    unassigned_count: int = 0


class CuadrillaStatistics(BaseModel):
    """Aggregated Cuadrilla statistics"""
    total_cuadrillas: int = 0
    principal_count: int = 0
    reserva_count: int = 0
    total_capacity: int = 0
    total_load: int = 0
    available_capacity: int = 0
    average_utilization_percent: float = 0.0
    available_cuadrillas_count: int = 0
    at_capacity_count: int = 0


# ============================================================================
# Planning Request/Response Schemas
# ============================================================================


class PlanningAutoRequest(BaseModel):
    """Request for automatic planning"""
    project_type: Optional[ProjectType] = None
    priority: Optional[str] = None


class ManualAssignmentRequest(BaseModel):
    """Request for manual OT assignment (Drag & Drop)"""
    ot_id: int
    cuadrilla_id: int
    reason: Optional[str] = None


class AssignmentValidationRequest(BaseModel):
    """Request to validate an assignment without committing"""
    ot_id: int
    cuadrilla_id: int


class AssignmentResponse(BaseModel):
    """Response for assignment operations"""
    success: bool
    ot_id: int
    cuadrilla_id: int
    distance_to_centroid_km: Optional[float] = None
    error: Optional[str] = None


# ============================================================================
# Governance Request/Response Schemas
# ============================================================================


class StateTransitionRequest(BaseModel):
    """Request for state transition validation"""
    ot_id: int
    new_status: OTStatus
    reason: Optional[str] = None


class DetentionReasonValidationRequest(BaseModel):
    """Request to validate a detention reason"""
    reason: str = Field(..., min_length=1)


class GovernanceAlert(BaseModel):
    """Governance alert for OTs requiring attention"""
    ot_id: int
    external_id: str
    status: OTStatus
    days_in_status: int
    reason: str
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    action_recommended: str


# ============================================================================
# Notification Request/Response Schemas
# ============================================================================


class TelegramNotificationRequest(BaseModel):
    """Request to send Telegram notification"""
    chat_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class EmailNotificationRequest(BaseModel):
    """Request to send Email notification"""
    to_email: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)


class NotificationTestRequest(BaseModel):
    """Request for test notification"""
    channel: str = Field(..., regex="^(telegram|email)$")
    recipient: str = Field(..., min_length=1)


# ============================================================================
# Agent Request/Response Schemas
# ============================================================================


class AgentChatRequest(BaseModel):
    """Request for agent chat/command"""
    message: str = Field(..., min_length=1)
    context: Optional[dict] = None


class AgentChatResponse(BaseModel):
    """Response from agent chat"""
    success: bool
    agent_response: str
    actions_taken: List[str] = []
    result: Optional[dict] = None
    error: Optional[str] = None


class AgentStatus(BaseModel):
    """Status information for an agent"""
    agent_name: str
    last_execution: Optional[datetime] = None
    success_rate: float = 0.0
    total_executions: int = 0
    status: str = "idle"  # idle, running, error


# ============================================================================
# Mock API Request/Response Schemas
# ============================================================================


class MockStatusUpdateRequest(BaseModel):
    """Request to update OT status in mock API"""
    new_status: OTStatus


class SystemModeResponse(BaseModel):
    """Response with current system mode"""
    mode: str  # MOCK or PRODUCTION
    description: str = ""

