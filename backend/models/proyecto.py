"""
Proyecto model - Represents projects with different types and rules.
Project type (PUBLICO, PRIVADO, TERCERIZADO) determines business logic and constraints.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String, Text, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class Proyecto(Base):
    """
    Proyecto (Project) model.
    Segments work orders by project type, each with different rules:
    - PUBLICO: Requires 29 documents in TelcoDrive
    - PRIVADO: Standard process with photo evidence and digital signatures
    - TERCERIZADO: Delegated to external companies with SLA differences
    """

    __tablename__ = "proyectos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    nombre = Column(String(255), nullable=False)
    tipo = Column(
        Enum("PUBLICO", "PRIVADO", "TERCERIZADO", name="proyecto_tipo_enum"),
        nullable=False,
    )
    descripcion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ordenes_trabajo = relationship(
        "OrdenTrabajo", back_populates="proyecto", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Proyecto(id={self.id}, nombre={self.nombre}, tipo={self.tipo})>"

