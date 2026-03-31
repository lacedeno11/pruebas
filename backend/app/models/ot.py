"""
OrdenTrabajo (OT) SQLAlchemy model.

Represents a work order in the DERCAS system with all essential fields:
- Identification: id (UUID), external_id (unique string from TELCOS API)
- Status tracking: 6 status enums
- Project type: 3 project type enums
- Location: lat/long coordinates (nullable, with error_geo flag)
- Assignment: cuadrilla_id (FK, nullable)
- Timestamps: created_at, updated_at for audit trail
- Relationships: Cuadrilla (many-to-one), LogAgente (one-to-many)
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class OTStatus(PyEnum):
    """OT Status enumeration - 6 valid states."""
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(PyEnum):
    """Project type enumeration - 3 types for business rules."""
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class OrdenTrabajo(Base):
    """
    OrdenTrabajo (Work Order) model.
    
    Core entity in DERCAS system representing a work order from TELCOS API.
    Each OT has:
    - Unique external ID from TELCOS system
    - Status lifecycle (6 states)
    - Project type (determines business rules)
    - Geographic coordinates (nullable, with error flag)
    - Assignment to cuadrilla (optional)
    - Audit trail (created/updated timestamps)
    
    Relationships:
    - cuadrilla: Many OTs can belong to one Cuadrilla
    - logs: One OT can have many LogAgente entries
    
    Table name: orden_trabajo
    """
    
    __tablename__ = "orden_trabajo"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
        comment="Unique identifier (UUID) for the OT"
    )
    
    # External ID from TELCOS API
    external_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique external ID from TELCOS API"
    )
    
    # Status - 6 valid states
    status = Column(
        Enum(OTStatus),
        nullable=False,
        default=OTStatus.PREPLANIFICADA,
        index=True,
        comment="OT status: PREPLANIFICADA, PLANIFICADA, ASIGNADO_TAREA, DETENIDA, ANULADA, FINALIZADA"
    )
    
    # Project Type - 3 types for business rule differentiation
    project_type = Column(
        Enum(ProjectType),
        nullable=False,
        index=True,
        comment="Project type: PUBLICO (29 docs required), PRIVADO, TERCERIZADO"
    )
    
    # Geographic Coordinates
    lat = Column(
        Float,
        nullable=True,
        comment="Latitude coordinate (nullable, Ecuador bounds: -2 to 1)"
    )
    long = Column(
        Float,
        nullable=True,
        comment="Longitude coordinate (nullable, Ecuador bounds: -81 to -75)"
    )
    
    # Error flag for invalid coordinates
    error_geo = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True if coordinates are outside Ecuador geographic bounds"
    )
    
    # Client and Login IDs
    cliente_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Client ID from TELCOS system"
    )
    login_id = Column(
        String(255),
        nullable=False,
        comment="Login ID from TELCOS system"
    )
    
    # Cuadrilla Assignment (optional)
    cuadrilla_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cuadrilla.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to assigned Cuadrilla (nullable until assigned)"
    )
    
    # Timestamps for audit trail
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when OT was created"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Timestamp when OT was last updated"
    )
    
    # Relationships
    cuadrilla = relationship(
        "Cuadrilla",
        back_populates="ots",
        foreign_keys=[cuadrilla_id],
        lazy="select",
        comment="Many-to-one relationship: OT belongs to Cuadrilla"
    )
    
    logs = relationship(
        "LogAgente",
        back_populates="ot",
        foreign_keys="LogAgente.ot_id",
        lazy="select",
        cascade="all, delete-orphan",
        comment="One-to-many relationship: OT has many LogAgente entries"
    )
    
    asignaciones = relationship(
        "Asignacion",
        back_populates="ot",
        foreign_keys="Asignacion.ot_id",
        lazy="select",
        cascade="all, delete-orphan",
        comment="One-to-many relationship: OT has many Asignacion records"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('external_id', name='uq_ot_external_id'),
    )
    
    def __repr__(self) -> str:
        """String representation of OrdenTrabajo instance."""
        return (
            f"OrdenTrabajo(id={self.id}, external_id={self.external_id}, "
            f"status={self.status}, project_type={self.project_type}, "
            f"cuadrilla_id={self.cuadrilla_id})"
        )
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        cuadrilla_info = f"Cuadrilla: {self.cuadrilla_id}" if self.cuadrilla_id else "Unassigned"
        return (
            f"OT {self.external_id} ({self.project_type}) - "
            f"Status: {self.status} - {cuadrilla_info}"
        )
    
    def is_assigned(self) -> bool:
        """Check if OT is assigned to a cuadrilla."""
        return self.cuadrilla_id is not None
    
    def has_valid_coordinates(self) -> bool:
        """Check if OT has valid (non-null) coordinates."""
        return self.lat is not None and self.long is not None
    
    def is_finalizeable(self) -> bool:
        """
        Check if OT can transition to FINALIZADA status.
        
        Rules:
        - PUBLICO: Requires 29 documents (checked separately with TelcoDrive)
        - PRIVADO: No special requirements
        - TERCERIZADO: No special requirements
        """
        if self.project_type == ProjectType.PUBLICO:
            # Document count check must be done separately via TelcosApiClient
            return True  # Document validation happens at endpoint level
        return True
    
    def days_in_status(self) -> int:
        """
        Calculate days in current status.
        
        Uses updated_at timestamp to determine duration in current status.
        
        Returns:
            int: Number of days since last status change
        """
        from datetime import timedelta
        duration = datetime.utcnow() - self.updated_at
        return max(0, duration.days)

