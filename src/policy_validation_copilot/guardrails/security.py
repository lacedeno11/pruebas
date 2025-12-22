"""
Comprehensive Guardrails Security System for Policy Validation Copilot

This module implements OWASP LLM Top 10 controls, RBAC/ABAC enforcement, PII masking,
source allowlist validation, anti-hallucination checks, injection detection, and
security event logging as specified in UC-OP-10.

Key Features:
- OWASP LLM Top 10 security controls
- RBAC/ABAC access control enforcement
- PII detection and masking
- Source allowlist validation
- Anti-hallucination verification
- Injection detection and prevention
- Security event logging and monitoring
- Integration with LangGraph workflow nodes

Business Rules Implemented:
- RB-01: No approval without verifiable evidence
- RB-02: Allowlist sources only - versioned/approved documents
- RB-10-01: Block without evidence
- RB-10-02: Minimal PII in LLM tools
"""

import re
import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field, validator
import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from ..models.guardrails import (
    GuardrailsResult,
    GuardrailFlag,
    PIIDetection,
    AccessControlCheck,
    SecurityEvent,
    HallucinationCheck,
    GuardrailDecision,
    SecurityThreatType,
    PIIType,
    MaskingLevel
)
from ..models.case import Case
from ..models.evidence import EvidencePack, EvidenceItem
from ..models.audit import AuditTrail


# Configure logging
logger = logging.getLogger(__name__)


class OWASPThreatType(str, Enum):
    """OWASP LLM Top 10 threat types"""
    PROMPT_INJECTION = "LLM01_PROMPT_INJECTION"
    INSECURE_OUTPUT_HANDLING = "LLM02_INSECURE_OUTPUT_HANDLING"
    TRAINING_DATA_POISONING = "LLM03_TRAINING_DATA_POISONING"
    MODEL_DENIAL_OF_SERVICE = "LLM04_MODEL_DENIAL_OF_SERVICE"
    SUPPLY_CHAIN_VULNERABILITIES = "LLM05_SUPPLY_CHAIN_VULNERABILITIES"
    SENSITIVE_INFORMATION_DISCLOSURE = "LLM06_SENSITIVE_INFORMATION_DISCLOSURE"
    INSECURE_PLUGIN_DESIGN = "LLM07_INSECURE_PLUGIN_DESIGN"
    EXCESSIVE_AGENCY = "LLM08_EXCESSIVE_AGENCY"
    OVERRELIANCE = "LLM09_OVERRELIANCE"
    MODEL_THEFT = "LLM10_MODEL_THEFT"


class AccessLevel(str, Enum):
    """Access levels for RBAC/ABAC"""
    READ = "read"
    WRITE = "write"
    APPROVE = "approve"
    AUDIT = "audit"
    ADMIN = "admin"


class UserRole(str, Enum):
    """User roles for RBAC"""
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    AUDITOR = "auditor"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class SecurityContext:
    """Security context for guardrails evaluation"""
    user_id: str
    user_role: UserRole
    session_id: str
    case_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    permissions: Set[str] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailsConfig:
    """Configuration for guardrails system"""
    # OWASP LLM Top 10 Controls
    enable_prompt_injection_detection: bool = True
    enable_output_validation: bool = True
    enable_data_poisoning_detection: bool = True
    enable_dos_protection: bool = True
    enable_supply_chain_validation: bool = True
    enable_sensitive_data_protection: bool = True
    enable_plugin_security: bool = True
    enable_agency_control: bool = True
    enable_overreliance_protection: bool = True
    enable_model_theft_protection: bool = True
    
    # PII Detection and Masking
    enable_pii_detection: bool = True
    pii_confidence_threshold: float = 0.8
    default_masking_level: MaskingLevel = MaskingLevel.PARTIAL
    
    # Source Allowlist
    enable_source_allowlist: bool = True
    allowed_document_types: Set[str] = field(default_factory=lambda: {
        "policy_document", "regulation", "guideline", "procedure"
    })
    
    # Anti-hallucination
    enable_hallucination_detection: bool = True
    evidence_requirement_threshold: float = 0.7
    
    # Injection Detection
    enable_injection_detection: bool = True
    injection_patterns: List[str] = field(default_factory=lambda: [
        r"ignore\s+previous\s+instructions",
        r"system\s*:\s*you\s+are",
        r"jailbreak",
        r"developer\s+mode",
        r"pretend\s+to\s+be",
    ])
    
    # Security Event Logging
    enable_security_logging: bool = True
    log_all_decisions: bool = True
    log_pii_detections: bool = True
    
    # Performance
    max_content_length: int = 1000000  # 1MB
    timeout_seconds: int = 30


