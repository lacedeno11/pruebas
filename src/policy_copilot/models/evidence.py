"""
Evidence Pack data model for Policy Validation Copilot

This module contains the Evidence Pack model for storing policy retrieval
results with exact document references and coverage metrics.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, DocumentPointer


class EvidenceItem(BaseEntity):
    """
    Individual evidence item with document reference and content.
    
    Contains exact pointers to source documents with checksums
    and relevance scores for traceability.
    """
    
    # Document identification
    doc_id: str = Field(..., description="Document identifier")
    doc_version: str = Field(..., description="Document version")
    doc_checksum: str = Field(..., description="Document SHA-256 checksum")
    
    # Content location
    pointer: DocumentPointer = Field(..., description="Exact location in document")
    excerpt: Optional[str] = Field(None, description="Text excerpt from document")
    table_ref: Optional[Dict] = Field(None, description="Table reference data")
    
    # Relevance and scoring
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    
    # Metadata
    extraction_method: str = Field(..., description="Method used for extraction")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    
    @validator('doc_checksum')
    def validate_checksum(cls, v):
        """Validate SHA-256 checksum format."""
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Document checksum must be a valid SHA-256 hash')
        return v.lower()
    
    @validator('excerpt')
    def validate_excerpt_length(cls, v):
        """Validate excerpt is not too long."""
        if v and len(v) > 5000:
            raise ValueError('Excerpt cannot exceed 5000 characters')
        return v


class ConflictDetection(BaseEntity):
    """
    Conflict detection between evidence items.
    
    Identifies contradictions or inconsistencies in retrieved evidence.
    """
    
    evidence_item_ids: List[UUID] = Field(..., description="Conflicting evidence item IDs")
    conflict_type: str = Field(..., description="Type of conflict detected")
    severity: str = Field(..., description="Conflict severity (LOW, MEDIUM, HIGH)")
    description: str = Field(..., description="Human-readable conflict description")
    resolution_required: bool = Field(True, description="Whether manual resolution is required")
    
    @validator('evidence_item_ids')
    def validate_evidence_items(cls, v):
        """Validate at least two evidence items for conflict."""
        if len(v) < 2:
            raise ValueError('Conflict must involve at least two evidence items')
        return v


class EvidencePack(BaseEntity):
    """
    Evidence Pack containing all retrieved evidence for a case.
    
    Aggregates evidence items with coverage metrics and conflict detection
    as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    
    # Evidence items
    items: List[EvidenceItem] = Field(default_factory=list, description="Evidence items with doc references")
    
    # Coverage and quality metrics
    coverage_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall coverage score (0-1)")
    completeness_score: float = Field(0.0, ge=0.0, le=1.0, description="Completeness score (0-1)")
    quality_score: float = Field(0.0, ge=0.0, le=1.0, description="Quality score (0-1)")
    
    # Conflict detection
    conflicts: List[ConflictDetection] = Field(default_factory=list, description="Detected conflicts")
    conflicts_detected: bool = Field(False, description="Whether conflicts were detected")
    
    # Source tracking
    sources_consulted: List[str] = Field(default_factory=list, description="List of source document IDs consulted")
    missing_sources: List[str] = Field(default_factory=list, description="List of expected but missing sources")
    
    # Retrieval metadata
    retrieval_query: str = Field(..., description="Original retrieval query")
    retrieval_method: str = Field(..., description="Retrieval method used")
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Retrieval timestamp")
    retrieval_duration_ms: Optional[int] = Field(None, description="Retrieval duration in milliseconds")
    
    # Allowlist validation
    allowlist_validated: bool = Field(False, description="Whether all sources are allowlisted")
    non_allowlisted_sources: List[str] = Field(default_factory=list, description="Non-allowlisted sources found")
    
    @validator('coverage_score')
    def validate_coverage_score(cls, v, values):
        """Validate coverage score consistency with items."""
        if 'items' in values and not values['items'] and v > 0:
            raise ValueError('Coverage score must be 0 when no evidence items exist')
        return v
    
    @validator('conflicts_detected')
    def validate_conflicts_detected(cls, v, values):
        """Validate conflicts_detected flag consistency."""
        if 'conflicts' in values:
            has_conflicts = len(values['conflicts']) > 0
            if v != has_conflicts:
                raise ValueError('conflicts_detected flag must match presence of conflicts')
        return v
    
    def add_evidence_item(self, item: EvidenceItem) -> None:
        """Add an evidence item to the pack."""
        self.items.append(item)
        self.sources_consulted.append(item.doc_id)
        self.updated_at = datetime.utcnow()
        self._recalculate_scores()
    
    def add_conflict(self, conflict: ConflictDetection) -> None:
        """Add a conflict detection result."""
        self.conflicts.append(conflict)
        self.conflicts_detected = True
        self.updated_at = datetime.utcnow()
    
    def mark_source_missing(self, source_id: str) -> None:
        """Mark a source as missing."""
        if source_id not in self.missing_sources:
            self.missing_sources.append(source_id)
            self.updated_at = datetime.utcnow()
            self._recalculate_scores()
    
    def validate_allowlist(self, allowlisted_sources: List[str]) -> None:
        """Validate all sources against allowlist."""
        self.non_allowlisted_sources = [
            source for source in self.sources_consulted 
            if source not in allowlisted_sources
        ]
        self.allowlist_validated = len(self.non_allowlisted_sources) == 0
        self.updated_at = datetime.utcnow()
    
    def _recalculate_scores(self) -> None:
        """Recalculate coverage and quality scores."""
        if not self.items:
            self.coverage_score = 0.0
            self.completeness_score = 0.0
            self.quality_score = 0.0
            return
        
        # Calculate coverage based on evidence items and missing sources
        total_expected = len(self.sources_consulted) + len(self.missing_sources)
        if total_expected > 0:
            self.coverage_score = len(self.sources_consulted) / total_expected
        
        # Calculate completeness based on evidence quality
        total_relevance = sum(item.relevance_score for item in self.items)
        self.completeness_score = total_relevance / len(self.items) if self.items else 0.0
        
        # Calculate quality based on confidence scores
        total_confidence = sum(item.confidence_score for item in self.items)
        self.quality_score = total_confidence / len(self.items) if self.items else 0.0
    
    def get_high_confidence_items(self, threshold: float = 0.8) -> List[EvidenceItem]:
        """Get evidence items with high confidence scores."""
        return [item for item in self.items if item.confidence_score >= threshold]
    
    def has_sufficient_coverage(self, threshold: float = 0.7) -> bool:
        """Check if evidence pack has sufficient coverage."""
        return self.coverage_score >= threshold and not self.conflicts_detected
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "coverage_score": 0.85,
                "completeness_score": 0.78,
                "quality_score": 0.82,
                "conflicts_detected": False,
                "retrieval_query": "medical consultation coverage policy",
                "retrieval_method": "semantic_search",
                "allowlist_validated": True,
                "sources_consulted": ["DOC-001", "DOC-002"],
                "missing_sources": []
            }
        }
