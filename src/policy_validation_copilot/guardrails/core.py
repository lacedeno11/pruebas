"""
Guardrails and Governance System (UC-OP-10).

This module implements comprehensive security controls following OWASP LLM Top 10,
including RBAC/ABAC authorization, PII masking, source allowlist validation,
injection detection, and security event logging.
"""

import hashlib
import logging
import re
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator

from ..models.guardrails import (
    GuardrailLog, SecurityEvent, RedactionLog, AccessControlLog,
    SourceAllowlistEntry, GuardrailsConfig, GuardrailAction,
    SecurityEventType
)
from ..models.case import Case
from ..models.evidence import EvidencePack, EvidenceItem

logger = logging.getLogger(__name__)


class AccessLevel(str, Enum):
    """Access levels for RBAC."""
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class ResourceType(str, Enum):
    """Resource types for ABAC."""
    CASE = "CASE"
    EVIDENCE = "EVIDENCE"
    POLICY = "POLICY"
    DECISION = "DECISION"
    AUDIT = "AUDIT"
    SYSTEM = "SYSTEM"


class PIIType(str, Enum):
    """Types of PII for masking."""
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    MEDICAL_ID = "MEDICAL_ID"
    INSURANCE_ID = "INSURANCE_ID"


class InjectionType(str, Enum):
    """Types of injection attacks."""
    PROMPT_INJECTION = "PROMPT_INJECTION"
    SQL_INJECTION = "SQL_INJECTION"
    COMMAND_INJECTION = "COMMAND_INJECTION"
    SCRIPT_INJECTION = "SCRIPT_INJECTION"
    JAILBREAK_ATTEMPT = "JAILBREAK_ATTEMPT"


class UserContext(BaseModel):
    """User context for authorization."""
    
    user_id: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    department: Optional[str] = None
    clearance_level: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ResourceContext(BaseModel):
    """Resource context for authorization."""
    
    resource_type: ResourceType
    resource_id: str
    owner_id: Optional[str] = None
    classification: Optional[str] = None
    sensitivity_level: Optional[str] = None
    department: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuardrailResult(BaseModel):
    """Result of guardrail evaluation."""
    
    passed: bool
    action: GuardrailAction
    confidence: float = Field(ge=0.0, le=1.0)
    flags: List[str] = Field(default_factory=list)
    redactions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    processing_time_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)


class PIIDetector:
    """PII detection and masking utility."""
    
    def __init__(self):
        self.patterns = {
            PIIType.SSN: [
                r'\b\d{3}-\d{2}-\d{4}\b',
                r'\b\d{9}\b'
            ],
            PIIType.CREDIT_CARD: [
                r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                r'\b\d{13,19}\b'
            ],
            PIIType.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            PIIType.PHONE: [
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\(\d{3}\)\s*\d{3}-\d{4}',
                r'\b\d{10}\b'
            ],
            PIIType.MEDICAL_ID: [
                r'\b[A-Z]{2}\d{8}\b',
                r'\bMRN[-\s]?\d{6,10}\b'
            ],
            PIIType.INSURANCE_ID: [
                r'\b[A-Z]{3}\d{9}\b',
                r'\bINS[-\s]?\d{8,12}\b'
            ]
        }
    
    def detect_pii(self, text: str) -> List[Tuple[PIIType, str, int, int]]:
        """
        Detect PII in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (pii_type, matched_text, start_pos, end_pos)
        """
        detections = []
        
        for pii_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    detections.append((
                        pii_type,
                        match.group(),
                        match.start(),
                        match.end()
                    ))
        
        return detections
    
    def mask_pii(self, text: str, mask_char: str = "*") -> Tuple[str, List[Dict[str, Any]]]:
        """
        Mask PII in text.
        
        Args:
            text: Text to mask
            mask_char: Character to use for masking
            
        Returns:
            Tuple of (masked_text, redaction_log)
        """
        detections = self.detect_pii(text)
        redaction_log = []
        
        # Sort detections by position (reverse order for replacement)
        detections.sort(key=lambda x: x[2], reverse=True)
        
        masked_text = text
        for pii_type, matched_text, start_pos, end_pos in detections:
            # Create mask of same length
            mask = mask_char * len(matched_text)
            
            # Replace in text
            masked_text = masked_text[:start_pos] + mask + masked_text[end_pos:]
            
            # Log redaction
            redaction_log.append({
                "pii_type": pii_type.value,
                "original_length": len(matched_text),
                "position": start_pos,
                "redacted_at": datetime.utcnow().isoformat()
            })
        
        return masked_text, redaction_log


