"""
Guardrails data models.

Represents security, governance, and compliance controls.
Based on UC-OP-10 Guardrails & Governance Enforcement.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GuardrailDecision(str, Enum):
    """Guardrail evaluation decision."""

    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


class GuardrailFlagType(str, Enum):
    """Types of guardrail flags/violations."""

    # OWASP LLM Top 10 related
    PROMPT_INJECTION = "PROMPT_INJECTION"
    JAILBREAK_ATTEMPT = "JAILBREAK_ATTEMPT"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    INSECURE_OUTPUT = "INSECURE_OUTPUT"

    # Data protection
    PII_DETECTED = "PII_DETECTED"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"

    # Source validation
    SOURCE_NOT_ALLOWLISTED = "SOURCE_NOT_ALLOWLISTED"
    UNVERIFIED_CLAIM = "UNVERIFIED_CLAIM"
    HALLUCINATION_RISK = "HALLUCINATION_RISK"

    # Policy violations
    RBAC_VIOLATION = "RBAC_VIOLATION"
    ABAC_VIOLATION = "ABAC_VIOLATION"
    POLICY_CONFLICT = "POLICY_CONFLICT"


class GuardrailFlag(BaseModel):
    """Individual guardrail violation or warning."""

    flag_id: str = Field(..., description="Unique flag identifier")
    flag_type: GuardrailFlagType = Field(..., description="Type of violation")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    description: str = Field(..., description="Human-readable description")
    source_context: Optional[str] = Field(None, description="Where violation was detected")
    remediation_action: Optional[str] = Field(None, description="Suggested fix")
    auto_remediated: bool = Field(default=False, description="Was it auto-fixed (e.g., PII masked)")


class RedactionRecord(BaseModel):
    """Record of data redaction/masking applied."""

    field_path: str = Field(..., description="JSON path of redacted field")
    original_type: str = Field(..., description="Type of data: EMAIL, PHONE, SSN, etc.")
    redaction_method: str = Field(..., description="Method: MASK, HASH, REMOVE")
    redacted_value: Optional[str] = Field(None, description="Masked representation")


class GuardrailResult(BaseModel):
    """
    Complete guardrail evaluation result.

    Applied at multiple checkpoints: input, processing, output.
    """

    result_id: str = Field(..., description="Evaluation result identifier")
    case_id: str = Field(..., description="Associated case identifier")
    checkpoint: str = Field(..., description="Checkpoint: INPUT, PROCESSING, OUTPUT, DECISION")

    # Primary decision
    decision: GuardrailDecision = Field(..., description="Overall guardrail decision")

    # Flags raised
    flags: list[GuardrailFlag] = Field(default_factory=list)
    critical_flags_count: int = Field(default=0)
    high_flags_count: int = Field(default=0)

    # Redactions applied
    redactions: list[RedactionRecord] = Field(default_factory=list)
    pii_detected: bool = Field(default=False)
    pii_masked: bool = Field(default=False)

    # RBAC/ABAC evaluation
    rbac_passed: bool = Field(default=True)
    user_role: Optional[str] = Field(None)
    required_permissions: list[str] = Field(default_factory=list)

    # Source validation
    sources_validated: bool = Field(default=True)
    non_allowlisted_sources: list[str] = Field(default_factory=list)

    # Anti-hallucination check
    hallucination_check_passed: bool = Field(default=True)
    unanchored_claims: list[str] = Field(default_factory=list)

    # Output payload (potentially redacted)
    redacted_payload: Optional[dict] = Field(None, description="Payload after redactions")

    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_duration_ms: Optional[int] = Field(None)
    guardrail_version: str = Field(default="1.0.0")

    def requires_human_review(self) -> bool:
        """Check if guardrails require HITL escalation."""
        return (
            self.decision == GuardrailDecision.REQUIRE_HITL
            or self.critical_flags_count > 0
            or not self.rbac_passed
            or not self.hallucination_check_passed
        )

    def can_proceed(self) -> bool:
        """Check if processing can continue."""
        return self.decision in (GuardrailDecision.ALLOW, GuardrailDecision.REDACT)
