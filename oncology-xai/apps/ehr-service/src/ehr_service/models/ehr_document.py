"""EHR Document database model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, func, Enum as SQLEnum, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ehr_service.database import Base


class EHRDocumentStatus(str, Enum):
    """EHR document processing status."""
    INGESTED = "INGESTED"
    PROCESSING = "PROCESSING"
    ENTITIES_EXTRACTED = "ENTITIES_EXTRACTED"
    MAPPED = "MAPPED"
    FAILED = "FAILED"


class EHRDocument(Base):
    """EHR Document database model."""

    __tablename__ = "ehr_documents"

    ehr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[EHRDocumentStatus] = mapped_column(
        SQLEnum(EHRDocumentStatus, name="ehr_document_status"),
        default=EHRDocumentStatus.INGESTED,
        nullable=False,
    )
    processing_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    entities = relationship(
        "EHREntity",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    mappings = relationship(
        "EHRMapping",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<EHRDocument(id={self.ehr_id}, case_id={self.case_id}, status={self.status})>"
