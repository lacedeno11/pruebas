from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class CuadrillaType(str, Enum):
    """Enumeration for cuadrilla (team) types."""
    PRINCIPAL = "Principal"
    RESERVA = "Reserva"


class Cuadrilla(Base):
    """
    Cuadrilla (Team/Crew) SQLAlchemy model.
    Represents installation teams that are assigned OTs (work orders).
    """
    __tablename__ = "cuadrillas"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Team information
    name = Column(String, unique=True, nullable=False)
    type = Column(SQLEnum(CuadrillaType), nullable=False)

    # Geographic centroid (center point of team's assigned work area)
    last_centroid_lat = Column(Float, nullable=True)
    last_centroid_long = Column(Float, nullable=True)

    # Capacity and load management
    capacity = Column(Integer, default=10, nullable=False)
    current_load = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ots = relationship("OT", back_populates="cuadrilla", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cuadrilla(id={self.id}, name={self.name}, type={self.type}, current_load={self.current_load}/{self.capacity})>"

    @property
    def load_percentage(self) -> float:
        """Calculate the current load percentage of the team."""
        if self.capacity == 0:
            return 0.0
        return (self.current_load / self.capacity) * 100

