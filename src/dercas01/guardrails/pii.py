"""
PII Detection and Masking for DERCAS 01 Policy Validation Copilot

Implements comprehensive PII detection, classification, and masking capabilities
to protect sensitive personal information in accordance with privacy regulations.
"""

import logging
import re
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of personally identifiable information."""
    
    # Identity information
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    MAIDEN_NAME = "maiden_name"
    
    # Government identifiers
    SSN = "ssn"
    PASSPORT_NUMBER = "passport_number"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    TAX_ID = "tax_id"
    
    # Contact information
    EMAIL_ADDRESS = "email_address"
    PHONE_NUMBER = "phone_number"
    HOME_ADDRESS = "home_address"
    MAILING_ADDRESS = "mailing_address"
    
    # Financial information
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    ROUTING_NUMBER = "routing_number"
    IBAN = "iban"
    
    # Medical information
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    HEALTH_PLAN_ID = "health_plan_id"
    PRESCRIPTION_NUMBER = "prescription_number"
    
    # Biometric data
    FINGERPRINT = "fingerprint"
    FACIAL_RECOGNITION = "facial_recognition"
    VOICE_PRINT = "voice_print"
    
    # Digital identifiers
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    DEVICE_ID = "device_id"
    USER_ID = "user_id"
    
    # Dates
    DATE_OF_BIRTH = "date_of_birth"
    DATE_OF_DEATH = "date_of_death"
    
    # Location data
    GPS_COORDINATES = "gps_coordinates"
    ZIP_CODE = "zip_code"
    
    # Other sensitive data
    MOTHER_MAIDEN_NAME = "mother_maiden_name"
    SECURITY_QUESTION_ANSWER = "security_question_answer"
    PASSWORD = "password"
    API_KEY = "api_key"


class PIISensitivityLevel(str, Enum):
    """Sensitivity levels for PII data."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaskingStrategy(str, Enum):
    """Strategies for masking PII data."""
    REDACT = "REDACT"  # Replace with [REDACTED]
    MASK = "MASK"  # Replace with asterisks
    HASH = "HASH"  # Replace with hash
    PARTIAL = "PARTIAL"  # Show only partial data
    TOKENIZE = "TOKENIZE"  # Replace with token
    REMOVE = "REMOVE"  # Remove completely


class PIIDetection(BaseModel):
    """Result of PII detection."""
    
    pii_type: PIIType
    sensitivity_level: PIISensitivityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Location in text
    start_position: int
    end_position: int
    original_text: str
    
    # Context
    context_before: str = ""
    context_after: str = ""
    
    # Detection metadata
    detection_method: str
    pattern_matched: Optional[str] = None
    
    # Masking information
    suggested_strategy: MaskingStrategy
    masked_text: str


class PIIConfig(BaseModel):
    """Configuration for PII detection and masking."""
    
    # Detection settings
    enable_detection: bool = True
    confidence_threshold: float = 0.7
    context_window: int = 20
    
    # Sensitivity mappings
    sensitivity_mapping: Dict[PIIType, PIISensitivityLevel] = Field(default_factory=lambda: {
        PIIType.SSN: PIISensitivityLevel.CRITICAL,
        PIIType.CREDIT_CARD: PIISensitivityLevel.CRITICAL,
        PIIType.PASSPORT_NUMBER: PIISensitivityLevel.CRITICAL,
        PIIType.MEDICAL_RECORD_NUMBER: PIISensitivityLevel.HIGH,
        PIIType.BANK_ACCOUNT: PIISensitivityLevel.HIGH,
        PIIType.EMAIL_ADDRESS: PIISensitivityLevel.MEDIUM,
        PIIType.PHONE_NUMBER: PIISensitivityLevel.MEDIUM,
        PIIType.FULL_NAME: PIISensitivityLevel.MEDIUM,
        PIIType.HOME_ADDRESS: PIISensitivityLevel.HIGH,
        PIIType.DATE_OF_BIRTH: PIISensitivityLevel.HIGH,
        PIIType.IP_ADDRESS: PIISensitivityLevel.LOW,
        PIIType.ZIP_CODE: PIISensitivityLevel.LOW,
    })
    
    # Masking strategies by sensitivity
    masking_strategies: Dict[PIISensitivityLevel, MaskingStrategy] = Field(default_factory=lambda: {
        PIISensitivityLevel.CRITICAL: MaskingStrategy.REDACT,
        PIISensitivityLevel.HIGH: MaskingStrategy.MASK,
        PIISensitivityLevel.MEDIUM: MaskingStrategy.PARTIAL,
        PIISensitivityLevel.LOW: MaskingStrategy.PARTIAL,
    })
    
    # Allowlisted patterns (won't be masked)
    allowlisted_patterns: List[str] = Field(default_factory=list)
    
    # Custom patterns
    custom_patterns: Dict[str, str] = Field(default_factory=dict)