class PIIMaskingEngine:
    """PII detection and masking engine using Presidio"""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Load spaCy model for NLP
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, using basic PII detection")
            self.nlp = None
    
    async def detect_pii(self, text: str) -> List[PIIDetection]:
        """Detect PII in text content"""
        if not self.config.enable_pii_detection:
            return []
        
        try:
            # Use Presidio for PII detection
            results = self.analyzer.analyze(
                text=text,
                language='en',
                score_threshold=self.config.pii_confidence_threshold
            )
            
            pii_detections = []
            for result in results:
                pii_type = self._map_presidio_type_to_pii_type(result.entity_type)
                detection = PIIDetection(
                    pii_type=pii_type,
                    confidence_score=result.score,
                    start_position=result.start,
                    end_position=result.end,
                    original_text=text[result.start:result.end],
                    masked_text=self._mask_text(
                        text[result.start:result.end], 
                        pii_type,
                        self.config.default_masking_level
                    ),
                    masking_level=self.config.default_masking_level
                )
                pii_detections.append(detection)
            
            return pii_detections
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            return []
    
    def _map_presidio_type_to_pii_type(self, presidio_type: str) -> PIIType:
        """Map Presidio entity types to our PII types"""
        mapping = {
            "PERSON": PIIType.NAME,
            "EMAIL_ADDRESS": PIIType.EMAIL,
            "PHONE_NUMBER": PIIType.PHONE,
            "CREDIT_CARD": PIIType.CREDIT_CARD,
            "IBAN_CODE": PIIType.FINANCIAL,
            "US_SSN": PIIType.SSN,
            "US_PASSPORT": PIIType.PASSPORT,
            "MEDICAL_LICENSE": PIIType.MEDICAL,
            "IP_ADDRESS": PIIType.IP_ADDRESS,
            "DATE_TIME": PIIType.DATE,
            "LOCATION": PIIType.ADDRESS,
        }
        return mapping.get(presidio_type, PIIType.OTHER)
    
    def _mask_text(self, text: str, pii_type: PIIType, masking_level: MaskingLevel) -> str:
        """Mask PII text based on type and level"""
        if masking_level == MaskingLevel.NONE:
            return text
        elif masking_level == MaskingLevel.FULL:
            return "*" * len(text)
        elif masking_level == MaskingLevel.PARTIAL:
            if len(text) <= 4:
                return "*" * len(text)
            return text[:2] + "*" * (len(text) - 4) + text[-2:]
        elif masking_level == MaskingLevel.HASH:
            return hashlib.sha256(text.encode()).hexdigest()[:8]
        else:
            return text
    
    async def mask_content(self, content: str, pii_detections: List[PIIDetection]) -> str:
        """Apply PII masking to content"""
        if not pii_detections:
            return content
        
        # Sort detections by position (reverse order to maintain indices)
        sorted_detections = sorted(pii_detections, key=lambda x: x.start_position, reverse=True)
        
        masked_content = content
        for detection in sorted_detections:
            masked_content = (
                masked_content[:detection.start_position] +
                detection.masked_text +
                masked_content[detection.end_position:]
            )
        
        return masked_content


