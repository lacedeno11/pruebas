"""Audit Event model."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Text, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditEvent(Base):
    """Audit Event model for tracking all system events."""

    __tablename__ = "audit_events"

    # Primary key
    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()::text")
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True
    )

    # User information
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    # Case information
    case_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    # Entity information
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    entity_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    # Additional details as JSON
    details_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Correlation ID for tracking related events
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    # Source service
    source_service: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # IP Address
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True
    )

    # User agent
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Additional metadata
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_audit_case_timestamp', 'case_id', 'timestamp'),
        Index('ix_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_audit_type_action', 'entity_type', 'action'),
        Index('ix_audit_timestamp_desc', text('timestamp DESC')),
    )

    def __repr__(self) -> str:
        """String representation of AuditEvent."""
        return (
            f"<AuditEvent(event_id={self.event_id}, "
            f"action={self.action}, "
            f"entity_type={self.entity_type}, "
            f"timestamp={self.timestamp})>"
        )
