"""
Guardrails & Governance Enforcement Service for Policy Validation Copilot

This module implements UC-OP-10 with comprehensive security controls including
OWASP LLM Top 10 protections, RBAC/ABAC authorization, PII detection/masking,
and anti-hallucination evidence anchoring.
"""

import hashlib
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel

from ..models.base import GuardrailDecision
from ..models.guardrails import (
    AntiHallucinationCheck, GuardrailsResult, PIIRedaction, SecurityEvent,
    SourceValidation
)
from ..models.state import PolicyValidationState

logger = logging.getLogger(__name__)


class GuardrailsConfig(BaseModel):
    """Configuration for guardrails enforcement."""
    
    # OWASP LLM Top 10 Controls
    enable_prompt_injection_detection: bool = True
    enable_insecure_output_handling: bool = True
    enable_training_data_poisoning_detection: bool = True
    enable_model_denial_of_service_protection: bool = True
    enable_supply_chain_vulnerabilities_check: bool = True
    enable_sensitive_information_disclosure_prevention: bool = True
    enable_insecure_plugin_design_validation: bool = True
    enable_excessive_agency_control: bool = True
    enable_overreliance_prevention: bool = True
    enable_model_theft_protection: bool = True
    
    # PII Detection and Masking
    enable_pii_detection: bool = True
    pii_patterns: Dict[str, str] = {
        'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
        'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'PHONE': r'\b\d{3}-\d{3}-\d{4}\b',
        'CREDIT_CARD': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'PASSPORT': r'\b[A-Z]{1,2}\d{6,9}\b',
        'DRIVER_LICENSE': r'\b[A-Z]{1,2}\d{6,8}\b'
    }
    pii_masking_char: str = '*'
    
    # Source Validation
    enable_allowlist_validation: bool = True
    allowed_sources: Set[str] = {
        'policy_documents_v2.1',
        'medical_guidelines_v1.3',
        'regulatory_framework_v3.0',
        'approved_procedures_v2.0'
    }
    
    # Anti-Hallucination Controls
    enable_evidence_anchoring: bool = True
    min_evidence_anchor_score: float = 0.7
    max_hallucination_risk: float = 0.3
    
    # RBAC/ABAC Settings
    enable_access_control: bool = True
    default_permissions: Dict[str, bool] = {
        'read_case': True,
        'write_case': False,
        'approve_case': False,
        'export_audit': False,
        'admin_access': False
    }
    
    # Security Event Logging
    enable_security_logging: bool = True
    log_all_events: bool = True
    alert_on_critical_events: bool = True
    
    # Rate Limiting and DoS Protection
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 100
    max_concurrent_requests: int = 10
    
    # Content Filtering
    enable_content_filtering: bool = True
    blocked_patterns: List[str] = [
        r'<script.*?>.*?</script>',  # XSS prevention
        r'javascript:',              # JavaScript injection
        r'data:text/html',          # Data URI attacks
        r'vbscript:',               # VBScript injection
    ]