class PIIDetector:
    """
    PII detection and masking service.
    
    Provides comprehensive PII detection using pattern matching,
    named entity recognition, and contextual analysis.
    """
    
    def __init__(self, config: PIIConfig):
        self.config = config
        self.detection_patterns = self._initialize_detection_patterns()
        self.name_patterns = self._initialize_name_patterns()
        self.tokenization_cache: Dict[str, str] = {}
    
    def _initialize_detection_patterns(self) -> Dict[PIIType, List[re.Pattern]]:
        """Initialize regex patterns for PII detection."""
        patterns = {}
        
        # Social Security Numbers
        patterns[PIIType.SSN] = [
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            re.compile(r'\b\d{3}\s\d{2}\s\d{4}\b'),
            re.compile(r'\b\d{9}\b'),
        ]
        
        # Credit Card Numbers
        patterns[PIIType.CREDIT_CARD] = [
            re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            re.compile(r'\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        ]
        
        # Email Addresses
        patterns[PIIType.EMAIL_ADDRESS] = [
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        ]
        
        # Phone Numbers
        patterns[PIIType.PHONE_NUMBER] = [
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),
            re.compile(r'\(\d{3}\)\s?\d{3}-\d{4}'),
        ]
        
        # Passport Numbers
        patterns[PIIType.PASSPORT_NUMBER] = [
            re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
            re.compile(r'\b\d{9}\b'),
        ]
        
        # Driver's License (simplified patterns)
        patterns[PIIType.DRIVERS_LICENSE] = [
            re.compile(r'\b[A-Z]\d{7,8}\b'),
            re.compile(r'\b\d{8,10}\b'),
        ]
        
        # Bank Account Numbers
        patterns[PIIType.BANK_ACCOUNT] = [
            re.compile(r'\b\d{8,17}\b'),
        ]
        
        # Routing Numbers
        patterns[PIIType.ROUTING_NUMBER] = [
            re.compile(r'\b\d{9}\b'),
        ]
        
        # IP Addresses
        patterns[PIIType.IP_ADDRESS] = [
            re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'),  # IPv6
        ]
        
        # MAC Addresses
        patterns[PIIType.MAC_ADDRESS] = [
            re.compile(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'),
        ]
        
        # Dates of Birth
        patterns[PIIType.DATE_OF_BIRTH] = [
            re.compile(r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'),
            re.compile(r'\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b'),
        ]
        
        # ZIP Codes
        patterns[PIIType.ZIP_CODE] = [
            re.compile(r'\b\d{5}(?:-\d{4})?\b'),
        ]
        
        # Medical Record Numbers
        patterns[PIIType.MEDICAL_RECORD_NUMBER] = [
            re.compile(r'\bMRN\s*:?\s*\d{6,10}\b', re.IGNORECASE),
            re.compile(r'\bMedical\s+Record\s*:?\s*\d{6,10}\b', re.IGNORECASE),
        ]
        
        # Health Plan IDs
        patterns[PIIType.HEALTH_PLAN_ID] = [
            re.compile(r'\b[A-Z]{2,4}\d{6,12}\b'),
        ]
        
        # API Keys and Tokens
        patterns[PIIType.API_KEY] = [
            re.compile(r'(?:api[_-]?key|token|secret)["\'\s]*[:=]["\'\s]*[A-Za-z0-9+/]{20,}', re.IGNORECASE),
            re.compile(r'sk-[A-Za-z0-9]{48}'),  # OpenAI API key
            re.compile(r'xoxb-[A-Za-z0-9-]{50,}'),  # Slack bot token
        ]
        
        # GPS Coordinates
        patterns[PIIType.GPS_COORDINATES] = [
            re.compile(r'\b-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+\b'),
        ]
        
        return patterns
    
    def _initialize_name_patterns(self) -> List[re.Pattern]:
        """Initialize patterns for detecting names."""
        return [
            # Common name patterns
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # First Last
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b'),  # First M. Last
            re.compile(r'\b[A-Z][a-z]+,\s+[A-Z][a-z]+\b'),  # Last, First
            
            # Titles with names
            re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b'),
        ]
    
    def detect_pii(self, text: str) -> List[PIIDetection]:
        """
        Detect PII in the given text.
        
        Args:
            text: Text to analyze for PII
            
        Returns:
            List of PII detections
        """
        detections = []
        
        try:
            # Pattern-based detection
            pattern_detections = self._detect_by_patterns(text)
            detections.extend(pattern_detections)
            
            # Name detection
            name_detections = self._detect_names(text)
            detections.extend(name_detections)
            
            # Context-based detection
            context_detections = self._detect_by_context(text)
            detections.extend(context_detections)
            
            # Remove overlapping detections
            detections = self._remove_overlaps(detections)
            
            # Filter by confidence threshold
            detections = [
                d for d in detections 
                if d.confidence >= self.config.confidence_threshold
            ]
            
            # Sort by position
            detections.sort(key=lambda x: x.start_position)
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
        
        return detections
    
    def _detect_by_patterns(self, text: str) -> List[PIIDetection]:
        """Detect PII using regex patterns."""
        detections = []
        
        for pii_type, patterns in self.detection_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Check if this match is allowlisted
                    if self._is_allowlisted(match.group()):
                        continue
                    
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_pattern_confidence(pii_type, match.group())
                    
                    # Get context
                    context_before, context_after = self._get_context(text, match.start(), match.end())
                    
                    # Determine masking strategy
                    sensitivity = self.config.sensitivity_mapping.get(pii_type, PIISensitivityLevel.MEDIUM)
                    strategy = self.config.masking_strategies.get(sensitivity, MaskingStrategy.MASK)
                    
                    # Create masked text
                    masked_text = self._apply_masking(match.group(), strategy, pii_type)
                    
                    detection = PIIDetection(
                        pii_type=pii_type,
                        sensitivity_level=sensitivity,
                        confidence=confidence,
                        start_position=match.start(),
                        end_position=match.end(),
                        original_text=match.group(),
                        context_before=context_before,
                        context_after=context_after,
                        detection_method="pattern_matching",
                        pattern_matched=pattern.pattern,
                        suggested_strategy=strategy,
                        masked_text=masked_text
                    )
                    
                    detections.append(detection)
        
        return detections
    
    def _detect_names(self, text: str) -> List[PIIDetection]:
        """Detect names using pattern matching and context."""
        detections = []
        
        for pattern in self.name_patterns:
            for match in pattern.finditer(text):
                # Additional validation for names
                name_text = match.group().strip()
                
                # Skip if it looks like a company name or other non-personal entity
                if self._is_likely_person_name(name_text):
                    confidence = 0.6  # Lower confidence for name detection
                    
                    # Increase confidence based on context
                    context_before, context_after = self._get_context(text, match.start(), match.end())
                    if self._has_name_context(context_before, context_after):
                        confidence = 0.8
                    
                    sensitivity = self.config.sensitivity_mapping.get(PIIType.FULL_NAME, PIISensitivityLevel.MEDIUM)
                    strategy = self.config.masking_strategies.get(sensitivity, MaskingStrategy.PARTIAL)
                    masked_text = self._apply_masking(name_text, strategy, PIIType.FULL_NAME)
                    
                    detection = PIIDetection(
                        pii_type=PIIType.FULL_NAME,
                        sensitivity_level=sensitivity,
                        confidence=confidence,
                        start_position=match.start(),
                        end_position=match.end(),
                        original_text=name_text,
                        context_before=context_before,
                        context_after=context_after,
                        detection_method="name_pattern",
                        suggested_strategy=strategy,
                        masked_text=masked_text
                    )
                    
                    detections.append(detection)
        
        return detections
    
    def _detect_by_context(self, text: str) -> List[PIIDetection]:
        """Detect PII using contextual clues."""
        detections = []
        
        # Context patterns for different PII types
        context_patterns = {
            PIIType.SSN: [
                r'(?:ssn|social\s+security)[\s:]*(\d{3}-?\d{2}-?\d{4})',
                r'(?:social\s+security\s+number)[\s:]*(\d{3}-?\d{2}-?\d{4})',
            ],
            PIIType.DATE_OF_BIRTH: [
                r'(?:dob|date\s+of\s+birth|born)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(?:birth\s+date)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            PIIType.PHONE_NUMBER: [
                r'(?:phone|tel|telephone|mobile|cell)[\s:]*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            ],
            PIIType.EMAIL_ADDRESS: [
                r'(?:email|e-mail)[\s:]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
            ],
        }
        
        for pii_type, patterns in context_patterns.items():
            for pattern_str in patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                for match in pattern.finditer(text):
                    if match.groups():
                        pii_text = match.group(1)
                        
                        # Higher confidence due to context
                        confidence = 0.9
                        
                        context_before, context_after = self._get_context(text, match.start(1), match.end(1))
                        sensitivity = self.config.sensitivity_mapping.get(pii_type, PIISensitivityLevel.MEDIUM)
                        strategy = self.config.masking_strategies.get(sensitivity, MaskingStrategy.MASK)
                        masked_text = self._apply_masking(pii_text, strategy, pii_type)
                        
                        detection = PIIDetection(
                            pii_type=pii_type,
                            sensitivity_level=sensitivity,
                            confidence=confidence,
                            start_position=match.start(1),
                            end_position=match.end(1),
                            original_text=pii_text,
                            context_before=context_before,
                            context_after=context_after,
                            detection_method="context_pattern",
                            pattern_matched=pattern_str,
                            suggested_strategy=strategy,
                            masked_text=masked_text
                        )
                        
                        detections.append(detection)
        
        return detections
    
    def _calculate_pattern_confidence(self, pii_type: PIIType, text: str) -> float:
        """Calculate confidence score for pattern match."""
        base_confidence = 0.7
        
        # Adjust confidence based on PII type and text characteristics
        if pii_type == PIIType.SSN:
            # SSN patterns are highly specific
            if re.match(r'^\d{3}-\d{2}-\d{4}$', text):
                return 0.95
            elif re.match(r'^\d{9}$', text):
                return 0.8
        
        elif pii_type == PIIType.CREDIT_CARD:
            # Validate using Luhn algorithm (simplified)
            if self._is_valid_credit_card(text):
                return 0.9
            else:
                return 0.6
        
        elif pii_type == PIIType.EMAIL_ADDRESS:
            # Email patterns are generally reliable
            return 0.85
        
        elif pii_type == PIIType.PHONE_NUMBER:
            # Phone number patterns can have false positives
            return 0.75
        
        return base_confidence
    
    def _is_valid_credit_card(self, number: str) -> bool:
        """Simplified Luhn algorithm check for credit card validation."""
        try:
            # Remove non-digits
            digits = re.sub(r'\D', '', number)
            
            if len(digits) < 13 or len(digits) > 19:
                return False
            
            # Luhn algorithm
            total = 0
            reverse_digits = digits[::-1]
            
            for i, digit in enumerate(reverse_digits):
                n = int(digit)
                if i % 2 == 1:
                    n *= 2
                    if n > 9:
                        n = n // 10 + n % 10
                total += n
            
            return total % 10 == 0
            
        except Exception:
            return False
    
    def _is_likely_person_name(self, text: str) -> bool:
        """Check if text is likely a person's name."""
        # Simple heuristics
        words = text.split()
        
        # Skip single words
        if len(words) < 2:
            return False
        
        # Skip if contains numbers
        if any(char.isdigit() for char in text):
            return False
        
        # Skip common non-name patterns
        non_name_patterns = [
            r'\b(?:Inc|LLC|Corp|Ltd|Company|Department|Office|Bureau)\b',
            r'\b(?:Street|Avenue|Road|Drive|Lane|Boulevard)\b',
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b',
        ]
        
        for pattern in non_name_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        return True
    
    def _has_name_context(self, context_before: str, context_after: str) -> bool:
        """Check if context suggests this is a person's name."""
        name_context_patterns = [
            r'(?:mr|mrs|ms|dr|prof)\.',
            r'(?:patient|client|customer|person|individual)',
            r'(?:name|called|known\s+as)',
            r'(?:signed|signature)',
        ]
        
        full_context = context_before + " " + context_after
        
        return any(
            re.search(pattern, full_context, re.IGNORECASE)
            for pattern in name_context_patterns
        )
    
    def _get_context(self, text: str, start: int, end: int) -> Tuple[str, str]:
        """Get context around a detected PII."""
        window = self.config.context_window
        
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        context_before = text[context_start:start]
        context_after = text[end:context_end]
        
        return context_before, context_after
    
    def _is_allowlisted(self, text: str) -> bool:
        """Check if text matches allowlisted patterns."""
        for pattern in self.config.allowlisted_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _remove_overlaps(self, detections: List[PIIDetection]) -> List[PIIDetection]:
        """Remove overlapping detections, keeping the highest confidence."""
        if not detections:
            return detections
        
        # Sort by start position
        sorted_detections = sorted(detections, key=lambda x: x.start_position)
        
        filtered = []
        for detection in sorted_detections:
            # Check for overlap with existing detections
            overlaps = False
            for existing in filtered:
                if (detection.start_position < existing.end_position and 
                    detection.end_position > existing.start_position):
                    # There's an overlap
                    if detection.confidence > existing.confidence:
                        # Replace existing with higher confidence detection
                        filtered.remove(existing)
                        filtered.append(detection)
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(detection)
        
        return filtered
    
    def _apply_masking(self, text: str, strategy: MaskingStrategy, pii_type: PIIType) -> str:
        """Apply masking strategy to PII text."""
        try:
            if strategy == MaskingStrategy.REDACT:
                return f"[REDACTED_{pii_type.value.upper()}]"
            
            elif strategy == MaskingStrategy.MASK:
                return "*" * len(text)
            
            elif strategy == MaskingStrategy.HASH:
                hash_obj = hashlib.sha256(text.encode())
                return f"[HASH_{hash_obj.hexdigest()[:8]}]"
            
            elif strategy == MaskingStrategy.PARTIAL:
                return self._partial_mask(text, pii_type)
            
            elif strategy == MaskingStrategy.TOKENIZE:
                return self._tokenize(text, pii_type)
            
            elif strategy == MaskingStrategy.REMOVE:
                return ""
            
            else:
                return "*" * len(text)
                
        except Exception as e:
            logger.error(f"Masking failed: {e}")
            return "*" * len(text)
    
    def _partial_mask(self, text: str, pii_type: PIIType) -> str:
        """Apply partial masking based on PII type."""
        if pii_type == PIIType.SSN:
            # Show last 4 digits: ***-**-1234
            if '-' in text:
                parts = text.split('-')
                return f"***-**-{parts[-1]}"
            else:
                return f"*****{text[-4:]}"
        
        elif pii_type == PIIType.CREDIT_CARD:
            # Show last 4 digits: ****-****-****-1234
            clean_text = re.sub(r'\D', '', text)
            return f"****-****-****-{clean_text[-4:]}"
        
        elif pii_type == PIIType.EMAIL_ADDRESS:
            # Show domain: ***@example.com
            if '@' in text:
                parts = text.split('@')
                return f"***@{parts[1]}"
            else:
                return "***@***.com"
        
        elif pii_type == PIIType.PHONE_NUMBER:
            # Show last 4 digits: ***-***-1234
            clean_text = re.sub(r'\D', '', text)
            if len(clean_text) >= 4:
                return f"***-***-{clean_text[-4:]}"
            else:
                return "***-***-****"
        
        elif pii_type == PIIType.FULL_NAME:
            # Show first letter of each word: J*** D***
            words = text.split()
            masked_words = []
            for word in words:
                if len(word) > 1:
                    masked_words.append(f"{word[0]}{'*' * (len(word) - 1)}")
                else:
                    masked_words.append("*")
            return " ".join(masked_words)
        
        else:
            # Default partial masking: show first and last character
            if len(text) <= 2:
                return "*" * len(text)
            else:
                return f"{text[0]}{'*' * (len(text) - 2)}{text[-1]}"
    
    def _tokenize(self, text: str, pii_type: PIIType) -> str:
        """Create a token for the PII text."""
        # Create a consistent token for the same text
        if text in self.tokenization_cache:
            return self.tokenization_cache[text]
        
        # Generate token
        hash_obj = hashlib.md5(text.encode())
        token = f"[TOKEN_{pii_type.value.upper()}_{hash_obj.hexdigest()[:8]}]"
        
        # Cache the token
        self.tokenization_cache[text] = token
        
        return token
    
    def mask_text(self, text: str, detections: Optional[List[PIIDetection]] = None) -> str:
        """
        Mask PII in text based on detections.
        
        Args:
            text: Original text
            detections: PII detections (if None, will detect automatically)
            
        Returns:
            Text with PII masked
        """
        if detections is None:
            detections = self.detect_pii(text)
        
        if not detections:
            return text
        
        # Sort detections by position (reverse order to maintain positions)
        sorted_detections = sorted(detections, key=lambda x: x.start_position, reverse=True)
        
        masked_text = text
        for detection in sorted_detections:
            # Replace the PII with masked version
            masked_text = (
                masked_text[:detection.start_position] +
                detection.masked_text +
                masked_text[detection.end_position:]
            )
        
        return masked_text
    
    def get_pii_summary(self, detections: List[PIIDetection]) -> Dict[str, Any]:
        """Get summary of PII detections."""
        summary = {
            "total_detections": len(detections),
            "pii_types": {},
            "sensitivity_levels": {},
            "highest_sensitivity": PIISensitivityLevel.LOW,
            "requires_special_handling": False,
        }
        
        for detection in detections:
            # Count PII types
            pii_type = detection.pii_type.value
            summary["pii_types"][pii_type] = summary["pii_types"].get(pii_type, 0) + 1
            
            # Count sensitivity levels
            sensitivity = detection.sensitivity_level.value
            summary["sensitivity_levels"][sensitivity] = summary["sensitivity_levels"].get(sensitivity, 0) + 1
            
            # Track highest sensitivity
            sensitivity_levels = [PIISensitivityLevel.LOW, PIISensitivityLevel.MEDIUM, PIISensitivityLevel.HIGH, PIISensitivityLevel.CRITICAL]
            if sensitivity_levels.index(detection.sensitivity_level) > sensitivity_levels.index(summary["highest_sensitivity"]):
                summary["highest_sensitivity"] = detection.sensitivity_level
        
        # Check if special handling is required
        summary["requires_special_handling"] = (
            summary["highest_sensitivity"] in [PIISensitivityLevel.HIGH, PIISensitivityLevel.CRITICAL] or
            summary["total_detections"] > 5
        )
        
        return summary


# Factory function
def create_pii_detector(config: Optional[PIIConfig] = None) -> PIIDetector:
    """Create a PII detector with default or custom configuration."""
    if config is None:
        config = PIIConfig()
    
    return PIIDetector(config)


# Utility functions
def quick_pii_check(text: str) -> bool:
    """Quick check if text contains potential PII."""
    detector = create_pii_detector()
    detections = detector.detect_pii(text)
    return len(detections) > 0


def mask_pii_in_text(text: str, config: Optional[PIIConfig] = None) -> str:
    """Convenience function to mask PII in text."""
    detector = create_pii_detector(config)
    return detector.mask_text(text)


def get_pii_types_in_text(text: str) -> List[PIIType]:
    """Get list of PII types found in text."""
    detector = create_pii_detector()
    detections = detector.detect_pii(text)
    return list(set(detection.pii_type for detection in detections))


def validate_pii_masking(original_text: str, masked_text: str) -> Dict[str, Any]:
    """Validate that PII has been properly masked."""
    detector = create_pii_detector()
    
    original_detections = detector.detect_pii(original_text)
    masked_detections = detector.detect_pii(masked_text)
    
    return {
        "original_pii_count": len(original_detections),
        "masked_pii_count": len(masked_detections),
        "masking_effective": len(masked_detections) < len(original_detections),
        "remaining_pii_types": [d.pii_type.value for d in masked_detections],
    }
