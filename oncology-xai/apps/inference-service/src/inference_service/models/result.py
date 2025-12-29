"""Result models for storing inference outputs."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inference_service.database import Base


class ResultBundle(Base):
    """Result bundle containing all inference outputs."""

    __tablename__ = "result_bundles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    ml_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ml_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Overall confidence and summary
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    pattern_results: Mapped[list["PatternResult"]] = relationship(
        "PatternResult",
        back_populates="result_bundle",
        cascade="all, delete-orphan",
    )
    genetic_results: Mapped[list["GeneticResult"]] = relationship(
        "GeneticResult",
        back_populates="result_bundle",
        cascade="all, delete-orphan",
    )
    xai_artifacts: Mapped[list["XAIArtifact"]] = relationship(
        "XAIArtifact",
        back_populates="result_bundle",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ResultBundle(id={self.id}, image_id={self.image_id})>"


class PatternResult(Base):
    """Pattern detection results."""

    __tablename__ = "pattern_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    result_bundle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("result_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pattern information
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Location information
    location: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Pattern details
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    clinical_significance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    result_bundle: Mapped["ResultBundle"] = relationship(
        "ResultBundle",
        back_populates="pattern_results",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<PatternResult(id={self.id}, pattern_name={self.pattern_name})>"


class GeneticResult(Base):
    """Genetic marker results."""

    __tablename__ = "genetic_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    result_bundle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("result_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Genetic marker information
    marker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_type: Mapped[str] = mapped_column(String(100), nullable=False)
    presence_probability: Mapped[float] = mapped_column(Float, nullable=False)

    # Clinical information
    clinical_relevance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    therapeutic_implications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Supporting evidence
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    result_bundle: Mapped["ResultBundle"] = relationship(
        "ResultBundle",
        back_populates="genetic_results",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<GeneticResult(id={self.id}, marker_name={self.marker_name})>"


class XAIArtifact(Base):
    """XAI (Explainable AI) artifacts for interpretability."""

    __tablename__ = "xai_artifacts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    result_bundle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("result_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Artifact information
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Artifact data
    artifact_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Description and interpretation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    result_bundle: Mapped["ResultBundle"] = relationship(
        "ResultBundle",
        back_populates="xai_artifacts",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<XAIArtifact(id={self.id}, artifact_name={self.artifact_name})>"
