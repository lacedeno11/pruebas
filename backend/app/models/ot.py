"""
OT (Orden de Trabajo) SQLAlchemy Model

Represents a Work Order in the DERCAS PEI system.

OT Lifecycle:
    PREPLANIFICADA → PLANIFICADA → ASIGNADO_TAREA → FINALIZADA
                  ↓                ↓
                DETENIDA → PLANIFICADA (resume)
                  ↓
                ANULADA (terminal)
    
    ERROR_GEO (special status for missing coordinates)

OT States:
    - PREPLANIFICADA: Initial state, awaiting planning
    - PLANIFICADA: Assigned to a crew
    - ASIGNADO_TAREA: Work order in progress
    - DETENIDA: Paused work order (can resume or cancel)
    - FINALIZADA: Completed successfully
    - ANULADA: Cancelled (terminal state)
    - ERROR_GEO: Missing geographic coordinates

Key Constraints:
    - PUBLICO projects: Require 29 documents before FINALIZADA
    - DETENIDA status: Auto-cancels after 30 days
    - Geographic: lat/long required for planning (ERROR_GEO if missing)
    - Crew assignment: Validates <10km proximity to centroid
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
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class OT(Base):
    """
    Work Order (Orden de Trabajo) model.
    
    Represents a work order in the DERCAS PEI system with:
    - Geographic location (lat/long for mapping and proximity checking)
    - Status tracking (lifecycle state management)
    - Crew assignment (cuadrilla_id for planning)
    - Project type (determines validation rules)
    - Detention tracking (reason and timestamp)
    
    Table: ots
    """

    __tablename__ = "ots"

    # ========================================================================
    # Primary Key
    # ========================================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique database identifier for OT",
    )

    # ========================================================================
    # External Identification
    # ========================================================================

    external_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="External OT identifier from TELCOS system (e.g., 'OT-2024-001')",
    )

    client_id = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Client/customer identifier",
    )

    login = Column(
        String(100),
        nullable=False,
        doc="Field technician login/username for work order",
    )

    # ========================================================================
    # Geographic Location
    # ========================================================================

    lat = Column(
        Float,
        nullable=True,
        doc="Latitude in decimal degrees (-90 to 90) for work location",
    )

    long = Column(
        Float,
        nullable=True,
        doc="Longitude in decimal degrees (-180 to 180) for work location",
    )

    # ========================================================================
    # Status & State Management
    # ========================================================================

    status = Column(
        Enum(
            "PREPLANIFICADA",
            "PLANIFICADA",
            "ASIGNADO_TAREA",
            "DETENIDA",
            "ANULADA",
            "FINALIZADA",
            "ERROR_GEO",
            name="ot_status",
        ),
        nullable=False,
        default="PREPLANIFICADA",
        index=True,
        doc="Current OT lifecycle status",
    )

    project_type = Column(
        Enum(
            "PUBLICO",
            "PRIVADO",
            "TERCERIZADO",
            name="project_type",
        ),
        nullable=False,
        default="PUBLICO",
        doc="Project type affecting validation rules (PUBLICO requires 29 docs)",
    )

    # ========================================================================
    # Crew Assignment
    # ========================================================================

    cuadrilla_id = Column(
        Integer,
        ForeignKey("cuadrillas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Assigned crew (Cuadrilla) ID, nullable until assignment",
    )

    # ========================================================================
    # Detention Tracking
    # ========================================================================

    detention_reason = Column(
        Text,
        nullable=True,
        doc="Reason for detention (operational, technical, authorization, etc.)",
    )

    detention_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when OT transitioned to DETENIDA status",
    )

    # ========================================================================
    # Timestamps
    # ========================================================================

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="UTC timestamp when OT was created",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp when OT was last updated",
    )

    # ========================================================================
    # Relationships
    # ========================================================================

    cuadrilla = relationship(
        "Cuadrilla",
        back_populates="ots",
        foreign_keys=[cuadrilla_id],
        doc="Assigned crew relationship",
    )

    logs = relationship(
        "LogAgente",
        back_populates="ot",
        cascade="all, delete-orphan",
        doc="Agent action logs for this OT",
    )

    asignaciones = relationship(
        "Asignacion",
        back_populates="ot",
        cascade="all, delete-orphan",
        doc="Assignment history records",
    )

    # ========================================================================
    # Indexes
    # ========================================================================

    __table_args__ = (
        # Composite index for efficient filtering by status and project type
        Index("idx_ot_status_project", "status", "project_type"),
        # Composite index for crew assignment queries
        Index("idx_ot_cuadrilla_status", "cuadrilla_id", "status"),
        # Index for geographic queries (finding OTs by location)
        Index("idx_ot_lat_long", "lat", "long"),
        # Index for time-based queries (inactivity checks)
        Index("idx_ot_created_at", "created_at"),
        # Index for detention tracking queries
        Index("idx_ot_detention_date", "detention_date"),
    )

    # ========================================================================
    # String Representation
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"OT(id={self.id}, external_id={self.external_id!r}, "
            f"status={self.status}, cuadrilla_id={self.cuadrilla_id})"
        )

    # ========================================================================
    # Properties for Common Operations
    # ========================================================================

    @property
    def has_coordinates(self) -> bool:
        """Check if OT has valid geographic coordinates."""
        return self.lat is not None and self.long is not None

    @property
    def is_assigned(self) -> bool:
        """Check if OT is assigned to a crew."""
        return self.cuadrilla_id is not None

    @property
    def is_completed(self) -> bool:
        """Check if OT is in terminal state."""
        return self.status in ("FINALIZADA", "ANULADA")

    @property
    def is_active(self) -> bool:
        """Check if OT is in active state (not completed or cancelled)."""
        return self.status not in ("FINALIZADA", "ANULADA")

    @property
    def is_detached(self) -> bool:
        """Check if OT is detached from crew (awaiting assignment)."""
        return self.status == "PREPLANIFICADA" and self.cuadrilla_id is None

    @property
    def days_in_status(self) -> float:
        """Get number of days OT has been in current status."""
        time_delta = datetime.now(timezone.utc) - self.created_at
        return time_delta.days + (time_delta.seconds / 86400)

    @property
    def days_in_detention(self) -> int:
        """Get number of days OT has been in DETENIDA status."""
        if self.status != "DETENIDA" or not self.detention_date:
            return 0
        time_delta = datetime.now(timezone.utc) - self.detention_date
        return time_delta.days

    # ========================================================================
    # Validation Methods
    # ========================================================================

    def can_transition_to(self, new_status: str) -> bool:
        """
        Check if OT can transition to the specified status.
        
        Enforces state machine rules:
        - PREPLANIFICADA → [PLANIFICADA, ANULADA]
        - PLANIFICADA → [ASIGNADO_TAREA, DETENIDA, ANULADA]
        - ASIGNADO_TAREA → [DETENIDA, FINALIZADA, ANULADA]
        - DETENIDA → [PLANIFICADA, ASIGNADO_TAREA, ANULADA]
        - ERROR_GEO → [PREPLANIFICADA, ANULADA]
        - FINALIZADA, ANULADA → [] (terminal states)
        
        Args:
            new_status: Target status string
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = {
            "PREPLANIFICADA": ["PLANIFICADA", "ANULADA"],
            "PLANIFICADA": ["ASIGNADO_TAREA", "DETENIDA", "ANULADA"],
            "ASIGNADO_TAREA": ["DETENIDA", "FINALIZADA", "ANULADA"],
            "DETENIDA": ["PLANIFICADA", "ASIGNADO_TAREA", "ANULADA"],
            "ERROR_GEO": ["PREPLANIFICADA", "ANULADA"],
            "FINALIZADA": [],
            "ANULADA": [],
        }

        if self.status not in valid_transitions:
            return False

        return new_status in valid_transitions[self.status]

    def requires_detention_reason(self, new_status: str) -> bool:
        """
        Check if detention reason is required for status transition.
        
        Args:
            new_status: Target status string
            
        Returns:
            True if detention reason is required, False otherwise
        """
        return new_status == "DETENIDA"

    def requires_crew_assignment(self, new_status: str) -> bool:
        """
        Check if crew assignment is required for status transition.
        
        Args:
            new_status: Target status string
            
        Returns:
            True if crew assignment is required, False otherwise
        """
        return new_status == "ASIGNADO_TAREA"

    def requires_document_verification(self) -> bool:
        """
        Check if document verification is required before finalizing.
        
        PUBLICO projects require 29 documents before FINALIZADA.
        
        Returns:
            True if document verification is required, False otherwise
        """
        return self.project_type == "PUBLICO"

    # ========================================================================
    # Status Update Methods
    # ========================================================================

    def mark_as_error_geo(self) -> None:
        """Mark OT as ERROR_GEO due to missing coordinates."""
        if not self.has_coordinates:
            self.status = "ERROR_GEO"

    def update_detention(self, reason: str) -> None:
        """
        Update detention information.
        
        Args:
            reason: Detention reason text
        """
        self.status = "DETENIDA"
        self.detention_reason = reason
        self.detention_date = datetime.now(timezone.utc)

    def resume_from_detention(self, new_status: str = "PLANIFICADA") -> None:
        """
        Resume OT from detention status.
        
        Args:
            new_status: Status to transition to (default: PLANIFICADA)
        """
        if self.status == "DETENIDA":
            self.status = new_status
            self.detention_reason = None
            self.detention_date = None


# ============================================================================
# Type Hints
# ============================================================================

__all__ = ["OT"]

