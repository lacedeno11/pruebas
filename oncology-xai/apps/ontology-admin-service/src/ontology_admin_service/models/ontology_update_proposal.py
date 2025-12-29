"""Ontology Update Proposal database model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, func, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from ontology_admin_service.database import Base


class ProposalStatus(str, Enum):
    """Proposal lifecycle status."""
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    REQUIRES_FIX = "REQUIRES_FIX"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ROLLBACK_REQUESTED = "ROLLBACK_REQUESTED"
    ROLLED_BACK = "ROLLED_BACK"


class OntologyUpdateProposal(Base):
    """Ontology update proposal database model."""

    __tablename__ = "ontology_update_proposals"

    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ontology_sources: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    status: Mapped[ProposalStatus] = mapped_column(
        SQLEnum(ProposalStatus, name="proposal_status"),
        default=ProposalStatus.DRAFT,
        nullable=False,
        index=True,
    )
    workflow_execution_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    diff_summary: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    impact_analysis: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    reasoner_results: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    validation_errors: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    uploaded_files: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    approval_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ontology_versions.version_id", ondelete="SET NULL"),
        nullable=True,
    )
    rollback_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ontology_versions.version_id", ondelete="SET NULL"),
        nullable=True,
    )
    rollback_to_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ontology_versions.version_id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
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
    approved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<OntologyUpdateProposal(id={self.proposal_id}, status={self.status})>"
