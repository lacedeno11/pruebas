"""EHR Mapping database model."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ehr_service.database import Base


class EHRMapping(Base):
    """EHR Mapping database model - represents ontology mappings for entities."""

    __tablename__ = "ehr_mappings"

    mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ehr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ehr_documents.ehr_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ehr_entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ontology: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    iri: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    mapping_method: Mapped[str] = mapped_column(
        String(100),
        default="automatic",
        nullable=False,
    )
    evidence: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document = relationship("EHRDocument", back_populates="mappings")
    entity = relationship("EHREntity", back_populates="mappings")

    def __repr__(self) -> str:
        return f"<EHRMapping(id={self.mapping_id}, ontology={self.ontology}, iri={self.iri})>"
