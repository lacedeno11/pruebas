"""
Injection Detection Guardrails Implementation

This module implements injection detection guardrails for the Policy Validation
Copilot system as part of UC-OP-10, protecting against various injection attacks
including prompt injection, SQL injection, and other security threats.
"""

from typing import Dict, Any, List, Optional, Pattern, Tuple
from pydantic import BaseModel, Field
import re
import logging
from datetime import datetime

from .base import (
    BaseGuardrail, GuardrailResult, GuardrailContext, GuardrailDecision,
    GuardrailSeverity, GuardrailFlag
)

logger = logging.getLogger(__name__)


class InjectionPattern(BaseModel):
    """Injection detection pattern definition"""
    name: str = Field(..., description="Pattern name")
    pattern: str = Field(..., description="Regex pattern")
    injection_type: str = Field(..., description="Type of injection")
    severity: GuardrailSeverity = Field(..., description="Severity level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    description: str = Field(..., description="Pattern description")


class InjectionDetectionGuardrail(BaseGuardrail):
    """
    Injection Detection guardrail implementation.
    
    Protects against various injection attacks including:
    - Prompt injection attacks
    - SQL injection attempts
    - Command injection
    - Script injection
    - LDAP injection
    - XPath injection
    - Template injection
    """
    
    def __init__(self):
        super().__init__("INJECTION_DETECTION", "1.0.0")
        self.injection_patterns: List[InjectionPattern] = []
        self.compiled_patterns: Dict[str, Pattern] = {}
        self.suspicious_keywords = set()
        self.encoding_patterns = []
        self._initialize_injection_patterns()
        self._initialize_suspicious_keywords()
        self._initialize_encoding_patterns()
    
    def _initialize_injection_patterns(self):
        """Initialize injection detection patterns"""
        patterns = [
            # Prompt Injection Patterns
            InjectionPattern(
                name="prompt_injection_ignore",
                pattern=r'(?i)(ignore|forget|disregard)\s+(previous|above|all|your)\s+(instructions?|prompts?|rules?)',
                injection_type="PROMPT_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.9,
                description="Attempt to ignore previous instructions"
            ),
            
            InjectionPattern(
                name="prompt_injection_roleplay",
                pattern=r'(?i)(pretend|act|roleplay|imagine)\s+(you\s+are|to\s+be|as)\s+(a\s+)?(different|new|another)',
                injection_type="PROMPT_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.8,
                description="Attempt to change AI role or behavior"
            ),
            
            InjectionPattern(
                name="prompt_injection_system",
                pattern=r'(?i)(system|admin|root|developer)\s*(mode|access|privileges?|commands?)',
                injection_type="PROMPT_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.85,
                description="Attempt to access system-level functions"
            ),
            
            InjectionPattern(
                name="prompt_injection_jailbreak",
                pattern=r'(?i)(jailbreak|bypass|override|circumvent)\s+(safety|security|restrictions?|limitations?)',
                injection_type="PROMPT_INJECTION",
                severity=GuardrailSeverity.CRITICAL,
                confidence=0.95,
                description="Attempt to bypass safety restrictions"
            ),
            
            # SQL Injection Patterns
            InjectionPattern(
                name="sql_injection_union",
                pattern=r'(?i)\b(union|select|insert|update|delete|drop|create|alter)\s+.*\b(from|into|table|database)\b',
                injection_type="SQL_INJECTION",
                severity=GuardrailSeverity.CRITICAL,
                confidence=0.9,
                description="SQL injection with UNION or DML statements"
            ),
            
            InjectionPattern(
                name="sql_injection_comment",
                pattern=r'(--|#|/\*|\*/|;)',
                injection_type="SQL_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.7,
                description="SQL comment characters indicating injection attempt"
            ),
            
            InjectionPattern(
                name="sql_injection_quotes",
                pattern=r"('.*'|\".*\")\s*(or|and)\s*('.*'|\".*\"|1=1|1=0)",
                injection_type="SQL_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.8,
                description="SQL injection with quote manipulation"
            ),
            
            # Command Injection Patterns
            InjectionPattern(
                name="command_injection_pipes",
                pattern=r'[;&|`$(){}[\]\\]',
                injection_type="COMMAND_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.6,
                description="Command injection metacharacters"
            ),
            
            InjectionPattern(
                name="command_injection_commands",
                pattern=r'(?i)\b(cat|ls|dir|type|echo|wget|curl|nc|netcat|bash|sh|cmd|powershell)\b',
                injection_type="COMMAND_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.7,
                description="Common command injection commands"
            ),
            
            # Script Injection Patterns
            InjectionPattern(
                name="script_injection_tags",
                pattern=r'<\s*(script|iframe|object|embed|form|input|img)\b[^>]*>',
                injection_type="SCRIPT_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.8,
                description="HTML/JavaScript injection tags"
            ),
            
            InjectionPattern(
                name="script_injection_events",
                pattern=r'(?i)\bon(load|click|error|focus|blur|change|submit|mouseover)\s*=',
                injection_type="SCRIPT_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.85,
                description="JavaScript event handlers"
            ),
            
            InjectionPattern(
                name="script_injection_javascript",
                pattern=r'(?i)javascript\s*:',
                injection_type="SCRIPT_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.9,
                description="JavaScript protocol injection"
            ),
            
            # LDAP Injection Patterns
            InjectionPattern(
                name="ldap_injection_operators",
                pattern=r'[()&|!*]',
                injection_type="LDAP_INJECTION",
                severity=GuardrailSeverity.MEDIUM,
                confidence=0.5,
                description="LDAP injection operators"
            ),
            
            # XPath Injection Patterns
            InjectionPattern(
                name="xpath_injection_functions",
                pattern=r'(?i)\b(and|or|not|contains|starts-with|substring|count|position)\s*\(',
                injection_type="XPATH_INJECTION",
                severity=GuardrailSeverity.MEDIUM,
                confidence=0.6,
                description="XPath injection functions"
            ),
            
            # Template Injection Patterns
            InjectionPattern(
                name="template_injection_delimiters",
                pattern=r'(\{\{|\}\}|\{%|%\}|\{#|#\})',
                injection_type="TEMPLATE_INJECTION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.7,
                description="Template injection delimiters"
            ),
            
            # Path Traversal Patterns
            InjectionPattern(
                name="path_traversal",
                pattern=r'(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)',
                injection_type="PATH_TRAVERSAL",
                severity=GuardrailSeverity.HIGH,
                confidence=0.8,
                description="Path traversal sequences"
            ),
            
            # Data Exfiltration Patterns
            InjectionPattern(
                name="data_exfiltration_requests",
                pattern=r'(?i)(send|post|get|fetch|request|transmit)\s+(to|data|information|details)',
                injection_type="DATA_EXFILTRATION",
                severity=GuardrailSeverity.HIGH,
                confidence=0.6,
                description="Potential data exfiltration attempt"
            )
        ]
        
        for pattern in patterns:
            self.add_injection_pattern(pattern)
    
    def _initialize_suspicious_keywords(self):
        """Initialize suspicious keywords list"""
        self.suspicious_keywords = {
            # System access keywords
            "admin", "administrator", "root", "system", "sudo", "su",
            "privilege", "escalation", "bypass", "override", "circumvent",
            
            # Security bypass keywords
            "jailbreak", "escape", "break", "hack", "exploit", "vulnerability",
            "backdoor", "trojan", "malware", "virus", "payload",
            
            # Instruction manipulation
            "ignore", "forget", "disregard", "override", "replace", "substitute",
            "pretend", "roleplay", "act", "imagine", "simulate",
            
            # Data access keywords
            "extract", "dump", "leak", "steal", "copy", "download", "upload",
            "exfiltrate", "transmit", "send", "post", "get", "fetch",
            
            # Encoding/obfuscation
            "encode", "decode", "base64", "hex", "unicode", "url", "html",
            "obfuscate", "hide", "mask", "disguise"
        }
    
    def _initialize_encoding_patterns(self):
        """Initialize encoding detection patterns"""
        self.encoding_patterns = [
            # Base64 encoding
            r'[A-Za-z0-9+/]{20,}={0,2}',
            
            # Hex encoding
            r'(?:0x)?[0-9a-fA-F]{10,}',
            
            # URL encoding
            r'%[0-9a-fA-F]{2}',
            
            # Unicode encoding
            r'\\u[0-9a-fA-F]{4}',
            
            # HTML entity encoding
            r'&[a-zA-Z][a-zA-Z0-9]*;|&#[0-9]+;|&#x[0-9a-fA-F]+;'
        ]
    
    def add_injection_pattern(self, pattern: InjectionPattern) -> None:
        """Add an injection detection pattern"""
        self.injection_patterns.append(pattern)
        try:
            self.compiled_patterns[pattern.name] = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)
            logger.info(f"Added injection pattern: {pattern.name}")
        except re.error as e:
            logger.error(f"Invalid regex pattern for {pattern.name}: {e}")
    
    def detect_injections_in_text(self, text: str) -> List[Tuple[InjectionPattern, List[str]]]:
        """
        Detect injection attempts in text.
        
        Args:
            text: Text to scan for injections
            
        Returns:
            List of (pattern, matches) tuples
        """
        detections = []
        
        for pattern in self.injection_patterns:
            if pattern.name in self.compiled_patterns:
                compiled_pattern = self.compiled_patterns[pattern.name]
                matches = compiled_pattern.findall(text)
                
                if matches:
                    # Handle tuple matches from groups
                    if matches and isinstance(matches[0], tuple):
                        matches = [''.join(match) if isinstance(match, tuple) else match for match in matches]
                    
                    detections.append((pattern, matches))
        
        return detections
    
    def check_suspicious_keywords(self, text: str) -> List[str]:
        """
        Check for suspicious keywords in text.
        
        Args:
            text: Text to check
            
        Returns:
            List of found suspicious keywords
        """
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.suspicious_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def detect_encoding_attempts(self, text: str) -> List[str]:
        """
        Detect potential encoding/obfuscation attempts.
        
        Args:
            text: Text to check for encoding
            
        Returns:
            List of detected encoding types
        """
        detected_encodings = []
        
        encoding_types = [
            ("base64", self.encoding_patterns[0]),
            ("hex", self.encoding_patterns[1]),
            ("url", self.encoding_patterns[2]),
            ("unicode", self.encoding_patterns[3]),
            ("html_entity", self.encoding_patterns[4])
        ]
        
        for encoding_type, pattern in encoding_types:
            if re.search(pattern, text):
                detected_encodings.append(encoding_type)
        
        return detected_encodings
    
    def calculate_injection_risk_score(
        self, 
        injections: List[Tuple[InjectionPattern, List[str]]],
        suspicious_keywords: List[str],
        encodings: List[str]
    ) -> float:
        """
        Calculate overall injection risk score.
        
        Args:
            injections: Detected injection patterns
            suspicious_keywords: Found suspicious keywords
            encodings: Detected encoding attempts
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        risk_score = 0.0
        
        # Score from injection patterns
        for pattern, matches in injections:
            pattern_score = pattern.confidence * len(matches) * 0.3
            if pattern.severity == GuardrailSeverity.CRITICAL:
                pattern_score *= 2.0
            elif pattern.severity == GuardrailSeverity.HIGH:
                pattern_score *= 1.5
            
            risk_score += pattern_score
        
        # Score from suspicious keywords
        keyword_score = min(len(suspicious_keywords) * 0.1, 0.3)
        risk_score += keyword_score
        
        # Score from encoding attempts
        encoding_score = min(len(encodings) * 0.15, 0.2)
        risk_score += encoding_score
        
        # Normalize to 0-1 range
        return min(risk_score, 1.0)
    
    def scan_payload_recursive(
        self, 
        payload: Dict[str, Any], 
        path: str = ""
    ) -> Tuple[List[GuardrailFlag], float]:
        """
        Recursively scan payload for injection attempts.
        
        Args:
            payload: Payload to scan
            path: Current field path
            
        Returns:
            Tuple of (flags, max_risk_score)
        """
        all_flags = []
        max_risk_score = 0.0
        
        for key, value in payload.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                nested_flags, nested_risk = self.scan_payload_recursive(value, current_path)
                all_flags.extend(nested_flags)
                max_risk_score = max(max_risk_score, nested_risk)
                
            elif isinstance(value, list):
                # Process lists
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_flags, item_risk = self.scan_payload_recursive(
                            item, f"{current_path}[{i}]"
                        )
                        all_flags.extend(item_flags)
                        max_risk_score = max(max_risk_score, item_risk)
                    elif isinstance(item, str):
                        item_flags, item_risk = self._scan_string_value(
                            item, f"{current_path}[{i}]"
                        )
                        all_flags.extend(item_flags)
                        max_risk_score = max(max_risk_score, item_risk)
                
            elif isinstance(value, str):
                # Process string values
                string_flags, string_risk = self._scan_string_value(value, current_path)
                all_flags.extend(string_flags)
                max_risk_score = max(max_risk_score, string_risk)
        
        return all_flags, max_risk_score
    
    async def _scan_string_value(self, value: str, field_path: str) -> Tuple[List[GuardrailFlag], float]:
        """
        Scan a string value for injection attempts.
        
        Args:
            value: String value to scan
            field_path: Path to the field
            
        Returns:
            Tuple of (flags, risk_score)
        """
        flags = []
        
        # Detect injection patterns
        injections = self.detect_injections_in_text(value)
        
        # Check for suspicious keywords
        suspicious_keywords = self.check_suspicious_keywords(value)
        
        # Detect encoding attempts
        encodings = self.detect_encoding_attempts(value)
        
        # Calculate risk score
        risk_score = self.calculate_injection_risk_score(injections, suspicious_keywords, encodings)
        
        # Create flags for detected threats
        if injections:
            injection_types = list(set(pattern.injection_type for pattern, _ in injections))
            high_severity_injections = [
                pattern for pattern, _ in injections 
                if pattern.severity in [GuardrailSeverity.HIGH, GuardrailSeverity.CRITICAL]
            ]
            
            severity = GuardrailSeverity.CRITICAL if any(
                p.severity == GuardrailSeverity.CRITICAL for p in high_severity_injections
            ) else GuardrailSeverity.HIGH
            
            flags.append(await self._create_flag(
                flag_type="INJECTION_DETECTED",
                severity=severity,
                message=f"Injection attempt detected in {field_path}: {', '.join(injection_types)}",
                details={
                    "field_path": field_path,
                    "injection_types": injection_types,
                    "pattern_matches": len(injections),
                    "risk_score": risk_score,
                    "detected_patterns": [pattern.name for pattern, _ in injections]
                },
                rule_id="INJECT-001"
            ))
        
        if suspicious_keywords:
            flags.append(await self._create_flag(
                flag_type="SUSPICIOUS_KEYWORDS",
                severity=GuardrailSeverity.MEDIUM,
                message=f"Suspicious keywords detected in {field_path}: {', '.join(suspicious_keywords[:5])}",
                details={
                    "field_path": field_path,
                    "keywords": suspicious_keywords,
                    "keyword_count": len(suspicious_keywords)
                },
                rule_id="INJECT-002"
            ))
        
        if encodings:
            flags.append(await self._create_flag(
                flag_type="ENCODING_DETECTED",
                severity=GuardrailSeverity.MEDIUM,
                message=f"Potential encoding/obfuscation detected in {field_path}: {', '.join(encodings)}",
                details={
                    "field_path": field_path,
                    "encoding_types": encodings
                },
                rule_id="INJECT-003"
            ))
        
        return flags, risk_score
    
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """Evaluate payload for injection attempts"""
        flags = []
        decision = GuardrailDecision.ALLOW
        
        # Scan payload for injection attempts
        injection_flags, max_risk_score = self.scan_payload_recursive(payload)
        flags.extend(injection_flags)
        
        # Determine decision based on risk score and detected threats
        critical_injections = [
            flag for flag in flags 
            if flag.flag_type == "INJECTION_DETECTED" and flag.severity == GuardrailSeverity.CRITICAL
        ]
        
        high_risk_injections = [
            flag for flag in flags 
            if flag.flag_type == "INJECTION_DETECTED" and flag.severity == GuardrailSeverity.HIGH
        ]
        
        if critical_injections:
            decision = GuardrailDecision.BLOCK
        elif high_risk_injections or max_risk_score >= 0.7:
            decision = GuardrailDecision.REQUIRE_HITL
        elif max_risk_score >= 0.4:
            decision = GuardrailDecision.REDACT
        
        # Log injection detection event
        if flags:
            await self._log_security_event(
                event_type="INJECTION_DETECTION",
                severity=GuardrailSeverity.CRITICAL if critical_injections else GuardrailSeverity.HIGH,
                description=f"Injection detection scan: {len(flags)} threats detected, risk score: {max_risk_score:.3f}",
                context=context,
                flags=flags,
                metadata={
                    "risk_score": max_risk_score,
                    "critical_injections": len(critical_injections),
                    "high_risk_injections": len(high_risk_injections),
                    "total_flags": len(flags)
                }
            )
        
        return GuardrailResult(
            decision=decision,
            flags=flags,
            security_context={
                "injection_check": True,
                "threats_detected": len(flags) > 0,
                "risk_score": max_risk_score,
                "critical_threats": len(critical_injections),
                "high_risk_threats": len(high_risk_injections)
            },
            guardrail_version=self.version
        )
    
    def get_rule_ids(self) -> List[str]:
        """Get injection detection rule IDs"""
        return ["INJECT-001", "INJECT-002", "INJECT-003"]
    
    def get_supported_injection_types(self) -> List[str]:
        """Get list of supported injection types"""
        return list(set(pattern.injection_type for pattern in self.injection_patterns))
    
    def update_pattern_confidence(self, pattern_name: str, new_confidence: float) -> bool:
        """Update confidence threshold for a specific pattern"""
        for pattern in self.injection_patterns:
            if pattern.name == pattern_name:
                pattern.confidence = max(0.0, min(1.0, new_confidence))
                logger.info(f"Updated confidence for {pattern_name} to {new_confidence}")
                return True
        return False
