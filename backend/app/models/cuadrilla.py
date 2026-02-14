"""
SQLAlchemy Cuadrilla (Crew/OPU) model for PEI Agentic Platform.
Represents technical crews that execute Orders of Work.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ot import OT
    from app.models.assignment import Assignment


# ============================================================================
# ENUMS
# ============================================================================


class CuadrillaType(str, Enum):
    """
    Crew types with different responsibilities.
    
    PRINCIPAL: Main crews handling standard daily workload (50% of fleet)
    RESERVA: Reserve crews for overflow and long-distance assignments (50% of fleet)
    """

    PRINCIPAL = "PRINCIPAL"
    RESERVA = "RESERVA"


# ============================================================================
# CUADRILLA MODEL
# ============================================================================


class Cuadrilla(Base):
    """
    Cuadrilla (Crew/OPU) model.
    
    Represents a technical crew that executes Orders of Work.
    Crews can be assigned multiple OTs up to their daily capacity.
    
    Attributes:
        id: UUID primary key
        name: Unique crew identifier/name
        type: Crew type (PRINCIPAL or RESERVA)
        last_centroid_lat: Last calculated centroid latitude from assigned OTs
        last_centroid_long: Last calculated centroid longitude from assigned OTs
        daily_capacity: Maximum number of OTs crew can handle per day
        current_load: Number of currently assigned active OTs
        active: Whether crew is active and accepting assignments
        created_at: Timestamp when crew was created
    """

    __tablename__ = "cuadrillas"

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
    # CORE FIELDS
    # ========================================================================

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique crew name identifier",
    )

    type: Mapped[CuadrillaType] = mapped_column(
        SQLEnum(CuadrillaType),
        nullable=False,
        index=True,
        doc="Crew type: PRINCIPAL (standard) or RESERVA (overflow/distance)",
    )

    # ========================================================================
    # GEOGRAPHIC FIELDS
    # ========================================================================

    last_centroid_lat: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Last calculated centroid latitude from assigned OTs",
    )

    last_centroid_long: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Last calculated centroid longitude from assigned OTs",
    )

    # ========================================================================
    # CAPACITY FIELDS
    # ========================================================================

    daily_capacity: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum number of OTs crew can handle per day",
    )

    current_load: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Current number of assigned OTs",
    )

    # ========================================================================
    # STATUS FIELDS
    # ========================================================================

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether crew is active and accepting assignments",
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        doc="Timestamp when crew was created",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    ots: Mapped[List["OT"]] = relationship(
        "OT",
        back_populates="cuadrilla",
        foreign_keys="OT.cuadrilla_id",
        doc="Orders of Work assigned to this crew",
    )

    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="cuadrilla",
        cascade="all, delete-orphan",
        doc="Assignment history for this crew",
    )

    # ========================================================================
    # COMPOSITE INDEXES
    # ========================================================================

    __table_args__ = (
        # Index for finding active crews with available capacity
        Index("ix_cuadrilla_active_load", "active", "current_load"),
        # Index for finding crews by type and active status
        Index("ix_cuadrilla_type_active", "type", "active"),
        # Index for time range queries
        Index("ix_cuadrilla_created_at", "created_at"),
    )

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"<Cuadrilla(id={self.id}, name={self.name}, type={self.type}, "
            f"load={self.current_load}/{self.daily_capacity}, active={self.active})>"
        )

    def __str__(self) -> str:
        """Human-readable string."""
        status = "Active" if self.active else "Inactive"
        return (
            f"Cuadrilla {self.name} ({self.type}) - "
            f"Load: {self.current_load}/{self.daily_capacity} - {status}"
        )

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def available_slots(self) -> int:
        """Calculate number of available slots."""
        return max(0, self.daily_capacity - self.current_load)

    @property
    def is_available(self) -> bool:
        """Check if crew has available capacity and is active."""
        return self.active and self.current_load < self.daily_capacity

    @property
    def is_at_capacity(self) -> bool:
        """Check if crew is at maximum capacity."""
        return self.current_load >= self.daily_capacity

    @property
    def utilization_percentage(self) -> float:
        """Calculate crew utilization as percentage."""
        if self.daily_capacity == 0:
            return 0.0
        return (self.current_load / self.daily_capacity) * 100

    @property
    def has_centroid(self) -> bool:
        """Check if crew has calculated centroid coordinates."""
        return self.last_centroid_lat is not None and self.last_centroid_long is not None

    @property
    def centroid(self) -> Optional[tuple]:
        """Return centroid as (lat, long) tuple or None."""
        if self.has_centroid:
            return (self.last_centroid_lat, self.last_centroid_long)
        return None

    # ========================================================================
    # METHODS FOR CAPACITY MANAGEMENT
    # ========================================================================

    def add_assignment(self, count: int = 1) -> bool:
        """
        Add OT assignment to crew (increment current_load).
        
        Args:
            count: Number of OTs to assign (default 1)
            
        Returns:
            bool: True if assignment successful, False if would exceed capacity
        """
        if self.current_load + count > self.daily_capacity:
            return False
        
        self.current_load += count
        return True

    def remove_assignment(self, count: int = 1) -> bool:
        """
        Remove OT assignment from crew (decrement current_load).
        
        Args:
            count: Number of OTs to unassign (default 1)
            
        Returns:
            bool: True if successful, False if would go negative
        """
        if self.current_load - count < 0:
            return False
        
        self.current_load -= count
        return True

    def has_capacity_for(self, count: int = 1) -> bool:
        """
        Check if crew can accept additional OTs.
        
        Args:
            count: Number of OTs to check (default 1)
            
        Returns:
            bool: True if crew has capacity and is active
        """
        return self.active and (self.current_load + count <= self.daily_capacity)

    def reset_load(self) -> None:
        """Reset current load to 0 (used for recalculation)."""
        self.current_load = 0

    # ========================================================================
    # METHODS FOR CENTROID MANAGEMENT
    # ========================================================================

    def update_centroid(self, lat: float, long: float) -> None:
        """
        Update crew centroid coordinates.
        
        Args:
            lat: New latitude
            long: New longitude
        """
        self.last_centroid_lat = lat
        self.last_centroid_long = long

    def clear_centroid(self) -> None:
        """Clear centroid coordinates."""
        self.last_centroid_lat = None
        self.last_centroid_long = None

    # ========================================================================
    # METHODS FOR ACTIVITY MANAGEMENT
    # ========================================================================

    def deactivate(self) -> None:
        """Mark crew as inactive (stops accepting new assignments)."""
        self.active = False

    def activate(self) -> None:
        """Mark crew as active (resumes accepting assignments)."""
        self.active = True

    def toggle_active(self) -> bool:
        """
        Toggle crew active status.
        
        Returns:
            bool: New active status
        """
        self.active = not self.active
        return self.active

    # ========================================================================
    # METHODS FOR CAPACITY CONFIGURATION
    # ========================================================================

    def set_daily_capacity(self, capacity: int) -> bool:
        """
        Update crew daily capacity.
        
        Args:
            capacity: New capacity (must be > 0)
            
        Returns:
            bool: True if successful, False if capacity is invalid
        """
        if capacity <= 0 or capacity > 50:
            return False
        
        self.daily_capacity = capacity
        return True

    # ========================================================================
    # DATA CONVERSION METHODS
    # ========================================================================

    def to_dict(self) -> dict:
        """
        Convert Cuadrilla to dictionary for API responses.
        
        Returns:
            dict: Cuadrilla data
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type.value,
            "last_centroid_lat": self.last_centroid_lat,
            "last_centroid_long": self.last_centroid_long,
            "daily_capacity": self.daily_capacity,
            "current_load": self.current_load,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "available_slots": self.available_slots,
            "utilization_percentage": self.utilization_percentage,
            "is_available": self.is_available,
            "has_centroid": self.has_centroid,
        }

    def to_dict_with_ots(self) -> dict:
        """
        Convert Cuadrilla to dictionary including assigned OTs.
        
        Returns:
            dict: Cuadrilla data with assigned OTs list
        """
        data = self.to_dict()
        data["assigned_ots"] = [ot.to_dict() for ot in self.ots]
        return data

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    def validate_capacity(self) -> bool:
        """
        Validate that current_load doesn't exceed daily_capacity.
        
        Returns:
            bool: True if valid, False if overloaded
        """
        return self.current_load <= self.daily_capacity

    def validate_state(self) -> tuple[bool, str]:
        """
        Validate overall crew state consistency.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.name:
            return False, "Crew name is required"
        
        if self.daily_capacity <= 0:
            return False, "Daily capacity must be positive"
        
        if self.current_load < 0:
            return False, "Current load cannot be negative"
        
        if self.current_load > self.daily_capacity:
            return False, "Current load exceeds daily capacity"
        
        return True, ""

    # ========================================================================
    # INFORMATION METHODS
    # ========================================================================

    def get_status_summary(self) -> str:
        """
        Get human-readable status summary.
        
        Returns:
            str: Status summary
        """
        if not self.active:
            return "Inactive - Not accepting assignments"
        
        if self.is_at_capacity:
            return "At capacity - No available slots"
        
        return f"Active - {self.available_slots} slots available"

    def get_capacity_warning(self) -> Optional[str]:
        """
        Get warning message if crew is near capacity.
        
        Returns:
            Optional[str]: Warning message or None
        """
        utilization = self.utilization_percentage
        
        if utilization >= 90:
            return f"Critical: {utilization:.0f}% capacity utilization"
        elif utilization >= 70:
            return f"Warning: {utilization:.0f}% capacity utilization"
        
        return None