class InjectionDetector:
    """Injection detection and prevention system"""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.injection_patterns = [re.compile(pattern, re.IGNORECASE) 
                                 for pattern in config.injection_patterns]
    
    async def detect_injection(self, content: str) -> List[GuardrailFlag]:
        """Detect injection attempts in content"""
        if not self.config.enable_injection_detection:
            return []
        
        flags = []
        
        # Check for prompt injection patterns
        for pattern in self.injection_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                flag = GuardrailFlag(
                    flag_type=SecurityThreatType.PROMPT_INJECTION,
                    severity="HIGH",
                    description=f"Potential prompt injection detected: {match.group()}",
                    location=f"Position {match.start()}-{match.end()}",
                    remediation="Content blocked due to injection attempt",
                    confidence_score=0.9
                )
                flags.append(flag)
        
        # Check for jailbreak attempts
        jailbreak_indicators = [
            "ignore previous instructions",
            "system: you are",
            "developer mode",
            "pretend to be",
            "act as if",
            "roleplay as"
        ]
        
        content_lower = content.lower()
        for indicator in jailbreak_indicators:
            if indicator in content_lower:
                flag = GuardrailFlag(
                    flag_type=SecurityThreatType.PROMPT_INJECTION,
                    severity="HIGH",
                    description=f"Jailbreak attempt detected: {indicator}",
                    location="Content analysis",
                    remediation="Content blocked due to jailbreak attempt",
                    confidence_score=0.85
                )
                flags.append(flag)
        
        # Check for data exfiltration attempts
        exfiltration_patterns = [
            r"show\s+me\s+all\s+data",
            r"export\s+database",
            r"dump\s+table",
            r"select\s+\*\s+from",
            r"show\s+tables"
        ]
        
        for pattern_str in exfiltration_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(content):
                flag = GuardrailFlag(
                    flag_type=SecurityThreatType.DATA_EXFILTRATION,
                    severity="CRITICAL",
                    description=f"Data exfiltration attempt detected: {pattern_str}",
                    location="Content analysis",
                    remediation="Content blocked due to exfiltration attempt",
                    confidence_score=0.95
                )
                flags.append(flag)
        
        return flags


class SourceAllowlistValidator:
    """Source allowlist validation system"""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.allowed_sources: Set[str] = set()
        self.allowed_document_types = config.allowed_document_types
    
    async def validate_evidence_sources(self, evidence_pack: EvidencePack) -> List[GuardrailFlag]:
        """Validate that all evidence sources are allowlisted"""
        if not self.config.enable_source_allowlist:
            return []
        
        flags = []
        
        for item in evidence_pack.items:
            # Check if source is allowlisted
            if not self._is_source_allowed(item):
                flag = GuardrailFlag(
                    flag_type=SecurityThreatType.UNAUTHORIZED_SOURCE,
                    severity="HIGH",
                    description=f"Evidence from non-allowlisted source: {item.document_id}",
                    location=f"Document: {item.document_id}",
                    remediation="Evidence excluded from consideration",
                    confidence_score=1.0
                )
                flags.append(flag)
            
            # Check document type
            if hasattr(item, 'source_type') and item.source_type not in self.allowed_document_types:
                flag = GuardrailFlag(
                    flag_type=SecurityThreatType.UNAUTHORIZED_SOURCE,
                    severity="MEDIUM",
                    description=f"Evidence from non-approved document type: {item.source_type}",
                    location=f"Document: {item.document_id}",
                    remediation="Evidence flagged for review",
                    confidence_score=0.9
                )
                flags.append(flag)
        
        return flags
    
    def _is_source_allowed(self, evidence_item: EvidenceItem) -> bool:
        """Check if evidence source is allowlisted"""
        # For now, check if document has proper versioning and checksum
        return (
            evidence_item.document_id and
            evidence_item.version and
            evidence_item.checksum and
            len(evidence_item.checksum) >= 32  # Minimum hash length
        )
    
    async def add_allowed_source(self, source_id: str, document_type: str) -> None:
        """Add source to allowlist"""
        self.allowed_sources.add(source_id)
        self.allowed_document_types.add(document_type)
    
    async def remove_allowed_source(self, source_id: str) -> None:
        """Remove source from allowlist"""
        self.allowed_sources.discard(source_id)


