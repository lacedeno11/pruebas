"""
SQLAlchemy ORM models for DERCAS PEI platform.
Defines all database entities and their relationships.
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database.base import Base


# Enumerations
class OTStatus(str, PyEnum):
    """OT Status enumeration"""
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    ANULADA = "ANULADA"
    FINALIZADA = "FINALIZADA"


class ProjectType(str, PyEnum):
    """Project Type enumeration"""
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class CuadrillaType(str, PyEnum):
    """Cuadrilla Type enumeration"""
    PRINCIPAL = "Principal"
    RESERVA = "Reserva"


class ClienteType(str, PyEnum):
    """Cliente Type enumeration"""
    NATURAL = "natural"
    JURIDICAL = "juridical"


# ============================================================================
# Models
# ============================================================================


class Cliente(Base):
    """
    Cliente (Customer) entity.
    
    Represents a natural or legal person in the system.
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(Enum(ClienteType), default=ClienteType.NATURAL, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    logins = relationship("Login", back_populates="cliente")
    ordenes_servicio = relationship("OrdenServicio", back_populates="cliente")


class Login(Base):
    """
    Login (Service Point) entity.
    
    Represents a physical service point where installations occur.
    Contains critical geographic coordinates.
    """
    __tablename__ = "logins"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(50), unique=True, index=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    address = Column(String(500))
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    cliente = relationship("Cliente", back_populates="logins")
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="login")


class OrdenServicio(Base):
    """
    OrdenServicio (Service Order) entity.
    
    Commercial document that originates the technical need.
    """
    __tablename__ = "ordenes_servicio"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(50), unique=True, index=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    cliente = relationship("Cliente", back_populates="ordenes_servicio")
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="orden_servicio")


class OrdenTrabajo(Base):
    """
    OrdenTrabajo (Work Order) entity.
    
    Central operational entity representing a work order.
    Has multiple states and can be assigned to crews.
    """
    __tablename__ = "ordenes_trabajo"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(50), unique=True, index=True, nullable=False)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id"), nullable=False)
    login_id = Column(Integer, ForeignKey("logins.id"), nullable=False)
    status = Column(
        Enum(OTStatus),
        default=OTStatus.PREPLANIFICADA,
        nullable=False,
        index=True,
    )
    project_type = Column(
        Enum(ProjectType),
        default=ProjectType.PRIVADO,
        nullable=False,
        index=True,
    )
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    geo_error = Column(Boolean, default=False, index=True)

    # Relationships
    orden_servicio = relationship("OrdenServicio", back_populates="ordenes_trabajo")
    login = relationship("Login", back_populates="ordenes_trabajo")
    cuadrilla = relationship("Cuadrilla", back_populates="ordenes_trabajo")
    tareas = relationship("Tarea", back_populates="orden_trabajo")
    logs = relationship("LogAgente", back_populates="orden_trabajo")
    asignaciones = relationship("Asignacion", back_populates="orden_trabajo")


class Cuadrilla(Base):
    """
    Cuadrilla (Crew/OPU) entity.
    
    Represents a team of technicians.
    Has a type (Principal or Reserva) and workload capacity.
    """
    __tablename__ = "cuadrillas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(
        Enum(CuadrillaType),
        default=CuadrillaType.PRINCIPAL,
        nullable=False,
        index=True,
    )
    last_centroid_lat = Column(Float, nullable=True)
    last_centroid_long = Column(Float, nullable=True)
    capacity = Column(Integer, default=10, nullable=False)
    current_load = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="cuadrilla")
    asignaciones = relationship("Asignacion", back_populates="cuadrilla")


class Tarea(Base):
    """
    Tarea (Task) entity.
    
    Represents specific activities within an OT.
    Examples: Fiber laying, fusion, equipment configuration.
    """
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pendiente", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    orden_trabajo = relationship("OrdenTrabajo", back_populates="tareas")


class LogAgente(Base):
    """
    LogAgente (Agent Log) entity.
    
    Audit trail for all agent actions and decisions.
    Stores LLM responses and action results.
    """
    __tablename__ = "logs_agentes"

    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True, index=True)
    agente_name = Column(String(100), nullable=False, index=True)
    accion = Column(String(255), nullable=False)
    resultado = Column(String(500))
    raw_llm_response = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # Relationships
    orden_trabajo = relationship("OrdenTrabajo", back_populates="logs")


class Asignacion(Base):
    """
    Asignacion (Assignment) entity.
    
    Represents the assignment of an OT to a crew.
    Tracks distance, assignment time, and agent responsible.
    """
    __tablename__ = "asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=False, index=True)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrillas.id"), nullable=False, index=True)
    assigned_by_agent = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    distance_to_centroid_km = Column(Float, nullable=True)

    # Relationships
    orden_trabajo = relationship("OrdenTrabajo", back_populates="asignaciones")
    cuadrilla = relationship("Cuadrilla", back_populates="asignaciones")

