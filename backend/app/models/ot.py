"""
SQLAlchemy OT (Order of Work) model for PEI Agentic Platform.
Represents work orders that flow through the planning and governance system.
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
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.cuadrilla import Cuadrilla
    from app.models.log_agente import LogAgente
    from app.models.assignment import Assignment


# ============================================================================
# ENUMS
# ============================================================================


class OTStatus(str, Enum):
    """
    OT workflow states.
    
    Transitions:
    PREPLANIFICADA -> PLANIFICADA -> ASIGNADO_TAREA -> DETENIDA/FINALIZADA
    DETENIDA -> ANULADA (after 30 days)
    Any state can transition to ANULADA manually
    """

    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(str, Enum):
    """
    Project types with different business rules.
    
    PUBLICO: Requires 29 mandatory documents (strictest governance)
    PRIVADO: Standard process
    TERCERIZADO: External company management (SLA constraints)
    """

    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


# ============================================================================
# OT MODEL
# ============================================================================


class OT(Base):
    """
    Order of Work (OT) model.
    
    Represents a work order in the TELCONET system that flows through:
    1. Ingestion (OTSAgent)
    2. Planning (PlanificacionAgent)
    3. Governance (GobernanzaAgent)
    4. Communication (ComunicacionAgent)
    
    Attributes:
        id: UUID primary key
        external_id: Unique identifier from TELCOS BSS system
        status: Current workflow state
        project_type: Project classification for business rules
        cliente_id: Customer ID from BSS
        login_id: Service point ID with coordinates
        lat: Latitude coordinate (decimal degrees)
        long: Longitude coordinate (decimal degrees)
        created_at: Timestamp when OT was created
        updated_at: Timestamp when OT was last modified
        cuadrilla_id: Assigned crew UUID (nullable)
        geo_error: Flag if coordinates are invalid
        detention_reason: Reason if OT is detained
    """

    __tablename__ = "ots"

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
    # CORE FIELDS (from Pydantic OTBase)
    # ========================================================================

    external_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique identifier from TELCOS/BSS system",
    )

    status: Mapped[OTStatus] = mapped_column(
        SQLEnum(OTStatus),
        default=OTStatus.PREPLANIFICADA,
        nullable=False,
        index=True,
        doc="Current OT workflow state",
    )

    project_type: Mapped[ProjectType] = mapped_column(
        SQLEnum(ProjectType),
        nullable=False,
        index=True,
        doc="Project classification (PUBLICO, PRIVADO, TERCERIZADO)",
    )

    cliente_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Customer ID from BSS",
    )

    login_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Service point ID",
    )

    # ========================================================================
    # GEOGRAPHIC FIELDS
    # ========================================================================

    lat: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Latitude in decimal degrees (-90 to 90)",
    )

    long: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Longitude in decimal degrees (-180 to 180)",
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True,
        doc="Timestamp when OT was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
        doc="Timestamp when OT was last updated",
    )

    # ========================================================================
    # ASSIGNMENT & VALIDATION
    # ========================================================================

    cuadrilla_id: Mapped[Optional[str]] = mapped_column(
        UUID,
        ForeignKey("cuadrillas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Assigned crew UUID",
    )

    geo_error: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="True if coordinates are invalid or missing",
    )

    detention_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Reason if OT is in DETENIDA status",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    cuadrilla: Mapped[Optional["Cuadrilla"]] = relationship(
        "Cuadrilla",
        back_populates="ots",
        foreign_keys=[cuadrilla_id],
        doc="Assigned crew (if any)",
    )

    logs_agentes: Mapped[List["LogAgente"]] = relationship(
        "LogAgente",
        back_populates="ot",
        cascade="all, delete-orphan",
        doc="Agent logs related to this OT",
    )

    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="ot",
        cascade="all, delete-orphan",
        doc="Assignment history for this OT",
    )

    # ========================================================================
    # COMPOSITE INDEXES
    # ========================================================================

    __table_args__ = (
        # Index for finding unassigned OTs
        Index("ix_ot_status_cuadrilla", "status", "cuadrilla_id"),
        # Index for finding OTs by project type and status
        Index("ix_ot_project_status", "project_type", "status"),
        # Index for finding geo errors
        Index("ix_ot_geo_error", "geo_error"),
        # Index for time range queries
        Index("ix_ot_created_at", "created_at"),
        # Index for client lookups
        Index("ix_ot_cliente_status", "cliente_id", "status"),
    )

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"<OT(id={self.id}, external_id={self.external_id}, "
            f"status={self.status}, cuadrilla_id={self.cuadrilla_id})>"
        )

    def __str__(self) -> str:
        """Human-readable string."""
        return (
            f"OT {self.external_id} ({self.status}) - "
            f"Cliente: {self.cliente_id}, Cuadrilla: {self.cuadrilla_id or 'Unassigned'}"
        )

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def is_assigned(self) -> bool:
        """Check if OT is assigned to a crew."""
        return self.cuadrilla_id is not None

    @property
    def is_active(self) -> bool:
        """Check if OT is in active workflow (not finalized/cancelled)."""
        return self.status not in (OTStatus.FINALIZADA, OTStatus.ANULADA)

    @property
    def is_detained(self) -> bool:
        """Check if OT is in detention status."""
        return self.status == OTStatus.DETENIDA

    @property
    def has_coordinates(self) -> bool:
        """Check if OT has valid coordinates."""
        return self.lat is not None and self.long is not None and not self.geo_error

    @property
    def coordinates(self) -> Optional[tuple]:
        """Return coordinates as (lat, long) tuple or None."""
        if self.has_coordinates:
            return (self.lat, self.long)
        return None

    # ========================================================================
    # METHODS
    # ========================================================================

    def can_transition_to(self, new_status: OTStatus) -> bool:
        """
        Check if OT can transition to a new status.
        
        Valid transitions:
        - Any status can go to ANULADA (cancellation)
        - PREPLANIFICADA -> PLANIFICADA
        - PLANIFICADA -> ASIGNADO_TAREA
        - ASIGNADO_TAREA -> DETENIDA or FINALIZADA
        - DETENIDA -> ANULADA (after 30 days) or back to other states
        
        Args:
            new_status: Target status
            
        Returns:
            bool: True if transition is allowed
        """
        # Can always cancel
        if new_status == OTStatus.ANULADA:
            return True

        # Valid forward transitions
        transitions = {
            OTStatus.PREPLANIFICADA: [OTStatus.PLANIFICADA, OTStatus.ANULADA],
            OTStatus.PLANIFICADA: [OTStatus.ASIGNADO_TAREA, OTStatus.ANULADA],
            OTStatus.ASIGNADO_TAREA: [OTStatus.DETENIDA, OTStatus.FINALIZADA, OTStatus.ANULADA],
            OTStatus.DETENIDA: [OTStatus.ASIGNADO_TAREA, OTStatus.ANULADA],
            OTStatus.FINALIZADA: [],  # No transitions from final state
            OTStatus.ANULADA: [],  # No transitions from cancelled state
        }

        return new_status in transitions.get(self.status, [])

    def mark_geo_error(self, error: bool = True) -> None:
        """
        Mark OT as having geographic/coordinate errors.
        
        Args:
            error: True to mark as error, False to clear
        """
        self.geo_error = error

    def mark_detained(self, reason: str) -> None:
        """
        Mark OT as detained with a reason.
        
        Args:
            reason: Reason for detention
        """
        self.status = OTStatus.DETENIDA
        self.detention_reason = reason

    def clear_detention(self) -> None:
        """Clear detention status and reason."""
        self.detention_reason = None

    def assign_to_cuadrilla(self, cuadrilla_id: str) -> None:
        """
        Assign OT to a crew.
        
        Args:
            cuadrilla_id: Crew UUID to assign to
        """
        self.cuadrilla_id = cuadrilla_id

    def unassign_from_cuadrilla(self) -> None:
        """Remove OT from assigned crew."""
        self.cuadrilla_id = None

    def to_dict(self) -> dict:
        """
        Convert OT to dictionary for API responses.
        
        Returns:
            dict: OT data
        """
        return {
            "id": str(self.id),
            "external_id": self.external_id,
            "status": self.status.value,
            "project_type": self.project_type.value,
            "cliente_id": self.cliente_id,
            "login_id": self.login_id,
            "lat": self.lat,
            "long": self.long,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "cuadrilla_id": str(self.cuadrilla_id) if self.cuadrilla_id else None,
            "geo_error": self.geo_error,
            "detention_reason": self.detention_reason,
            "is_assigned": self.is_assigned,
            "has_coordinates": self.has_coordinates,
        }

