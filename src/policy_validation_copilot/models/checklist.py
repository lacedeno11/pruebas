"""
Checklist data models.

Represents deterministic rule evaluation results.
Based on UC-OP-07 Rules & Checklist Builder.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChecklistOutcome(str, Enum):
    """Outcome of a single checklist item evaluation."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ChecklistItem(BaseModel):
    """
    Single checklist item with deterministic evaluation.

    Each item must be traceable to evidence (RB-07-01).
    """

    item_id: str = Field(..., description="Checklist item identifier")
    rule_id: str = Field(..., description="Associated rule identifier from policy-as-code")
    rule_version: str = Field(..., description="Rule version for reproducibility")

    # Description
    description: str = Field(..., description="Human-readable requirement description")
    category: str = Field(..., description="Category: COVERAGE, AUTHORIZATION, LIMIT, EXCLUSION")

    # Evaluation result
    outcome: ChecklistOutcome = Field(default=ChecklistOutcome.UNKNOWN)
    outcome_reason: Optional[str] = Field(None, description="Explanation of outcome")

    # Evidence linkage - mandatory for PASSED/FAILED (RB-07-01)
    evidence_ref: Optional[str] = Field(None, description="Evidence item ID supporting outcome")
    evidence_excerpt: Optional[str] = Field(None, description="Relevant excerpt from evidence")

    # Criticality
    is_blocking: bool = Field(
        default=False, description="If FAILED/MISSING, blocks APPROVED status (RB-07-02)"
    )
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Importance weight")

    # Evaluation metadata
    evaluated_at: Optional[datetime] = Field(None)
    evaluation_duration_ms: Optional[int] = Field(None)


class MissingField(BaseModel):
    """Required field that is missing from case data."""

    field_name: str = Field(..., description="Name of missing field")
    field_path: str = Field(..., description="JSON path to field in case data")
    is_critical: bool = Field(default=True, description="Blocks processing if missing")
    suggested_source: Optional[str] = Field(None, description="Where to obtain this data")


class Checklist(BaseModel):
    """
    Complete checklist evaluation for a case.

    Aggregates all rule evaluations with summary metrics.
    """

    checklist_id: str = Field(..., description="Checklist identifier")
    case_id: str = Field(..., description="Associated case identifier")

    # Evaluated items
    items: list[ChecklistItem] = Field(default_factory=list)

    # Missing data tracking
    missing_fields: list[MissingField] = Field(default_factory=list)

    # Rules applied
    rule_ids_applied: list[str] = Field(default_factory=list)
    rule_set_version: Optional[str] = Field(None, description="Version of ruleset used")

    # Exception handling
    exceptions_applied: list[str] = Field(
        default_factory=list, description="Exception rule IDs that were applied"
    )

    # Evaluation log for audit
    evaluation_log: list[dict] = Field(
        default_factory=list, description="Detailed evaluation trace"
    )

    # Summary metrics
    total_items: int = Field(default=0)
    passed_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    unknown_count: int = Field(default=0)
    missing_count: int = Field(default=0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_duration_ms: Optional[int] = Field(None)

    def update_counts(self) -> None:
        """Recalculate summary counts from items."""
        self.total_items = len(self.items)
        self.passed_count = sum(1 for i in self.items if i.outcome == ChecklistOutcome.PASSED)
        self.failed_count = sum(1 for i in self.items if i.outcome == ChecklistOutcome.FAILED)
        self.unknown_count = sum(1 for i in self.items if i.outcome == ChecklistOutcome.UNKNOWN)
        self.missing_count = sum(1 for i in self.items if i.outcome == ChecklistOutcome.MISSING)

    def has_blocking_failures(self) -> bool:
        """Check if any blocking items have failed or are missing."""
        return any(
            i.is_blocking and i.outcome in (ChecklistOutcome.FAILED, ChecklistOutcome.MISSING)
            for i in self.items
        )

    def can_auto_approve(self) -> bool:
        """Check if checklist allows automatic approval."""
        self.update_counts()
        return (
            self.failed_count == 0
            and self.missing_count == 0
            and not self.has_blocking_failures()
            and len(self.missing_fields) == 0
        )
