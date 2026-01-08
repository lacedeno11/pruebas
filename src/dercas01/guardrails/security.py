"""
Security Guardrails for DERCAS 01 Policy Validation Copilot

Implements OWASP LLM Top 10 protections, injection detection, and anti-hallucination checks.
Provides comprehensive security controls for LLM interactions and data processing.
"""

import logging
import re
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SecurityThreatLevel(str, Enum):
    """Security threat levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityCheckType(str, Enum):
    """Types of security checks."""
    PROMPT_INJECTION = "PROMPT_INJECTION"
    DATA_LEAKAGE = "DATA_LEAKAGE"
    HALLUCINATION = "HALLUCINATION"
    MALICIOUS_INPUT = "MALICIOUS_INPUT"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    MODEL_THEFT = "MODEL_THEFT"
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    MODEL_POISONING = "MODEL_POISONING"


class SecurityCheckResult(BaseModel):
    """Result of a security check."""
    
    check_type: SecurityCheckType
    threat_level: SecurityThreatLevel
    is_blocked: bool
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Details
    description: str
    evidence: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Metadata
    check_timestamp: datetime = Field(default_factory=datetime.utcnow)
    check_duration_ms: Optional[float] = None


class SecurityConfig(BaseModel):
    """Configuration for security guardrails."""
    
    # OWASP LLM-01: Prompt Injection
    enable_prompt_injection_detection: bool = True
    prompt_injection_threshold: float = 0.7
    
    # OWASP LLM-02: Insecure Output Handling
    enable_output_sanitization: bool = True
    max_output_length: int = 10000
    
    # OWASP LLM-03: Training Data Poisoning
    enable_training_data_validation: bool = True
    
    # OWASP LLM-04: Model Denial of Service
    enable_dos_protection: bool = True
    max_requests_per_minute: int = 100
    max_input_length: int = 50000
    
    # OWASP LLM-05: Supply Chain Vulnerabilities
    enable_supply_chain_checks: bool = True
    trusted_sources: Set[str] = Field(default_factory=lambda: {"internal", "verified"})
    
    # OWASP LLM-06: Sensitive Information Disclosure
    enable_sensitive_data_detection: bool = True
    
    # OWASP LLM-07: Insecure Plugin Design
    enable_plugin_validation: bool = True
    
    # OWASP LLM-08: Excessive Agency
    enable_agency_controls: bool = True
    max_external_calls: int = 5
    
    # OWASP LLM-09: Overreliance
    enable_confidence_thresholds: bool = True
    min_confidence_for_auto_decision: float = 0.85
    
    # OWASP LLM-10: Model Theft
    enable_model_protection: bool = True
    
    # Anti-hallucination
    enable_hallucination_detection: bool = True
    hallucination_threshold: float = 0.6
    require_source_citations: bool = True
    
    # Rate limiting
    enable_rate_limiting: bool = True
    rate_limit_window_seconds: int = 60


class SecurityGuardrails:
    """
    Main security guardrails implementation.
    
    Implements OWASP LLM Top 10 protections and additional security controls.
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
        # Threat detection patterns
        self.injection_patterns = self._load_injection_patterns()
        self.sensitive_patterns = self._load_sensitive_patterns()
        self.malicious_patterns = self._load_malicious_patterns()
        
        # Rate limiting tracking
        self.request_counts: Dict[str, List[datetime]] = {}
        
        # Known good sources
        self.trusted_sources = config.trusted_sources
        
        # Hallucination detection
        self.fact_database = self._initialize_fact_database()
    
    def _load_injection_patterns(self) -> List[re.Pattern]:
        """Load prompt injection detection patterns."""
        patterns = [
            # Direct injection attempts
            r"ignore\s+(?:previous|all)\s+(?:instructions|prompts)",
            r"forget\s+(?:everything|all)\s+(?:above|before)",
            r"new\s+(?:instructions|task|role)",
            r"act\s+as\s+(?:a\s+)?(?:different|new)",
            r"pretend\s+(?:to\s+be|you\s+are)",
            
            # System prompt manipulation
            r"system\s*:\s*",
            r"assistant\s*:\s*",
            r"human\s*:\s*",
            r"<\s*/?system\s*>",
            r"<\s*/?assistant\s*>",
            
            # Jailbreaking attempts
            r"jailbreak",
            r"break\s+out\s+of",
            r"escape\s+(?:the\s+)?(?:system|constraints)",
            r"override\s+(?:safety|security)",
            
            # Role manipulation
            r"you\s+are\s+now\s+(?:a\s+)?(?:hacker|admin|root)",
            r"switch\s+to\s+(?:developer|admin)\s+mode",
            r"enable\s+(?:debug|admin)\s+mode",
            
            # Data extraction attempts
            r"show\s+me\s+(?:the\s+)?(?:system|internal|hidden)",
            r"reveal\s+(?:the\s+)?(?:prompt|instructions|code)",
            r"what\s+(?:are\s+)?(?:your\s+)?(?:instructions|rules)",
            
            # Code injection
            r"<script[^>]*>",
            r"javascript\s*:",
            r"eval\s*\(",
            r"exec\s*\(",
            r"import\s+os",
            r"__import__",
        ]
        
        return [re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in patterns]
    
    def _load_sensitive_patterns(self) -> List[re.Pattern]:
        """Load sensitive data detection patterns."""
        patterns = [
            # Credit card numbers
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            
            # Social security numbers
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{9}\b",
            
            # Email addresses
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            
            # Phone numbers
            r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
            
            # API keys and tokens
            r"(?:api[_-]?key|token|secret)[\"'\s]*[:=][\"'\s]*[A-Za-z0-9+/]{20,}",
            r"sk-[A-Za-z0-9]{48}",  # OpenAI API key pattern
            r"xoxb-[A-Za-z0-9-]{50,}",  # Slack bot token
            
            # Database connection strings
            r"(?:mongodb|mysql|postgresql)://[^\s]+",
            
            # IP addresses
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            
            # Internal system references
            r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0)",
            r"(?:admin|root|administrator)\s*[:=]\s*[^\s]+",
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _load_malicious_patterns(self) -> List[re.Pattern]:
        """Load malicious content detection patterns."""
        patterns = [
            # SQL injection
            r"(?:union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?:or|and)\s+(?:1=1|true|false)",
            r"(?:--|#|/\*|\*/)",
            
            # XSS attempts
            r"<script[^>]*>.*?</script>",
            r"on(?:click|load|error|focus)\s*=",
            r"javascript\s*:",
            
            # Command injection
            r"(?:;|\||\&\&|\|\|)\s*(?:rm|del|format|shutdown)",
            r"(?:cat|type|more|less)\s+/",
            r"(?:wget|curl|nc|netcat)",
            
            # Path traversal
            r"\.\.(?:/|\\)",
            r"(?:/etc/passwd|/etc/shadow|/etc/hosts)",
            r"(?:c:\\windows|c:\\users)",
            
            # Suspicious keywords
            r"(?:exploit|payload|shellcode|backdoor)",
            r"(?:metasploit|nmap|sqlmap|burp)",
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _initialize_fact_database(self) -> Dict[str, Any]:
        """Initialize fact database for hallucination detection."""
        # In production, this would be loaded from a comprehensive knowledge base
        return {
            "known_facts": {
                "company_policies": {},
                "medical_procedures": {},
                "insurance_regulations": {},
            },
            "fact_sources": {},
            "verification_rules": {},
        }
    
    def check_input_security(self, input_text: str, context: Dict[str, Any] = None) -> List[SecurityCheckResult]:
        """
        Perform comprehensive security checks on input text.
        
        Args:
            input_text: Text to check
            context: Additional context for checks
            
        Returns:
            List of security check results
        """
        results = []
        context = context or {}
        
        try:
            # OWASP LLM-01: Prompt Injection Detection
            if self.config.enable_prompt_injection_detection:
                injection_result = self._check_prompt_injection(input_text)
                if injection_result:
                    results.append(injection_result)
            
            # OWASP LLM-04: DoS Protection
            if self.config.enable_dos_protection:
                dos_result = self._check_dos_protection(input_text, context)
                if dos_result:
                    results.append(dos_result)
            
            # OWASP LLM-06: Sensitive Information Detection
            if self.config.enable_sensitive_data_detection:
                sensitive_result = self._check_sensitive_data(input_text)
                if sensitive_result:
                    results.append(sensitive_result)
            
            # Malicious content detection
            malicious_result = self._check_malicious_content(input_text)
            if malicious_result:
                results.append(malicious_result)
            
            # Rate limiting check
            if self.config.enable_rate_limiting:
                rate_limit_result = self._check_rate_limiting(context)
                if rate_limit_result:
                    results.append(rate_limit_result)
            
        except Exception as e:
            logger.error(f"Security check failed: {e}")
            results.append(SecurityCheckResult(
                check_type=SecurityCheckType.UNAUTHORIZED_ACCESS,
                threat_level=SecurityThreatLevel.HIGH,
                is_blocked=True,
                confidence=1.0,
                description="Security check system error",
                evidence=[str(e)],
                recommendations=["Review security system logs", "Contact security team"]
            ))
        
        return results
    
    def check_output_security(self, output_text: str, context: Dict[str, Any] = None) -> List[SecurityCheckResult]:
        """
        Perform security checks on output text.
        
        Args:
            output_text: Output text to check
            context: Additional context for checks
            
        Returns:
            List of security check results
        """
        results = []
        context = context or {}
        
        try:
            # OWASP LLM-02: Insecure Output Handling
            if self.config.enable_output_sanitization:
                output_result = self._check_output_security(output_text)
                if output_result:
                    results.append(output_result)
            
            # OWASP LLM-06: Sensitive Information Disclosure
            if self.config.enable_sensitive_data_detection:
                sensitive_result = self._check_sensitive_data(output_text)
                if sensitive_result:
                    results.append(sensitive_result)
            
            # Hallucination detection
            if self.config.enable_hallucination_detection:
                hallucination_result = self._check_hallucination(output_text, context)
                if hallucination_result:
                    results.append(hallucination_result)
            
        except Exception as e:
            logger.error(f"Output security check failed: {e}")
            results.append(SecurityCheckResult(
                check_type=SecurityCheckType.DATA_LEAKAGE,
                threat_level=SecurityThreatLevel.HIGH,
                is_blocked=True,
                confidence=1.0,
                description="Output security check system error",
                evidence=[str(e)],
                recommendations=["Review output security logs", "Contact security team"]
            ))
        
        return results
    
    def _check_prompt_injection(self, text: str) -> Optional[SecurityCheckResult]:
        """Check for prompt injection attempts."""
        try:
            detected_patterns = []
            
            for pattern in self.injection_patterns:
                matches = pattern.findall(text)
                if matches:
                    detected_patterns.extend(matches)
            
            if detected_patterns:
                confidence = min(len(detected_patterns) * 0.3, 1.0)
                
                if confidence >= self.config.prompt_injection_threshold:
                    return SecurityCheckResult(
                        check_type=SecurityCheckType.PROMPT_INJECTION,
                        threat_level=SecurityThreatLevel.HIGH,
                        is_blocked=True,
                        confidence=confidence,
                        description="Potential prompt injection detected",
                        evidence=detected_patterns[:5],  # Limit evidence
                        recommendations=[
                            "Block the request",
                            "Log security incident",
                            "Review user permissions"
                        ]
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Prompt injection check failed: {e}")
            return None
    
    def _check_dos_protection(self, text: str, context: Dict[str, Any]) -> Optional[SecurityCheckResult]:
        """Check for denial of service attempts."""
        try:
            # Check input length
            if len(text) > self.config.max_input_length:
                return SecurityCheckResult(
                    check_type=SecurityCheckType.DENIAL_OF_SERVICE,
                    threat_level=SecurityThreatLevel.MEDIUM,
                    is_blocked=True,
                    confidence=1.0,
                    description=f"Input exceeds maximum length ({len(text)} > {self.config.max_input_length})",
                    evidence=[f"Input length: {len(text)}"],
                    recommendations=["Reject oversized requests", "Implement input size limits"]
                )
            
            # Check for resource-intensive patterns
            resource_intensive_patterns = [
                r"(.{1,10})\1{100,}",  # Repeated patterns
                r"\s{1000,}",  # Excessive whitespace
                r"[^\x00-\x7F]{1000,}",  # Excessive unicode
            ]
            
            for pattern in resource_intensive_patterns:
                if re.search(pattern, text):
                    return SecurityCheckResult(
                        check_type=SecurityCheckType.DENIAL_OF_SERVICE,
                        threat_level=SecurityThreatLevel.MEDIUM,
                        is_blocked=True,
                        confidence=0.8,
                        description="Resource-intensive input pattern detected",
                        evidence=["Suspicious pattern in input"],
                        recommendations=["Block request", "Implement pattern filtering"]
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"DoS protection check failed: {e}")
            return None
    
    def _check_sensitive_data(self, text: str) -> Optional[SecurityCheckResult]:
        """Check for sensitive data exposure."""
        try:
            detected_sensitive = []
            
            for pattern in self.sensitive_patterns:
                matches = pattern.findall(text)
                if matches:
                    detected_sensitive.extend(matches)
            
            if detected_sensitive:
                return SecurityCheckResult(
                    check_type=SecurityCheckType.SENSITIVE_DATA,
                    threat_level=SecurityThreatLevel.HIGH,
                    is_blocked=True,
                    confidence=0.9,
                    description="Sensitive data detected in content",
                    evidence=[f"Found {len(detected_sensitive)} sensitive patterns"],
                    recommendations=[
                        "Redact sensitive information",
                        "Log data exposure incident",
                        "Review data handling procedures"
                    ]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Sensitive data check failed: {e}")
            return None
    
    def _check_malicious_content(self, text: str) -> Optional[SecurityCheckResult]:
        """Check for malicious content."""
        try:
            detected_malicious = []
            
            for pattern in self.malicious_patterns:
                matches = pattern.findall(text)
                if matches:
                    detected_malicious.extend(matches)
            
            if detected_malicious:
                return SecurityCheckResult(
                    check_type=SecurityCheckType.MALICIOUS_INPUT,
                    threat_level=SecurityThreatLevel.HIGH,
                    is_blocked=True,
                    confidence=0.85,
                    description="Malicious content patterns detected",
                    evidence=detected_malicious[:3],  # Limit evidence
                    recommendations=[
                        "Block request immediately",
                        "Log security incident",
                        "Investigate user account"
                    ]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Malicious content check failed: {e}")
            return None
    
    def _check_rate_limiting(self, context: Dict[str, Any]) -> Optional[SecurityCheckResult]:
        """Check rate limiting."""
        try:
            user_id = context.get('user_id', 'anonymous')
            current_time = datetime.utcnow()
            
            # Initialize user tracking
            if user_id not in self.request_counts:
                self.request_counts[user_id] = []
            
            # Clean old requests
            cutoff_time = current_time.timestamp() - self.config.rate_limit_window_seconds
            self.request_counts[user_id] = [
                req_time for req_time in self.request_counts[user_id]
                if req_time.timestamp() > cutoff_time
            ]
            
            # Add current request
            self.request_counts[user_id].append(current_time)
            
            # Check rate limit
            if len(self.request_counts[user_id]) > self.config.max_requests_per_minute:
                return SecurityCheckResult(
                    check_type=SecurityCheckType.DENIAL_OF_SERVICE,
                    threat_level=SecurityThreatLevel.MEDIUM,
                    is_blocked=True,
                    confidence=1.0,
                    description=f"Rate limit exceeded for user {user_id}",
                    evidence=[f"Requests in window: {len(self.request_counts[user_id])}"],
                    recommendations=["Implement rate limiting", "Consider user suspension"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            return None
    
    def _check_output_security(self, text: str) -> Optional[SecurityCheckResult]:
        """Check output for security issues."""
        try:
            # Check output length
            if len(text) > self.config.max_output_length:
                return SecurityCheckResult(
                    check_type=SecurityCheckType.DATA_LEAKAGE,
                    threat_level=SecurityThreatLevel.MEDIUM,
                    is_blocked=True,
                    confidence=1.0,
                    description=f"Output exceeds maximum length ({len(text)} > {self.config.max_output_length})",
                    evidence=[f"Output length: {len(text)}"],
                    recommendations=["Truncate output", "Review output generation"]
                )
            
            # Check for potential code execution in output
            code_patterns = [
                r"<script[^>]*>",
                r"javascript:",
                r"eval\s*\(",
                r"exec\s*\(",
            ]
            
            for pattern in code_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return SecurityCheckResult(
                        check_type=SecurityCheckType.DATA_LEAKAGE,
                        threat_level=SecurityThreatLevel.HIGH,
                        is_blocked=True,
                        confidence=0.9,
                        description="Potentially executable code in output",
                        evidence=["Code pattern detected"],
                        recommendations=["Sanitize output", "Review generation logic"]
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Output security check failed: {e}")
            return None
    
    def _check_hallucination(self, text: str, context: Dict[str, Any]) -> Optional[SecurityCheckResult]:
        """Check for potential hallucinations."""
        try:
            # Check for source citations if required
            if self.config.require_source_citations:
                citation_patterns = [
                    r"\[source:\s*[^\]]+\]",
                    r"\(ref:\s*[^)]+\)",
                    r"according\s+to\s+[A-Za-z0-9\s]+",
                    r"as\s+stated\s+in\s+[A-Za-z0-9\s]+",
                ]
                
                has_citations = any(
                    re.search(pattern, text, re.IGNORECASE)
                    for pattern in citation_patterns
                )
                
                # Check for factual claims without citations
                factual_claim_patterns = [
                    r"(?:the\s+)?(?:policy|regulation|rule)\s+(?:states|requires|mandates)",
                    r"(?:according\s+to|based\s+on)\s+(?:our\s+)?(?:records|data|policy)",
                    r"(?:the\s+)?(?:coverage|benefit)\s+(?:includes|excludes|covers)",
                ]
                
                has_factual_claims = any(
                    re.search(pattern, text, re.IGNORECASE)
                    for pattern in factual_claim_patterns
                )
                
                if has_factual_claims and not has_citations:
                    return SecurityCheckResult(
                        check_type=SecurityCheckType.HALLUCINATION,
                        threat_level=SecurityThreatLevel.MEDIUM,
                        is_blocked=False,  # Warning, not blocking
                        confidence=0.7,
                        description="Factual claims without source citations detected",
                        evidence=["Uncited factual claims"],
                        recommendations=[
                            "Add source citations",
                            "Verify facts against knowledge base",
                            "Flag for human review"
                        ]
                    )
            
            # Check for confidence indicators
            low_confidence_patterns = [
                r"(?:i\s+think|i\s+believe|probably|maybe|perhaps)",
                r"(?:it\s+seems|appears\s+to\s+be|might\s+be)",
                r"(?:not\s+sure|uncertain|unclear)",
            ]
            
            has_uncertainty = any(
                re.search(pattern, text, re.IGNORECASE)
                for pattern in low_confidence_patterns
            )
            
            if has_uncertainty:
                return SecurityCheckResult(
                    check_type=SecurityCheckType.HALLUCINATION,
                    threat_level=SecurityThreatLevel.LOW,
                    is_blocked=False,
                    confidence=0.6,
                    description="Uncertainty indicators in response",
                    evidence=["Uncertainty language detected"],
                    recommendations=[
                        "Flag for human review",
                        "Request additional verification",
                        "Lower confidence score"
                    ]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Hallucination check failed: {e}")
            return None
    
    def sanitize_output(self, text: str) -> str:
        """Sanitize output text for security."""
        try:
            # Remove potential script tags
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
            
            # Remove javascript: URLs
            text = re.sub(r"javascript\s*:", "", text, flags=re.IGNORECASE)
            
            # Remove event handlers
            text = re.sub(r"on\w+\s*=\s*[\"'][^\"']*[\"']", "", text, flags=re.IGNORECASE)
            
            # Limit output length
            if len(text) > self.config.max_output_length:
                text = text[:self.config.max_output_length] + "... [truncated]"
            
            return text
            
        except Exception as e:
            logger.error(f"Output sanitization failed: {e}")
            return text
    
    def mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive data in text."""
        try:
            # Mask credit card numbers
            text = re.sub(r"\b(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})\b", r"\1-****-****-\4", text)
            
            # Mask SSN
            text = re.sub(r"\b(\d{3})-(\d{2})-(\d{4})\b", r"\1-**-\3", text)
            
            # Mask email addresses
            text = re.sub(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b", r"***@\2", text)
            
            # Mask phone numbers
            text = re.sub(r"\b(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b", r"\1-***-\3", text)
            
            # Mask API keys
            text = re.sub(r"((?:api[_-]?key|token|secret)[\"'\s]*[:=][\"'\s]*)([A-Za-z0-9+/]{8})[A-Za-z0-9+/]{12,}", r"\1\2************", text, flags=re.IGNORECASE)
            
            return text
            
        except Exception as e:
            logger.error(f"Sensitive data masking failed: {e}")
            return text
    
    def get_security_summary(self, results: List[SecurityCheckResult]) -> Dict[str, Any]:
        """Get summary of security check results."""
        try:
            summary = {
                "total_checks": len(results),
                "blocked_checks": sum(1 for r in results if r.is_blocked),
                "threat_levels": {},
                "check_types": {},
                "highest_threat": SecurityThreatLevel.LOW,
                "recommendations": [],
            }
            
            for result in results:
                # Count threat levels
                threat_level = result.threat_level.value
                summary["threat_levels"][threat_level] = summary["threat_levels"].get(threat_level, 0) + 1
                
                # Count check types
                check_type = result.check_type.value
                summary["check_types"][check_type] = summary["check_types"].get(check_type, 0) + 1
                
                # Track highest threat
                threat_levels = [SecurityThreatLevel.LOW, SecurityThreatLevel.MEDIUM, SecurityThreatLevel.HIGH, SecurityThreatLevel.CRITICAL]
                if threat_levels.index(result.threat_level) > threat_levels.index(summary["highest_threat"]):
                    summary["highest_threat"] = result.threat_level
                
                # Collect recommendations
                summary["recommendations"].extend(result.recommendations)
            
            # Remove duplicate recommendations
            summary["recommendations"] = list(set(summary["recommendations"]))
            
            return summary
            
        except Exception as e:
            logger.error(f"Security summary generation failed: {e}")
            return {"error": str(e)}


# Factory function
def create_security_guardrails(config: Optional[SecurityConfig] = None) -> SecurityGuardrails:
    """Create security guardrails with default or custom configuration."""
    if config is None:
        config = SecurityConfig()
    
    return SecurityGuardrails(config)


# Utility functions
def is_security_threat_blocking(results: List[SecurityCheckResult]) -> bool:
    """Check if any security results require blocking."""
    return any(result.is_blocked for result in results)


def get_highest_threat_level(results: List[SecurityCheckResult]) -> SecurityThreatLevel:
    """Get the highest threat level from results."""
    if not results:
        return SecurityThreatLevel.LOW
    
    threat_levels = [SecurityThreatLevel.LOW, SecurityThreatLevel.MEDIUM, SecurityThreatLevel.HIGH, SecurityThreatLevel.CRITICAL]
    highest_index = max(threat_levels.index(result.threat_level) for result in results)
    
    return threat_levels[highest_index]


def format_security_report(results: List[SecurityCheckResult]) -> str:
    """Format security check results into a human-readable report."""
    if not results:
        return "No security issues detected."
    
    report_lines = ["Security Check Report", "=" * 20, ""]
    
    for result in results:
        report_lines.extend([
            f"Check Type: {result.check_type.value}",
            f"Threat Level: {result.threat_level.value}",
            f"Blocked: {'Yes' if result.is_blocked else 'No'}",
            f"Confidence: {result.confidence:.2f}",
            f"Description: {result.description}",
            ""
        ])
        
        if result.evidence:
            report_lines.append("Evidence:")
            for evidence in result.evidence:
                report_lines.append(f"  - {evidence}")
            report_lines.append("")
        
        if result.recommendations:
            report_lines.append("Recommendations:")
            for rec in result.recommendations:
                report_lines.append(f"  - {rec}")
            report_lines.append("")
        
        report_lines.append("-" * 40)
        report_lines.append("")
    
    return "\n".join(report_lines)
