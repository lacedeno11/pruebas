"""
OT (Orden de Trabajo) SQLAlchemy model for the PEI Platform.
Represents a work order that needs to be assigned and executed by a cuadrilla.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


class OTStatus(str, Enum):
    """Enumeration of possible OT statuses in the lifecycle."""

    PREPLANIFICADA = "PREPLANIFICADA"  # Initial state, waiting for assignment
    PLANIFICADA = "PLANIFICADA"  # Assigned to a cuadrilla
    ASIGNADO_TAREA = "ASIGNADO_TAREA"  # Task assigned and work in progress
    DETENIDA = "DETENIDA"  # Detained/stopped for some reason
    ANULADA = "ANULADA"  # Cancelled/annulled
    FINALIZADA = "FINALIZADA"  # Completed


class ProjectType(str, Enum):
    """Enumeration of OT project types."""

    PUBLICO = "PUBLICO"  # Public project (requires 29 documents)
    PRIVADO = "PRIVADO"  # Private project
    TERCERIZADO = "TERCERIZADO"  # Outsourced project


class OT(Base):
    """
    OT (Orden de Trabajo) database model.

    Represents a work order that needs to be assigned to a cuadrilla and executed.
    Tracks the OT through its complete lifecycle from creation to completion or cancellation.

    Attributes:
        id: Primary key, unique identifier in database
        external_id: Unique identifier from TELCOS system
        cliente_id: ID of the client associated with this OT
        login_id: ID of the technician/login assigned
        status: Current status in OT lifecycle (PREPLANIFICADA, PLANIFICADA, etc.)
        project_type: Type of project (PUBLICO, PRIVADO, TERCERIZADO)
        lat: Latitude of OT location (nullable for geo_error cases)
        long: Longitude of OT location (nullable for geo_error cases)
        created_at: Timestamp when OT was created
        updated_at: Timestamp when OT was last updated
        geo_error: Flag indicating missing or invalid geographic coordinates
        detencion_motivo: Reason why OT is in DETENIDA status (if applicable)
        cuadrilla_id: Foreign key to assigned Cuadrilla (nullable if unassigned)

    Relationships:
        cuadrilla: Many-to-one relationship with Cuadrilla model
        logs: One-to-many relationship with LogAgente model
    """

    __tablename__ = "ots"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # External system identifiers
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    cliente_id = Column(String(255), nullable=False)
    login_id = Column(String(255), nullable=False)

    # OT status and type
    status = Column(
        SQLEnum(OTStatus),
        nullable=False,
        default=OTStatus.PREPLANIFICADA,
        index=True,
    )
    project_type = Column(
        SQLEnum(ProjectType),
        nullable=False,
        default=ProjectType.PRIVADO,
        index=True,
    )

    # Geographic information
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    geo_error = Column(Boolean, default=False, index=True)

    # Assignment and execution
    cuadrilla_id = Column(
        Integer, ForeignKey("cuadrillas.id"), nullable=True, index=True
    )
    detencion_motivo = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    cuadrilla = relationship("Cuadrilla", back_populates="ots")
    logs = relationship(
        "LogAgente",
        back_populates="ot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_ots_status_created", "status", "created_at"),
        Index("idx_ots_project_type_status", "project_type", "status"),
        Index("idx_ots_cuadrilla_status", "cuadrilla_id", "status"),
        Index("idx_ots_geo_error", "geo_error"),
    )

    def __repr__(self) -> str:
        """String representation of OT instance."""
        return (
            f"<OT(id={self.id}, external_id={self.external_id}, "
            f"status={self.status}, project_type={self.project_type})>"
        )

    def is_assigned(self) -> bool:
        """Check if OT is assigned to a cuadrilla."""
        return self.cuadrilla_id is not None

    def is_public_project(self) -> bool:
        """Check if OT is a public project that requires document validation."""
        return self.project_type == ProjectType.PUBLICO

    def can_transition_to(self, target_status: OTStatus) -> bool:
        """
        Check if OT can transition to a target status.

        Implements state machine logic for OT lifecycle transitions.

        Allowed transitions:
        - PREPLANIFICADA -> PLANIFICADA, ANULADA
        - PLANIFICADA -> ASIGNADO_TAREA, DETENIDA, ANULADA
        - ASIGNADO_TAREA -> FINALIZADA, DETENIDA, ANULADA
        - DETENIDA -> ANULADA, ASIGNADO_TAREA (resume)
        - FINALIZADA -> (no transitions, terminal state)
        - ANULADA -> (no transitions, terminal state)

        Args:
            target_status: Target OTStatus to transition to

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed_transitions = {
            OTStatus.PREPLANIFICADA: [OTStatus.PLANIFICADA, OTStatus.ANULADA],
            OTStatus.PLANIFICADA: [
                OTStatus.ASIGNADO_TAREA,
                OTStatus.DETENIDA,
                OTStatus.ANULADA,
            ],
            OTStatus.ASIGNADO_TAREA: [
                OTStatus.FINALIZADA,
                OTStatus.DETENIDA,
                OTStatus.ANULADA,
            ],
            OTStatus.DETENIDA: [OTStatus.ANULADA, OTStatus.ASIGNADO_TAREA],
            OTStatus.FINALIZADA: [],  # Terminal state
            OTStatus.ANULADA: [],  # Terminal state
        }

        return target_status in allowed_transitions.get(self.status, [])