class OWASPLLMControls:
    """Implementation of OWASP LLM Top 10 security controls."""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'forget\s+everything\s+above',
            r'system\s*:\s*you\s+are',
            r'act\s+as\s+if\s+you\s+are',
            r'pretend\s+to\s+be',
            r'roleplay\s+as',
            r'\\n\\n.*system.*\\n\\n',
            r'<\|im_start\|>',
            r'<\|im_end\|>',
        ]
    
    def detect_prompt_injection(self, content: str) -> Tuple[bool, List[str]]:
        """LLM01: Detect prompt injection attempts."""
        if not self.config.enable_prompt_injection_detection:
            return False, []
        
        detected_patterns = []
        content_lower = content.lower()
        
        for pattern in self.injection_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected_patterns.append(pattern)
        
        # Check for suspicious instruction patterns
        suspicious_phrases = [
            'ignore all previous instructions',
            'disregard the above',
            'forget what i told you',
            'new instructions:',
            'system override',
            'admin mode',
            'developer mode'
        ]
        
        for phrase in suspicious_phrases:
            if phrase in content_lower:
                detected_patterns.append(phrase)
        
        return len(detected_patterns) > 0, detected_patterns
    
    def validate_output_handling(self, output: str) -> Tuple[bool, List[str]]:
        """LLM02: Validate insecure output handling."""
        if not self.config.enable_insecure_output_handling:
            return True, []
        
        issues = []
        
        # Check for potential XSS in output
        xss_patterns = [
            r'<script.*?>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe.*?>',
            r'<object.*?>',
            r'<embed.*?>'
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Potential XSS pattern detected: {pattern}")
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*\s+set',
            r'exec\s*\(',
            r'sp_executesql'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Potential SQL injection pattern detected: {pattern}")
        
        return len(issues) == 0, issues
    
    def check_training_data_poisoning(self, content: str) -> Tuple[bool, List[str]]:
        """LLM03: Check for training data poisoning indicators."""
        if not self.config.enable_training_data_poisoning_detection:
            return False, []
        
        poisoning_indicators = []
        
        # Check for unusual patterns that might indicate poisoned training data
        suspicious_patterns = [
            r'this\s+is\s+a\s+test\s+of\s+the\s+emergency',
            r'canary\s+token',
            r'honeypot\s+data',
            r'synthetic\s+training\s+example',
            r'backdoor\s+trigger'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                poisoning_indicators.append(pattern)
        
        return len(poisoning_indicators) > 0, poisoning_indicators
    
    def check_dos_protection(self, request_size: int, complexity_score: float) -> Tuple[bool, str]:
        """LLM04: Model Denial of Service protection."""
        if not self.config.enable_model_denial_of_service_protection:
            return True, ""
        
        # Check request size limits
        max_request_size = 1024 * 1024  # 1MB
        if request_size > max_request_size:
            return False, f"Request size {request_size} exceeds limit {max_request_size}"
        
        # Check complexity score
        max_complexity = 0.9
        if complexity_score > max_complexity:
            return False, f"Request complexity {complexity_score} exceeds limit {max_complexity}"
        
        return True, ""
    
    def validate_supply_chain(self, component: str, version: str) -> Tuple[bool, str]:
        """LLM05: Supply Chain Vulnerabilities check."""
        if not self.config.enable_supply_chain_vulnerabilities_check:
            return True, ""
        
        # Check against known vulnerable versions
        vulnerable_components = {
            'transformers': ['4.20.0', '4.20.1'],
            'torch': ['1.12.0'],
            'tensorflow': ['2.9.0', '2.9.1']
        }
        
        if component in vulnerable_components:
            if version in vulnerable_components[component]:
                return False, f"Vulnerable version {version} of {component} detected"
        
        return True, ""
    
    def prevent_sensitive_disclosure(self, content: str) -> Tuple[bool, List[str]]:
        """LLM06: Sensitive Information Disclosure prevention."""
        if not self.config.enable_sensitive_information_disclosure_prevention:
            return False, []
        
        sensitive_patterns = []
        
        # Check for API keys, tokens, passwords
        secret_patterns = [
            r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}',
            r'secret[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}',
            r'password\s*[:=]\s*["\']?[a-zA-Z0-9]{8,}',
            r'token\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}',
            r'bearer\s+[a-zA-Z0-9]{20,}',
            r'sk-[a-zA-Z0-9]{48}'  # OpenAI API key pattern
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                sensitive_patterns.append(pattern)
        
        return len(sensitive_patterns) > 0, sensitive_patterns
    
    def validate_plugin_design(self, plugin_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """LLM07: Insecure Plugin Design validation."""
        if not self.config.enable_insecure_plugin_design_validation:
            return True, []
        
        issues = []
        
        # Check for required security fields
        required_fields = ['name', 'version', 'permissions', 'signature']
        for field in required_fields:
            if field not in plugin_config:
                issues.append(f"Missing required field: {field}")
        
        # Validate permissions
        if 'permissions' in plugin_config:
            dangerous_permissions = ['file_system_access', 'network_access', 'system_commands']
            for perm in dangerous_permissions:
                if perm in plugin_config['permissions']:
                    issues.append(f"Dangerous permission detected: {perm}")
        
        return len(issues) == 0, issues
    
    def control_excessive_agency(self, action_count: int, risk_score: float) -> Tuple[bool, str]:
        """LLM08: Excessive Agency control."""
        if not self.config.enable_excessive_agency_control:
            return True, ""
        
        max_actions = 10
        max_risk = 0.7
        
        if action_count > max_actions:
            return False, f"Action count {action_count} exceeds limit {max_actions}"
        
        if risk_score > max_risk:
            return False, f"Risk score {risk_score} exceeds limit {max_risk}"
        
        return True, ""
    
    def prevent_overreliance(self, confidence_score: float, evidence_count: int) -> Tuple[bool, str]:
        """LLM09: Overreliance prevention."""
        if not self.config.enable_overreliance_prevention:
            return True, ""
        
        min_evidence = 2
        min_confidence = 0.6
        
        if evidence_count < min_evidence:
            return False, f"Insufficient evidence: {evidence_count} < {min_evidence}"
        
        if confidence_score < min_confidence:
            return False, f"Low confidence: {confidence_score} < {min_confidence}"
        
        return True, ""
    
    def protect_model_theft(self, query_pattern: str, frequency: int) -> Tuple[bool, str]:
        """LLM10: Model Theft protection."""
        if not self.config.enable_model_theft_protection:
            return True, ""
        
        # Check for extraction attempts
        extraction_patterns = [
            r'what\s+are\s+your\s+weights',
            r'show\s+me\s+your\s+parameters',
            r'export\s+your\s+model',
            r'dump\s+your\s+training\s+data',
            r'reverse\s+engineer'
        ]
        
        for pattern in extraction_patterns:
            if re.search(pattern, query_pattern, re.IGNORECASE):
                return False, f"Model extraction attempt detected: {pattern}"
        
        # Check query frequency for potential scraping
        max_frequency = 100
        if frequency > max_frequency:
            return False, f"High query frequency detected: {frequency} > {max_frequency}"
        
        return True, ""


class PIIDetector:
    """PII detection and masking service."""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.compiled_patterns = {
            pii_type: re.compile(pattern, re.IGNORECASE)
            for pii_type, pattern in config.pii_patterns.items()
        }
    
    def detect_and_mask_pii(self, content: str, field_name: str) -> Tuple[str, List[PIIRedaction]]:
        """Detect and mask PII in content."""
        if not self.config.enable_pii_detection:
            return content, []
        
        redactions = []
        masked_content = content
        
        for pii_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(content)
            
            for match in matches:
                original_value = match.group()
                original_hash = hashlib.sha256(original_value.encode()).hexdigest()
                
                # Create masked value
                if pii_type == 'EMAIL':
                    # Preserve domain for emails
                    parts = original_value.split('@')
                    if len(parts) == 2:
                        masked_value = f"{self.config.pii_masking_char * len(parts[0])}@{parts[1]}"
                    else:
                        masked_value = self.config.pii_masking_char * len(original_value)
                elif pii_type in ['SSN', 'CREDIT_CARD']:
                    # Show last 4 digits
                    masked_value = self.config.pii_masking_char * (len(original_value) - 4) + original_value[-4:]
                else:
                    # Full masking
                    masked_value = self.config.pii_masking_char * len(original_value)
                
                # Replace in content
                masked_content = masked_content.replace(original_value, masked_value)
                
                # Create redaction record
                redaction = PIIRedaction(
                    field_name=field_name,
                    pii_type=pii_type,
                    original_value_hash=original_hash,
                    redacted_value=masked_value,
                    detection_method="regex_pattern",
                    confidence_score=0.9,
                    redaction_method="character_masking",
                    redaction_pattern=f"mask_with_{self.config.pii_masking_char}",
                    regulation_basis=["GDPR", "HIPAA", "CCPA"],
                    retention_policy="7_years"
                )
                redactions.append(redaction)
        
        return masked_content, redactions


class SourceValidator:
    """Source validation against allowlists."""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
    
    def validate_source(self, source_id: str, source_type: str, source_version: str = None) -> SourceValidation:
        """Validate source against allowlist."""
        if not self.config.enable_allowlist_validation:
            return SourceValidation(
                source_id=source_id,
                source_type=source_type,
                validation_status="APPROVED",
                allowlist_name="disabled",
                allowlist_version="N/A",
                in_allowlist=True,
                validated_by="SYSTEM"
            )
        
        # Check if source is in allowlist
        in_allowlist = source_id in self.config.allowed_sources
        
        validation_status = "APPROVED" if in_allowlist else "REJECTED"
        validation_errors = [] if in_allowlist else [f"Source {source_id} not in allowlist"]
        
        return SourceValidation(
            source_id=source_id,
            source_type=source_type,
            validation_status=validation_status,
            allowlist_name="default_allowlist",
            allowlist_version="v1.0",
            in_allowlist=in_allowlist,
            source_version=source_version,
            validation_rules=["allowlist_check"],
            validation_errors=validation_errors,
            validated_by="SYSTEM"
        )


class AntiHallucinationService:
    """Anti-hallucination evidence anchoring service."""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
    
    def check_evidence_anchoring(
        self,
        content: str,
        evidence_references: List[UUID],
        content_type: str = "DECISION"
    ) -> AntiHallucinationCheck:
        """Check if content is properly anchored to evidence."""
        if not self.config.enable_evidence_anchoring:
            return AntiHallucinationCheck(
                content_id=str(uuid4()),
                content_type=content_type,
                evidence_references=evidence_references,
                anchor_score=1.0,
                hallucination_risk=0.0,
                verification_methods=["disabled"],
                is_anchored=True,
                hallucination_detected=False,
                verification_passed=True,
                checked_by="SYSTEM"
            )
        
        # Calculate anchor score based on evidence references
        anchor_score = min(1.0, len(evidence_references) * 0.3)
        
        # Calculate hallucination risk
        hallucination_risk = max(0.0, 1.0 - anchor_score)
        
        # Check for hallucination indicators
        hallucination_patterns = [
            r'i\s+think\s+that',
            r'it\s+seems\s+like',
            r'probably',
            r'might\s+be',
            r'could\s+be',
            r'appears\s+to\s+be',
            r'based\s+on\s+my\s+understanding'
        ]
        
        hallucination_detected = False
        for pattern in hallucination_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                hallucination_detected = True
                hallucination_risk = min(1.0, hallucination_risk + 0.2)
                break
        
        # Determine if content is properly anchored
        is_anchored = (
            anchor_score >= self.config.min_evidence_anchor_score and
            hallucination_risk <= self.config.max_hallucination_risk
        )
        
        verification_passed = is_anchored and not hallucination_detected
        
        return AntiHallucinationCheck(
            content_id=str(uuid4()),
            content_type=content_type,
            evidence_references=evidence_references,
            anchor_score=anchor_score,
            hallucination_risk=hallucination_risk,
            verification_methods=["evidence_count", "pattern_detection"],
            cross_references=[str(ref) for ref in evidence_references],
            is_anchored=is_anchored,
            hallucination_detected=hallucination_detected,
            verification_passed=verification_passed,
            checked_by="ANTI_HALLUCINATION_SERVICE"
        )


class RBACService:
    """Role-Based Access Control service."""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.role_permissions = {
            'agent': {
                'read_case': True,
                'write_case': True,
                'approve_case': False,
                'export_audit': False,
                'admin_access': False
            },
            'supervisor': {
                'read_case': True,
                'write_case': True,
                'approve_case': True,
                'export_audit': True,
                'admin_access': False
            },
            'admin': {
                'read_case': True,
                'write_case': True,
                'approve_case': True,
                'export_audit': True,
                'admin_access': True
            }
        }
    
    def check_permissions(self, user_role: str, required_permissions: List[str]) -> Tuple[bool, List[str]]:
        """Check if user role has required permissions."""
        if not self.config.enable_access_control:
            return True, []
        
        user_permissions = self.role_permissions.get(user_role, self.config.default_permissions)
        missing_permissions = []
        
        for permission in required_permissions:
            if not user_permissions.get(permission, False):
                missing_permissions.append(permission)
        
        access_granted = len(missing_permissions) == 0
        return access_granted, missing_permissions


class GuardrailsService:
    """Main guardrails enforcement service implementing UC-OP-10."""
    
    def __init__(self, config: GuardrailsConfig = None):
        self.config = config or GuardrailsConfig()
        self.owasp_controls = OWASPLLMControls(self.config)
        self.pii_detector = PIIDetector(self.config)
        self.source_validator = SourceValidator(self.config)
        self.anti_hallucination = AntiHallucinationService(self.config)
        self.rbac_service = RBACService(self.config)
        
        # Request tracking for rate limiting
        self.request_counts: Dict[str, int] = {}
        self.last_reset = datetime.utcnow()
    
    def enforce_guardrails(
        self,
        state: PolicyValidationState,
        user_role: str = "agent",
        user_id: str = "system"
    ) -> GuardrailsResult:
        """Main guardrails enforcement method."""
        logger.info(f"Enforcing guardrails for case {state.case.case_id}")
        
        result = GuardrailsResult(
            case_id=state.case.case_id,
            decision=GuardrailDecision.ALLOW,
            guardrails_version="1.0.0",
            processing_time_ms=0
        )
        
        start_time = datetime.utcnow()
        
        try:
            # 1. RBAC/ABAC Access Control
            self._check_access_control(result, user_role, user_id)
            
            # 2. Rate Limiting and DoS Protection
            self._check_rate_limiting(result, user_id)
            
            # 3. OWASP LLM Top 10 Controls
            self._apply_owasp_controls(result, state)
            
            # 4. PII Detection and Masking
            self._detect_and_mask_pii(result, state)
            
            # 5. Source Validation
            self._validate_sources(result, state)
            
            # 6. Anti-Hallucination Checks
            self._check_anti_hallucination(result, state)
            
            # 7. Content Filtering
            self._apply_content_filtering(result, state)
            
            # 8. Final Decision Logic
            self._make_final_decision(result)
            
        except Exception as e:
            logger.error(f"Error in guardrails enforcement: {e}")
            self._add_security_event(
                result,
                "SYSTEM_ERROR",
                "CRITICAL",
                f"Guardrails enforcement failed: {e}",
                "GUARDRAILS_SERVICE"
            )
            result.decision = GuardrailDecision.BLOCK
        
        # Calculate processing time
        end_time = datetime.utcnow()
        result.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"Guardrails enforcement completed: {result.decision}")
        return result
    
    def _check_access_control(self, result: GuardrailsResult, user_role: str, user_id: str) -> None:
        """Check RBAC/ABAC access control."""
        required_permissions = ['read_case', 'write_case']
        access_granted, missing_permissions = self.rbac_service.check_permissions(user_role, required_permissions)
        
        result.access_granted = access_granted
        
        if not access_granted:
            result.access_restrictions = missing_permissions
            result.critical_flags.append("ACCESS_DENIED")
            self._add_security_event(
                result,
                "ACCESS_CONTROL_VIOLATION",
                "HIGH",
                f"User {user_id} with role {user_role} lacks permissions: {missing_permissions}",
                "RBAC_SERVICE"
            )
    
    def _check_rate_limiting(self, result: GuardrailsResult, user_id: str) -> None:
        """Check rate limiting and DoS protection."""
        if not self.config.enable_rate_limiting:
            return
        
        current_time = datetime.utcnow()
        
        # Reset counters every minute
        if (current_time - self.last_reset).total_seconds() > 60:
            self.request_counts.clear()
            self.last_reset = current_time
        
        # Check request count
        user_requests = self.request_counts.get(user_id, 0)
        if user_requests >= self.config.max_requests_per_minute:
            result.critical_flags.append("RATE_LIMIT_EXCEEDED")
            self._add_security_event(
                result,
                "RATE_LIMIT_VIOLATION",
                "HIGH",
                f"User {user_id} exceeded rate limit: {user_requests}/{self.config.max_requests_per_minute}",
                "RATE_LIMITER"
            )
        
        # Increment counter
        self.request_counts[user_id] = user_requests + 1
    
    def _apply_owasp_controls(self, result: GuardrailsResult, state: PolicyValidationState) -> None:
        """Apply OWASP LLM Top 10 controls."""
        # Check case content for prompt injection
        case_content = f"{state.case.service} {state.case.additional_data or ''}"
        
        injection_detected, patterns = self.owasp_controls.detect_prompt_injection(case_content)
        if injection_detected:
            result.critical_flags.append("PROMPT_INJECTION")
            self._add_security_event(
                result,
                "PROMPT_INJECTION_ATTEMPT",
                "CRITICAL",
                f"Prompt injection patterns detected: {patterns}",
                "OWASP_LLM01"
            )
        
        # Check for sensitive information disclosure
        sensitive_detected, patterns = self.owasp_controls.prevent_sensitive_disclosure(case_content)
        if sensitive_detected:
            result.critical_flags.append("SENSITIVE_INFO_DISCLOSURE")
            self._add_security_event(
                result,
                "SENSITIVE_INFO_DETECTED",
                "HIGH",
                f"Sensitive information patterns detected: {patterns}",
                "OWASP_LLM06"
            )
        
        # DoS protection check
        request_size = len(case_content.encode('utf-8'))
        complexity_score = min(1.0, request_size / 10000)  # Simple complexity metric
        
        dos_safe, dos_message = self.owasp_controls.check_dos_protection(request_size, complexity_score)
        if not dos_safe:
            result.critical_flags.append("DOS_PROTECTION")
            self._add_security_event(
                result,
                "DOS_PROTECTION_TRIGGERED",
                "HIGH",
                dos_message,
                "OWASP_LLM04"
            )
    
    def _detect_and_mask_pii(self, result: GuardrailsResult, state: PolicyValidationState) -> None:
        """Detect and mask PII in case data."""
        # Check case service field
        masked_service, service_redactions = self.pii_detector.detect_and_mask_pii(
            state.case.service, "service"
        )
        
        if service_redactions:
            result.add_pii_redaction(service_redactions[0])
            # Update the case service with masked version
            state.case.service = masked_service
        
        # Check additional data if present
        if state.case.additional_data:
            additional_data_str = str(state.case.additional_data)
            masked_data, data_redactions = self.pii_detector.detect_and_mask_pii(
                additional_data_str, "additional_data"
            )
            
            for redaction in data_redactions:
                result.add_pii_redaction(redaction)
    
    def _validate_sources(self, result: GuardrailsResult, state: PolicyValidationState) -> None:
        """Validate sources against allowlists."""
        if state.evidence_pack:
            for evidence_item in state.evidence_pack.items:
                validation = self.source_validator.validate_source(
                    evidence_item.doc_id,
                    "DOCUMENT",
                    evidence_item.doc_version
                )
                result.add_source_validation(validation)
    
    def _check_anti_hallucination(self, result: GuardrailsResult, state: PolicyValidationState) -> None:
        """Check for hallucination in generated content."""
        if state.decision and state.decision.rationale:
            evidence_refs = []
            if state.evidence_pack:
                evidence_refs = [item.id for item in state.evidence_pack.items]
            
            rationale_text = str(state.decision.rationale.primary_reason)
            
            hallucination_check = self.anti_hallucination.check_evidence_anchoring(
                rationale_text,
                evidence_refs,
                "DECISION_RATIONALE"
            )
            
            result.add_hallucination_check(hallucination_check)
    
    def _apply_content_filtering(self, result: GuardrailsResult, state: PolicyValidationState) -> None:
        """Apply content filtering for malicious patterns."""
        if not self.config.enable_content_filtering:
            return
        
        content_to_check = f"{state.case.service} {state.case.additional_data or ''}"
        
        for pattern in self.config.blocked_patterns:
            if re.search(pattern, content_to_check, re.IGNORECASE):
                result.flags.append(f"BLOCKED_PATTERN_{pattern[:20]}")
                self._add_security_event(
                    result,
                    "CONTENT_FILTER_VIOLATION",
                    "MEDIUM",
                    f"Blocked pattern detected: {pattern}",
                    "CONTENT_FILTER"
                )
    
    def _make_final_decision(self, result: GuardrailsResult) -> None:
        """Make final guardrails decision based on all checks."""
        # Critical flags always block
        if result.critical_flags:
            result.decision = GuardrailDecision.BLOCK
            return
        
        # Hallucination detection requires HITL
        if result.hallucination_detected:
            result.decision = GuardrailDecision.REQUIRE_HITL
            return
        
        # Invalid sources require HITL
        if result.invalid_sources:
            result.decision = GuardrailDecision.REQUIRE_HITL
            return
        
        # PII redactions may require redaction decision
        if result.redactions:
            result.decision = GuardrailDecision.REDACT
            return
        
        # Access denied blocks
        if not result.access_granted:
            result.decision = GuardrailDecision.BLOCK
            return
        
        # Default to allow if no issues
        result.decision = GuardrailDecision.ALLOW
    
    def _add_security_event(
        self,
        result: GuardrailsResult,
        event_type: str,
        severity: str,
        description: str,
        source_component: str
    ) -> None:
        """Add a security event to the result."""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            source_component=source_component,
            detection_rule=f"{source_component}_{event_type}",
            confidence_score=0.9,
            action_taken="LOGGED",
            blocked=(severity in ["HIGH", "CRITICAL"]),
            escalated=(severity == "CRITICAL")
        )
        
        result.add_security_event(event)
        
        if self.config.enable_security_logging:
            logger.warning(f"Security event: {event_type} - {description}")
    
    def get_guardrails_status(self) -> Dict[str, Any]:
        """Get current guardrails service status."""
        return {
            'service_name': 'GuardrailsService',
            'version': '1.0.0',
            'config': {
                'owasp_controls_enabled': True,
                'pii_detection_enabled': self.config.enable_pii_detection,
                'source_validation_enabled': self.config.enable_allowlist_validation,
                'anti_hallucination_enabled': self.config.enable_evidence_anchoring,
                'access_control_enabled': self.config.enable_access_control,
                'rate_limiting_enabled': self.config.enable_rate_limiting
            },
            'request_counts': dict(self.request_counts),
            'last_reset': self.last_reset.isoformat()
        }


# Factory function for easy instantiation
def create_guardrails_service(config: GuardrailsConfig = None) -> GuardrailsService:
    """Create a guardrails service instance."""
    return GuardrailsService(config)