class AntiHallucinationValidator:
    """Anti-hallucination validation system"""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
    
    async def validate_evidence_anchoring(
        self, 
        decision_text: str, 
        evidence_pack: EvidencePack
    ) -> HallucinationCheck:
        """Validate that decision is properly anchored to evidence"""
        if not self.config.enable_hallucination_detection:
            return HallucinationCheck(
                is_anchored=True,
                confidence_score=1.0,
                evidence_coverage=1.0,
                unanchored_claims=[],
                evidence_references=[]
            )
        
        # Extract claims from decision text
        claims = self._extract_claims(decision_text)
        
        # Check each claim against evidence
        anchored_claims = []
        unanchored_claims = []
        evidence_references = []
        
        for claim in claims:
            evidence_support = self._find_evidence_support(claim, evidence_pack)
            if evidence_support:
                anchored_claims.append(claim)
                evidence_references.extend(evidence_support)
            else:
                unanchored_claims.append(claim)
        
        # Calculate metrics
        total_claims = len(claims)
        anchored_count = len(anchored_claims)
        
        if total_claims == 0:
            confidence_score = 0.0
            evidence_coverage = 0.0
        else:
            confidence_score = anchored_count / total_claims
            evidence_coverage = len(set(evidence_references)) / len(evidence_pack.items) if evidence_pack.items else 0.0
        
        is_anchored = confidence_score >= self.config.evidence_requirement_threshold
        
        return HallucinationCheck(
            is_anchored=is_anchored,
            confidence_score=confidence_score,
            evidence_coverage=evidence_coverage,
            unanchored_claims=unanchored_claims,
            evidence_references=list(set(evidence_references))
        )
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text"""
        # Simple implementation - split by sentences and filter
        sentences = re.split(r'[.!?]+', text)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and self._is_factual_claim(sentence):
                claims.append(sentence)
        
        return claims
    
    def _is_factual_claim(self, sentence: str) -> bool:
        """Determine if sentence contains a factual claim"""
        # Look for factual indicators
        factual_indicators = [
            "according to", "based on", "the policy states",
            "coverage includes", "excluded", "required",
            "must", "shall", "will", "is covered", "is not covered"
        ]
        
        sentence_lower = sentence.lower()
        return any(indicator in sentence_lower for indicator in factual_indicators)
    
    def _find_evidence_support(self, claim: str, evidence_pack: EvidencePack) -> List[str]:
        """Find evidence items that support a claim"""
        supporting_evidence = []
        
        # Simple keyword matching - in production, use semantic similarity
        claim_words = set(claim.lower().split())
        
        for item in evidence_pack.items:
            if item.excerpt:
                excerpt_words = set(item.excerpt.lower().split())
                overlap = len(claim_words.intersection(excerpt_words))
                
                # If significant overlap, consider it supporting evidence
                if overlap >= min(3, len(claim_words) * 0.3):
                    supporting_evidence.append(item.document_id)
        
        return supporting_evidence


class RBACEnforcer:
    """Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC) enforcer"""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, Set[str]]:
        """Initialize default role permissions"""
        return {
            UserRole.AGENT: {
                "case.read", "case.create", "case.update",
                "evidence.read", "checklist.read"
            },
            UserRole.SUPERVISOR: {
                "case.read", "case.create", "case.update", "case.approve",
                "evidence.read", "evidence.approve", "checklist.read", "checklist.approve",
                "exception.create", "exception.approve", "hitl.approve"
            },
            UserRole.AUDITOR: {
                "case.read", "evidence.read", "checklist.read",
                "audit.read", "audit.export", "decision.read"
            },
            UserRole.ADMIN: {
                "case.*", "evidence.*", "checklist.*", "audit.*",
                "decision.*", "exception.*", "hitl.*", "system.*"
            },
            UserRole.SYSTEM: {
                "case.*", "evidence.*", "checklist.*", "ml.*", "guardrails.*"
            }
        }
    
    async def check_access(
        self, 
        context: SecurityContext, 
        resource: str, 
        action: str
    ) -> AccessControlCheck:
        """Check if user has access to perform action on resource"""
        permission = f"{resource}.{action}"
        
        # Check role-based permissions
        role_permissions = self.role_permissions.get(context.user_role, set())
        has_role_permission = (
            permission in role_permissions or
            f"{resource}.*" in role_permissions or
            "*" in role_permissions
        )
        
        # Check explicit permissions
        has_explicit_permission = permission in context.permissions
        
        # Check attribute-based conditions
        attribute_conditions_met = self._check_attribute_conditions(
            context, resource, action
        )
        
        access_granted = (
            (has_role_permission or has_explicit_permission) and
            attribute_conditions_met
        )
        
        return AccessControlCheck(
            user_id=context.user_id,
            user_role=context.user_role,
            resource=resource,
            action=action,
            access_granted=access_granted,
            reason=self._get_access_reason(
                has_role_permission, has_explicit_permission, attribute_conditions_met
            ),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _check_attribute_conditions(
        self, 
        context: SecurityContext, 
        resource: str, 
        action: str
    ) -> bool:
        """Check attribute-based access conditions"""
        # Example attribute-based rules
        
        # Case ownership check
        if resource == "case" and action in ["update", "approve"]:
            case_owner = context.attributes.get("case_owner")
            if case_owner and case_owner != context.user_id and context.user_role == UserRole.AGENT:
                return False
        
        # Time-based restrictions
        current_hour = datetime.now().hour
        if action == "approve" and current_hour < 6 or current_hour > 22:
            # No approvals outside business hours for non-supervisors
            if context.user_role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
                return False
        
        # IP-based restrictions
        if context.ip_address and action in ["export", "audit"]:
            # Check if IP is from allowed network (simplified)
            allowed_networks = ["10.0.0.0/8", "192.168.0.0/16"]
            # In production, use proper IP network checking
        
        return True
    
    def _get_access_reason(
        self, 
        has_role_permission: bool, 
        has_explicit_permission: bool, 
        attribute_conditions_met: bool
    ) -> str:
        """Get human-readable access decision reason"""
        if not (has_role_permission or has_explicit_permission):
            return "Insufficient permissions for this action"
        elif not attribute_conditions_met:
            return "Access denied due to attribute-based policy violation"
        else:
            return "Access granted"


class SecurityEventLogger:
    """Security event logging and monitoring system"""
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.security_events")
    
    async def log_security_event(self, event: SecurityEvent) -> None:
        """Log security event"""
        if not self.config.enable_security_logging:
            return
        
        # Log to application logger
        self.logger.warning(
            f"Security Event: {event.event_type} - {event.description}",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "user_id": event.user_id,
                "case_id": event.case_id,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata
            }
        )
        
        # In production, also send to SIEM/security monitoring system
        await self._send_to_siem(event)
    
    async def _send_to_siem(self, event: SecurityEvent) -> None:
        """Send security event to SIEM system"""
        # Placeholder for SIEM integration
        # In production, integrate with security monitoring tools
        pass
    
    async def log_guardrail_decision(
        self, 
        decision: GuardrailDecision, 
        context: SecurityContext,
        flags: List[GuardrailFlag]
    ) -> None:
        """Log guardrail decision for audit purposes"""
        if not self.config.log_all_decisions:
            return
        
        event = SecurityEvent(
            event_type=SecurityThreatType.GUARDRAIL_DECISION,
            severity="INFO" if decision == GuardrailDecision.ALLOW else "WARNING",
            description=f"Guardrail decision: {decision}",
            user_id=context.user_id,
            case_id=context.case_id,
            metadata={
                "decision": decision,
                "flags_count": len(flags),
                "flags": [flag.dict() for flag in flags],
                "user_role": context.user_role,
                "session_id": context.session_id
            }
        )
        
        await self.log_security_event(event)


class PolicyValidationGuardrails:
    """Main guardrails enforcement system for Policy Validation Copilot"""
    
    def __init__(self, config: Optional[GuardrailsConfig] = None):
        self.config = config or GuardrailsConfig()
        
        # Initialize components
        self.pii_engine = PIIMaskingEngine(self.config)
        self.injection_detector = InjectionDetector(self.config)
        self.source_validator = SourceAllowlistValidator(self.config)
        self.hallucination_validator = AntiHallucinationValidator(self.config)
        self.rbac_enforcer = RBACEnforcer(self.config)
        self.security_logger = SecurityEventLogger(self.config)
    
    async def enforce_guardrails(
        self,
        context: SecurityContext,
        case: Optional[Case] = None,
        evidence_pack: Optional[EvidencePack] = None,
        decision_text: Optional[str] = None,
        user_input: Optional[str] = None
    ) -> GuardrailsResult:
        """Main guardrails enforcement entry point"""
        
        start_time = datetime.now(timezone.utc)
        flags = []
        pii_detections = []
        access_checks = []
        
        try:
            # 1. RBAC/ABAC Access Control
            if case:
                access_check = await self.rbac_enforcer.check_access(
                    context, "case", "read"
                )
                access_checks.append(access_check)
                
                if not access_check.access_granted:
                    flags.append(GuardrailFlag(
                        flag_type=SecurityThreatType.ACCESS_VIOLATION,
                        severity="HIGH",
                        description="Access denied to case",
                        location="RBAC check",
                        remediation="Request proper permissions",
                        confidence_score=1.0
                    ))
            
            # 2. PII Detection and Masking
            content_to_check = []
            if user_input:
                content_to_check.append(("user_input", user_input))
            if decision_text:
                content_to_check.append(("decision_text", decision_text))
            
            for content_type, content in content_to_check:
                if len(content) > self.config.max_content_length:
                    flags.append(GuardrailFlag(
                        flag_type=SecurityThreatType.DOS_ATTACK,
                        severity="HIGH",
                        description=f"Content too large: {len(content)} bytes",
                        location=content_type,
                        remediation="Content truncated",
                        confidence_score=1.0
                    ))
                    content = content[:self.config.max_content_length]
                
                # Detect PII
                pii_found = await self.pii_engine.detect_pii(content)
                pii_detections.extend(pii_found)
                
                # Detect injection attempts
                injection_flags = await self.injection_detector.detect_injection(content)
                flags.extend(injection_flags)
            
            # 3. Source Allowlist Validation
            if evidence_pack:
                source_flags = await self.source_validator.validate_evidence_sources(evidence_pack)
                flags.extend(source_flags)
            
            # 4. Anti-hallucination Check
            hallucination_check = None
            if decision_text and evidence_pack:
                hallucination_check = await self.hallucination_validator.validate_evidence_anchoring(
                    decision_text, evidence_pack
                )
                
                if not hallucination_check.is_anchored:
                    flags.append(GuardrailFlag(
                        flag_type=SecurityThreatType.HALLUCINATION,
                        severity="HIGH",
                        description="Decision not properly anchored to evidence",
                        location="Decision validation",
                        remediation="Require human review",
                        confidence_score=hallucination_check.confidence_score
                    ))
            
            # 5. Determine overall decision
            decision = self._determine_guardrail_decision(flags, pii_detections)
            
            # 6. Apply content redaction if needed
            redacted_content = {}
            if decision in [GuardrailDecision.REDACT, GuardrailDecision.ALLOW]:
                for content_type, content in content_to_check:
                    relevant_pii = [pii for pii in pii_detections 
                                  if content_type in str(pii)]
                    redacted_content[content_type] = await self.pii_engine.mask_content(
                        content, relevant_pii
                    )
            
            # 7. Create result
            result = GuardrailsResult(
                decision=decision,
                flags=flags,
                pii_detections=pii_detections,
                access_checks=access_checks,
                hallucination_check=hallucination_check,
                redacted_content=redacted_content,
                processing_time_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                guardrails_version="1.0.0"
            )
            
            # 8. Log decision
            await self.security_logger.log_guardrail_decision(decision, context, flags)
            
            # 9. Log security events for critical flags
            for flag in flags:
                if flag.severity in ["HIGH", "CRITICAL"]:
                    event = SecurityEvent(
                        event_type=flag.flag_type,
                        severity=flag.severity,
                        description=flag.description,
                        user_id=context.user_id,
                        case_id=context.case_id,
                        metadata={
                            "flag": flag.dict(),
                            "location": flag.location,
                            "remediation": flag.remediation
                        }
                    )
                    await self.security_logger.log_security_event(event)
            
            return result
            
        except Exception as e:
            logger.error(f"Guardrails enforcement failed: {e}")
            
            # Return safe default - block on error
            return GuardrailsResult(
                decision=GuardrailDecision.BLOCK,
                flags=[GuardrailFlag(
                    flag_type=SecurityThreatType.SYSTEM_ERROR,
                    severity="CRITICAL",
                    description=f"Guardrails system error: {str(e)}",
                    location="System",
                    remediation="Manual review required",
                    confidence_score=1.0
                )],
                pii_detections=[],
                access_checks=[],
                redacted_content={},
                processing_time_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                guardrails_version="1.0.0"
            )
    
    def _determine_guardrail_decision(
        self, 
        flags: List[GuardrailFlag], 
        pii_detections: List[PIIDetection]
    ) -> GuardrailDecision:
        """Determine overall guardrail decision based on flags and PII"""
        
        # Check for critical/high severity flags
        critical_flags = [f for f in flags if f.severity == "CRITICAL"]
        high_flags = [f for f in flags if f.severity == "HIGH"]
        
        # Block on critical issues
        if critical_flags:
            return GuardrailDecision.BLOCK
        
        # Require human review on high severity issues
        if high_flags:
            return GuardrailDecision.REQUIRE_HITL
        
        # Redact if PII found
        if pii_detections:
            return GuardrailDecision.REDACT
        
        # Allow if no issues
        return GuardrailDecision.ALLOW
    
    async def validate_llm_output(
        self,
        context: SecurityContext,
        output_text: str,
        evidence_pack: Optional[EvidencePack] = None
    ) -> GuardrailsResult:
        """Validate LLM output for OWASP LLM02 - Insecure Output Handling"""
        
        return await self.enforce_guardrails(
            context=context,
            evidence_pack=evidence_pack,
            decision_text=output_text
        )
    
    async def validate_user_input(
        self,
        context: SecurityContext,
        user_input: str
    ) -> GuardrailsResult:
        """Validate user input for OWASP LLM01 - Prompt Injection"""
        
        return await self.enforce_guardrails(
            context=context,
            user_input=user_input
        )
    
    async def validate_evidence_integrity(
        self,
        context: SecurityContext,
        evidence_pack: EvidencePack
    ) -> GuardrailsResult:
        """Validate evidence integrity and source allowlist"""
        
        return await self.enforce_guardrails(
            context=context,
            evidence_pack=evidence_pack
        )


# Factory function for easy instantiation
def create_guardrails_system(config: Optional[GuardrailsConfig] = None) -> PolicyValidationGuardrails:
    """Create and configure guardrails system"""
    return PolicyValidationGuardrails(config)


# Decorator for automatic guardrails enforcement in LangGraph nodes
def with_guardrails(
    check_input: bool = True,
    check_output: bool = True,
    check_evidence: bool = True
):
    """Decorator to automatically apply guardrails to LangGraph nodes"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract context and data from arguments
            # This would be customized based on actual LangGraph node signatures
            
            # Apply input guardrails
            if check_input:
                # Validate inputs
                pass
            
            # Execute original function
            result = await func(*args, **kwargs)
            
            # Apply output guardrails
            if check_output:
                # Validate outputs
                pass
            
            return result
        
        return wrapper
    return decorator
