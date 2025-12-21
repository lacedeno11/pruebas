"""
Evidence pack data models.

Represents retrieved policy documents and evidence for decision-making.
Based on UC-OP-06 Policy Retrieval Agent (RAG).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Type of evidence source."""

    POLICY_TEXT = "POLICY_TEXT"
    POLICY_TABLE = "POLICY_TABLE"
    EXCEPTION_RULE = "EXCEPTION_RULE"
    EXTERNAL_RESPONSE = "EXTERNAL_RESPONSE"
    HISTORICAL_CASE = "HISTORICAL_CASE"


class ConflictFlag(BaseModel):
    """Detected conflict between evidence sources."""

    conflict_id: str = Field(..., description="Conflict identifier")
    source_a: str = Field(..., description="First conflicting source doc_id")
    source_b: str = Field(..., description="Second conflicting source doc_id")
    conflict_type: str = Field(..., description="Type: COVERAGE, EXCLUSION, LIMIT, DATE")
    description: str = Field(..., description="Human-readable conflict description")
    resolution_hint: Optional[str] = Field(None, description="Suggested resolution approach")
    requires_hitl: bool = Field(default=False)


class EvidenceItem(BaseModel):
    """
    Single piece of evidence from policy documents.

    Includes verifiable pointers (page, cell, section) for anti-hallucination.
    """

    evidence_id: str = Field(..., description="Unique evidence item identifier")
    doc_id: str = Field(..., description="Source document identifier")
    doc_version: str = Field(..., description="Document version for reproducibility")
    checksum: str = Field(..., description="Document checksum for integrity")

    # Precise location pointers - critical for anti-hallucination (RB-06-02)
    pointer: str = Field(..., description="Exact location: page:line, sheet:cell, section:paragraph")
    page_number: Optional[int] = Field(None, description="PDF page number if applicable")
    cell_reference: Optional[str] = Field(None, description="Excel cell reference if applicable")
    section_id: Optional[str] = Field(None, description="Document section identifier")

    # Content
    evidence_type: EvidenceType = Field(default=EvidenceType.POLICY_TEXT)
    excerpt: Optional[str] = Field(None, description="Text excerpt (may be redacted)")
    table_data: Optional[dict] = Field(None, description="Structured table data if applicable")

    # Relevance scores
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Semantic relevance to query")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")

    # Source validation
    is_allowlisted: bool = Field(default=True, description="Source in approved allowlist")
    effective_date: Optional[datetime] = Field(None, description="Policy effective date")
    expiration_date: Optional[datetime] = Field(None, description="Policy expiration date")

    # Metadata
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    retrieval_query: Optional[str] = Field(None, description="Query used for retrieval")


class EvidencePack(BaseModel):
    """
    Complete evidence package for a case decision.

    Aggregates all retrieved evidence with coverage metrics.
    """

    pack_id: str = Field(..., description="Evidence pack identifier")
    case_id: str = Field(..., description="Associated case identifier")

    # Evidence items
    items: list[EvidenceItem] = Field(default_factory=list)

    # Coverage assessment
    coverage_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall coverage of policy requirements"
    )
    missing_sources: list[str] = Field(
        default_factory=list, description="Required sources not found"
    )

    # Conflict detection
    conflicts: list[ConflictFlag] = Field(default_factory=list)
    conflicts_detected: bool = Field(default=False)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retrieval_duration_ms: Optional[int] = Field(None)
    total_documents_searched: int = Field(default=0)

    def has_sufficient_coverage(self, threshold: float = 0.7) -> bool:
        """Check if coverage meets minimum threshold."""
        return self.coverage_score >= threshold and not any(c.requires_hitl for c in self.conflicts)

    def get_primary_evidence(self) -> list[EvidenceItem]:
        """Get highest relevance evidence items."""
        return sorted(self.items, key=lambda x: x.relevance_score, reverse=True)[:5]
