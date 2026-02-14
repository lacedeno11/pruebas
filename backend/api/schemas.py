"""
Pydantic models for API request/response schemas.
Defines data validation and serialization for all endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== OT Schemas ====================


class OTResponse(BaseModel):
    """Response schema for a single Order of Work (OT)."""

    id: UUID
    external_id: str = Field(..., description="External OT identifier")
    status: str = Field(..., description="OT status")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    long: Optional[float] = Field(None, description="Longitude coordinate")
    geo_error: bool = Field(False, description="Indicates if coordinates are invalid")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OTListResponse(BaseModel):
    """Response schema for list of OTs."""

    items: List[OTResponse]
    total: int = Field(..., description="Total count of OTs")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(10, description="Items per page")


class UpdateStatusRequest(BaseModel):
    """Request schema for updating OT status."""

    new_status: str = Field(..., description="New OT status")
    reason: Optional[str] = Field(None, description="Reason for status change")


class AssignCuadrillaRequest(BaseModel):
    """Request schema for assigning OT to crew."""

    cuadrilla_id: UUID = Field(..., description="ID of crew to assign")


# ==================== Cuadrilla Schemas ====================


class AsignacionResponse(BaseModel):
    """Response schema for OT assignment."""

    id: UUID
    ot_id: UUID
    cuadrilla_id: UUID
    assigned_by_agent: str
    distancia_centroide_km: Optional[float]
    assigned_at: datetime
    activa: bool

    class Config:
        from_attributes = True


class CuadrillaResponse(BaseModel):
    """Response schema for a crew (Cuadrilla)."""

    id: UUID
    nombre: str = Field(..., description="Crew name")
    tipo: str = Field(..., description="Crew type: PRINCIPAL or RESERVA")
    capacidad_diaria: int = Field(5, description="Daily capacity")
    activa: bool = Field(True, description="Is crew active")
    last_centroid_lat: Optional[float]
    last_centroid_long: Optional[float]
    created_at: datetime
    assigned_ots_count: Optional[int] = Field(None, description="Current OTs assigned")
    available_capacity: Optional[int] = Field(None, description="Available capacity slots")

    class Config:
        from_attributes = True


# ==================== Agent Chat Schemas ====================


class ChatRequest(BaseModel):
    """Request schema for agent chat endpoint."""

    message: str = Field(..., description="User message for agent", min_length=1)


class ChatResponse(BaseModel):
    """Response schema for agent chat endpoint."""

    message: str = Field(..., description="Agent response")
    agent_used: Optional[str] = Field(None, description="Which agent processed the message")
    success: bool = Field(True, description="Whether processing was successful")
    error: Optional[str] = Field(None, description="Error message if failed")


# ==================== Planning Schemas ====================


class PlanningStatsResponse(BaseModel):
    """Response schema for planning statistics."""

    ots_by_status: Dict[str, int] = Field(..., description="Count of OTs per status")
    ots_by_project_type: Dict[str, int] = Field(..., description="Count of OTs per project type")
    crew_utilization: Dict[str, Any] = Field(..., description="Crew capacity utilization")
    average_assignment_distance_km: float = Field(..., description="Average distance from crew centroid")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ==================== Alert/Governance Schemas ====================


class AlertResponse(BaseModel):
    """Response schema for governance alerts."""

    id: UUID
    ot_id: Optional[UUID]
    alert_type: str = Field(..., description="Type of alert")
    message: str = Field(..., description="Alert message")
    created_at: datetime
    resolved: bool = Field(False, description="Whether alert has been resolved")

    class Config:
        from_attributes = True


class ValidateReasonRequest(BaseModel):
    """Request schema for validating stop reason."""

    reason: str = Field(..., description="Reason for stopping OT", min_length=1)
    ot_id: Optional[UUID] = Field(None, description="Optional OT context")


class ValidateReasonResponse(BaseModel):
    """Response schema for reason validation."""

    valid: bool = Field(..., description="Whether reason is valid")
    message: Optional[str] = Field(None, description="Validation feedback")
    confidence: float = Field(1.0, description="Confidence level of validation (0-1)")


# ==================== Error Response ====================


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")

