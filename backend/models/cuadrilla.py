"""
Cuadrilla (Work Team) SQLAlchemy model for the PEI Platform.
Represents a team of technicians that can be assigned and execute OTs.
"""

from datetime import datetime
from enum import Enum
from typing import List, Tuple, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import relationship

from backend.db.database import Base
from backend.utils.geo_utils import calculate_centroid as geo_calculate_centroid


class CuadrillaType(str, Enum):
    """Enumeration of cuadrilla team types."""

    PRINCIPAL = "PRINCIPAL"  # Primary team with full capacity
    RESERVA = "RESERVA"  # Backup/reserve team


class Cuadrilla(Base):
    """
    Cuadrilla (Work Team) database model.

    Represents a team of technicians that can be assigned OTs and execute them
    in a geographic area. Tracks team capacity, current load, and geographic position.

    Attributes:
        id: Primary key, unique identifier in database
        name: Unique name of the cuadrilla team
        type: Type of cuadrilla (PRINCIPAL or RESERVA)
        last_centroid_lat: Latitude of the team's last calculated centroid
        last_centroid_long: Longitude of the team's last calculated centroid
        daily_capacity: Maximum OTs this team can handle per day
        current_load: Current number of assigned OTs
        is_active: Flag indicating if team is active/available for assignments
        created_at: Timestamp when cuadrilla was created

    Relationships:
        ots: One-to-many relationship with OT model (assigned work orders)
    """

    __tablename__ = "cuadrillas"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Team identification
    name = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(
        SQLEnum(CuadrillaType),
        nullable=False,
        default=CuadrillaType.PRINCIPAL,
        index=True,
    )

    # Geographic position (centroid of service area)
    last_centroid_lat = Column(Float, nullable=True)
    last_centroid_long = Column(Float, nullable=True)

    # Capacity management
    daily_capacity = Column(Integer, nullable=False)
    current_load = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ots = relationship(
        "OT",
        back_populates="cuadrilla",
        foreign_keys="OT.cuadrilla_id",
        cascade="all, delete-orphan",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_cuadrillas_type_active", "type", "is_active"),
        Index("idx_cuadrillas_capacity_load", "daily_capacity", "current_load"),
    )

    def __repr__(self) -> str:
        """String representation of Cuadrilla instance."""
        return (
            f"<Cuadrilla(id={self.id}, name={self.name}, type={self.type}, "
            f"current_load={self.current_load}/{self.daily_capacity})>"
        )

    def has_capacity(self) -> bool:
        """
        Check if cuadrilla has available capacity for more OTs.

        Returns:
            True if current_load < daily_capacity, False otherwise
        """
        return self.current_load < self.daily_capacity

    def get_available_capacity(self) -> int:
        """
        Get the number of OTs this cuadrilla can still accept.

        Returns:
            Remaining capacity (daily_capacity - current_load)
        """
        return max(0, self.daily_capacity - self.current_load)

    def get_centroid(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get the current centroid position of the cuadrilla.

        Returns:
            Tuple of (latitude, longitude) if centroid is set, (None, None) otherwise
        """
        if self.last_centroid_lat is None or self.last_centroid_long is None:
            return (None, None)
        return (self.last_centroid_lat, self.last_centroid_long)

    def calculate_centroid(self) -> Tuple[float, float]:
        """
        Calculate and update the geographic centroid from all assigned OTs.

        This method computes the average latitude and longitude of all OTs
        assigned to this cuadrilla, then updates the last_centroid_lat and
        last_centroid_long fields.

        The centroid represents the geographic center of the cuadrilla's
        service area based on currently assigned OTs.

        Returns:
            Tuple of (centroid_latitude, centroid_longitude) for the cuadrilla

        Algorithm:
            1. Get all assigned OTs with valid coordinates (lat and long not None)
            2. Extract (lat, long) tuples from OTs
            3. Calculate arithmetic mean using geo_utils.calculate_centroid()
            4. Update last_centroid_lat and last_centroid_long
            5. Return the new centroid position

        Note:
            If the cuadrilla has no assigned OTs with coordinates, the centroid
            is set to (0.0, 0.0) and the method returns (0.0, 0.0).

            This method should be called:
            - After OT assignments (PlanificacionAgent Phase 2)
            - During nightly normalization (scheduler.run_nightly_normalization())
            - After OT completion or removal
        """
        # Get all assigned OTs with valid coordinates
        valid_ots = [
            ot for ot in self.ots
            if ot.lat is not None and ot.long is not None
        ]

        # If no OTs with valid coordinates, set centroid to (0, 0)
        if not valid_ots:
            self.last_centroid_lat = 0.0
            self.last_centroid_long = 0.0
            return (0.0, 0.0)

        # Extract coordinates from OTs
        coordinates = [(ot.lat, ot.long) for ot in valid_ots]

        # Calculate centroid using geo_utils
        centroid_lat, centroid_long = geo_calculate_centroid(coordinates)

        # Update centroid fields
        self.last_centroid_lat = centroid_lat
        self.last_centroid_long = centroid_long

        return (centroid_lat, centroid_long)

    def get_assigned_ots(self) -> List:
        """
        Get list of OTs assigned to this cuadrilla.

        Returns:
            List of OT objects assigned to this cuadrilla
        """
        return self.ots if self.ots else []

    def get_ot_count(self) -> int:
        """
        Get the number of OTs currently assigned to this cuadrilla.

        Returns:
            Count of assigned OTs
        """
        return len(self.ots) if self.ots else 0

    def get_load_percentage(self) -> float:
        """
        Calculate the current load as a percentage of capacity.

        Returns:
            Percentage (0-100) of current load relative to daily capacity
        """
        if self.daily_capacity == 0:
            return 0.0
        return (self.current_load / self.daily_capacity) * 100.0

