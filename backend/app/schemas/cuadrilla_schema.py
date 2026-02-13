from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CuadrillaType(str, Enum):
    """Enumeration for cuadrilla types."""
    Principal = "Principal"
    Reserva = "Reserva"


class CuadrillaBase(BaseModel):
    """Base Cuadrilla schema with common fields."""
    name: str = Field(..., description="Team name")
    type: CuadrillaType = Field(..., description="Type of team (Principal or Reserva)")
    capacity: int = Field(default=10, description="Maximum capacity of team")


class CuadrillaCreate(CuadrillaBase):
    """Schema for creating a new Cuadrilla."""
    pass


class CuadrillaUpdate(BaseModel):
    """Schema for updating Cuadrilla fields (all optional)."""
    name: Optional[str] = None
    type: Optional[CuadrillaType] = None
    capacity: Optional[int] = None
    last_centroid_lat: Optional[float] = None
    last_centroid_long: Optional[float] = None

    model_config = ConfigDict(extra="ignore")


class CuadrillaInDB(CuadrillaBase):
    """Schema for Cuadrilla data as stored in database."""
    id: int = Field(..., description="Primary key")
    last_centroid_lat: Optional[float] = Field(None, description="Latitude of team centroid")
    last_centroid_long: Optional[float] = Field(None, description="Longitude of team centroid")
    current_load: int = Field(default=0, description="Current number of assigned OTs")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class CuadrillaResponse(CuadrillaInDB):
    """Schema for API responses with calculated fields."""
    ot_count: int = Field(default=0, description="Current count of assigned OTs")
    load_percentage: float = Field(default=0.0, description="Current load as percentage (current_load / capacity * 100)")

    model_config = ConfigDict(from_attributes=True)

    @property
    def calculated_load_percentage(self) -> float:
        """Calculate load percentage based on capacity."""
        if self.capacity <= 0:
            return 0.0
        return round((self.current_load / self.capacity) * 100, 2)

