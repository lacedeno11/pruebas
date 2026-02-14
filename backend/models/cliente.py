"""
Cliente model - Represents customers/clients in the system.
Can be natural person or legal entity (Persona Natural or Jurídica).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class Cliente(Base):
    """
    Cliente (Customer) model.
    Represents a natural or legal person who is a customer of TELCONET.
    """

    __tablename__ = "clientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    tipo_persona = Column(
        Enum("NATURAL", "JURIDICA", name="tipo_persona_enum"),
        nullable=False,
    )
    bss_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    logins = relationship("Login", back_populates="cliente", cascade="all, delete-orphan")
    ordenes_trabajo = relationship(
        "OrdenTrabajo", back_populates="cliente", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Cliente(id={self.id}, external_id={self.external_id}, nombre={self.nombre})>"

