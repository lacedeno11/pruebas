"""
Cuadrilla SQLAlchemy model.

Represents a work team/crew in the DERCAS system with:
- Identification: id (UUID), name (unique string)
- Type: PRINCIPAL or RESERVA enumeration
- Capacity: capacity_daily (max OTs per day), current_load (current count)
- Location: last_centroid_lat/long (nullable, updated during planning)
- Status: is_active (boolean)
- Timestamps: created_at for audit trail
- Relationships: OrdenTrabajo (one-to-many assigned OTs)
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class CuadrillaType(PyEnum):
    """Cuadrilla type enumeration - 2 types for team classification."""
    PRINCIPAL = "PRINCIPAL"
    RESERVA = "RESERVA"


class Cuadrilla(Base):
    """
    Cuadrilla (Work Team/Crew) model.
    
    Represents a team of technicians/workers that can be assigned OTs.
    Each cuadrilla has:
    - Unique name identifier
    - Type classification (PRINCIPAL or RESERVA)
    - Daily capacity (max OTs per day)
    - Current load tracking (current OT count)
    - Geographic centroid (updated during planning Phase 2)
    - Active status for team availability
    - Audit trail (creation timestamp)
    
    Relationships:
    - ots: One Cuadrilla can have many assigned OrdenTrabajos
    - asignaciones: One Cuadrilla can have many Asignacion records
    
    Table name: cuadrilla
    """
    
    __tablename__ = "cuadrilla"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
        comment="Unique identifier (UUID) for the Cuadrilla"
    )
    
    # Name - Unique identifier for the team
    name = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique name for the Cuadrilla (e.g., 'Team Alpha', 'Squad 1')"
    )
    
    # Type - PRINCIPAL or RESERVA
    type = Column(
        Enum(CuadrillaType),
        nullable=False,
        index=True,
        default=CuadrillaType.PRINCIPAL,
        comment="Cuadrilla type: PRINCIPAL (main team) or RESERVA (backup team)"
    )
    
    # Capacity Management
    capacity_daily = Column(
        Integer,
        nullable=False,
        default=10,
        comment="Maximum number of OTs this cuadrilla can handle per day"
    )
    
    current_load = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Current number of OTs assigned to this cuadrilla"
    )
    
    # Geographic Centroid (updated during planning Phase 2)
    last_centroid_lat = Column(
        Float,
        nullable=True,
        comment="Last calculated centroid latitude (Ecuador bounds: -2 to 1)"
    )
    
    last_centroid_long = Column(
        Float,
        nullable=True,
        comment="Last calculated centroid longitude (Ecuador bounds: -81 to -75)"
    )
    
    # Active Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the cuadrilla is available for assignments"
    )
    
    # Timestamps for audit trail
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when Cuadrilla was created"
    )
    
    # Relationships
    ots = relationship(
        "OrdenTrabajo",
        back_populates="cuadrilla",
        foreign_keys="OrdenTrabajo.cuadrilla_id",
        lazy="select",
        cascade="all, delete-orphan",
        comment="One-to-many relationship: Cuadrilla has many assigned OTs"
    )
    
    asignaciones = relationship(
        "Asignacion",
        back_populates="cuadrilla",
        foreign_keys="Asignacion.cuadrilla_id",
        lazy="select",
        cascade="all, delete-orphan",
        comment="One-to-many relationship: Cuadrilla has many Asignacion records"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('name', name='uq_cuadrilla_name'),
    )
    
    def __repr__(self) -> str:
        """String representation of Cuadrilla instance."""
        return (
            f"Cuadrilla(id={self.id}, name={self.name}, "
            f"type={self.type}, load={self.current_load}/{self.capacity_daily})"
        )
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        status = "Active" if self.is_active else "Inactive"
        return (
            f"{self.name} ({self.type}) - "
            f"Load: {self.current_load}/{self.capacity_daily} - {status}"
        )
    
    def get_available_capacity(self) -> int:
        """
        Calculate remaining available capacity for this cuadrilla.
        
        Returns:
            int: Number of OTs that can still be assigned
                 (capacity_daily - current_load)
        """
        available = self.capacity_daily - self.current_load
        return max(0, available)
    
    def is_at_capacity(self) -> bool:
        """
        Check if cuadrilla has reached daily capacity.
        
        Returns:
            bool: True if current_load >= capacity_daily
        """
        return self.current_load >= self.capacity_daily
    
    def can_accept_ot(self) -> bool:
        """
        Check if cuadrilla can accept a new OT assignment.
        
        Conditions:
        - Must be active (is_active=True)
        - Must have available capacity (current_load < capacity_daily)
        
        Returns:
            bool: True if cuadrilla can accept new assignments
        """
        return self.is_active and not self.is_at_capacity()
    
    def has_centroid(self) -> bool:
        """
        Check if cuadrilla has a calculated centroid.
        
        Returns:
            bool: True if both last_centroid_lat and last_centroid_long are set
        """
        return (
            self.last_centroid_lat is not None and
            self.last_centroid_long is not None
        )
    
    def update_centroid(self, lat: float, long: float) -> None:
        """
        Update the cuadrilla's geographic centroid.
        
        Used during planning Phase 2 to calculate new centroid based on
        assigned OT coordinates.
        
        Args:
            lat: New latitude coordinate
            long: New longitude coordinate
        """
        self.last_centroid_lat = lat
        self.last_centroid_long = long
    
    def update_load(self, new_load: int) -> None:
        """
        Update the current load (number of assigned OTs).
        
        Args:
            new_load: New load count
        """
        self.current_load = max(0, new_load)  # Prevent negative loads
    
    def increment_load(self) -> None:
        """Increment current load by 1 when assigning an OT."""
        if not self.is_at_capacity():
            self.current_load += 1
    
    def decrement_load(self) -> None:
        """Decrement current load by 1 when unassigning an OT."""
        if self.current_load > 0:
            self.current_load -= 1
    
    def get_capacity_percentage(self) -> float:
        """
        Calculate current load as a percentage of capacity.
        
        Returns:
            float: Percentage (0-100) of capacity currently used
        """
        if self.capacity_daily == 0:
            return 0.0
        return (self.current_load / self.capacity_daily) * 100

