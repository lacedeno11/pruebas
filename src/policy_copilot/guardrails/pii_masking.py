"""
PII Masking Guardrails Implementation

This module implements PII (Personally Identifiable Information) detection and masking
guardrails for the Policy Validation Copilot system as part of UC-OP-10.
"""

from typing import Dict, Any, List, Optional, Pattern, Tuple
from pydantic import BaseModel, Field
import re
import logging
from datetime import datetime

from .base import (
    BaseGuardrail, GuardrailResult, GuardrailContext, GuardrailDecision,
    GuardrailSeverity, GuardrailRedaction
)

logger = logging.getLogger(__name__)


class PIIPattern(BaseModel):
    """PII detection pattern definition"""
    name: str = Field(..., description="Pattern name")
    pattern: str = Field(..., description="Regex pattern")
    pii_type: str = Field(..., description="Type of PII")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    mask_char: str = Field(default="*", description="Character to use for masking")
    preserve_format: bool = Field(default=True, description="Whether to preserve format")


class PIIMaskingGuardrail(BaseGuardrail):
    """
    PII Masking guardrail implementation.
    
    Detects and masks personally identifiable information in payloads
    before they are sent to LLM/ML services.
    """
    
    def __init__(self):
        super().__init__("PII_MASKING", "1.0.0")
        self.pii_patterns: List[PIIPattern] = []
        self.compiled_patterns: Dict[str, Pattern] = {}
        self.sensitive_fields = set()
        self._initialize_pii_patterns()
        self._initialize_sensitive_fields()
    
    def _initialize_pii_patterns(self):
        """Initialize PII detection patterns"""
        patterns = [
            # Social Security Numbers (US format)
            PIIPattern(
                name="ssn_us",
                pattern=r'\b\d{3}-?\d{2}-?\d{4}\b',
                pii_type="SSN",
                confidence=0.9,
                preserve_format=True
            ),
            
            # Credit Card Numbers
            PIIPattern(
                name="credit_card",
                pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                pii_type="CREDIT_CARD",
                confidence=0.85,
                preserve_format=True
            ),
            
            # Email Addresses
            PIIPattern(
                name="email",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                pii_type="EMAIL",
                confidence=0.95,
                preserve_format=False
            ),
            
            # Phone Numbers (various formats)
            PIIPattern(
                name="phone_us",
                pattern=r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                pii_type="PHONE",
                confidence=0.8,
                preserve_format=True
            ),
            
            # Driver's License (generic pattern)
            PIIPattern(
                name="drivers_license",
                pattern=r'\b[A-Z]{1,2}\d{6,8}\b',
                pii_type="DRIVERS_LICENSE",
                confidence=0.7,
                preserve_format=True
            ),
            
            # Passport Numbers
            PIIPattern(
                name="passport",
                pattern=r'\b[A-Z]{1,2}\d{6,9}\b',
                pii_type="PASSPORT",
                confidence=0.75,
                preserve_format=True
            ),
            
            # Medical Record Numbers
            PIIPattern(
                name="medical_record",
                pattern=r'\bMRN[-:\s]?\d{6,10}\b',
                pii_type="MEDICAL_RECORD",
                confidence=0.9,
                preserve_format=True
            ),
            
            # Insurance Policy Numbers
            PIIPattern(
                name="insurance_policy",
                pattern=r'\b[A-Z]{2,4}\d{6,12}\b',
                pii_type="INSURANCE_POLICY",
                confidence=0.6,
                preserve_format=True
            ),
            
            # Bank Account Numbers
            PIIPattern(
                name="bank_account",
                pattern=r'\b\d{8,17}\b',
                pii_type="BANK_ACCOUNT",
                confidence=0.5,
                preserve_format=True
            ),
            
            # Date of Birth patterns
            PIIPattern(
                name="date_of_birth",
                pattern=r'\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b',
                pii_type="DATE_OF_BIRTH",
                confidence=0.8,
                preserve_format=True
            ),
            
            # Full Names (heuristic pattern)
            PIIPattern(
                name="full_name",
                pattern=r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',
                pii_type="FULL_NAME",
                confidence=0.4,
                preserve_format=False
            ),
            
            # Address patterns
            PIIPattern(
                name="street_address",
                pattern=r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b',
                pii_type="ADDRESS",
                confidence=0.7,
                preserve_format=False
            )
        ]
        
        for pattern in patterns:
            self.add_pii_pattern(pattern)
    
    def _initialize_sensitive_fields(self):
        """Initialize list of sensitive field names"""
        self.sensitive_fields = {
            # Personal identifiers
            "ssn", "social_security_number", "tax_id", "taxpayer_id",
            "customer_id", "patient_id", "member_id", "subscriber_id",
            
            # Contact information
            "email", "email_address", "phone", "phone_number", "mobile",
            "address", "street_address", "home_address", "mailing_address",
            
            # Financial information
            "credit_card", "card_number", "account_number", "routing_number",
            "bank_account", "iban", "swift_code",
            
            # Medical information
            "medical_record_number", "mrn", "diagnosis", "medical_history",
            "prescription", "medication", "treatment",
            
            # Personal details
            "date_of_birth", "dob", "birth_date", "age",
            "full_name", "first_name", "last_name", "maiden_name",
            
            # Government IDs
            "passport", "passport_number", "drivers_license", "license_number",
            "visa_number", "green_card"
        }
    
    def add_pii_pattern(self, pattern: PIIPattern) -> None:
        """Add a PII detection pattern"""
        self.pii_patterns.append(pattern)
        try:
            self.compiled_patterns[pattern.name] = re.compile(pattern.pattern, re.IGNORECASE)
            logger.info(f"Added PII pattern: {pattern.name}")
        except re.error as e:
            logger.error(f"Invalid regex pattern for {pattern.name}: {e}")
    
    def detect_pii_in_text(self, text: str) -> List[Tuple[PIIPattern, List[str]]]:
        """
        Detect PII in text using compiled patterns.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            List of (pattern, matches) tuples
        """
        detections = []
        
        for pattern in self.pii_patterns:
            if pattern.name in self.compiled_patterns:
                compiled_pattern = self.compiled_patterns[pattern.name]
                matches = compiled_pattern.findall(text)
                
                if matches:
                    # Handle tuple matches from groups
                    if isinstance(matches[0], tuple):
                        matches = [''.join(match) for match in matches]
                    
                    detections.append((pattern, matches))
        
        return detections
    
    def mask_text(self, text: str, pattern: PIIPattern, matches: List[str]) -> str:
        """
        Mask PII in text based on pattern and matches.
        
        Args:
            text: Original text
            pattern: PII pattern that matched
            matches: List of matched strings
            
        Returns:
            Text with PII masked
        """
        masked_text = text
        
        for match in matches:
            if pattern.preserve_format:
                # Preserve format by replacing only alphanumeric characters
                masked_value = ''.join(
                    pattern.mask_char if c.isalnum() else c 
                    for c in match
                )
            else:
                # Replace entire match with mask characters
                masked_value = pattern.mask_char * len(match)
            
            masked_text = masked_text.replace(match, masked_value)
        
        return masked_text
    
    def scan_payload_recursive(
        self, 
        payload: Dict[str, Any], 
        path: str = ""
    ) -> Tuple[Dict[str, Any], List[GuardrailRedaction]]:
        """
        Recursively scan payload for PII and create redacted version.
        
        Args:
            payload: Payload to scan
            path: Current field path
            
        Returns:
            Tuple of (redacted_payload, redactions)
        """
        redacted_payload = {}
        redactions = []
        
        for key, value in payload.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                redacted_value, nested_redactions = self.scan_payload_recursive(value, current_path)
                redacted_payload[key] = redacted_value
                redactions.extend(nested_redactions)
                
            elif isinstance(value, list):
                # Process lists
                redacted_list = []
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        redacted_item, item_redactions = self.scan_payload_recursive(
                            item, f"{current_path}[{i}]"
                        )
                        redacted_list.append(redacted_item)
                        redactions.extend(item_redactions)
                    elif isinstance(item, str):
                        redacted_item, item_redactions = self._process_string_value(
                            item, f"{current_path}[{i}]", key
                        )
                        redacted_list.append(redacted_item)
                        redactions.extend(item_redactions)
                    else:
                        redacted_list.append(item)
                
                redacted_payload[key] = redacted_list
                
            elif isinstance(value, str):
                # Process string values
                redacted_value, string_redactions = self._process_string_value(
                    value, current_path, key
                )
                redacted_payload[key] = redacted_value
                redactions.extend(string_redactions)
                
            else:
                # Keep non-string values as-is
                redacted_payload[key] = value
        
        return redacted_payload, redactions
    
    def _process_string_value(
        self, 
        value: str, 
        field_path: str, 
        field_name: str
    ) -> Tuple[str, List[GuardrailRedaction]]:
        """
        Process a string value for PII detection and masking.
        
        Args:
            value: String value to process
            field_path: Path to the field
            field_name: Name of the field
            
        Returns:
            Tuple of (redacted_value, redactions)
        """
        redactions = []
        redacted_value = value
        
        # Check if field name indicates sensitive data
        is_sensitive_field = any(
            sensitive in field_name.lower() 
            for sensitive in self.sensitive_fields
        )
        
        # Detect PII in the text
        pii_detections = self.detect_pii_in_text(value)
        
        for pattern, matches in pii_detections:
            # Adjust confidence based on field sensitivity
            confidence = pattern.confidence
            if is_sensitive_field:
                confidence = min(confidence + 0.2, 1.0)
            
            # Only redact if confidence is above threshold
            if confidence >= 0.6:
                # Create redaction record
                redaction = GuardrailRedaction(
                    field_path=field_path,
                    original_value=value,
                    redacted_value=self.mask_text(redacted_value, pattern, matches),
                    redaction_type=pattern.pii_type,
                    confidence=confidence
                )
                redactions.append(redaction)
                
                # Apply masking
                redacted_value = redaction.redacted_value
        
        return redacted_value, redactions
    
    def should_redact_field(self, field_name: str, field_value: Any) -> bool:
        """
        Determine if a field should be redacted based on name and value.
        
        Args:
            field_name: Name of the field
            field_value: Value of the field
            
        Returns:
            True if field should be redacted
        """
        # Check if field name indicates sensitive data
        field_lower = field_name.lower()
        
        # Always redact known sensitive fields
        if any(sensitive in field_lower for sensitive in self.sensitive_fields):
            return True
        
        # Check for PII patterns in string values
        if isinstance(field_value, str):
            detections = self.detect_pii_in_text(field_value)
            return len(detections) > 0
        
        return False
    
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """Evaluate payload for PII and apply masking"""
        flags = []
        decision = GuardrailDecision.ALLOW
        
        # Scan payload for PII
        redacted_payload, redactions = self.scan_payload_recursive(payload)
        
        # Create flags for detected PII
        pii_types_found = set()
        high_confidence_redactions = 0
        
        for redaction in redactions:
            pii_types_found.add(redaction.redaction_type)
            
            if redaction.confidence >= 0.8:
                high_confidence_redactions += 1
        
        if redactions:
            flags.append(await self._create_flag(
                flag_type="PII_DETECTED",
                severity=GuardrailSeverity.MEDIUM,
                message=f"Detected {len(redactions)} PII instances of types: {', '.join(pii_types_found)}",
                details={
                    "pii_types": list(pii_types_found),
                    "total_redactions": len(redactions),
                    "high_confidence_redactions": high_confidence_redactions
                },
                rule_id="PII-001"
            ))
            
            # Require redaction if PII found
            if decision == GuardrailDecision.ALLOW:
                decision = GuardrailDecision.REDACT
        
        # Flag high-risk PII types
        high_risk_types = {"SSN", "CREDIT_CARD", "MEDICAL_RECORD", "PASSPORT"}
        detected_high_risk = pii_types_found.intersection(high_risk_types)
        
        if detected_high_risk:
            flags.append(await self._create_flag(
                flag_type="HIGH_RISK_PII",
                severity=GuardrailSeverity.HIGH,
                message=f"High-risk PII detected: {', '.join(detected_high_risk)}",
                details={"high_risk_types": list(detected_high_risk)},
                rule_id="PII-002"
            ))
            
            # Require human review for high-risk PII
            decision = GuardrailDecision.REQUIRE_HITL
        
        # Log PII detection event
        if redactions:
            await self._log_security_event(
                event_type="PII_DETECTION",
                severity=GuardrailSeverity.HIGH if detected_high_risk else GuardrailSeverity.MEDIUM,
                description=f"PII detected and masked: {len(redactions)} instances",
                context=context,
                flags=flags,
                metadata={
                    "pii_types": list(pii_types_found),
                    "redaction_count": len(redactions)
                }
            )
        
        return GuardrailResult(
            decision=decision,
            flags=flags,
            redactions=redactions,
            modified_payload=redacted_payload if redactions else None,
            security_context={
                "pii_check": True,
                "pii_detected": len(redactions) > 0,
                "pii_types": list(pii_types_found),
                "redaction_applied": len(redactions) > 0
            },
            guardrail_version=self.version
        )
    
    def get_rule_ids(self) -> List[str]:
        """Get PII masking rule IDs"""
        return ["PII-001", "PII-002", "PII-003"]
    
    def get_supported_pii_types(self) -> List[str]:
        """Get list of supported PII types"""
        return list(set(pattern.pii_type for pattern in self.pii_patterns))
    
    def update_pattern_confidence(self, pattern_name: str, new_confidence: float) -> bool:
        """Update confidence threshold for a specific pattern"""
        for pattern in self.pii_patterns:
            if pattern.name == pattern_name:
                pattern.confidence = max(0.0, min(1.0, new_confidence))
                logger.info(f"Updated confidence for {pattern_name} to {new_confidence}")
                return True
        return False
