"""
Asignacion SQLAlchemy model.

Represents assignment records tracking when OTs are assigned to cuadrillas:
- Identification: id (UUID)
- References: ot_id (FK to OrdenTrabajo), cuadrilla_id (FK to Cuadrilla)
- Metadata: assigned_by_agent (which agent made assignment), distance_from_centroid (FK)
- Status: is_active (whether assignment is currently active)
- Timestamps: created_at for audit trail
- Relationships: OrdenTrabajo (many-to-one), Cuadrilla (many-to-one)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Asignacion(Base):
    """
    Asignacion (Assignment) model.
    
    Tracks all OT-to-Cuadrilla assignments for audit trail and historical analysis.
    Each assignment record captures:
    - Which OT was assigned (ot_id FK)
    - Which Cuadrilla received it (cuadrilla_id FK)
    - Which agent made the assignment (assigned_by_agent, typically PlanificacionAgent)
    - Distance from cuadrilla centroid to OT location (distance_from_centroid)
    - Assignment status (is_active: whether assignment is currently in effect)
    - Timestamp when assignment was created (created_at)
    
    Relationships:
    - ot: Many Asignacion records belong to one OrdenTrabajo
    - cuadrilla: Many Asignacion records belong to one Cuadrilla
    
    Table name: asignacion
    
    Usage:
    - Track assignment history: Which cuadrillas were considered before final selection
    - Performance metrics: Distance traveled, assignment efficiency
    - Audit trail: Which agent made which decisions
    - Reassignment: Mark old assignments as is_active=False when reassigning
    """
    
    __tablename__ = "asignacion"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
        comment="Unique identifier (UUID) for the assignment record"
    )
    
    # Foreign Keys
    ot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orden_trabajo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to OrdenTrabajo being assigned"
    )
    
    cuadrilla_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cuadrilla.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to Cuadrilla receiving the assignment"
    )
    
    # Assignment Metadata
    assigned_by_agent = Column(
        String(255),
        nullable=False,
        comment="Name of agent that created this assignment (e.g., 'PlanificacionAgent')"
    )
    
    distance_from_centroid = Column(
        Float,
        nullable=True,
        comment="Distance in kilometers from cuadrilla centroid to OT location (nullable if centroid not available)"
    )
    
    # Assignment Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this assignment is currently active (True) or superseded (False)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when this assignment was created"
    )
    
    # Relationships
    ot = relationship(
        "OrdenTrabajo",
        back_populates="asignaciones",
        foreign_keys=[ot_id],
        lazy="select",
        comment="Many-to-one relationship: Asignacion belongs to OrdenTrabajo"
    )
    
    cuadrilla = relationship(
        "Cuadrilla",
        back_populates="asignaciones",
        foreign_keys=[cuadrilla_id],
        lazy="select",
        comment="Many-to-one relationship: Asignacion belongs to Cuadrilla"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_ot_id_is_active', 'ot_id', 'is_active'),
        Index('idx_cuadrilla_id_is_active', 'cuadrilla_id', 'is_active'),
        Index('idx_ot_cuadrilla_created', 'ot_id', 'cuadrilla_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        """String representation of Asignacion instance."""
        status = "active" if self.is_active else "inactive"
        return (
            f"Asignacion(id={self.id}, ot_id={self.ot_id}, "
            f"cuadrilla_id={self.cuadrilla_id}, status={status})"
        )
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        status = "Active" if self.is_active else "Inactive"
        distance_info = (
            f" ({self.distance_from_centroid:.2f}km from centroid)"
            if self.distance_from_centroid is not None
            else ""
        )
        return (
            f"OT {self.ot_id} → Cuadrilla {self.cuadrilla_id} "
            f"by {self.assigned_by_agent}{distance_info} [{status}]"
        )
    
    def get_distance_display(self) -> str:
        """
        Get user-friendly distance display.
        
        Returns:
            str: Formatted distance string (e.g., "5.23 km") or "Unknown"
        """
        if self.distance_from_centroid is not None:
            return f"{self.distance_from_centroid:.2f} km"
        return "Unknown"
    
    def is_within_proximity_threshold(self, threshold_km: float = 10.0) -> bool:
        """
        Check if assignment is within proximity threshold.
        
        Used during planning Phase 2 to ensure OT is within acceptable distance
        from cuadrilla centroid (default: 10km).
        
        Args:
            threshold_km: Maximum acceptable distance in kilometers
            
        Returns:
            bool: True if distance <= threshold_km, False otherwise
        """
        if self.distance_from_centroid is None:
            return True  # No distance data = assume valid
        return self.distance_from_centroid <= threshold_km
    
    def deactivate(self) -> None:
        """
        Mark assignment as inactive.
        
        Used when reassigning an OT to a different cuadrilla.
        The old assignment is marked inactive while new one is created.
        """
        self.is_active = False
    
    def activate(self) -> None:
        """Mark assignment as active."""
        self.is_active = True
    
    def format_for_display(self) -> dict:
        """
        Format assignment for API/display.
        
        Returns:
            dict: Formatted assignment data
        """
        return {
            'id': str(self.id),
            'ot_id': str(self.ot_id),
            'cuadrilla_id': str(self.cuadrilla_id),
            'assigned_by_agent': self.assigned_by_agent,
            'distance_from_centroid': self.distance_from_centroid,
            'distance_display': self.get_distance_display(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'within_threshold': self.is_within_proximity_threshold(),
        }


# Assignment tracking helper class (for planning algorithm results)
class AssignmentResult:
    """
    Data class for planning algorithm assignment results.
    
    Used to collect assignment decisions before persisting to database.
    Keeps planning logic separate from database operations.
    """
    
    def __init__(
        self,
        ot_id: str,
        cuadrilla_id: str,
        assigned_by_agent: str,
        distance_from_centroid: Optional[float] = None
    ):
        """
        Initialize assignment result.
        
        Args:
            ot_id: OT UUID
            cuadrilla_id: Cuadrilla UUID
            assigned_by_agent: Agent name performing assignment
            distance_from_centroid: Distance in km (optional)
        """
        self.ot_id = ot_id
        self.cuadrilla_id = cuadrilla_id
        self.assigned_by_agent = assigned_by_agent
        self.distance_from_centroid = distance_from_centroid
    
    def to_model(self) -> 'Asignacion':
        """
        Convert to Asignacion model instance.
        
        Returns:
            Asignacion: Ready to persist to database
        """
        return Asignacion(
            ot_id=self.ot_id,
            cuadrilla_id=self.cuadrilla_id,
            assigned_by_agent=self.assigned_by_agent,
            distance_from_centroid=self.distance_from_centroid,
            is_active=True,
        )
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AssignmentResult(ot={self.ot_id}, cuadrilla={self.cuadrilla_id}, "
            f"distance={self.distance_from_centroid})"
        )


# Assignment statistics helper
def calculate_assignment_stats(assignments: list) -> dict:
    """
    Calculate statistics from assignment list.
    
    Args:
        assignments: List of Asignacion model instances
        
    Returns:
        dict: Statistics including averages, totals, etc.
    """
    if not assignments:
        return {
            'total': 0,
            'active': 0,
            'inactive': 0,
            'average_distance': None,
            'min_distance': None,
            'max_distance': None,
        }
    
    active_assignments = [a for a in assignments if a.is_active]
    distances = [
        a.distance_from_centroid
        for a in assignments
        if a.distance_from_centroid is not None
    ]
    
    return {
        'total': len(assignments),
        'active': len(active_assignments),
        'inactive': len(assignments) - len(active_assignments),
        'average_distance': sum(distances) / len(distances) if distances else None,
        'min_distance': min(distances) if distances else None,
        'max_distance': max(distances) if distances else None,
    }

