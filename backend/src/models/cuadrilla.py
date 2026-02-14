"""
Cuadrilla (Technical Team) Model for PEI Platform.

This module defines the SQLAlchemy ORM model for cuadrillas (technical teams/crew)
that execute OTs in the field. Cuadrillas can be PRINCIPAL (base load) or RESERVA
(overflow/distance-critical).
"""

from enum import Enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin
from src.utils.geo_utils import calculate_centroid


class CuadrillaType(str, Enum):
    """Cuadrilla type enumeration."""

    PRINCIPAL = "PRINCIPAL"  # Base load teams (50% of capacity)
    RESERVA = "RESERVA"      # Overflow/distance-critical teams (50% of capacity)


class Cuadrilla(Base, TimestampMixin):
    """
    Cuadrilla (Technical Team) Model.

    Represents a technical team that can be assigned OTs for execution.
    Cuadrillas have geographic centroids (calculated from assigned OTs)
    used for proximity-based assignment decisions.

    Attributes:
        id: Unique internal identifier (primary key)
        name: Human-readable team name (unique)
        type: Team type (PRINCIPAL or RESERVA)
        last_centroid_lat: Latitude of geographic center of assigned OTs
        last_centroid_long: Longitude of geographic center of assigned OTs
        max_daily_capacity: Maximum OTs that can be assigned per day (default: 10)
        current_load: Currently assigned OTs count
        created_at: Timestamp when cuadrilla was created (via TimestampMixin)
        updated_at: Timestamp when cuadrilla was last updated (via TimestampMixin)
    """

    __tablename__ = "cuadrillas"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, doc="Internal cuadrilla identifier")

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Human-readable team name (e.g., 'Quito-Norte-01')",
    )

    type: Mapped[CuadrillaType] = mapped_column(
        String(20),
        default=CuadrillaType.PRINCIPAL,
        nullable=False,
        doc="Team type: PRINCIPAL (base load) or RESERVA (overflow)",
    )

    # Geographic Center (Centroid)
    last_centroid_lat: Mapped[float | None] = mapped_column(
        nullable=True,
        doc="Latitude of geographic center (calculated from assigned OTs)",
    )

    last_centroid_long: Mapped[float | None] = mapped_column(
        nullable=True,
        doc="Longitude of geographic center (calculated from assigned OTs)",
    )

    # Capacity Management
    max_daily_capacity: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum OTs that can be assigned to this cuadrilla per day",
    )

    current_load: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Currently assigned OTs (incremented by Planificación Agent)",
    )

    # Relationships
    ots: Mapped[list["OT"]] = relationship(
        "OT",
        back_populates="cuadrilla",
        doc="OTs assigned to this cuadrilla",
    )

    def __repr__(self) -> str:
        """String representation of Cuadrilla."""
        return (
            f"<Cuadrilla(id={self.id}, name={self.name}, type={self.type}, "
            f"load={self.current_load}/{self.max_daily_capacity})>"
        )

    def to_dict(self) -> dict:
        """Convert Cuadrilla to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, CuadrillaType) else self.type,
            "last_centroid_lat": self.last_centroid_lat,
            "last_centroid_long": self.last_centroid_long,
            "max_daily_capacity": self.max_daily_capacity,
            "current_load": self.current_load,
            "available_capacity": self.max_daily_capacity - self.current_load,
            "utilization_percent": round((self.current_load / self.max_daily_capacity) * 100, 2)
            if self.max_daily_capacity > 0
            else 0,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def calculate_centroid(self) -> tuple[float, float] | None:
        """
        Calculate the geographic centroid of all assigned OTs.

        Used by Planificación Agent to determine the center point for
        proximity calculations (10km radius check).

        Returns:
            tuple[float, float] | None: (lat, lon) of centroid, or None if no OTs assigned
        """
        # Get OTs with valid coordinates
        ots_with_coords = [
            (ot.lat, ot.long)
            for ot in self.ots
            if ot.lat is not None and ot.long is not None and not ot.is_geo_error
        ]

        if not ots_with_coords:
            return None

        return calculate_centroid(ots_with_coords)

    def update_capacity_load(self, delta: int) -> None:
        """
        Update the current load (add or remove OTs).

        Args:
            delta (int): Change in load (positive to add, negative to remove)
        """
        self.current_load = max(0, self.current_load + delta)

    def has_capacity_available(self) -> bool:
        """
        Check if the cuadrilla has capacity to accept more OTs.

        Returns:
            bool: True if current_load < max_daily_capacity
        """
        return self.current_load < self.max_daily_capacity

    def get_available_capacity(self) -> int:
        """
        Get the number of additional OTs that can be assigned.

        Returns:
            int: max_daily_capacity - current_load
        """
        return max(0, self.max_daily_capacity - self.current_load)

    def get_utilization_percent(self) -> float:
        """
        Get the capacity utilization as a percentage.

        Returns:
            float: (current_load / max_daily_capacity) * 100
        """
        if self.max_daily_capacity == 0:
            return 0.0
        return round((self.current_load / self.max_daily_capacity) * 100, 2)

    def is_principal(self) -> bool:
        """Check if this is a PRINCIPAL team."""
        return self.type == CuadrillaType.PRINCIPAL or self.type == "PRINCIPAL"

    def is_reserva(self) -> bool:
        """Check if this is a RESERVA team."""
        return self.type == CuadrillaType.RESERVA or self.type == "RESERVA"