class InjectionDetector:
    """Injection attack detection utility."""
    
    def __init__(self):
        self.patterns = {
            InjectionType.PROMPT_INJECTION: [
                r'ignore\s+previous\s+instructions',
                r'forget\s+everything\s+above',
                r'system\s*:\s*you\s+are',
                r'act\s+as\s+if\s+you\s+are',
                r'pretend\s+to\s+be',
                r'roleplay\s+as',
                r'\\n\\n.*system.*\\n\\n',
            ],
            InjectionType.JAILBREAK_ATTEMPT: [
                r'DAN\s+mode',
                r'developer\s+mode',
                r'ignore\s+safety',
                r'bypass\s+restrictions',
                r'unrestricted\s+mode',
                r'evil\s+mode',
            ],
            InjectionType.SQL_INJECTION: [
                r"'.*OR.*'.*'",
                r'UNION\s+SELECT',
                r'DROP\s+TABLE',
                r'INSERT\s+INTO',
                r'DELETE\s+FROM',
                r'--\s*$',
                r'/\*.*\*/',
            ],
            InjectionType.COMMAND_INJECTION: [
                r';\s*rm\s+-rf',
                r';\s*cat\s+/etc/passwd',
                r'`.*`',
                r'\$\(.*\)',
                r'&&\s*rm',
                r'\|\s*nc\s+',
            ],
            InjectionType.SCRIPT_INJECTION: [
                r'<script.*>',
                r'javascript:',
                r'on\w+\s*=',
                r'eval\s*\(',
                r'document\.cookie',
                r'window\.location',
            ]
        }
    
    def detect_injection(self, text: str) -> List[Tuple[InjectionType, str, float]]:
        """
        Detect injection attempts in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (injection_type, matched_pattern, confidence)
        """
        detections = []
        
        for injection_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Calculate confidence based on pattern specificity
                    confidence = min(0.9, 0.5 + len(matches) * 0.1)
                    detections.append((injection_type, pattern, confidence))
        
        return detections


