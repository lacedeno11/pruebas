"""
SQLAlchemy Assignment model for PEI Agentic Platform.
Tracks the history of OT assignments to Cuadrillas (crews).
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    UUID,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ot import OT
    from app.models.cuadrilla import Cuadrilla


# ============================================================================
# ENUMS
# ============================================================================


class AssignmentPhase(str, Enum):
    """
    Planning phases for OT assignments.
    
    INITIAL_BALANCE: Phase 1 - round-robin distribution (1 OT per crew)
    PROXIMITY: Phase 2 - proximity-based assignment within 10km radius
    NIGHTLY_NORMALIZATION: Phase 3 - route optimization scheduled nightly
    """

    INITIAL_BALANCE = "INITIAL_BALANCE"
    PROXIMITY = "PROXIMITY"
    NIGHTLY_NORMALIZATION = "NIGHTLY_NORMALIZATION"


class AssignmentStatus(str, Enum):
    """
    Status of an assignment.
    
    ACTIVE: Currently assigned to crew
    COMPLETED: OT completed by crew
    REASSIGNED: OT was reassigned to different crew
    CANCELLED: Assignment was cancelled
    """

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    REASSIGNED = "REASSIGNED"
    CANCELLED = "CANCELLED"


# ============================================================================
# ASSIGNMENT MODEL
# ============================================================================


class Assignment(Base):
    """
    Assignment model for OT-Cuadrilla relationships.
    
    Tracks which crew is assigned to which OT, when, and through which
    planning phase. Maintains full history of assignments for analytics.
    
    Attributes:
        id: UUID primary key
        ot_id: Foreign key to OT
        cuadrilla_id: Foreign key to Cuadrilla (crew)
        assigned_at: Timestamp when assignment was made
        assigned_by: Agent that made assignment (e.g., 'PlanificacionAgent')
        distance_from_centroid: Distance from crew centroid to OT in kilometers
        phase: Planning phase during which assignment occurred
        status: Current status of assignment
        completed_at: Timestamp when OT was completed (nullable)
        notes: Additional notes about assignment
    """

    __tablename__ = "assignments"

    # ========================================================================
    # PRIMARY KEY
    # ========================================================================

    id: Mapped[str] = mapped_column(
        UUID,
        primary_key=True,
        default=lambda: str(__import__("uuid").uuid4()),
        doc="Unique UUID identifier",
    )

    # ========================================================================
    # FOREIGN KEYS
    # ========================================================================

    ot_id: Mapped[str] = mapped_column(
        UUID,
        ForeignKey("ots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated OT",
    )

    cuadrilla_id: Mapped[str] = mapped_column(
        UUID,
        ForeignKey("cuadrillas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Assigned crew",
    )

    # ========================================================================
    # ASSIGNMENT FIELDS
    # ========================================================================

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        doc="When assignment was made",
    )

    assigned_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Agent that made assignment (e.g., 'PlanificacionAgent')",
    )

    # ========================================================================
    # GEOGRAPHIC & PLANNING FIELDS
    # ========================================================================

    distance_from_centroid: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Distance from crew centroid to OT in kilometers",
    )

    phase: Mapped[AssignmentPhase] = mapped_column(
        SQLEnum(AssignmentPhase),
        nullable=False,
        index=True,
        doc="Planning phase (INITIAL_BALANCE, PROXIMITY, NIGHTLY_NORMALIZATION)",
    )

    # ========================================================================
    # STATUS FIELDS
    # ========================================================================

    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus),
        default=AssignmentStatus.ACTIVE,
        nullable=False,
        index=True,
        doc="Assignment status (ACTIVE, COMPLETED, REASSIGNED, CANCELLED)",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When OT was completed",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Additional notes about assignment",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    ot: Mapped["OT"] = relationship(
        "OT",
        back_populates="assignments",
        foreign_keys=[ot_id],
        doc="Associated OT",
    )

    cuadrilla: Mapped["Cuadrilla"] = relationship(
        "Cuadrilla",
        back_populates="assignments",
        foreign_keys=[cuadrilla_id],
        doc="Assigned crew",
    )

    # ========================================================================
    # COMPOSITE INDEXES
    # ========================================================================

    __table_args__ = (
        # Index for finding assignments by OT and cuadrilla
        Index("ix_assignment_ot_cuadrilla", "ot_id", "cuadrilla_id"),
        # Index for finding active assignments for a crew
        Index("ix_assignment_cuadrilla_status", "cuadrilla_id", "status"),
        # Index for finding assignments by phase
        Index("ix_assignment_phase_assigned_at", "phase", "assigned_at"),
        # Index for finding assignments by agent
        Index("ix_assignment_assigned_by", "assigned_by"),
    )

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"<Assignment(id={self.id}, ot_id={self.ot_id}, "
            f"cuadrilla_id={self.cuadrilla_id}, status={self.status}, "
            f"phase={self.phase})>"
        )

    def __str__(self) -> str:
        """Human-readable string."""
        return (
            f"Assignment: OT {self.ot_id} → Crew {self.cuadrilla_id} "
            f"({self.phase}) [{self.status}]"
        )

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def is_active(self) -> bool:
        """Check if assignment is currently active."""
        return self.status == AssignmentStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if assignment is completed."""
        return self.status == AssignmentStatus.COMPLETED

    @property
    def is_reassigned(self) -> bool:
        """Check if assignment was reassigned."""
        return self.status == AssignmentStatus.REASSIGNED

    @property
    def is_cancelled(self) -> bool:
        """Check if assignment was cancelled."""
        return self.status == AssignmentStatus.CANCELLED

    @property
    def has_distance(self) -> bool:
        """Check if distance from centroid is recorded."""
        return self.distance_from_centroid is not None

    @property
    def within_constraint(self) -> bool:
        """Check if assignment is within 10km constraint."""
        if not self.has_distance:
            return False
        return self.distance_from_centroid <= 10.0

    # ========================================================================
    # METHODS FOR STATUS MANAGEMENT
    # ========================================================================

    def mark_completed(self) -> None:
        """Mark assignment as completed."""
        self.status = AssignmentStatus.COMPLETED
        self.completed_at = datetime.now(datetime.timezone.utc)

    def mark_reassigned(self) -> None:
        """Mark assignment as reassigned."""
        self.status = AssignmentStatus.REASSIGNED

    def mark_cancelled(self, reason: Optional[str] = None) -> None:
        """
        Mark assignment as cancelled.
        
        Args:
            reason: Optional cancellation reason
        """
        self.status = AssignmentStatus.CANCELLED
        if reason:
            self.notes = f"Cancelled: {reason}"

    def reactivate(self) -> None:
        """Reactivate a cancelled or reassigned assignment."""
        self.status = AssignmentStatus.ACTIVE
        self.completed_at = None

    # ========================================================================
    # METHODS FOR INFORMATION
    # ========================================================================

    def get_duration_minutes(self) -> Optional[int]:
        """
        Get assignment duration in minutes (from assigned to completed).
        
        Returns:
            Optional[int]: Duration in minutes, or None if not completed
        """
        if not self.completed_at:
            return None

        duration = self.completed_at - self.assigned_at
        return int(duration.total_seconds() / 60)

    def get_distance_status(self) -> str:
        """
        Get distance constraint status description.
        
        Returns:
            str: Status description
        """
        if not self.has_distance:
            return "No distance recorded"

        if self.within_constraint:
            remaining = 10.0 - self.distance_from_centroid
            return f"Within constraint ({remaining:.1f}km buffer)"
        else:
            excess = self.distance_from_centroid - 10.0
            return f"Outside constraint (exceeds by {excess:.1f}km)"

    def get_phase_description(self) -> str:
        """
        Get human-readable description of planning phase.
        
        Returns:
            str: Phase description
        """
        descriptions = {
            AssignmentPhase.INITIAL_BALANCE: "Round-robin initial distribution",
            AssignmentPhase.PROXIMITY: "Proximity-based (within 10km)",
            AssignmentPhase.NIGHTLY_NORMALIZATION: "Nightly route optimization",
        }
        return descriptions.get(self.phase, str(self.phase))

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    def validate(self) -> tuple[bool, str]:
        """
        Validate assignment consistency.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.ot_id:
            return False, "OT ID is required"

        if not self.cuadrilla_id:
            return False, "Cuadrilla ID is required"

        if not self.assigned_by:
            return False, "Assigned by agent is required"

        if self.assigned_at is None:
            return False, "Assigned at timestamp is required"

        if self.has_distance and self.distance_from_centroid < 0:
            return False, "Distance cannot be negative"

        if self.completed_at and self.assigned_at and self.completed_at < self.assigned_at:
            return False, "Completed time cannot be before assigned time"

        return True, ""

    def validate_phase_transition(self, new_phase: AssignmentPhase) -> bool:
        """
        Check if phase transition is valid.
        
        Phases progress: INITIAL_BALANCE → PROXIMITY → NIGHTLY_NORMALIZATION
        But assignments can be reassigned in any phase.
        
        Args:
            new_phase: Target phase
            
        Returns:
            bool: True if transition is valid
        """
        # If reassigned, can transition to any phase
        if self.is_reassigned:
            return True

        # Phase progression order
        phase_order = {
            AssignmentPhase.INITIAL_BALANCE: 1,
            AssignmentPhase.PROXIMITY: 2,
            AssignmentPhase.NIGHTLY_NORMALIZATION: 3,
        }

        current_order = phase_order.get(self.phase, 0)
        new_order = phase_order.get(new_phase, 0)

        # Can only move to later phases
        return new_order >= current_order

    # ========================================================================
    # DATA CONVERSION METHODS
    # ========================================================================

    def to_dict(self) -> dict:
        """
        Convert Assignment to dictionary for API responses.
        
        Returns:
            dict: Assignment data
        """
        return {
            "id": str(self.id),
            "ot_id": str(self.ot_id),
            "cuadrilla_id": str(self.cuadrilla_id),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
            "distance_from_centroid": self.distance_from_centroid,
            "phase": self.phase.value,
            "status": self.status.value,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "is_active": self.is_active,
            "within_constraint": self.within_constraint,
            "distance_status": self.get_distance_status(),
            "phase_description": self.get_phase_description(),
        }

    # ========================================================================
    # STATIC METHODS FOR ASSIGNMENT CREATION
    # ========================================================================

    @staticmethod
    def create_from_planning(
        ot_id: str,
        cuadrilla_id: str,
        phase: AssignmentPhase,
        distance_from_centroid: Optional[float] = None,
    ) -> "Assignment":
        """
        Create assignment from planning operation.
        
        Args:
            ot_id: OT to assign
            cuadrilla_id: Crew to assign to
            phase: Planning phase
            distance_from_centroid: Distance in km (for Phase 2)
            
        Returns:
            Assignment: New assignment record
        """
        return Assignment(
            ot_id=ot_id,
            cuadrilla_id=cuadrilla_id,
            assigned_by="PlanificacionAgent",
            distance_from_centroid=distance_from_centroid,
            phase=phase,
            status=AssignmentStatus.ACTIVE,
        )

    @staticmethod
    def create_from_manual_assignment(
        ot_id: str,
        cuadrilla_id: str,
        assigned_by_user: str,
        distance_from_centroid: Optional[float] = None,
    ) -> "Assignment":
        """
        Create assignment from manual user action.
        
        Args:
            ot_id: OT to assign
            cuadrilla_id: Crew to assign to
            assigned_by_user: Username of user making assignment
            distance_from_centroid: Distance in km (optional)
            
        Returns:
            Assignment: New assignment record
        """
        return Assignment(
            ot_id=ot_id,
            cuadrilla_id=cuadrilla_id,
            assigned_by=f"ManualAssignment({assigned_by_user})",
            distance_from_centroid=distance_from_centroid,
            phase=AssignmentPhase.INITIAL_BALANCE,
            status=AssignmentStatus.ACTIVE,
        )

    @staticmethod
    def create_from_reassignment(
        original_assignment: "Assignment",
        new_cuadrilla_id: str,
        new_distance: Optional[float] = None,
    ) -> "Assignment":
        """
        Create new assignment from reassignment of existing assignment.
        
        Args:
            original_assignment: Original assignment to replace
            new_cuadrilla_id: New crew ID
            new_distance: Distance to new crew centroid
            
        Returns:
            Assignment: New assignment record
        """
        # Mark original as reassigned
        original_assignment.mark_reassigned()

        # Create new assignment
        return Assignment(
            ot_id=original_assignment.ot_id,
            cuadrilla_id=new_cuadrilla_id,
            assigned_by=original_assignment.assigned_by,
            distance_from_centroid=new_distance,
            phase=original_assignment.phase,
            status=AssignmentStatus.ACTIVE,
            notes=f"Reassigned from {original_assignment.cuadrilla_id}",
        )

