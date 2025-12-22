"""
Checklist data model for Policy Validation Copilot

This module contains the Checklist model for deterministic rule evaluation
and policy compliance checking as specified in Anexo A.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, ChecklistOutcome


class ChecklistItem(BaseEntity):
    """
    Individual checklist item with evaluation outcome.
    
    Represents a single rule or requirement evaluation with
    evidence reference and outcome determination.
    """
    
    # Rule identification
    rule_id: str = Field(..., description="Rule identifier")
    rule_description: str = Field(..., description="Human-readable rule description")
    rule_version: str = Field(..., description="Rule version")
    
    # Evaluation outcome
    outcome: ChecklistOutcome = Field(..., description="Evaluation outcome")
    
    # Evidence reference
    evidence_ref: Optional[UUID] = Field(None, description="Reference to evidence item ID")
    evidence_excerpt: Optional[str] = Field(None, description="Relevant evidence excerpt")
    
    # Evaluation details
    evaluation_method: str = Field(..., description="Method used for evaluation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in evaluation")
    
    # Failure details (if applicable)
    failure_reason: Optional[str] = Field(None, description="Reason for failure if outcome is FAIL")
    missing_data: Optional[List[str]] = Field(None, description="List of missing data fields")
    
    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow, description="Evaluation timestamp")
    evaluator: str = Field(..., description="System or agent that performed evaluation")
    
    @validator('confidence_score')
    def validate_confidence_with_outcome(cls, v, values):
        """Validate confidence score consistency with outcome."""
        if 'outcome' in values:
            if values['outcome'] == ChecklistOutcome.UNKNOWN and v > 0.5:
                raise ValueError('UNKNOWN outcome should have low confidence score')
            if values['outcome'] == ChecklistOutcome.MISSING and v > 0.1:
                raise ValueError('MISSING outcome should have very low confidence score')
        return v
    
    @validator('failure_reason')
    def validate_failure_reason(cls, v, values):
        """Validate failure reason is provided for FAIL outcomes."""
        if 'outcome' in values and values['outcome'] == ChecklistOutcome.FAIL and not v:
            raise ValueError('Failure reason is required for FAIL outcomes')
        return v


class MissingField(BaseEntity):
    """
    Missing field information for incomplete evaluations.
    
    Tracks required data fields that are missing and preventing
    complete policy evaluation.
    """
    
    field_name: str = Field(..., description="Name of missing field")
    field_type: str = Field(..., description="Expected data type")
    required_for: List[str] = Field(..., description="List of rules requiring this field")
    criticality: str = Field(..., description="Criticality level (LOW, MEDIUM, HIGH, CRITICAL)")
    suggested_source: Optional[str] = Field(None, description="Suggested source for obtaining field")
    
    @validator('criticality')
    def validate_criticality(cls, v):
        """Validate criticality level."""
        valid_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f'Criticality must be one of: {valid_levels}')
        return v


class RuleEvaluationLog(BaseEntity):
    """
    Detailed log of rule evaluation process.
    
    Provides audit trail for rule execution including
    inputs, processing steps, and decision rationale.
    """
    
    rule_id: str = Field(..., description="Rule identifier")
    execution_id: str = Field(..., description="Unique execution identifier")
    
    # Input data
    input_data: Dict = Field(..., description="Input data used for evaluation")
    evidence_used: List[UUID] = Field(default_factory=list, description="Evidence items used")
    
    # Processing steps
    processing_steps: List[Dict] = Field(default_factory=list, description="Detailed processing steps")
    decision_tree: Optional[Dict] = Field(None, description="Decision tree traversal")
    
    # Execution metadata
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Errors encountered during execution")
    warnings: List[str] = Field(default_factory=list, description="Warnings generated during execution")
    
    @validator('execution_time_ms')
    def validate_execution_time(cls, v):
        """Validate execution time is non-negative."""
        if v < 0:
            raise ValueError('Execution time cannot be negative')
        return v


class Checklist(BaseEntity):
    """
    Complete checklist for policy validation case.
    
    Contains all evaluated checklist items, missing fields,
    and rule evaluation logs as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    
    # Checklist items
    items: List[ChecklistItem] = Field(default_factory=list, description="Checklist items with outcomes")
    
    # Missing data tracking
    missing_fields: List[MissingField] = Field(default_factory=list, description="Missing required fields")
    
    # Rule execution tracking
    rule_ids_applied: List[str] = Field(default_factory=list, description="List of rule IDs that were applied")
    evaluation_log: List[RuleEvaluationLog] = Field(default_factory=list, description="Detailed rule evaluation logs")
    
    # Summary metrics
    total_rules: int = Field(0, description="Total number of rules evaluated")
    passed_rules: int = Field(0, description="Number of rules that passed")
    failed_rules: int = Field(0, description="Number of rules that failed")
    missing_rules: int = Field(0, description="Number of rules with missing data")
    unknown_rules: int = Field(0, description="Number of rules with unknown outcomes")
    
    # Completion status
    evaluation_complete: bool = Field(False, description="Whether evaluation is complete")
    blocking_issues: List[str] = Field(default_factory=list, description="Issues blocking completion")
    
    # Policy compliance
    compliance_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall compliance score")
    critical_failures: List[str] = Field(default_factory=list, description="Critical rule failures")
    
    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow, description="Evaluation timestamp")
    policy_version: str = Field(..., description="Policy version used for evaluation")
    
    @validator('total_rules')
    def validate_rule_counts(cls, v, values):
        """Validate rule count consistency."""
        if 'items' in values:
            actual_count = len(values['items'])
            if v != actual_count:
                raise ValueError(f'Total rules ({v}) must match items count ({actual_count})')
        return v
    
    def add_checklist_item(self, item: ChecklistItem) -> None:
        """Add a checklist item and update metrics."""
        self.items.append(item)
        if item.rule_id not in self.rule_ids_applied:
            self.rule_ids_applied.append(item.rule_id)
        self._update_metrics()
    
    def add_missing_field(self, field: MissingField) -> None:
        """Add a missing field requirement."""
        self.missing_fields.append(field)
        if field.criticality in ['HIGH', 'CRITICAL']:
            self.blocking_issues.append(f"Missing critical field: {field.field_name}")
        self.updated_at = datetime.utcnow()
    
    def add_evaluation_log(self, log: RuleEvaluationLog) -> None:
        """Add a rule evaluation log entry."""
        self.evaluation_log.append(log)
        self.updated_at = datetime.utcnow()
    
    def _update_metrics(self) -> None:
        """Update summary metrics based on current items."""
        self.total_rules = len(self.items)
        self.passed_rules = len([item for item in self.items if item.outcome == ChecklistOutcome.PASS])
        self.failed_rules = len([item for item in self.items if item.outcome == ChecklistOutcome.FAIL])
        self.missing_rules = len([item for item in self.items if item.outcome == ChecklistOutcome.MISSING])
        self.unknown_rules = len([item for item in self.items if item.outcome == ChecklistOutcome.UNKNOWN])
        
        # Calculate compliance score
        if self.total_rules > 0:
            self.compliance_score = self.passed_rules / self.total_rules
        
        # Update critical failures
        self.critical_failures = [
            item.rule_id for item in self.items 
            if item.outcome == ChecklistOutcome.FAIL and 'CRITICAL' in item.rule_description.upper()
        ]
        
        # Check if evaluation is complete
        self.evaluation_complete = (
            self.missing_rules == 0 and 
            self.unknown_rules == 0 and 
            len(self.blocking_issues) == 0
        )
        
        self.updated_at = datetime.utcnow()
    
    def has_critical_failures(self) -> bool:
        """Check if there are any critical rule failures."""
        return len(self.critical_failures) > 0
    
    def can_approve(self) -> bool:
        """Check if case can be approved based on checklist."""
        return (
            self.evaluation_complete and
            not self.has_critical_failures() and
            self.compliance_score >= 0.8  # Configurable threshold
        )
    
    def get_failed_items(self) -> List[ChecklistItem]:
        """Get all failed checklist items."""
        return [item for item in self.items if item.outcome == ChecklistOutcome.FAIL]
    
    def get_missing_items(self) -> List[ChecklistItem]:
        """Get all items with missing data."""
        return [item for item in self.items if item.outcome == ChecklistOutcome.MISSING]
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "total_rules": 15,
                "passed_rules": 12,
                "failed_rules": 1,
                "missing_rules": 2,
                "unknown_rules": 0,
                "evaluation_complete": False,
                "compliance_score": 0.8,
                "policy_version": "v2.1.0",
                "blocking_issues": ["Missing critical field: diagnosis_code"]
            }
        }