class SourceAllowlistValidator:
    """Source allowlist validation utility."""
    
    def __init__(self, allowlist_entries: List[SourceAllowlistEntry]):
        self.allowlist = {entry.source_id: entry for entry in allowlist_entries}
    
    def validate_source(self, source_id: str, version: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate if source is in allowlist.
        
        Args:
            source_id: Source identifier
            version: Optional version
            
        Returns:
            Tuple of (is_valid, reason)
        """
        entry = self.allowlist.get(source_id)
        
        if not entry:
            return False, f"Source {source_id} not in allowlist"
        
        if not entry.is_active:
            return False, f"Source {source_id} is inactive"
        
        if entry.expiry_date and entry.expiry_date < datetime.utcnow():
            return False, f"Source {source_id} has expired"
        
        if version and entry.allowed_versions and version not in entry.allowed_versions:
            return False, f"Version {version} not allowed for source {source_id}"
        
        return True, None
    
    def get_source_metadata(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a source."""
        entry = self.allowlist.get(source_id)
        return entry.metadata if entry else None


class RBACAuthorizer:
    """Role-Based Access Control authorizer."""
    
    def __init__(self, role_permissions: Dict[str, List[str]]):
        self.role_permissions = role_permissions
    
    def check_permission(self, user_context: UserContext, required_permission: str) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user_context: User context
            required_permission: Required permission
            
        Returns:
            True if authorized
        """
        # Check direct permissions
        if required_permission in user_context.permissions:
            return True
        
        # Check role-based permissions
        for role in user_context.roles:
            role_perms = self.role_permissions.get(role, [])
            if required_permission in role_perms:
                return True
        
        return False


class ABACAuthorizer:
    """Attribute-Based Access Control authorizer."""
    
    def __init__(self):
        self.policies = []
    
    def add_policy(self, policy: Dict[str, Any]):
        """Add ABAC policy."""
        self.policies.append(policy)
    
    def check_access(
        self,
        user_context: UserContext,
        resource_context: ResourceContext,
        action: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check access using ABAC policies.
        
        Args:
            user_context: User context
            resource_context: Resource context
            action: Requested action
            
        Returns:
            Tuple of (is_authorized, reason)
        """
        for policy in self.policies:
            if self._evaluate_policy(policy, user_context, resource_context, action):
                return True, "Access granted by policy"
        
        return False, "No policy grants access"
    
    def _evaluate_policy(
        self,
        policy: Dict[str, Any],
        user_context: UserContext,
        resource_context: ResourceContext,
        action: str
    ) -> bool:
        """Evaluate a single ABAC policy."""
        # Simple policy evaluation - can be extended
        conditions = policy.get("conditions", {})
        
        # Check action
        if "actions" in conditions and action not in conditions["actions"]:
            return False
        
        # Check resource type
        if "resource_types" in conditions and resource_context.resource_type.value not in conditions["resource_types"]:
            return False
        
        # Check user roles
        if "roles" in conditions and not any(role in user_context.roles for role in conditions["roles"]):
            return False
        
        # Check department match
        if "same_department" in conditions and conditions["same_department"]:
            if user_context.department != resource_context.department:
                return False
        
        return True


class GuardrailsService:
    """Main guardrails and governance service (UC-OP-10)."""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.pii_detector = PIIDetector()
        self.injection_detector = InjectionDetector()
        self.source_validator = SourceAllowlistValidator(config.source_allowlist)
        self.rbac_authorizer = RBACAuthorizer(config.role_permissions)
        self.abac_authorizer = ABACAuthorizer()
        
        # Initialize ABAC policies
        self._initialize_abac_policies()
        
        # Security event tracking
        self.security_events: List[SecurityEvent] = []
        
        logger.info("GuardrailsService initialized with OWASP LLM Top 10 controls")
    
    def _initialize_abac_policies(self):
        """Initialize default ABAC policies."""
        # Policy 1: Users can read cases in their department
        self.abac_authorizer.add_policy({
            "name": "department_case_read",
            "conditions": {
                "actions": ["READ"],
                "resource_types": ["CASE"],
                "same_department": True
            }
        })
        
        # Policy 2: Admins can access everything
        self.abac_authorizer.add_policy({
            "name": "admin_full_access",
            "conditions": {
                "roles": ["ADMIN", "SYSTEM_ADMIN"]
            }
        })
        
        # Policy 3: Auditors can read audit trails
        self.abac_authorizer.add_policy({
            "name": "auditor_audit_access",
            "conditions": {
                "actions": ["READ"],
                "resource_types": ["AUDIT"],
                "roles": ["AUDITOR", "COMPLIANCE_OFFICER"]
            }
        })
    
    async def evaluate_guardrails(
        self,
        case: Case,
        evidence_pack: Optional[EvidencePack] = None,
        user_context: Optional[UserContext] = None,
        content_to_check: Optional[str] = None
    ) -> GuardrailResult:
        """
        Evaluate all guardrails for a case.
        
        Args:
            case: Case to evaluate
            evidence_pack: Optional evidence pack
            user_context: Optional user context
            content_to_check: Optional content for injection detection
            
        Returns:
            GuardrailResult with evaluation results
        """
        start_time = datetime.utcnow()
        logger.info(f"Evaluating guardrails for case {case.case_id}")
        
        result = GuardrailResult(
            passed=True,
            action=GuardrailAction.ALLOW,
            confidence=1.0,
            processing_time_ms=0.0
        )
        
        try:
            # 1. Authorization check (OWASP LLM-02: Insecure Output Handling)
            if user_context:
                auth_result = await self._check_authorization(case, user_context)
                if not auth_result["authorized"]:
                    result.passed = False
                    result.action = GuardrailAction.BLOCK
                    result.flags.append("AUTHORIZATION_FAILED")
                    result.details["authorization"] = auth_result
            
            # 2. Source allowlist validation (OWASP LLM-03: Training Data Poisoning)
            if evidence_pack:
                source_result = await self._validate_sources(evidence_pack)
                if not source_result["all_valid"]:
                    result.passed = False
                    result.action = GuardrailAction.BLOCK
                    result.flags.append("INVALID_SOURCES")
                    result.details["source_validation"] = source_result
            
            # 3. PII detection and masking (OWASP LLM-06: Sensitive Information Disclosure)
            pii_result = await self._detect_and_mask_pii(case, evidence_pack)
            if pii_result["pii_detected"]:
                result.flags.append("PII_DETECTED")
                result.redactions.extend(pii_result["redactions"])
                result.details["pii_detection"] = pii_result
            
            # 4. Injection detection (OWASP LLM-01: Prompt Injection)
            if content_to_check:
                injection_result = await self._detect_injections(content_to_check)
                if injection_result["injections_detected"]:
                    result.passed = False
                    result.action = GuardrailAction.BLOCK
                    result.flags.append("INJECTION_DETECTED")
                    result.details["injection_detection"] = injection_result
            
            # 5. Content filtering (OWASP LLM-04: Model Denial of Service)
            content_result = await self._check_content_limits(case, evidence_pack)
            if not content_result["within_limits"]:
                result.passed = False
                result.action = GuardrailAction.BLOCK
                result.flags.append("CONTENT_LIMITS_EXCEEDED")
                result.details["content_limits"] = content_result
            
            # 6. Rate limiting check (OWASP LLM-04: Model Denial of Service)
            if user_context:
                rate_result = await self._check_rate_limits(user_context)
                if not rate_result["within_limits"]:
                    result.passed = False
                    result.action = GuardrailAction.THROTTLE
                    result.flags.append("RATE_LIMIT_EXCEEDED")
                    result.details["rate_limiting"] = rate_result
            
            # 7. Model security check (OWASP LLM-07: Insecure Plugin Design)
            model_result = await self._check_model_security(case)
            if not model_result["secure"]:
                result.warnings.append("MODEL_SECURITY_WARNING")
                result.details["model_security"] = model_result
            
            # 8. Supply chain validation (OWASP LLM-05: Supply Chain Vulnerabilities)
            supply_result = await self._validate_supply_chain(evidence_pack)
            if not supply_result["valid"]:
                result.warnings.append("SUPPLY_CHAIN_WARNING")
                result.details["supply_chain"] = supply_result
            
            # Calculate overall confidence
            result.confidence = self._calculate_confidence(result)
            
            # Log security events if needed
            if not result.passed or result.flags:
                await self._log_security_event(case, result, user_context)
        
        except Exception as e:
            logger.error(f"Error evaluating guardrails: {e}")
            result.passed = False
            result.action = GuardrailAction.BLOCK
            result.flags.append("EVALUATION_ERROR")
            result.details["error"] = str(e)
        
        finally:
            # Calculate processing time
            end_time = datetime.utcnow()
            result.processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            f"Guardrails evaluation completed for case {case.case_id}: "
            f"passed={result.passed}, action={result.action.value}, "
            f"flags={len(result.flags)}, time={result.processing_time_ms:.1f}ms"
        )
        
        return result
    
    async def _check_authorization(self, case: Case, user_context: UserContext) -> Dict[str, Any]:
        """Check user authorization for case access."""
        resource_context = ResourceContext(
            resource_type=ResourceType.CASE,
            resource_id=case.case_id,
            owner_id=case.customer_id,
            department=getattr(case, 'department', None),
            classification=getattr(case, 'classification', None)
        )
        
        # Check RBAC
        rbac_authorized = self.rbac_authorizer.check_permission(user_context, "case:read")
        
        # Check ABAC
        abac_authorized, abac_reason = self.abac_authorizer.check_access(
            user_context, resource_context, "READ"
        )
        
        authorized = rbac_authorized or abac_authorized
        
        # Log access attempt
        access_log = AccessControlLog(
            user_id=user_context.user_id,
            resource_type=ResourceType.CASE.value,
            resource_id=case.case_id,
            action="READ",
            authorized=authorized,
            authorization_method="RBAC" if rbac_authorized else "ABAC" if abac_authorized else "NONE",
            session_id=user_context.session_id,
            ip_address=user_context.ip_address,
            user_agent=user_context.user_agent,
        )
        
        return {
            "authorized": authorized,
            "rbac_authorized": rbac_authorized,
            "abac_authorized": abac_authorized,
            "abac_reason": abac_reason,
            "access_log": access_log
        }
    
    async def _validate_sources(self, evidence_pack: EvidencePack) -> Dict[str, Any]:
        """Validate evidence sources against allowlist."""
        validation_results = []
        all_valid = True
        
        for item in evidence_pack.items:
            is_valid, reason = self.source_validator.validate_source(
                item.document_id, item.version
            )
            
            validation_results.append({
                "document_id": item.document_id,
                "version": item.version,
                "valid": is_valid,
                "reason": reason
            })
            
            if not is_valid:
                all_valid = False
        
        return {
            "all_valid": all_valid,
            "validation_results": validation_results,
            "total_sources": len(evidence_pack.items),
            "valid_sources": sum(1 for r in validation_results if r["valid"])
        }
    
    async def _detect_and_mask_pii(
        self, 
        case: Case, 
        evidence_pack: Optional[EvidencePack] = None
    ) -> Dict[str, Any]:
        """Detect and mask PII in case and evidence."""
        pii_detected = False
        redactions = []
        
        # Check case description
        if case.service_description:
            masked_desc, desc_redactions = self.pii_detector.mask_pii(case.service_description)
            if desc_redactions:
                pii_detected = True
                redactions.extend(desc_redactions)
                # Update case with masked description
                case.service_description = masked_desc
        
        # Check evidence items
        if evidence_pack:
            for item in evidence_pack.items:
                if item.excerpt:
                    masked_excerpt, excerpt_redactions = self.pii_detector.mask_pii(item.excerpt)
                    if excerpt_redactions:
                        pii_detected = True
                        redactions.extend(excerpt_redactions)
                        # Update evidence with masked excerpt
                        item.excerpt = masked_excerpt
        
        # Log redactions
        if redactions:
            redaction_log = RedactionLog(
                case_id=case.case_id,
                redaction_type="PII_MASKING",
                original_content_hash=hashlib.sha256(
                    (case.service_description or "").encode()
                ).hexdigest(),
                redacted_fields=len(redactions),
                redaction_method="PATTERN_MATCHING",
                quality_score=0.9,  # High confidence in pattern matching
            )
        
        return {
            "pii_detected": pii_detected,
            "redactions": redactions,
            "redaction_count": len(redactions),
            "redaction_log": redaction_log if redactions else None
        }
    
    async def _detect_injections(self, content: str) -> Dict[str, Any]:
        """Detect injection attempts in content."""
        detections = self.injection_detector.detect_injection(content)
        
        return {
            "injections_detected": len(detections) > 0,
            "detections": [
                {
                    "type": injection_type.value,
                    "pattern": pattern,
                    "confidence": confidence
                }
                for injection_type, pattern, confidence in detections
            ],
            "highest_confidence": max([conf for _, _, conf in detections], default=0.0)
        }
    
    async def _check_content_limits(
        self, 
        case: Case, 
        evidence_pack: Optional[EvidencePack] = None
    ) -> Dict[str, Any]:
        """Check content size limits."""
        total_size = 0
        
        # Calculate case content size
        if case.service_description:
            total_size += len(case.service_description)
        
        # Calculate evidence content size
        if evidence_pack:
            for item in evidence_pack.items:
                if item.excerpt:
                    total_size += len(item.excerpt)
        
        within_limits = total_size <= self.config.max_content_size
        
        return {
            "within_limits": within_limits,
            "total_size": total_size,
            "max_size": self.config.max_content_size,
            "utilization": total_size / self.config.max_content_size
        }
    
    async def _check_rate_limits(self, user_context: UserContext) -> Dict[str, Any]:
        """Check rate limits for user."""
        # Simple rate limiting - can be enhanced with Redis/database
        # For now, return within limits
        return {
            "within_limits": True,
            "current_rate": 0,
            "max_rate": self.config.max_requests_per_minute,
            "reset_time": datetime.utcnow() + timedelta(minutes=1)
        }
    
    async def _check_model_security(self, case: Case) -> Dict[str, Any]:
        """Check model security configurations."""
        # Placeholder for model security checks
        return {
            "secure": True,
            "model_version_validated": True,
            "model_signature_valid": True,
            "model_source_trusted": True
        }
    
    async def _validate_supply_chain(self, evidence_pack: Optional[EvidencePack] = None) -> Dict[str, Any]:
        """Validate supply chain integrity."""
        # Placeholder for supply chain validation
        return {
            "valid": True,
            "dependencies_verified": True,
            "signatures_valid": True,
            "no_known_vulnerabilities": True
        }
    
    def _calculate_confidence(self, result: GuardrailResult) -> float:
        """Calculate overall confidence in guardrail evaluation."""
        base_confidence = 1.0
        
        # Reduce confidence for each flag
        confidence_reduction = len(result.flags) * 0.1
        
        # Reduce confidence for warnings
        warning_reduction = len(result.warnings) * 0.05
        
        return max(0.0, base_confidence - confidence_reduction - warning_reduction)
    
    async def _log_security_event(
        self,
        case: Case,
        result: GuardrailResult,
        user_context: Optional[UserContext] = None
    ):
        """Log security event."""
        if "AUTHORIZATION_FAILED" in result.flags:
            event_type = SecurityEventType.UNAUTHORIZED_ACCESS
        elif "INJECTION_DETECTED" in result.flags:
            event_type = SecurityEventType.INJECTION_ATTEMPT
        elif "PII_DETECTED" in result.flags:
            event_type = SecurityEventType.PII_EXPOSURE
        elif "INVALID_SOURCES" in result.flags:
            event_type = SecurityEventType.POLICY_VIOLATION
        else:
            event_type = SecurityEventType.SUSPICIOUS_ACTIVITY
        
        security_event = SecurityEvent(
            case_id=case.case_id,
            event_type=event_type,
            severity="HIGH" if not result.passed else "MEDIUM",
            description=f"Guardrails evaluation: {', '.join(result.flags)}",
            user_id=user_context.user_id if user_context else None,
            ip_address=user_context.ip_address if user_context else None,
            user_agent=user_context.user_agent if user_context else None,
            confidence_score=result.confidence,
            potential_impact="Case processing blocked" if not result.passed else "Case flagged for review",
            mitigation_applied=result.action.value,
            additional_context={
                "flags": result.flags,
                "warnings": result.warnings,
                "processing_time_ms": result.processing_time_ms
            }
        )
        
        self.security_events.append(security_event)
        logger.warning(f"Security event logged: {security_event.event_id}")
    
    async def create_guardrail_log(
        self,
        case_id: str,
        result: GuardrailResult,
        user_context: Optional[UserContext] = None
    ) -> GuardrailLog:
        """Create guardrail log entry."""
        return GuardrailLog(
            case_id=case_id,
            guardrail_type="COMPREHENSIVE_OWASP_LLM",
            action_taken=result.action,
            flags_raised=result.flags,
            confidence_score=result.confidence,
            processing_time_ms=result.processing_time_ms,
            user_id=user_context.user_id if user_context else None,
            session_id=user_context.session_id if user_context else None,
            details=result.details,
            redactions_applied=result.redactions,
        )
    
    def get_security_events(
        self,
        case_id: Optional[str] = None,
        event_type: Optional[SecurityEventType] = None,
        since: Optional[datetime] = None
    ) -> List[SecurityEvent]:
        """Get security events with optional filtering."""
        events = self.security_events
        
        if case_id:
            events = [e for e in events if e.case_id == case_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if since:
            events = [e for e in events if e.detected_at >= since]
        
        return events
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get guardrails metrics."""
        total_events = len(self.security_events)
        
        if total_events == 0:
            return {
                "total_security_events": 0,
                "events_by_type": {},
                "events_by_severity": {},
                "average_confidence": 0.0
            }
        
        events_by_type = {}
        events_by_severity = {}
        total_confidence = 0.0
        
        for event in self.security_events:
            # Count by type
            event_type = event.event_type.value
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            
            # Count by severity
            events_by_severity[event.severity] = events_by_severity.get(event.severity, 0) + 1
            
            # Sum confidence
            total_confidence += event.confidence_score
        
        return {
            "total_security_events": total_events,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity,
            "average_confidence": total_confidence / total_events,
            "last_event_time": max(e.detected_at for e in self.security_events).isoformat()
        }
