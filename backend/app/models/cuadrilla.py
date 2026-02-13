"""
Cuadrilla (Work Crew) SQLAlchemy Model

Represents a work crew (Cuadrilla) in the DERCAS PEI system.

Crew Types:
    PRINCIPAL: Primary crew (50% of base workload capacity)
    RESERVA: Reserve crew (activated only when needed for overflow/distance)

Crew Assignment:
    - Each crew has a max_capacity (default 10 OTs)
    - Tracks last calculated centroid (lat/long) for proximity assignment
    - Maintains relationship to all assigned OTs
    - Can be queried for assigned OT count and utilization metrics

Centroid Tracking:
    - last_centroid_lat/long: Updated nightly by Phase 3 optimization
    - Used by Phase 2 to validate <10km proximity for new assignments
    - Recalculated from all currently assigned OTs with valid coordinates
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Cuadrilla(Base):
    """
    Work Crew (Cuadrilla) model.
    
    Represents a crew that can be assigned work orders. Tracks:
    - Crew identification (name, type)
    - Current location/centroid for proximity-based assignment
    - Capacity constraints and utilization
    - Assignment history via relationship to OT records
    
    Table: cuadrillas
    """

    __tablename__ = "cuadrillas"

    # ========================================================================
    # Primary Key
    # ========================================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique database identifier for crew",
    )

    # ========================================================================
    # Crew Identification
    # ========================================================================

    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique crew name identifier (e.g., 'Crew A', 'Crew Downtown')",
    )

    type = Column(
        Enum("PRINCIPAL", "RESERVA", name="cuadrilla_type"),
        nullable=False,
        default="PRINCIPAL",
        index=True,
        doc="Crew type: PRINCIPAL (base crew) or RESERVA (overflow crew)",
    )

    # ========================================================================
    # Capacity Management
    # ========================================================================

    max_capacity = Column(
        Integer,
        nullable=False,
        default=10,
        doc="Maximum number of OTs this crew can handle simultaneously",
    )

    # ========================================================================
    # Geographic Location (Centroid)
    # ========================================================================

    last_centroid_lat = Column(
        Float,
        nullable=True,
        doc="Last calculated latitude of crew's centroid (average of assigned OT locations)",
    )

    last_centroid_long = Column(
        Float,
        nullable=True,
        doc="Last calculated longitude of crew's centroid (average of assigned OT locations)",
    )

    # ========================================================================
    # Timestamps
    # ========================================================================

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="UTC timestamp when crew was created",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp when crew was last updated",
    )

    # ========================================================================
    # Relationships
    # ========================================================================

    ots = relationship(
        "OT",
        back_populates="cuadrilla",
        foreign_keys="OT.cuadrilla_id",
        doc="Work orders assigned to this crew",
    )

    asignaciones = relationship(
        "Asignacion",
        back_populates="cuadrilla",
        cascade="all, delete-orphan",
        doc="Assignment history records for this crew",
    )

    # ========================================================================
    # Indexes
    # ========================================================================

    __table_args__ = (
        # Index for filtering by type (PRINCIPAL vs RESERVA)
        Index("idx_cuadrilla_type", "type"),
        # Index for time-based queries
        Index("idx_cuadrilla_created_at", "created_at"),
    )

    # ========================================================================
    # String Representation
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Cuadrilla(id={self.id}, name={self.name!r}, type={self.type}, "
            f"assigned_ots_count={self.assigned_ots_count}, "
            f"max_capacity={self.max_capacity})"
        )

    # ========================================================================
    # Properties for Common Operations
    # ========================================================================

    @property
    def assigned_ots_count(self) -> int:
        """
        Get count of OTs currently assigned to this crew.
        
        Counts all OTs where cuadrilla_id = this crew's id
        and status is not terminal (not ANULADA or FINALIZADA).
        
        Returns:
            Number of active assignments
        """
        if not self.ots:
            return 0
        
        # Count active (non-terminal) OTs
        active_count = sum(
            1 for ot in self.ots
            if ot.status not in ("ANULADA", "FINALIZADA")
        )
        return active_count

    @property
    def utilization_percentage(self) -> float:
        """
        Get crew utilization as percentage of max_capacity.
        
        Returns:
            Percentage from 0 to 100+ (can exceed 100 if over capacity)
        """
        if self.max_capacity == 0:
            return 0.0
        
        return (self.assigned_ots_count / self.max_capacity) * 100

    @property
    def has_capacity(self) -> bool:
        """
        Check if crew has capacity for more assignments.
        
        Returns:
            True if assigned_ots_count < max_capacity
        """
        return self.assigned_ots_count < self.max_capacity

    @property
    def available_slots(self) -> int:
        """
        Get number of available assignment slots.
        
        Returns:
            max_capacity - assigned_ots_count, minimum 0
        """
        available = self.max_capacity - self.assigned_ots_count
        return max(0, available)

    @property
    def has_centroid(self) -> bool:
        """
        Check if crew has a calculated centroid.
        
        Returns:
            True if both last_centroid_lat and last_centroid_long are set
        """
        return (
            self.last_centroid_lat is not None
            and self.last_centroid_long is not None
        )

    @property
    def centroid(self) -> tuple | None:
        """
        Get crew's centroid as (lat, long) tuple.
        
        Returns:
            Tuple of (latitude, longitude) or None if not set
        """
        if self.has_centroid:
            return (self.last_centroid_lat, self.last_centroid_long)
        return None

    @property
    def is_principal(self) -> bool:
        """Check if this is a PRINCIPAL crew."""
        return self.type == "PRINCIPAL"

    @property
    def is_reserva(self) -> bool:
        """Check if this is a RESERVA crew."""
        return self.type == "RESERVA"

    # ========================================================================
    # Status Check Methods
    # ========================================================================

    def is_at_capacity(self) -> bool:
        """
        Check if crew is at or over max capacity.
        
        Returns:
            True if assigned_ots_count >= max_capacity
        """
        return self.assigned_ots_count >= self.max_capacity

    def can_accept_assignment(self, count: int = 1) -> bool:
        """
        Check if crew can accept specified number of new assignments.
        
        Args:
            count: Number of assignments to check (default: 1)
            
        Returns:
            True if crew has capacity for all requested assignments
        """
        return (self.assigned_ots_count + count) <= self.max_capacity

    def get_remaining_capacity(self) -> int:
        """
        Get remaining assignment capacity.
        
        Returns:
            Number of additional OTs that can be assigned
        """
        remaining = self.max_capacity - self.assigned_ots_count
        return max(0, remaining)

    # ========================================================================
    # Centroid Management Methods
    # ========================================================================

    def update_centroid(self, lat: float, lon: float) -> None:
        """
        Update crew's centroid coordinates.
        
        Called by Phase 3 optimization after recalculating centroid
        from all assigned OTs.
        
        Args:
            lat: New centroid latitude
            lon: New centroid longitude
        """
        self.last_centroid_lat = lat
        self.last_centroid_long = lon
        self.updated_at = datetime.now(timezone.utc)

    def clear_centroid(self) -> None:
        """
        Clear crew's centroid (set to None).
        
        Used when crew has no assigned OTs or when resetting.
        """
        self.last_centroid_lat = None
        self.last_centroid_long = None
        self.updated_at = datetime.now(timezone.utc)

    # ========================================================================
    # Workload Analysis Methods
    # ========================================================================

    def get_ots_by_status(self, status: str) -> list:
        """
        Get OTs assigned to this crew filtered by status.
        
        Args:
            status: OT status to filter by (e.g., 'ASIGNADO_TAREA')
            
        Returns:
            List of OT objects matching the status
        """
        return [ot for ot in self.ots if ot.status == status]

    def get_active_ots_count(self) -> int:
        """
        Get count of active (in-progress) OTs.
        
        Returns:
            Count of OTs in ASIGNADO_TAREA status
        """
        return len(self.get_ots_by_status("ASIGNADO_TAREA"))

    def get_pending_ots_count(self) -> int:
        """
        Get count of pending (not yet started) OTs.
        
        Returns:
            Count of OTs in PLANIFICADA or PREPLANIFICADA status
        """
        pending_statuses = ["PLANIFICADA", "PREPLANIFICADA"]
        return sum(
            1 for ot in self.ots
            if ot.status in pending_statuses
        )

    def get_detained_ots_count(self) -> int:
        """
        Get count of detained OTs.
        
        Returns:
            Count of OTs in DETENIDA status
        """
        return len(self.get_ots_by_status("DETENIDA"))

    # ========================================================================
    # Distance Analysis Methods
    # ========================================================================

    def get_distance_stats(self) -> dict:
        """
        Get statistics on distance from centroid to assigned OTs.
        
        Only includes OTs with valid coordinates and assignment distance.
        
        Returns:
            Dict with 'min', 'max', 'avg', 'count' distances in km
        """
        from app.models import Asignacion
        
        distances = []
        
        for ot in self.ots:
            # Find most recent assignment for this OT
            recent_assignment = None
            for asignacion in ot.asignaciones:
                if asignacion.cuadrilla_id == self.id:
                    if asignacion.distance_from_centroid is not None:
                        distances.append(asignacion.distance_from_centroid)
                    break
        
        if not distances:
            return {
                "min": None,
                "max": None,
                "avg": None,
                "count": 0,
            }
        
        return {
            "min": min(distances),
            "max": max(distances),
            "avg": sum(distances) / len(distances),
            "count": len(distances),
        }

    # ========================================================================
    # Crew Type Methods
    # ========================================================================

    def activate_as_principal(self) -> None:
        """Convert crew to PRINCIPAL type."""
        self.type = "PRINCIPAL"
        self.updated_at = datetime.now(timezone.utc)

    def activate_as_reserva(self) -> None:
        """Convert crew to RESERVA type."""
        self.type = "RESERVA"
        self.updated_at = datetime.now(timezone.utc)

    # ========================================================================
    # Capacity Adjustment Methods
    # ========================================================================

    def set_capacity(self, new_capacity: int) -> None:
        """
        Set crew's max capacity.
        
        Args:
            new_capacity: New maximum capacity value
        """
        if new_capacity < 1:
            raise ValueError("Capacity must be at least 1")
        
        self.max_capacity = new_capacity
        self.updated_at = datetime.now(timezone.utc)

    def increase_capacity(self, delta: int = 1) -> None:
        """
        Increase crew's max capacity.
        
        Args:
            delta: Amount to increase (default: 1)
        """
        self.max_capacity += delta
        self.updated_at = datetime.now(timezone.utc)

    def decrease_capacity(self, delta: int = 1) -> None:
        """
        Decrease crew's max capacity.
        
        Args:
            delta: Amount to decrease (default: 1)
        """
        new_capacity = self.max_capacity - delta
        if new_capacity < 1:
            raise ValueError(
                f"Cannot decrease capacity below 1 "
                f"(current: {self.max_capacity}, delta: {delta})"
            )
        
        self.max_capacity = new_capacity
        self.updated_at = datetime.now(timezone.utc)


# ============================================================================
# Type Hints
# ============================================================================

__all__ = ["Cuadrilla"]

