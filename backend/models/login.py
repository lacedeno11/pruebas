"""
Login model - Represents service points (direcciones) where installations occur.
Each login is linked to a cliente and contains geographical coordinates.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, UUID
from sqlalchemy.orm import relationship

from backend.models import Base


class Login(Base):
    """
    Login (Service Point) model.
    Represents a physical location where TELCONET provides services.
    Contains critical geographical coordinates for location-based operations.
    """

    __tablename__ = "logins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    direccion = Column(Text, nullable=False)
    lat = Column(Float, nullable=True)
    long = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    cliente = relationship("Cliente", back_populates="logins")
    ordenes_trabajo = relationship(
        "OrdenTrabajo", back_populates="login", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Login(id={self.id}, external_id={self.external_id}, direccion={self.direccion})>"

