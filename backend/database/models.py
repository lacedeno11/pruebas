"""SQLAlchemy database models for PEI Agéntico."""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

Base = declarative_base()


class OTStatus(str, enum.Enum):
    """OT status enumeration."""
    PREPLANIFICADA = "PREPLANIFICADA"
    PLANIFICADA = "PLANIFICADA"
    ASIGNADO_TAREA = "ASIGNADO_TAREA"
    DETENIDA = "DETENIDA"
    FINALIZADA = "FINALIZADA"
    ANULADA = "ANULADA"


class ProjectType(str, enum.Enum):
    """Project type enumeration."""
    PUBLICO = "PUBLICO"
    PRIVADO = "PRIVADO"
    TERCERIZADO = "TERCERIZADO"


class CuadrillaType(str, enum.Enum):
    """Crew type enumeration."""
    PRINCIPAL = "Principal"
    RESERVA = "Reserva"


class OT(Base):
    """Work Order (OT) model."""
    
    __tablename__ = "ot"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=False, index=True)
    status = Column(Enum(OTStatus), nullable=False, index=True, default=OTStatus.PREPLANIFICADA)
    project_type = Column(Enum(ProjectType), nullable=False)
    lat = Column(Float, nullable=False)
    long = Column(Float, nullable=False)
    cliente_id = Column(String, nullable=False)
    login = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrilla.id", ondelete="SET NULL"), nullable=True, index=True)
    error_geo = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    cuadrilla = relationship("Cuadrilla", back_populates="ots")
    assignments = relationship("Assignment", back_populates="ot", cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="ot", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OT(id={self.id}, external_id={self.external_id}, status={self.status})>"


class Cuadrilla(Base):
    """Field crew (Cuadrilla) model."""
    
    __tablename__ = "cuadrilla"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    type = Column(Enum(CuadrillaType), nullable=False, default=CuadrillaType.PRINCIPAL)
    last_centroid_lat = Column(Float, nullable=True)
    last_centroid_long = Column(Float, nullable=True)
    capacidad_diaria = Column(Integer, default=20, nullable=False)
    ots_asignadas_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    ots = relationship("OT", back_populates="cuadrilla")
    assignments = relationship("Assignment", back_populates="cuadrilla", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cuadrilla(id={self.id}, name={self.name}, ots_asignadas_count={self.ots_asignadas_count})>"


class Assignment(Base):
    """OT to Cuadrilla assignment model."""
    
    __tablename__ = "assignment"
    
    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ot.id", ondelete="CASCADE"), nullable=False, index=True)
    cuadrilla_id = Column(Integer, ForeignKey("cuadrilla.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    assigned_by_agent = Column(String, nullable=False)
    
    # Relationships
    ot = relationship("OT", back_populates="assignments")
    cuadrilla = relationship("Cuadrilla", back_populates="assignments")
    
    def __repr__(self):
        return f"<Assignment(id={self.id}, ot_id={self.ot_id}, cuadrilla_id={self.cuadrilla_id})>"


class AgentLog(Base):
    """Agent action audit log model."""
    
    __tablename__ = "agent_log"
    
    id = Column(Integer, primary_key=True, index=True)
    ot_id = Column(Integer, ForeignKey("ot.id", ondelete="SET NULL"), nullable=True, index=True)
    agente_name = Column(String, nullable=False)
    accion = Column(String, nullable=False)
    resultado = Column(String, nullable=False)
    raw_llm_response = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    # Relationships
    ot = relationship("OT", back_populates="agent_logs")
    
    def __repr__(self):
        return f"<AgentLog(id={self.id}, agente_name={self.agente_name}, accion={self.accion})>"

