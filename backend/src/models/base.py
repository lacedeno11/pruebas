"""
SQLAlchemy declarative base and common model mixins for PEI Platform.

This module defines the declarative base for all ORM models and provides
common functionality through mixins for timestamp management.
"""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column


# Create the declarative base for all models
Base = declarative_base()


class TimestampMixin:
    """
    Mixin class that adds created_at and updated_at timestamp fields to models.

    These timestamps are automatically managed:
    - created_at: Set when a record is first inserted
    - updated_at: Set when a record is created or updated
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="When the record was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="When the record was last updated (UTC)",
    )

