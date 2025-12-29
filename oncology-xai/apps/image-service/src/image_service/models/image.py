"""Image database model."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, BigInteger, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from image_service.database import Base

class ImageFormat(str, Enum):
    PNG = "png"
    BIFF = "biff"

class Image(Base):
    __tablename__ = "images"

    image_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    format: Mapped[ImageFormat] = mapped_column(SQLEnum(ImageFormat, name="image_format"), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    magnification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Image(id={self.image_id}, format={self.format})>"
