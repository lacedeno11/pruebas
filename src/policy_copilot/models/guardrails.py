"""
Guardrails data model for Policy Validation Copilot

This module contains the Guardrails model for security controls and governance
enforcement as specified in UC-OP-10 and Anexo A.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, GuardrailDecision


class SecurityEvent(BaseEntity):
    """
    Security event detected by guardrails.
    
    Records security violations, policy breaches, and
    suspicious activities for audit and monitoring.
    """
    
    event_type: str = Field(..., description="Type of security event")
    severity: str = Field(..., description="Event severity (LOW, MEDIUM, HIGH, CRITICAL)")
    description: str = Field(..., description="Human-readable event description")
    
    # Event details
    source_component: str = Field(..., description="Component that detected the event")
    affected_resource: Optional[str] = Field(None, description="Affected resource identifier")
    user_context: Optional[Dict] = Field(None, description="User context when event occurred")
    
    # Detection details
    detection_rule: str = Field(..., description="Rule or pattern that triggered detection")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    
    # Response actions
    action_taken: str = Field(..., description="Action taken in response to event")
    blocked: bool = Field(False, description="Whether action was blocked")
    escalated: bool = Field(False, description="Whether event was escalated")
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Detection timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    
    @validator('severity')
    def validate_severity(cls, v):
        """Validate severity level."""
        valid_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of: {valid_severities}')
        return v


class PIIRedaction(BaseEntity):
    """
    PII redaction record for data privacy compliance.
    
    Tracks personally identifiable information that was
    detected and redacted from system processing.
    """
    
    field_name: str = Field(..., description="Name of field containing PII")
    pii_type: str = Field(..., description="Type of PII detected")
    original_value_hash: str = Field(..., description="Hash of original value")
    redacted_value: str = Field(..., description="Redacted/masked value")
    
    # Detection details
    detection_method: str = Field(..., description="Method used to detect PII")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    
    # Redaction details
    redaction_method: str = Field(..., description="Method used for redaction")
    redaction_pattern: str = Field(..., description="Pattern used for masking")
    
    # Compliance
    regulation_basis: List[str] = Field(default_factory=list, description="Regulations requiring redaction")
    retention_policy: Optional[str] = Field(None, description="Data retention policy applied")
    
    # Metadata
    redacted_at: datetime = Field(default_factory=datetime.utcnow, description="Redaction timestamp")
    
    @validator('pii_type')
    def validate_pii_type(cls, v):
        """Validate PII type is recognized."""
        valid_types = [
            'SSN', 'EMAIL', 'PHONE', 'CREDIT_CARD', 'PASSPORT', 'DRIVER_LICENSE',
            'MEDICAL_ID', 'BANK_ACCOUNT', 'NAME', 'ADDRESS', 'DATE_OF_BIRTH'
        ]
        if v not in valid_types:
            raise ValueError(f'PII type must be one of: {valid_types}')
        return v


class SourceValidation(BaseEntity):
    """
    Source validation record for allowlist enforcement.
    
    Tracks validation of information sources against
    approved allowlists and policy requirements.
    """
    
    source_id: str = Field(..., description="Source identifier")
    source_type: str = Field(..., description="Type of source (DOCUMENT, API, DATABASE, etc.)")
    validation_status: str = Field(..., description="Validation status (APPROVED, REJECTED, PENDING)")
    
    # Allowlist validation
    allowlist_name: str = Field(..., description="Name of allowlist used for validation")
    allowlist_version: str = Field(..., description="Version of allowlist")
    in_allowlist: bool = Field(..., description="Whether source is in allowlist")
    
    # Source metadata
    source_checksum: Optional[str] = Field(None, description="Source content checksum")
    source_version: Optional[str] = Field(None, description="Source version")
    last_verified: Optional[datetime] = Field(None, description="Last verification timestamp")
    
    # Validation details
    validation_rules: List[str] = Field(default_factory=list, description="Validation rules applied")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors found")
    
    # Metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")
    validated_by: str = Field(..., description="System or agent that performed validation")
    
    @validator('validation_status')
    def validate_status(cls, v):
        """Validate status is from allowed set."""
        valid_statuses = ['APPROVED', 'REJECTED', 'PENDING', 'EXPIRED']
        if v not in valid_statuses:
            raise ValueError(f'Validation status must be one of: {valid_statuses}')
        return v


class AntiHallucinationCheck(BaseEntity):
    """
    Anti-hallucination verification record.
    
    Tracks verification that generated content is properly
    anchored to evidence and not hallucinated.
    """
    
    content_id: str = Field(..., description="Identifier of content being checked")
    content_type: str = Field(..., description="Type of content (DECISION, EXPLANATION, SUMMARY)")
    
    # Evidence anchoring
    evidence_references: List[UUID] = Field(default_factory=list, description="Evidence items referenced")
    anchor_score: float = Field(..., ge=0.0, le=1.0, description="Evidence anchoring score")
    hallucination_risk: float = Field(..., ge=0.0, le=1.0, description="Hallucination risk score")
    
    # Verification methods
    verification_methods: List[str] = Field(default_factory=list, description="Methods used for verification")
    cross_references: List[str] = Field(default_factory=list, description="Cross-references found")
    
    # Check results
    is_anchored: bool = Field(..., description="Whether content is properly anchored")
    hallucination_detected: bool = Field(False, description="Whether hallucination was detected")
    verification_passed: bool = Field(..., description="Whether verification passed")
    
    # Metadata
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    checked_by: str = Field(..., description="System or agent that performed check")
    
    @validator('verification_passed')
    def validate_verification_consistency(cls, v, values):
        """Validate verification result consistency."""
        if 'hallucination_detected' in values and values['hallucination_detected'] and v:
            raise ValueError('Verification cannot pass if hallucination is detected')
        if 'is_anchored' in values and not values['is_anchored'] and v:
            raise ValueError('Verification cannot pass if content is not anchored')
        return v


class GuardrailsResult(BaseEntity):
    """
    Guardrails enforcement result for LangGraph state.
    
    Contains decision, flags, redactions, and security events
    as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    
    # Overall decision
    decision: GuardrailDecision = Field(..., description="Overall guardrails decision")
    
    # Security and compliance flags
    flags: List[str] = Field(default_factory=list, description="Security and compliance flags raised")
    critical_flags: List[str] = Field(default_factory=list, description="Critical flags requiring immediate attention")
    
    # Data redactions
    redactions: List[PIIRedaction] = Field(default_factory=list, description="PII redactions performed")
    redacted_fields: List[str] = Field(default_factory=list, description="List of redacted field names")
    
    # Security events
    security_events: List[SecurityEvent] = Field(default_factory=list, description="Security events detected")
    
    # Source validation
    source_validations: List[SourceValidation] = Field(default_factory=list, description="Source validation results")
    invalid_sources: List[str] = Field(default_factory=list, description="Invalid or non-allowlisted sources")
    
    # Anti-hallucination checks
    hallucination_checks: List[AntiHallucinationCheck] = Field(default_factory=list, description="Anti-hallucination check results")
    hallucination_detected: bool = Field(False, description="Whether hallucination was detected")
    
    # RBAC/ABAC results
    access_granted: bool = Field(True, description="Whether access was granted")
    access_restrictions: List[str] = Field(default_factory=list, description="Access restrictions applied")
    user_permissions: Dict[str, bool] = Field(default_factory=dict, description="User permission evaluation results")
    
    # Processing metadata
    guardrails_version: str = Field(..., description="Guardrails engine version")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    
    # Risk assessment
    overall_risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall risk score from guardrails")
    risk_factors: Dict[str, float] = Field(default_factory=dict, description="Individual risk factor scores")
    
    @validator('decision')
    def validate_decision_consistency(cls, v, values):
        """Validate decision consistency with flags and events."""
        if 'critical_flags' in values and values['critical_flags']:
            if v not in [GuardrailDecision.BLOCK, GuardrailDecision.REQUIRE_HITL]:
                raise ValueError('Critical flags should result in BLOCK or REQUIRE_HITL decision')
        
        if 'hallucination_detected' in values and values['hallucination_detected']:
            if v == GuardrailDecision.ALLOW:
                raise ValueError('Cannot ALLOW when hallucination is detected')
        
        return v
    
    def add_security_event(self, event: SecurityEvent) -> None:
        """Add a security event to the result."""
        self.security_events.append(event)
        if event.severity in ['HIGH', 'CRITICAL']:
            self.critical_flags.append(f"SECURITY_{event.event_type}")
        self.flags.append(f"SEC_{event.event_type}")
        self._update_decision()
    
    def add_pii_redaction(self, redaction: PIIRedaction) -> None:
        """Add a PII redaction to the result."""
        self.redactions.append(redaction)
        self.redacted_fields.append(redaction.field_name)
        self.flags.append(f"PII_{redaction.pii_type}")
        self.updated_at = datetime.utcnow()
    
    def add_source_validation(self, validation: SourceValidation) -> None:
        """Add a source validation result."""
        self.source_validations.append(validation)
        if validation.validation_status == 'REJECTED':
            self.invalid_sources.append(validation.source_id)
            self.flags.append(f"INVALID_SOURCE_{validation.source_id}")
            self._update_decision()
        self.updated_at = datetime.utcnow()
    
    def add_hallucination_check(self, check: AntiHallucinationCheck) -> None:
        """Add an anti-hallucination check result."""
        self.hallucination_checks.append(check)
        if check.hallucination_detected:
            self.hallucination_detected = True
            self.critical_flags.append("HALLUCINATION_DETECTED")
            self._update_decision()
        self.updated_at = datetime.utcnow()
    
    def _update_decision(self) -> None:
        """Update overall decision based on current state."""
        # Critical flags force BLOCK or REQUIRE_HITL
        if self.critical_flags:
            self.decision = GuardrailDecision.BLOCK
            return
        
        # Hallucination detection requires HITL
        if self.hallucination_detected:
            self.decision = GuardrailDecision.REQUIRE_HITL
            return
        
        # Invalid sources require HITL
        if self.invalid_sources:
            self.decision = GuardrailDecision.REQUIRE_HITL
            return
        
        # High-severity security events require HITL
        high_severity_events = [
            event for event in self.security_events 
            if event.severity in ['HIGH', 'CRITICAL']
        ]
        if high_severity_events:
            self.decision = GuardrailDecision.REQUIRE_HITL
            return
        
        # PII redactions may require redaction decision
        if self.redactions:
            self.decision = GuardrailDecision.REDACT
            return
        
        # Default to ALLOW if no issues
        self.decision = GuardrailDecision.ALLOW
    
    def is_blocking(self) -> bool:
        """Check if guardrails are blocking the case."""
        return self.decision == GuardrailDecision.BLOCK
    
    def requires_hitl(self) -> bool:
        """Check if guardrails require human-in-the-loop review."""
        return self.decision == GuardrailDecision.REQUIRE_HITL
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical security or compliance issues."""
        return (
            len(self.critical_flags) > 0 or
            self.hallucination_detected or
            len(self.invalid_sources) > 0 or
            not self.access_granted
        )
    
    def get_risk_summary(self) -> Dict[str, any]:
        """Get a summary of risk factors and scores."""
        return {
            'overall_risk_score': self.overall_risk_score,
            'critical_flags_count': len(self.critical_flags),
            'security_events_count': len(self.security_events),
            'pii_redactions_count': len(self.redactions),
            'invalid_sources_count': len(self.invalid_sources),
            'hallucination_detected': self.hallucination_detected,
            'access_granted': self.access_granted,
            'decision': self.decision
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "decision": "ALLOW",
                "flags": ["PII_EMAIL"],
                "critical_flags": [],
                "redacted_fields": ["customer_email"],
                "invalid_sources": [],
                "hallucination_detected": False,
                "access_granted": True,
                "overall_risk_score": 0.15,
                "guardrails_version": "v1.0.0",
                "processing_time_ms": 250
            }
        }
