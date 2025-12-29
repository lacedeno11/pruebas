"""Ontology Version database model."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ontology_admin_service.database import Base


class OntologyVersion(Base):
    """Ontology version database model."""

    __tablename__ = "ontology_versions"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ontology_source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    version_tag: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    ontology_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    statistics: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
    published_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<OntologyVersion(id={self.version_id}, source={self.ontology_source}, version={self.version_tag})>"
