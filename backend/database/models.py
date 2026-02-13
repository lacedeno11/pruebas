"""SQLAlchemy ORM Models for PEI Platform Database"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from .base import Base


class OT(Base):
    """Order of Work (Orden de Trabajo) model"""

    __tablename__ = "ots"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Identifiers
    external_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="External OT ID from TELCOS system",
    )
    cliente_id = Column(String(50), index=True, doc="Client identifier")
    login_id = Column(String(50), doc="Login/user identifier")

    # Status and type
    status = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Current OT status",
    )
    project_type = Column(
        String(20),
        nullable=False,
        index=True,
        doc="Project type (PUBLICO, PRIVADO, TERCERIZADO)",
    )

    # Geographic coordinates
    lat = Column(Float, nullable=True, doc="Latitude")
    long = Column(Float, nullable=True, doc="Longitude")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_status_change = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    # Assignment
    cuadrilla_id = Column(
        Integer,
        ForeignKey("cuadrillas.id"),
        nullable=True,
        index=True,
        doc="Assigned cuadrilla",
    )

    # Details
    detalle_detencion = Column(
        Text,
        nullable=True,
        doc="Reason for DETENIDA status",
    )

    # Relationships
    cuadrilla = relationship("Cuadrilla", back_populates="ots")
    asignaciones = relationship("Asignacion", back_populates="ot", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="ot", cascade="all, delete-orphan")
    logs = relationship("LogAgente", back_populates="ot", cascade="all, delete-orphan")

    # Check constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('PREPLANIFICADA', 'PLANIFICADA', 'ASIGNADO_TAREA', 'DETENIDA', 'ANULADA', 'FINALIZADA')",
            name="check_ot_status",
        ),
        CheckConstraint(
            "project_type IN ('PUBLICO', 'PRIVADO', 'TERCERIZADO')",
            name="check_project_type",
        ),
        Index("idx_ots_status", "status"),
        Index("idx_ots_project_type", "project_type"),
        Index("idx_ots_cuadrilla", "cuadrilla_id"),
        Index("idx_ots_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<OT {self.external_id} - {self.status}>"


class Cuadrilla(Base):
    """Work team/crew model"""

    __tablename__ = "cuadrillas"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(100), nullable=False, doc="Team name")
    type = Column(
        String(20),
        nullable=False,
        doc="Team type (Principal or Reserva)",
    )

    # Capacity
    capacity = Column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum OTs this team can handle",
    )

    # Centroid coordinates
    last_centroid_lat = Column(Float, nullable=True, doc="Last calculated centroid latitude")
    last_centroid_long = Column(Float, nullable=True, doc="Last calculated centroid longitude")

    # Status
    active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether team is active",
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    ots = relationship("OT", back_populates="cuadrilla")
    asignaciones = relationship("Asignacion", back_populates="cuadrilla", cascade="all, delete-orphan")

    # Check constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('Principal', 'Reserva')",
            name="check_cuadrilla_type",
        ),
        Index("idx_cuadrillas_type", "type"),
        Index("idx_cuadrillas_active", "active"),
    )

    def __repr__(self):
        return f"<Cuadrilla {self.name} - {self.type}>"


class LogAgente(Base):
    """Agent action log model"""

    __tablename__ = "logs_agentes"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key
    ot_id = Column(
        Integer,
        ForeignKey("ots.id"),
        nullable=True,
        index=True,
        doc="Associated OT ID (NULL for system-level events)",
    )

    # Agent info
    agente_name = Column(String(50), nullable=False, doc="Name of agent")
    accion = Column(String(100), nullable=False, doc="Action performed")
    resultado = Column(
        String(20),
        nullable=False,
        doc="Result status (SUCCESS, ERROR, WARNING)",
    )

    # LLM response
    raw_llm_response = Column(Text, nullable=True, doc="Raw LLM response for debugging")

    # Metadata
    metadata = Column(String(2000), nullable=True, doc="JSON metadata")

    # Timestamp
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # Relationships
    ot = relationship("OT", back_populates="logs")

    # Indexes
    __table_args__ = (
        Index("idx_logs_ot", "ot_id"),
        Index("idx_logs_timestamp", "timestamp"),
        Index("idx_logs_agente_name", "agente_name"),
    )

    def __repr__(self):
        return f"<LogAgente {self.agente_name} - {self.accion} - {self.resultado}>"


class Asignacion(Base):
    """Assignment tracking model"""

    __tablename__ = "asignaciones"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    ot_id = Column(
        Integer,
        ForeignKey("ots.id"),
        nullable=False,
        index=True,
        doc="Assigned OT",
    )
    cuadrilla_id = Column(
        Integer,
        ForeignKey("cuadrillas.id"),
        nullable=False,
        index=True,
        doc="Assigned cuadrilla",
    )

    # Assignment details
    assigned_at = Column(DateTime, default=datetime.now, nullable=False, doc="Assignment timestamp")
    assigned_by_agent = Column(String(50), nullable=True, doc="Agent that made the assignment")
    distance_to_centroid = Column(Float, nullable=True, doc="Distance from OT to cuadrilla centroid (km)")
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this assignment is currently active",
    )

    # Relationships
    ot = relationship("OT", back_populates="asignaciones")
    cuadrilla = relationship("Cuadrilla", back_populates="asignaciones")

    # Indexes
    __table_args__ = (
        Index("idx_asignaciones_ot", "ot_id"),
        Index("idx_asignaciones_cuadrilla", "cuadrilla_id"),
        Index("idx_asignaciones_active", "is_active"),
        Index("idx_asignaciones_assigned_at", "assigned_at"),
    )

    def __repr__(self):
        return f"<Asignacion OT:{self.ot_id} -> Cuadrilla:{self.cuadrilla_id}>"


class Alerta(Base):
    """Alert/notification model"""

    __tablename__ = "alertas"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key
    ot_id = Column(
        Integer,
        ForeignKey("ots.id"),
        nullable=False,
        index=True,
        doc="Associated OT",
    )

    # Alert details
    tipo = Column(
        String(50),
        nullable=False,
        doc="Alert type (WARNING_20, WARNING_25, FINAL_WARNING, AUTO_CANCELLED, INACTIVITY_48H)",
    )
    mensaje = Column(Text, nullable=False, doc="Alert message content")
    destinatario = Column(String(100), nullable=True, doc="Alert recipient (email or name)")
    canal = Column(
        String(20),
        nullable=False,
        doc="Channel (EMAIL or TELEGRAM)",
    )

    # Status
    enviado_at = Column(DateTime, nullable=True, doc="When alert was sent")
    leido = Column(Boolean, default=False, nullable=False, doc="Whether alert was read")

    # Relationships
    ot = relationship("OT", back_populates="alertas")

    # Indexes
    __table_args__ = (
        Index("idx_alertas_ot", "ot_id"),
        Index("idx_alertas_tipo", "tipo"),
        Index("idx_alertas_enviado_at", "enviado_at"),
    )

    def __repr__(self):
        return f"<Alerta {self.tipo} for OT:{self.ot_id}>"

