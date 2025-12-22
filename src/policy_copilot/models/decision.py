"""
Decision data model for Policy Validation Copilot

This module contains the Decision model for policy validation outcomes
and decision orchestration as specified in Anexo A.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, CaseStatus, RiskLevel, ConfidenceLevel, ThresholdConfig


class NextAction(BaseEntity):
    """
    Next action recommendation for case processing.
    
    Defines specific actions to be taken based on decision outcome
    with priority and timing information.
    """
    
    action_type: str = Field(..., description="Type of action (APPROVE, REJECT, ESCALATE, etc.)")
    description: str = Field(..., description="Human-readable action description")
    priority: str = Field(..., description="Action priority (LOW, MEDIUM, HIGH, CRITICAL)")
    assigned_to: Optional[str] = Field(None, description="Agent or queue assigned to action")
    due_date: Optional[datetime] = Field(None, description="Action due date")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites for action")
    
    @validator('action_type')
    def validate_action_type(cls, v):
        """Validate action type is from allowed set."""
        valid_types = [
            'APPROVE', 'REJECT', 'ESCALATE', 'REQUEST_INFO', 'CONSULT_EXTERNAL',
            'MANUAL_REVIEW', 'WAIT_FOR_DATA', 'REPROCESS', 'CLOSE'
        ]
        if v not in valid_types:
            raise ValueError(f'Action type must be one of: {valid_types}')
        return v


class DecisionRationale(BaseEntity):
    """
    Decision rationale with supporting evidence and reasoning.
    
    Provides detailed explanation for decision outcome with
    references to evidence and rule evaluations.
    """
    
    primary_reason: str = Field(..., description="Primary reason for decision")
    supporting_evidence: List[UUID] = Field(default_factory=list, description="Supporting evidence item IDs")
    rule_references: List[str] = Field(default_factory=list, description="Rule IDs that influenced decision")
    confidence_factors: Dict[str, float] = Field(default_factory=dict, description="Factors affecting confidence")
    risk_factors: Dict[str, float] = Field(default_factory=dict, description="Factors affecting risk assessment")
    
    # Detailed reasoning
    decision_tree: Optional[Dict] = Field(None, description="Decision tree path taken")
    alternative_outcomes: List[str] = Field(default_factory=list, description="Alternative outcomes considered")
    uncertainty_sources: List[str] = Field(default_factory=list, description="Sources of uncertainty")
    
    @validator('supporting_evidence')
    def validate_evidence_exists(cls, v):
        """Validate at least one evidence item for non-rejection decisions."""
        # This will be enhanced with actual evidence validation in integration
        return v


class Decision(BaseEntity):
    """
    Policy validation decision model.
    
    Contains the final decision outcome with confidence, risk assessment,
    next actions, and threshold version as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    
    # Decision outcome
    status: CaseStatus = Field(..., description="Decision status/outcome")
    
    # Confidence and risk assessment
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Decision confidence score (0-1)")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level category")
    risk_level: RiskLevel = Field(..., description="Risk level assessment")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0-1)")
    
    # Decision rationale
    rationale: DecisionRationale = Field(..., description="Detailed decision rationale")
    
    # Next actions
    next_actions: List[NextAction] = Field(default_factory=list, description="Recommended next actions")
    immediate_action: Optional[str] = Field(None, description="Immediate action required")
    
    # Threshold configuration used
    thresholds_version: str = Field(..., description="Threshold configuration version used")
    threshold_config: ThresholdConfig = Field(..., description="Threshold configuration applied")
    
    # Signal consolidation
    checklist_score: float = Field(..., ge=0.0, le=1.0, description="Checklist compliance score")
    ml_confidence: float = Field(..., ge=0.0, le=1.0, description="ML confidence score")
    coverage_score: float = Field(..., ge=0.0, le=1.0, description="Evidence coverage score")
    guardrail_flags: List[str] = Field(default_factory=list, description="Guardrail flags raised")
    
    # Decision metadata
    decision_method: str = Field(..., description="Method used for decision (AUTO, HITL, HYBRID)")
    decided_by: str = Field(..., description="System or agent that made decision")
    decided_at: datetime = Field(default_factory=datetime.utcnow, description="Decision timestamp")
    
    # Quality metrics
    decision_quality_score: Optional[float] = Field(None, description="Decision quality assessment")
    explainability_score: Optional[float] = Field(None, description="Decision explainability score")
    
    # Escalation tracking
    escalation_required: bool = Field(False, description="Whether escalation is required")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")
    escalation_queue: Optional[str] = Field(None, description="Queue for escalation")
    
    @validator('confidence_level')
    def validate_confidence_consistency(cls, v, values):
        """Validate confidence level matches confidence score."""
        if 'confidence_score' in values and 'threshold_config' in values:
            score = values['confidence_score']
            thresholds = values['threshold_config']
            
            if score >= thresholds.confidence_high and v != ConfidenceLevel.HIGH:
                raise ValueError('High confidence score must have HIGH confidence level')
            elif score >= thresholds.confidence_medium and v not in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]:
                raise ValueError('Medium confidence score must have MEDIUM or HIGH confidence level')
            elif score < thresholds.confidence_medium and v != ConfidenceLevel.LOW:
                raise ValueError('Low confidence score must have LOW confidence level')
        return v
    
    @validator('escalation_required')
    def validate_escalation_consistency(cls, v, values):
        """Validate escalation requirement consistency."""
        if v and 'escalation_reason' in values and not values['escalation_reason']:
            raise ValueError('Escalation reason required when escalation is required')
        return v
    
    @validator('status')
    def validate_status_with_scores(cls, v, values):
        """Validate decision status consistency with scores."""
        if 'confidence_score' in values and 'risk_level' in values:
            confidence = values['confidence_score']
            risk = values['risk_level']
            
            # High risk cases should not be auto-approved
            if v == CaseStatus.APROBADO and risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                raise ValueError('High risk cases cannot be auto-approved')
            
            # Low confidence cases should be escalated
            if v == CaseStatus.APROBADO and confidence < 0.6:
                raise ValueError('Low confidence cases should not be auto-approved')
        return v
    
    def add_next_action(self, action: NextAction) -> None:
        """Add a next action to the decision."""
        self.next_actions.append(action)
        self.updated_at = datetime.utcnow()
    
    def should_auto_close(self) -> bool:
        """Check if case should be auto-closed based on thresholds."""
        return (
            self.confidence_level == ConfidenceLevel.HIGH and
            self.risk_level == RiskLevel.LOW and
            self.coverage_score >= self.threshold_config.coverage_ok and
            len(self.guardrail_flags) == 0 and
            not self.escalation_required
        )
    
    def requires_hitl(self) -> bool:
        """Check if case requires human-in-the-loop review."""
        return (
            self.confidence_level == ConfidenceLevel.LOW or
            self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            len(self.guardrail_flags) > 0 or
            self.escalation_required or
            self.coverage_score < self.threshold_config.coverage_ok
        )
    
    def calculate_overall_score(self) -> float:
        """Calculate overall decision score combining all factors."""
        weights = {
            'confidence': 0.3,
            'checklist': 0.25,
            'ml': 0.2,
            'coverage': 0.15,
            'risk': 0.1  # Risk is inverse - lower risk is better
        }
        
        risk_normalized = 1.0 - self.risk_score  # Invert risk score
        
        overall_score = (
            weights['confidence'] * self.confidence_score +
            weights['checklist'] * self.checklist_score +
            weights['ml'] * self.ml_confidence +
            weights['coverage'] * self.coverage_score +
            weights['risk'] * risk_normalized
        )
        
        # Apply penalty for guardrail flags
        if self.guardrail_flags:
            penalty = min(0.2, len(self.guardrail_flags) * 0.05)
            overall_score -= penalty
        
        return max(0.0, min(1.0, overall_score))
    
    def get_decision_summary(self) -> Dict[str, any]:
        """Get a summary of the decision for reporting."""
        return {
            'case_id': self.case_id,
            'status': self.status,
            'confidence_level': self.confidence_level,
            'risk_level': self.risk_level,
            'overall_score': self.calculate_overall_score(),
            'auto_close_eligible': self.should_auto_close(),
            'hitl_required': self.requires_hitl(),
            'next_actions_count': len(self.next_actions),
            'guardrail_flags_count': len(self.guardrail_flags),
            'decided_at': self.decided_at,
            'decided_by': self.decided_by
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "status": "APROBADO",
                "confidence_score": 0.85,
                "confidence_level": "HIGH",
                "risk_level": "LOW",
                "risk_score": 0.15,
                "checklist_score": 0.9,
                "ml_confidence": 0.82,
                "coverage_score": 0.88,
                "guardrail_flags": [],
                "thresholds_version": "v1.0.0",
                "decision_method": "AUTO",
                "decided_by": "DECISION_ORCHESTRATOR",
                "escalation_required": False
            }
        }
