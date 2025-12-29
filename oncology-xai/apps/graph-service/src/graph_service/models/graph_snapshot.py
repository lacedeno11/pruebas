"""Case Graph Snapshot database model."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from graph_service.database import Base


class CaseGraphSnapshot(Base):
    """Case Graph Snapshot database model.

    Stores complete graph snapshots including nodes, edges, layout, and metadata.
    """

    __tablename__ = "case_graph_snapshots"

    graph_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Graph data
    nodes: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of graph nodes with properties",
    )
    edges: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of graph edges with properties",
    )

    # Layout information for visualization
    layout: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Node positions and layout metadata",
    )

    # Metadata
    depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        comment="Depth of graph traversal",
    )
    include_inferred: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Whether inferred relationships are included",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        comment="Additional metadata (provenance, stats, etc.)",
    )

    # Task tracking
    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Celery task ID if built asynchronously",
    )

    # Timestamps
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

    def __repr__(self) -> str:
        return f"<CaseGraphSnapshot(id={self.graph_snapshot_id}, case_id={self.case_id})>"
