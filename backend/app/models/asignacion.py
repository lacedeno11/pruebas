"""
Asignacion (Assignment) SQLAlchemy Model

Represents an assignment record in the DERCAS PEI system.

Assignment Tracking:
    Each Asignacion record tracks when an OT was assigned to a crew,
    by which planning phase (BALANCE, PROXIMITY, RESERVA), and the
    distance from the crew's centroid at assignment time.

Assignment Phases:
    BALANCE: Phase 1 initial distribution (1 OT per crew)
    PROXIMITY: Phase 2 proximity-based assignment (<10km from centroid)
    RESERVA: Phase 3 reserve crew activation for overflow/distance

Assignment History:
    An OT can have multiple Asignacion records if:
    - Reassigned from one crew to another (route optimization)
    - Reassigned after return from DETENIDA status
    - Moved between PRINCIPAL and RESERVA crews

Audit Trail:
    - assigned_at: UTC timestamp of assignment
    - assigned_by_agent: Which agent created the assignment
    - distance_from_centroid: Distance validation data
    - phase: Which planning phase created the assignment
    - created_at: Log timestamp for record creation
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Asignacion(Base):
    """
    Assignment History model.
    
    Records each OT assignment to a crew, including:
    - Which OT was assigned
    - Which crew received the assignment
    - When the assignment occurred
    - Which planning phase created it
    - Distance from crew's centroid at assignment time
    - Which agent performed the assignment
    
    Enables audit trail, optimization analytics, and reassignment logic.
    
    Table: asignaciones
    """

    __tablename__ = "asignaciones"

    # ========================================================================
    # Primary Key
    # ========================================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique database identifier for assignment record",
    )

    # ========================================================================
    # Foreign Keys
    # ========================================================================

    ot_id = Column(
        Integer,
        ForeignKey("ots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="OT being assigned",
    )

    cuadrilla_id = Column(
        Integer,
        ForeignKey("cuadrillas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Crew receiving the assignment",
    )

    # ========================================================================
    # Assignment Details
    # ========================================================================

    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp when assignment was made",
    )

    assigned_by_agent = Column(
        String(100),
        nullable=False,
        doc="Agent that created this assignment (e.g., 'PLANIFICACION_AGENT')",
    )

    # ========================================================================
    # Distance Information
    # ========================================================================

    distance_from_centroid = Column(
        Float,
        nullable=True,
        doc="Distance from crew's centroid to OT location in km (nullable for first assignment)",
    )

    # ========================================================================
    # Planning Phase
    # ========================================================================

    phase = Column(
        Enum("BALANCE", "PROXIMITY", "RESERVA", name="assignment_phase"),
        nullable=False,
        doc="Planning phase that created this assignment",
    )

    # ========================================================================
    # Audit Timestamp
    # ========================================================================

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="UTC timestamp when record was created",
    )

    # ========================================================================
    # Relationships
    # ========================================================================

    ot = relationship(
        "OT",
        back_populates="asignaciones",
        foreign_keys=[ot_id],
        doc="Associated OT",
    )

    cuadrilla = relationship(
        "Cuadrilla",
        back_populates="asignaciones",
        foreign_keys=[cuadrilla_id],
        doc="Assigned crew",
    )

    # ========================================================================
    # Indexes
    # ========================================================================

    __table_args__ = (
        # Composite index for assignment history queries
        Index("idx_asignacion_ot_assigned_at", "ot_id", "assigned_at"),
        # Composite index for crew assignment tracking
        Index("idx_asignacion_cuadrilla_assigned_at", "cuadrilla_id", "assigned_at"),
        # Index for phase-based queries
        Index("idx_asignacion_phase", "phase"),
        # Index for time-based queries
        Index("idx_asignacion_created_at", "created_at"),
    )

    # ========================================================================
    # String Representation
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Asignacion(id={self.id}, ot_id={self.ot_id}, "
            f"cuadrilla_id={self.cuadrilla_id}, phase={self.phase}, "
            f"distance={self.distance_from_centroid}km)"
        )

    # ========================================================================
    # Properties for Common Operations
    # ========================================================================

    @property
    def is_balanced_assignment(self) -> bool:
        """Check if this is a Phase 1 (BALANCE) assignment."""
        return self.phase == "BALANCE"

    @property
    def is_proximity_assignment(self) -> bool:
        """Check if this is a Phase 2 (PROXIMITY) assignment."""
        return self.phase == "PROXIMITY"

    @property
    def is_reserva_assignment(self) -> bool:
        """Check if this is a Phase 3 (RESERVA) assignment."""
        return self.phase == "RESERVA"

    @property
    def has_distance(self) -> bool:
        """Check if distance from centroid is recorded."""
        return self.distance_from_centroid is not None

    @property
    def is_within_proximity_threshold(self) -> bool:
        """
        Check if assignment is within <10km proximity threshold.
        
        Returns:
            True if distance < 10km, False if distance >= 10km or no distance recorded
        """
        if not self.has_distance:
            return False
        return self.distance_from_centroid < 10.0

    @property
    def days_since_assignment(self) -> float:
        """
        Get number of days since this assignment was made.
        
        Returns:
            Number of days as float (includes fractional days)
        """
        time_delta = datetime.now(timezone.utc) - self.assigned_at
        return time_delta.days + (time_delta.seconds / 86400)

    @property
    def hours_since_assignment(self) -> float:
        """
        Get number of hours since this assignment was made.
        
        Returns:
            Number of hours as float
        """
        time_delta = datetime.now(timezone.utc) - self.assigned_at
        return (time_delta.total_seconds() / 3600)

    # ========================================================================
    # Status Check Methods
    # ========================================================================

    def is_recent(self, hours: int = 24) -> bool:
        """
        Check if assignment is recent (within specified hours).
        
        Args:
            hours: Number of hours to consider "recent" (default: 24)
            
        Returns:
            True if assigned within specified hours, False otherwise
        """
        return self.hours_since_assignment <= hours

    def is_old(self, days: int = 30) -> bool:
        """
        Check if assignment is old (older than specified days).
        
        Args:
            days: Number of days before considering "old" (default: 30)
            
        Returns:
            True if assigned more than specified days ago, False otherwise
        """
        return self.days_since_assignment > days

    def validate_distance(self) -> tuple[bool, str]:
        """
        Validate assignment distance against business rules.
        
        Returns:
            Tuple of (is_valid, message)
        """
        # Phase 1 (BALANCE) doesn't require distance validation
        if self.is_balanced_assignment:
            return True, "Phase 1 (BALANCE) - No distance validation required"

        # Phase 2 (PROXIMITY) requires <10km distance
        if self.is_proximity_assignment:
            if not self.has_distance:
                return False, "Phase 2 (PROXIMITY) - Distance not recorded"
            if self.is_within_proximity_threshold:
                return True, f"Phase 2 (PROXIMITY) - Within 10km threshold ({self.distance_from_centroid:.2f}km)"
            else:
                return False, f"Phase 2 (PROXIMITY) - Outside 10km threshold ({self.distance_from_centroid:.2f}km)"

        # Phase 3 (RESERVA) is for overflow - distance may be flexible
        if self.is_reserva_assignment:
            if self.has_distance:
                return True, f"Phase 3 (RESERVA) - Distance recorded ({self.distance_from_centroid:.2f}km)"
            else:
                return True, "Phase 3 (RESERVA) - Overflow assignment"

        return False, f"Unknown phase: {self.phase}"

    # ========================================================================
    # Analysis Methods
    # ========================================================================

    def get_assignment_type(self) -> str:
        """
        Get human-readable assignment type.
        
        Returns:
            String describing the assignment type
        """
        types = {
            "BALANCE": "Initial Distribution (Phase 1)",
            "PROXIMITY": "Proximity-Based (Phase 2)",
            "RESERVA": "Reserve Crew (Phase 3)",
        }
        return types.get(self.phase, f"Unknown ({self.phase})")

    def get_phase_description(self) -> str:
        """
        Get detailed description of the planning phase.
        
        Returns:
            Phase description string
        """
        descriptions = {
            "BALANCE": (
                "Phase 1: Initial Balance - Distributed 1 OT to each crew "
                "with 0 assignments for equitable distribution"
            ),
            "PROXIMITY": (
                "Phase 2: Proximity Assignment - Assigned based on OT location "
                "being within <10km of crew's calculated centroid"
            ),
            "RESERVA": (
                "Phase 3: Reserve Crew Activation - Assigned to RESERVA crew "
                "for overflow workload or distance-based constraints"
            ),
        }
        return descriptions.get(self.phase, f"Unknown phase: {self.phase}")

    def get_distance_summary(self) -> str:
        """
        Get human-readable distance summary.
        
        Returns:
            Distance summary string
        """
        if not self.has_distance:
            return "No distance recorded"

        if self.is_within_proximity_threshold:
            return f"{self.distance_from_centroid:.2f}km (within threshold)"
        else:
            return f"{self.distance_from_centroid:.2f}km (exceeds threshold)"

    # ========================================================================
    # Assignment Quality Metrics
    # ========================================================================

    def get_quality_score(self) -> float:
        """
        Calculate assignment quality score (0-100).
        
        Scoring:
        - Phase 1 (BALANCE): 100 (perfect initial distribution)
        - Phase 2 (PROXIMITY): 100 if <10km, 50-80 if >= 10km
        - Phase 3 (RESERVA): 70-90 (acceptable for overflow)
        
        Returns:
            Quality score from 0 to 100
        """
        if self.is_balanced_assignment:
            return 100.0

        if self.is_proximity_assignment:
            if self.is_within_proximity_threshold:
                return 100.0 - (self.distance_from_centroid / 10.0) * 20.0
            else:
                return max(50.0, 80.0 - (self.distance_from_centroid / 20.0) * 30.0)

        if self.is_reserva_assignment:
            if self.has_distance and self.distance_from_centroid < 15.0:
                return 85.0
            else:
                return 70.0

        return 0.0

    def get_optimization_potential(self) -> float:
        """
        Calculate potential for optimization (0-100).
        
        Higher value indicates more potential for optimization.
        
        Returns:
            Optimization potential from 0 to 100
        """
        # Phase 1 is already optimal
        if self.is_balanced_assignment:
            return 0.0

        # Phase 2 outside threshold has high optimization potential
        if self.is_proximity_assignment and not self.is_within_proximity_threshold:
            return min(100.0, (self.distance_from_centroid - 10.0) * 5.0)

        # Phase 3 (RESERVA) has moderate optimization potential
        if self.is_reserva_assignment:
            return 50.0

        return 0.0

    # ========================================================================
    # Audit Trail Methods
    # ========================================================================

    def get_audit_message(self) -> str:
        """
        Get formatted audit message for logging.
        
        Returns:
            Formatted audit trail message
        """
        return (
            f"OT assigned to Crew {self.cuadrilla_id} "
            f"via {self.get_assignment_type()} "
            f"by {self.assigned_by_agent} "
            f"at {self.assigned_at.isoformat()} "
            f"({self.get_distance_summary()})"
        )

    def to_dict(self) -> dict:
        """
        Convert assignment record to dictionary.
        
        Returns:
            Dictionary representation of assignment
        """
        return {
            "id": self.id,
            "ot_id": self.ot_id,
            "cuadrilla_id": self.cuadrilla_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by_agent": self.assigned_by_agent,
            "distance_from_centroid": self.distance_from_centroid,
            "phase": self.phase,
            "phase_description": self.get_phase_description(),
            "quality_score": self.get_quality_score(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Type Hints
# ============================================================================

__all__ = ["Asignacion"]

