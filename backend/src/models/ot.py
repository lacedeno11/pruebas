"""
OT (Orden de Trabajo) Model for PEI Platform.

This module defines the SQLAlchemy ORM model for work orders (OTs) in the system.
OTs represent the core operational entities that flow through the planning and
governance lifecycle.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class OTStatus(str, Enum):
    """OT lifecycle status enumeration."""

    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(str, Enum):
    """Project type enumeration with different governance rules."""

    PUBLICO = "PUBLICO"  # Public/government projects (requires 29 docs)
    PRIVADO = "PRIVADO"  # Private enterprise projects
    TERCERIZADO = "TERCERIZADO"  # Outsourced/third-party projects


class OT(Base, TimestampMixin):
    """
    OT (Orden de Trabajo) Model.

    Represents a work order to be executed by a cuadrilla (technical team).
    Each OT flows through multiple states from PREPLANIFICADA to FINALIZADA.

    Attributes:
        id: Unique internal identifier (primary key)
        external_id: Unique identifier from TELCOS system
        status: Current OT lifecycle status
        project_type: Type of project (determines governance rules)
        lat: Latitude of service location (nullable for ERROR_GEO cases)
        long: Longitude of service location (nullable for ERROR_GEO cases)
        cliente_id: Customer identifier from TELCOS
        login_id: Service point identifier from TELCOS
        is_geo_error: Flag indicating missing/invalid coordinates
        cuadrilla_id: Foreign key to assigned cuadrilla (nullable until assignment)
        assigned_at: Timestamp when cuadrilla was assigned
        created_at: Timestamp when OT was created (via TimestampMixin)
        updated_at: Timestamp when OT was last updated (via TimestampMixin)
    """

    __tablename__ = "ots"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, doc="Internal OT identifier")

    # External Integration
    external_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Unique identifier from TELCOS system",
    )

    # Status and Classification
    status: Mapped[OTStatus] = mapped_column(
        SQLEnum(OTStatus),
        default=OTStatus.PREPLANIFICADA,
        nullable=False,
        doc="Current lifecycle status of the OT",
    )

    project_type: Mapped[ProjectType] = mapped_column(
        SQLEnum(ProjectType),
        nullable=False,
        doc="Type of project (PUBLICO requires 29 docs, others standard)",
    )

    # Geographic Information
    lat: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Latitude of service location (decimal degrees)",
    )

    long: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Longitude of service location (decimal degrees)",
    )

    is_geo_error: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Flag indicating missing or invalid geographic coordinates",
    )

    # Customer Information
    cliente_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Customer identifier from TELCOS BSS",
    )

    login_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Service point identifier (physical location of installation)",
    )

    # Assignment Information
    cuadrilla_id: Mapped[int | None] = mapped_column(
        ForeignKey("cuadrillas.id"),
        nullable=True,
        doc="Foreign key to assigned cuadrilla (nullable until assignment)",
    )

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp when cuadrilla was assigned (Phase 1 or Phase 2 of planning)",
    )

    # Relationships
    cuadrilla: Mapped["Cuadrilla"] = relationship(
        "Cuadrilla",
        back_populates="ots",
        doc="Reference to assigned cuadrilla",
    )

    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog",
        back_populates="ot",
        cascade="all, delete-orphan",
        doc="Agent execution logs related to this OT",
    )

    def __repr__(self) -> str:
        """String representation of OT."""
        return (
            f"<OT(id={self.id}, external_id={self.external_id}, "
            f"status={self.status}, project_type={self.project_type})>"
        )

    def to_dict(self) -> dict:
        """Convert OT to dictionary for API responses."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "status": self.status.value if isinstance(self.status, OTStatus) else self.status,
            "project_type": (
                self.project_type.value if isinstance(self.project_type, ProjectType) else self.project_type
            ),
            "lat": self.lat,
            "long": self.long,
            "cliente_id": self.cliente_id,
            "login_id": self.login_id,
            "is_geo_error": self.is_geo_error,
            "cuadrilla_id": self.cuadrilla_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

