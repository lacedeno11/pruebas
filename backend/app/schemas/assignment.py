"""
Pydantic schemas for OT-Cuadrilla assignment tracking.
Provides request/response models for persisting and querying crew assignments.

An Assignment record tracks when and how an OT is assigned to a Cuadrilla:
- Which OT and crew are involved
- When the assignment was made
- Who/what made the assignment (agent name)
- Distance from crew centroid (for monitoring constraint violations)
- Which planning phase executed the assignment
- Current assignment status (ACTIVE, COMPLETED, REASSIGNED)
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================


class AssignmentPhase(str, Enum):
    """
    Planning algorithm phase that created the assignment.
    
    Tracks which planning phase assigned this OT to understand the assignment strategy:
    - INITIAL_BALANCE: Round-robin distribution (Phase 1)
    - PROXIMITY: Distance-based assignment within 10km (Phase 2)
    - NIGHTLY_NORMALIZATION: Overnight route optimization (Phase 3)
    """

    INITIAL_BALANCE = "INITIAL_BALANCE"
    """Round-robin initial distribution (Phase 1: assign 1 OT per crew)"""

    PROXIMITY = "PROXIMITY"
    """Proximity-based assignment (Phase 2: distance < 10km from centroid)"""

    NIGHTLY_NORMALIZATION = "NIGHTLY_NORMALIZATION"
    """Overnight route optimization (Phase 3: scheduled at 00:00 daily)"""


class AssignmentStatus(str, Enum):
    """
    Status of an assignment record.
    
    ACTIVE: Currently assigned to crew (OT in ASIGNADO_TAREA state)
    COMPLETED: OT finished (OT in FINALIZADA state)
    REASSIGNED: OT reassigned to different crew
    CANCELLED: Assignment cancelled (OT moved back to unassigned)
    """

    ACTIVE = "ACTIVE"
    """Currently assigned to crew"""

    COMPLETED = "COMPLETED"
    """OT completed (FINALIZADA state)"""

    REASSIGNED = "REASSIGNED"
    """OT reassigned to different crew"""

    CANCELLED = "CANCELLED"
    """Assignment cancelled"""


# ============================================================================
# BASE SCHEMAS
# ============================================================================


class AssignmentBase(BaseModel):
    """
    Base assignment schema with core fields.
    
    Attributes:
        ot_id: OT being assigned
        cuadrilla_id: Crew receiving assignment
    """

    ot_id: str = Field(
        ...,
        description="OT being assigned",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    cuadrilla_id: str = Field(
        ...,
        description="Crew receiving assignment",
        example="f47ac10b-58cc-4372-a567-0e02b2c3d479",
    )

    class Config:
        """Pydantic configuration for AssignmentBase"""
        from_attributes = True


# ============================================================================
# CREATE SCHEMA
# ============================================================================


class AssignmentCreate(AssignmentBase):
    """
    Schema for creating a new assignment record.
    Inherits OT and crew IDs from AssignmentBase, adds planning context.
    Used when planning algorithm assigns OT to crew.
    
    Attributes:
        assigned_by: Agent or process that made the assignment
        distance_from_centroid: Distance from crew centroid to OT location
        phase: Which planning phase created this assignment
    
    Example:
        {
            "ot_id": "550e8400-e29b-41d4-a716-446655440000",
            "cuadrilla_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "assigned_by": "PlanificacionAgent",
            "distance_from_centroid": 5.3,
            "phase": "PROXIMITY"
        }
    """

    assigned_by: str = Field(
        default="PlanificacionAgent",
        min_length=1,
        max_length=100,
        description="Agent or process that made the assignment",
        example="PlanificacionAgent",
    )

    distance_from_centroid: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Distance from crew centroid to OT location (kilometers)",
    )

    phase: AssignmentPhase = Field(
        default=AssignmentPhase.INITIAL_BALANCE,
        description="Planning phase that created this assignment",
    )

    class Config:
        """Pydantic configuration for AssignmentCreate"""
        from_attributes = True


# ============================================================================
# DATABASE SCHEMA
# ============================================================================


class AssignmentInDB(AssignmentBase):
    """
    Assignment schema as stored in database.
    Includes auto-generated id, timestamps, and assignment metadata.
    Internal use (not exposed in API responses directly).
    
    Attributes:
        id: UUID primary key (auto-generated)
        assigned_at: Timestamp when assignment was created
        assigned_by: Agent that created the assignment
        distance_from_centroid: Distance in kilometers from crew centroid
        phase: Planning phase that created assignment
        status: Current assignment status (ACTIVE, COMPLETED, REASSIGNED, CANCELLED)
        completed_at: Timestamp when assignment was completed (if status=COMPLETED)
        notes: Optional additional notes about the assignment
    """

    id: str = Field(
        ...,
        description="Unique UUID identifier",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    assigned_at: datetime = Field(
        ...,
        description="Timestamp when assignment was created",
    )

    assigned_by: str = Field(
        ...,
        description="Agent or process that made the assignment",
    )

    distance_from_centroid: Optional[float] = Field(
        default=None,
        description="Distance from crew centroid to OT location (kilometers)",
    )

    phase: AssignmentPhase = Field(
        ...,
        description="Planning phase that created this assignment",
    )

    status: AssignmentStatus = Field(
        default=AssignmentStatus.ACTIVE,
        description="Current assignment status",
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when OT was completed (if status=COMPLETED)",
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional notes about the assignment",
    )

    class Config:
        """Pydantic configuration for AssignmentInDB"""
        from_attributes = True


# ============================================================================
# RESPONSE SCHEMA
# ============================================================================


class AssignmentResponse(AssignmentInDB):
    """
    Assignment schema for API responses.
    Includes all database fields with relationship information.
    Returned by GET endpoints for assignment retrieval.
    
    Example response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "ot_id": "550e8400-e29b-41d4-a716-446655440001",
            "cuadrilla_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "assigned_at": "2024-02-13T15:30:45.123456",
            "assigned_by": "PlanificacionAgent",
            "distance_from_centroid": 5.3,
            "phase": "PROXIMITY",
            "status": "ACTIVE",
            "completed_at": null,
            "notes": "Assigned in Phase 2, within 10km radius"
        }
    """

    class Config:
        """Pydantic configuration for AssignmentResponse"""
        from_attributes = True


# ============================================================================
# LIST RESPONSE SCHEMA
# ============================================================================


class AssignmentListResponse(BaseModel):
    """
    Paginated list response for assignment queries.
    
    Used by GET /api/v1/assignments endpoint (for administrative views).
    
    Example:
        {
            "items": [
                { ... assignment 1 ... },
                { ... assignment 2 ... }
            ],
            "total": 500,
            "page": 1,
            "page_size": 50,
            "total_pages": 10
        }
    """

    items: List[AssignmentResponse] = Field(description="Assignments in current page")
    total: int = Field(description="Total number of assignments")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# FILTER SCHEMA
# ============================================================================


class AssignmentFilters(BaseModel):
    """
    Query filters for retrieving assignments.
    
    Used by GET /api/v1/assignments endpoint.
    
    Attributes:
        ot_id: Filter by OT
        cuadrilla_id: Filter by crew
        phase: Filter by planning phase
        status: Filter by assignment status
        assigned_by: Filter by assigning agent
        from_date: Start of date range
        to_date: End of date range
        page: Page number (1-indexed)
        page_size: Items per page (max 500)
    """

    ot_id: Optional[str] = Field(
        default=None,
        description="Filter by OT",
    )

    cuadrilla_id: Optional[str] = Field(
        default=None,
        description="Filter by crew",
    )

    phase: Optional[AssignmentPhase] = Field(
        default=None,
        description="Filter by planning phase",
    )

    status: Optional[AssignmentStatus] = Field(
        default=None,
        description="Filter by assignment status",
    )

    assigned_by: Optional[str] = Field(
        default=None,
        description="Filter by assigning agent",
    )

    from_date: Optional[datetime] = Field(
        default=None,
        description="Start of date range",
    )

    to_date: Optional[datetime] = Field(
        default=None,
        description="End of date range",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )

    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Items per page (max 500)",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================


class AssignmentStatistics(BaseModel):
    """
    Statistics about assignments.
    
    Used by planning and dashboard endpoints.
    
    Example:
        {
            "total_assignments": 500,
            "by_phase": {
                "INITIAL_BALANCE": 150,
                "PROXIMITY": 300,
                "NIGHTLY_NORMALIZATION": 50
            },
            "by_status": {
                "ACTIVE": 200,
                "COMPLETED": 250,
                "REASSIGNED": 40,
                "CANCELLED": 10
            },
            "average_distance_km": 5.8,
            "max_distance_km": 9.9,
            "assignments_today": 45
        }
    """

    total_assignments: int = Field(description="Total number of assignments")
    by_phase: dict = Field(description="Count by planning phase")
    by_status: dict = Field(description="Count by assignment status")
    average_distance_km: float = Field(description="Average distance from centroid")
    max_distance_km: float = Field(description="Maximum distance from centroid")
    assignments_today: int = Field(description="Assignments made today")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# PLANNING ALGORITHM STATISTICS
# ============================================================================


class PhaseStatistics(BaseModel):
    """
    Statistics for a specific planning phase.
    
    Used by GET /api/v1/planning/algorithm-stats endpoint.
    
    Attributes:
        phase: Planning phase identifier
        assignments_count: Total assignments in this phase
        average_distance_km: Average distance from centroid
        successful_assignments: Count of successful assignments
        failed_assignments: Count of failed assignments
        last_execution: Timestamp of last phase execution
        total_ots_processed: Total OTs processed in this phase (all time)
    """

    phase: AssignmentPhase = Field(description="Planning phase")
    assignments_count: int = Field(description="Total assignments in this phase")
    average_distance_km: float = Field(description="Average distance from centroid")
    successful_assignments: int = Field(description="Successful assignments")
    failed_assignments: int = Field(description="Failed assignments")
    last_execution: Optional[datetime] = Field(default=None, description="Last phase execution")
    total_ots_processed: int = Field(description="Total OTs processed all-time")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class PlanningAlgorithmStats(BaseModel):
    """
    Overall planning algorithm statistics.
    
    Used by GET /api/v1/planning/algorithm-stats endpoint.
    Shows performance metrics and distribution across phases.
    
    Example:
        {
            "total_assignments": 500,
            "overall_average_distance_km": 5.8,
            "phases": [
                {
                    "phase": "INITIAL_BALANCE",
                    "assignments_count": 150,
                    "average_distance_km": 0.0,
                    ...
                },
                ...
            ],
            "load_distribution": {
                "cuadrilla_1": {"current": 8, "capacity": 10, "distance_km": 5.3},
                "cuadrilla_2": {"current": 9, "capacity": 10, "distance_km": 6.1},
                ...
            },
            "constraint_violations": 0,
            "algorithm_efficiency": 95.5
        }
    """

    total_assignments: int = Field(description="Total assignments")
    overall_average_distance_km: float = Field(description="Overall average distance")
    phases: List[PhaseStatistics] = Field(description="Per-phase statistics")
    load_distribution: dict = Field(
        description="Current load per crew",
        example={
            "crew_1": {"current": 8, "capacity": 10, "distance_km": 5.3},
            "crew_2": {"current": 9, "capacity": 10, "distance_km": 6.1},
        },
    )
    constraint_violations: int = Field(description="Distance constraint violations")
    algorithm_efficiency: float = Field(
        description="Efficiency percentage (successful / total)",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# OT ASSIGNMENT HISTORY
# ============================================================================


class OTAssignmentHistory(BaseModel):
    """
    Complete assignment history for a single OT.
    
    Shows all assignments (current and past) for an OT.
    Useful for audit trail and understanding OT routing.
    
    Attributes:
        ot_id: OT identifier
        current_assignment: Current active assignment (if any)
        assignment_history: All assignments (past and current)
        total_reassignments: Number of times reassigned
    """

    ot_id: str = Field(description="OT identifier")
    current_assignment: Optional[AssignmentResponse] = Field(
        default=None,
        description="Current active assignment",
    )
    assignment_history: List[AssignmentResponse] = Field(
        description="All assignments (sorted by date, newest first)",
    )
    total_reassignments: int = Field(
        description="Number of times reassigned",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# CUADRILLA ASSIGNMENT SUMMARY
# ============================================================================


class CuadrillaAssignmentSummary(BaseModel):
    """
    Assignment summary for a crew.
    
    Shows active assignments and pending OTs for a crew.
    Used in crew detail pages and capacity planning.
    
    Attributes:
        cuadrilla_id: Crew identifier
        current_load: Number of active assignments
        daily_capacity: Maximum daily capacity
        active_assignments: List of active assignment OT IDs
        pending_ots: Number of unassigned OTs waiting for this crew
    """

    cuadrilla_id: str = Field(description="Crew identifier")
    current_load: int = Field(description="Number of active assignments")
    daily_capacity: int = Field(description="Maximum daily capacity")
    active_assignments: List[str] = Field(
        description="List of active assignment OT IDs",
    )
    pending_ots: int = Field(
        description="Unassigned OTs waiting for this crew",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# REASSIGNMENT REQUEST
# ============================================================================


class ReassignmentRequest(BaseModel):
    """
    Request to reassign an OT to a different crew.
    
    Used by POST /api/v1/planning/reassign endpoint.
    Allows manual override of assignments.
    
    Attributes:
        ot_id: OT to reassign
        new_cuadrilla_id: New crew target
        reason: Why reassignment is needed
        force: If True, override constraints
    """

    ot_id: str = Field(
        ...,
        description="OT to reassign",
    )

    new_cuadrilla_id: str = Field(
        ...,
        description="New crew to assign to",
    )

    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Reason for reassignment",
        example="Original crew unable to meet deadline",
    )

    force: bool = Field(
        default=False,
        description="If True, override distance and capacity constraints",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class ReassignmentResponse(BaseModel):
    """
    Response from reassignment operation.
    
    Attributes:
        success: Whether reassignment succeeded
        message: Result message
        old_assignment: Previous assignment details
        new_assignment: New assignment details
        warnings: Any constraint warnings
    """

    success: bool = Field(description="Whether reassignment succeeded")
    message: str = Field(description="Result message")
    old_assignment: Optional[AssignmentResponse] = Field(
        default=None,
        description="Previous assignment",
    )
    new_assignment: Optional[AssignmentResponse] = Field(
        default=None,
        description="New assignment",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Constraint warning messages",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# EXPORT SCHEMAS
# ============================================================================

__all__ = [
    "AssignmentBase",
    "AssignmentCreate",
    "AssignmentInDB",
    "AssignmentResponse",
    "AssignmentListResponse",
    "AssignmentFilters",
    "AssignmentStatistics",
    "PhaseStatistics",
    "PlanningAlgorithmStats",
    "OTAssignmentHistory",
    "CuadrillaAssignmentSummary",
    "ReassignmentRequest",
    "ReassignmentResponse",
    "AssignmentPhase",
    "AssignmentStatus",
]

