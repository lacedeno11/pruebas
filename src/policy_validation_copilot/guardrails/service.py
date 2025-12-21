"""
Guardrails Service.

Main service for security, governance, and compliance controls.
Based on UC-OP-10 Guardrails & Governance Enforcement.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from policy_validation_copilot.models.guardrails import (
    GuardrailDecision,
    GuardrailFlag,
    GuardrailFlagType,
    GuardrailResult,
    RedactionRecord,
)
from policy_validation_copilot.models.evidence import EvidencePack
from policy_validation_copilot.models.state import PolicyValidationState
from policy_validation_copilot.guardrails.pii_detector import PIIDetector
from policy_validation_copilot.guardrails.source_validator import SourceValidator
from policy_validation_copilot.guardrails.hallucination_checker import HallucinationChecker

logger = logging.getLogger(__name__)


class GuardrailsService:
    """
    Main guardrails enforcement service.

    Implements OWASP LLM Top 10 controls, RBAC/ABAC, PII masking,
    source allowlisting, and anti-hallucination checks.
    """

    def __init__(
        self,
        pii_masking_enabled: bool = True,
        allowlist_sources_only: bool = True,
        anti_hallucination_enabled: bool = True,
        rbac_enabled: bool = True,
    ):
        self.pii_masking_enabled = pii_masking_enabled
        self.allowlist_sources_only = allowlist_sources_only
        self.anti_hallucination_enabled = anti_hallucination_enabled
        self.rbac_enabled = rbac_enabled

        # Initialize sub-components
        self.pii_detector = PIIDetector()
        self.source_validator = SourceValidator()
        self.hallucination_checker = HallucinationChecker()

        # RBAC configuration (simplified)
        self._role_permissions = {
            "AGENT": ["view_case", "process_case", "add_note"],
            "SUPERVISOR": ["view_case", "process_case", "add_note", "approve_exception", "override_decision"],
            "AUDITOR": ["view_case", "view_audit", "export_audit"],
            "ADMIN": ["*"],
        }

    async def evaluate(
        self,
        state: PolicyValidationState,
        checkpoint: str,
        user_role: Optional[str] = None,
        required_permissions: Optional[list[str]] = None,
    ) -> GuardrailResult:
        """
        Main guardrail evaluation.

        Called at multiple checkpoints: INPUT, PROCESSING, OUTPUT, DECISION.
        """
        start_time = datetime.utcnow()
        result_id = str(uuid4())

        flags: list[GuardrailFlag] = []
        redactions: list[RedactionRecord] = []
        decision = GuardrailDecision.ALLOW

        # 1. RBAC/ABAC check
        rbac_passed = True
        if self.rbac_enabled and user_role and required_permissions:
            rbac_passed, rbac_flags = self._check_rbac(
                user_role, required_permissions
            )
            flags.extend(rbac_flags)
            if not rbac_passed:
                decision = GuardrailDecision.BLOCK

        # 2. PII detection and masking
        pii_detected = False
        pii_masked = False
        if self.pii_masking_enabled and state.case:
            pii_detected, pii_masked, pii_flags, pii_redactions = await self._process_pii(state)
            flags.extend(pii_flags)
            redactions.extend(pii_redactions)
            if pii_detected and not pii_masked:
                decision = GuardrailDecision.REDACT

        # 3. Source validation
        sources_validated = True
        non_allowlisted: list[str] = []
        if self.allowlist_sources_only and state.evidence_pack:
            sources_validated, non_allowlisted, source_flags = self._validate_sources(
                state.evidence_pack
            )
            flags.extend(source_flags)
            if not sources_validated and checkpoint == "OUTPUT":
                decision = GuardrailDecision.REQUIRE_HITL

        # 4. Hallucination check
        hallucination_passed = True
        unanchored_claims: list[str] = []
        if (
            self.anti_hallucination_enabled
            and state.evidence_pack
            and state.decision
            and checkpoint == "OUTPUT"
        ):
            hallucination_passed, unanchored_claims, halluc_flags = self._check_hallucination(
                state.decision.explanation_summary, state.evidence_pack
            )
            flags.extend(halluc_flags)
            if not hallucination_passed:
                decision = GuardrailDecision.REQUIRE_HITL

        # 5. Injection/jailbreak detection (for LLM inputs)
        injection_flags = self._detect_injection(state)
        flags.extend(injection_flags)
        if any(f.severity == "CRITICAL" for f in injection_flags):
            decision = GuardrailDecision.BLOCK

        # Count severity
        critical_count = sum(1 for f in flags if f.severity == "CRITICAL")
        high_count = sum(1 for f in flags if f.severity == "HIGH")

        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return GuardrailResult(
            result_id=result_id,
            case_id=state.case.case_id if state.case else "",
            checkpoint=checkpoint,
            decision=decision,
            flags=flags,
            critical_flags_count=critical_count,
            high_flags_count=high_count,
            redactions=redactions,
            pii_detected=pii_detected,
            pii_masked=pii_masked,
            rbac_passed=rbac_passed,
            user_role=user_role,
            required_permissions=required_permissions or [],
            sources_validated=sources_validated,
            non_allowlisted_sources=non_allowlisted,
            hallucination_check_passed=hallucination_passed,
            unanchored_claims=unanchored_claims,
            evaluation_duration_ms=duration,
        )

    def _check_rbac(
        self,
        user_role: str,
        required_permissions: list[str],
    ) -> tuple[bool, list[GuardrailFlag]]:
        """Check RBAC permissions."""
        flags = []
        role_perms = self._role_permissions.get(user_role, [])

        # Admin has all permissions
        if "*" in role_perms:
            return True, []

        missing = [p for p in required_permissions if p not in role_perms]

        if missing:
            flags.append(
                GuardrailFlag(
                    flag_id=str(uuid4()),
                    flag_type=GuardrailFlagType.RBAC_VIOLATION,
                    severity="HIGH",
                    description=f"Missing permissions: {', '.join(missing)}",
                    source_context=f"role={user_role}",
                    remediation_action="Request elevated permissions or escalate",
                )
            )
            return False, flags

        return True, []

    async def _process_pii(
        self,
        state: PolicyValidationState,
    ) -> tuple[bool, bool, list[GuardrailFlag], list[RedactionRecord]]:
        """Process PII detection and masking."""
        flags = []
        all_redactions: list[RedactionRecord] = []
        pii_detected = False
        pii_masked = False

        # Check case data
        if state.case:
            # Check service description
            if state.case.service_description:
                if self.pii_detector.contains_pii(state.case.service_description):
                    pii_detected = True
                    _, redactions = self.pii_detector.mask(state.case.service_description)
                    all_redactions.extend(redactions)
                    pii_masked = True

        if pii_detected:
            flags.append(
                GuardrailFlag(
                    flag_id=str(uuid4()),
                    flag_type=GuardrailFlagType.PII_DETECTED,
                    severity="MEDIUM",
                    description="PII detected in case data",
                    auto_remediated=pii_masked,
                )
            )

        return pii_detected, pii_masked, flags, all_redactions

    def _validate_sources(
        self,
        evidence_pack: EvidencePack,
    ) -> tuple[bool, list[str], list[GuardrailFlag]]:
        """Validate evidence sources."""
        flags = []
        is_valid, report = self.source_validator.validate_pack(evidence_pack)
        non_allowlisted = report.get("non_allowlisted", [])

        if non_allowlisted:
            flags.append(
                GuardrailFlag(
                    flag_id=str(uuid4()),
                    flag_type=GuardrailFlagType.SOURCE_NOT_ALLOWLISTED,
                    severity="HIGH",
                    description=f"Non-allowlisted sources: {', '.join(non_allowlisted)}",
                    remediation_action="Use only approved policy documents",
                )
            )

        return is_valid, non_allowlisted, flags

    def _check_hallucination(
        self,
        explanation: str,
        evidence_pack: EvidencePack,
    ) -> tuple[bool, list[str], list[GuardrailFlag]]:
        """Check for hallucinated claims."""
        flags = []
        is_valid, report = self.hallucination_checker.validate_decision_explanation(
            explanation, evidence_pack
        )

        unanchored = [c["claim"] for c in report.get("unanchored_claims", [])]

        if unanchored:
            flags.append(
                GuardrailFlag(
                    flag_id=str(uuid4()),
                    flag_type=GuardrailFlagType.HALLUCINATION_RISK,
                    severity="HIGH",
                    description=f"Found {len(unanchored)} unanchored claims",
                    remediation_action="Verify claims against evidence or remove",
                )
            )

        return is_valid, unanchored, flags

    def _detect_injection(
        self,
        state: PolicyValidationState,
    ) -> list[GuardrailFlag]:
        """Detect prompt injection or jailbreak attempts."""
        flags = []

        # Patterns indicating injection attempts
        injection_patterns = [
            r"ignore\s+(previous|all)\s+instructions",
            r"disregard\s+(the\s+)?rules",
            r"you\s+are\s+now\s+a",
            r"pretend\s+to\s+be",
            r"bypass\s+(security|restrictions)",
            r"<\s*script\s*>",
            r"\{\{\s*.*\s*\}\}",  # Template injection
        ]

        import re
        text_to_check = ""
        if state.case and state.case.service_description:
            text_to_check += state.case.service_description + " "

        for pattern in injection_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                flags.append(
                    GuardrailFlag(
                        flag_id=str(uuid4()),
                        flag_type=GuardrailFlagType.PROMPT_INJECTION,
                        severity="CRITICAL",
                        description="Potential prompt injection detected",
                        source_context=pattern,
                        remediation_action="Block input and log security event",
                    )
                )
                break

        return flags
