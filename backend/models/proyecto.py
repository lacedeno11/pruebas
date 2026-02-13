"""Pydantic models for unified API responses"""

from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime


class StandardResponse(BaseModel):
    """Standard API response format"""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if any")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


class AssignmentResult(BaseModel):
    """Result of assigning an OT to a Cuadrilla"""

    ot_id: int = Field(..., description="OT ID")
    cuadrilla_id: int = Field(..., description="Assigned Cuadrilla ID")
    distance_to_centroid: float = Field(
        ..., description="Distance to cuadrilla centroid in km"
    )
    assigned_by_agent: str = Field(..., description="Name of assigning agent")


class PlanningResult(BaseModel):
    """Result of planning operation"""

    assignments: List[AssignmentResult] = Field(
        default_factory=list, description="List of successful assignments"
    )
    total_assigned: int = Field(
        default=0, description="Total OTs assigned"
    )
    unassigned: List[int] = Field(
        default_factory=list, description="OT IDs that could not be assigned"
    )


class GovernanceResult(BaseModel):
    """Result of governance operation"""

    alerts_sent: int = Field(
        default=0, description="Number of alerts sent"
    )
    ots_cancelled: int = Field(
        default=0, description="Number of OTs cancelled"
    )
    details: List[dict] = Field(
        default_factory=list, description="Detailed results"
    )


class IngestionResult(BaseModel):
    """Result of OT ingestion operation"""

    total: int = Field(default=0, description="Total OTs processed")
    inserted: int = Field(
        default=0, description="Successfully inserted OTs"
    )
    errors: int = Field(default=0, description="OTs with errors")
    error_details: List[dict] = Field(
        default_factory=list, description="Detailed error information"
    )

