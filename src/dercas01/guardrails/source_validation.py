"""
Source Validation for DERCAS 01 Policy Validation Copilot

Implements allowlist enforcement and source verification to ensure only trusted
and verified sources are used for policy retrieval and decision making.
"""

import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from urllib.parse import urlparse

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    """Types of sources that can be validated."""
    POLICY_DOCUMENT = "policy_document"
    EXCEPTION_RULE = "exception_rule"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    WEB_SERVICE = "web_service"
    KNOWLEDGE_BASE = "knowledge_base"


class SourceStatus(str, Enum):
    """Status of source validation."""
    TRUSTED = "TRUSTED"
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"


class ValidationResult(str, Enum):
    """Result of source validation."""
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class SourceValidationResult(BaseModel):
    """Result of source validation check."""
    
    source_id: str
    source_type: SourceType
    validation_result: ValidationResult
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Validation details
    is_allowlisted: bool
    is_verified: bool
    trust_score: float = Field(ge=0.0, le=1.0)
    
    # Issues found
    security_issues: List[str] = Field(default_factory=list)
    integrity_issues: List[str] = Field(default_factory=list)
    compliance_issues: List[str] = Field(default_factory=list)
    
    # Metadata
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    validator_version: str = "1.0.0"
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    requires_manual_review: bool = False


class TrustedSource(BaseModel):
    """Definition of a trusted source."""
    
    source_id: str
    source_type: SourceType
    name: str
    description: str
    
    # Trust attributes
    trust_level: int = Field(ge=1, le=5)  # 1=lowest, 5=highest
    verification_method: str
    verified_by: str
    verified_at: datetime
    
    # Source details
    url_patterns: List[str] = Field(default_factory=list)
    file_patterns: List[str] = Field(default_factory=list)
    api_endpoints: List[str] = Field(default_factory=list)
    
    # Validity
    valid_from: datetime
    valid_until: Optional[datetime] = None
    
    # Security requirements
    requires_encryption: bool = True
    requires_authentication: bool = True
    allowed_protocols: List[str] = Field(default_factory=lambda: ["https", "sftp"])
    
    # Compliance
    compliance_tags: List[str] = Field(default_factory=list)
    data_classification: str = "INTERNAL"
    
    # Monitoring
    last_verified: Optional[datetime] = None
    verification_frequency: timedelta = Field(default=timedelta(days=30))
    
    # Status
    status: SourceStatus = SourceStatus.VERIFIED
    status_reason: Optional[str] = None


class SourceValidationConfig(BaseModel):
    """Configuration for source validation."""
    
    # Validation settings
    enable_allowlist_enforcement: bool = True
    enable_integrity_checks: bool = True
    enable_compliance_checks: bool = True
    
    # Trust thresholds
    min_trust_score: float = 0.7
    min_trust_level: int = 3
    
    # Security requirements
    require_https: bool = True
    require_valid_certificates: bool = True
    block_suspicious_domains: bool = True
    
    # File validation
    allowed_file_extensions: Set[str] = Field(default_factory=lambda: {
        ".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt", ".json", ".xml"
    })
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # Content validation
    enable_content_scanning: bool = True
    block_malicious_content: bool = True
    
    # Monitoring
    log_all_validations: bool = True
    alert_on_blocked_sources: bool = True
    
    # Cache settings
    cache_validation_results: bool = True
    cache_ttl_hours: int = 24


class SourceValidator:
    """
    Source validation service for enforcing allowlists and verifying sources.
    
    Implements comprehensive source validation including:
    - Allowlist enforcement
    - Trust score calculation
    - Integrity verification
    - Compliance checking
    - Security validation
    """
    
    def __init__(self, config: SourceValidationConfig):
        self.config = config
        self.trusted_sources: Dict[str, TrustedSource] = {}
        self.blocked_sources: Set[str] = set()
        self.validation_cache: Dict[str, SourceValidationResult] = {}
        
        # Initialize with default trusted sources
        self._initialize_default_sources()
        
        # Suspicious patterns
        self.suspicious_patterns = self._load_suspicious_patterns()
        
        # Malicious content patterns
        self.malicious_patterns = self._load_malicious_patterns()
    
    def _initialize_default_sources(self):
        """Initialize default trusted sources."""
        # Internal policy repository
        self.trusted_sources["internal_policy_repo"] = TrustedSource(
            source_id="internal_policy_repo",
            source_type=SourceType.POLICY_DOCUMENT,
            name="Internal Policy Repository",
            description="Company internal policy document repository",
            trust_level=5,
            verification_method="internal_audit",
            verified_by="security_team",
            verified_at=datetime.utcnow(),
            url_patterns=["https://policies.internal.company.com/*"],
            valid_from=datetime.utcnow(),
            requires_encryption=True,
            requires_authentication=True,
            compliance_tags=["SOX", "HIPAA", "GDPR"],
            data_classification="CONFIDENTIAL"
        )
        
        # Verified external APIs
        self.trusted_sources["insurance_api"] = TrustedSource(
            source_id="insurance_api",
            source_type=SourceType.EXTERNAL_API,
            name="Insurance Company API",
            description="Verified insurance company API endpoints",
            trust_level=4,
            verification_method="api_certification",
            verified_by="integration_team",
            verified_at=datetime.utcnow(),
            api_endpoints=["https://api.insurance-partner.com/v1/*"],
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=365),
            compliance_tags=["SOX", "PCI"],
            data_classification="RESTRICTED"
        )
        
        # Known blocked sources
        self.blocked_sources.update([
            "suspicious-domain.com",
            "malware-site.net",
            "phishing-attempt.org"
        ])
    
    def _load_suspicious_patterns(self) -> List[re.Pattern]:
        """Load patterns for detecting suspicious sources."""
        patterns = [
            # Suspicious domains
            r"(?:bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly)",  # URL shorteners
            r"(?:\.tk|\.ml|\.ga|\.cf)",  # Suspicious TLDs
            r"(?:temp|temporary|disposable)",  # Temporary services
            
            # Suspicious file patterns
            r"(?:temp|tmp|cache)[\\/]",  # Temporary directories
            r"(?:\.tmp|\.temp|\.cache)",  # Temporary files
            
            # Suspicious API patterns
            r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0)",  # Local addresses
            r"(?:test|staging|dev)\..*\.com",  # Non-production environments
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _load_malicious_patterns(self) -> List[re.Pattern]:
        """Load patterns for detecting malicious content."""
        patterns = [
            # Script injection
            r"<script[^>]*>.*?</script>",
            r"javascript\s*:",
            r"vbscript\s*:",
            
            # SQL injection
            r"(?:union|select|insert|update|delete|drop)\s+",
            r"(?:or|and)\s+(?:1=1|true)",
            
            # Command injection
            r"(?:;|\||\&\&)\s*(?:rm|del|format)",
            r"(?:wget|curl|nc)\s+",
            
            # Suspicious executables
            r"\.(?:exe|bat|cmd|scr|vbs|ps1)$",
        ]
        
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def validate_source(
        self, 
        source_id: str, 
        source_type: SourceType, 
        source_location: str,
        content: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SourceValidationResult:
        """
        Validate a source for trustworthiness and compliance.
        
        Args:
            source_id: Unique identifier for the source
            source_type: Type of source being validated
            source_location: URL, file path, or other location identifier
            content: Optional content for validation
            metadata: Additional metadata about the source
            
        Returns:
            SourceValidationResult with validation outcome
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(source_id, source_location)
            if self.config.cache_validation_results and cache_key in self.validation_cache:
                cached_result = self.validation_cache[cache_key]
                cache_age = datetime.utcnow() - cached_result.validation_timestamp
                if cache_age.total_seconds() < self.config.cache_ttl_hours * 3600:
                    return cached_result
            
            # Perform validation
            result = self._perform_validation(source_id, source_type, source_location, content, metadata)
            
            # Cache the result
            if self.config.cache_validation_results:
                self.validation_cache[cache_key] = result
            
            # Log the validation
            if self.config.log_all_validations:
                self._log_validation(result)
            
            # Alert if blocked
            if result.validation_result == ValidationResult.DENIED and self.config.alert_on_blocked_sources:
                self._send_security_alert(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Source validation failed for {source_id}: {e}")
            return SourceValidationResult(
                source_id=source_id,
                source_type=source_type,
                validation_result=ValidationResult.DENIED,
                confidence=1.0,
                is_allowlisted=False,
                is_verified=False,
                trust_score=0.0,
                security_issues=[f"Validation error: {str(e)}"],
                recommendations=["Contact security team", "Manual review required"]
            )
    
    def _perform_validation(
        self,
        source_id: str,
        source_type: SourceType,
        source_location: str,
        content: Optional[bytes],
        metadata: Optional[Dict[str, Any]]
    ) -> SourceValidationResult:
        """Perform the actual validation checks."""
        
        issues = {
            "security": [],
            "integrity": [],
            "compliance": []
        }
        
        recommendations = []
        is_allowlisted = False
        is_verified = False
        trust_score = 0.0
        
        # Step 1: Check if source is explicitly blocked
        if self._is_blocked_source(source_location):
            return SourceValidationResult(
                source_id=source_id,
                source_type=source_type,
                validation_result=ValidationResult.DENIED,
                confidence=1.0,
                is_allowlisted=False,
                is_verified=False,
                trust_score=0.0,
                security_issues=["Source is explicitly blocked"],
                recommendations=["Remove from blocked list if legitimate", "Contact security team"]
            )
        
        # Step 2: Check allowlist
        trusted_source = self._find_trusted_source(source_id, source_location)
        if trusted_source:
            is_allowlisted = True
            is_verified = True
            trust_score = trusted_source.trust_level / 5.0
            
            # Check if source is still valid
            if not self._is_source_valid(trusted_source):
                issues["compliance"].append("Source verification has expired")
                trust_score *= 0.5
        
        # Step 3: Security validation
        security_issues = self._validate_security(source_location, content)
        issues["security"].extend(security_issues)
        
        # Step 4: Integrity validation
        if content:
            integrity_issues = self._validate_integrity(content, metadata)
            issues["integrity"].extend(integrity_issues)
        
        # Step 5: Compliance validation
        compliance_issues = self._validate_compliance(source_type, source_location, metadata)
        issues["compliance"].extend(compliance_issues)
        
        # Step 6: Calculate final trust score
        if not is_allowlisted:
            trust_score = self._calculate_trust_score(source_location, issues)
        
        # Apply penalties for issues
        if issues["security"]:
            trust_score *= 0.3
        if issues["integrity"]:
            trust_score *= 0.7
        if issues["compliance"]:
            trust_score *= 0.8
        
        # Step 7: Determine validation result
        validation_result = self._determine_validation_result(
            is_allowlisted, trust_score, issues
        )
        
        # Step 8: Generate recommendations
        recommendations = self._generate_recommendations(validation_result, issues, trust_score)
        
        return SourceValidationResult(
            source_id=source_id,
            source_type=source_type,
            validation_result=validation_result,
            confidence=min(trust_score + 0.2, 1.0),
            is_allowlisted=is_allowlisted,
            is_verified=is_verified,
            trust_score=trust_score,
            security_issues=issues["security"],
            integrity_issues=issues["integrity"],
            compliance_issues=issues["compliance"],
            recommendations=recommendations,
            requires_manual_review=validation_result == ValidationResult.REQUIRES_REVIEW
        )
    
    def _is_blocked_source(self, source_location: str) -> bool:
        """Check if source is explicitly blocked."""
        # Extract domain from URL
        try:
            if source_location.startswith(('http://', 'https://')):
                domain = urlparse(source_location).netloc
                return domain in self.blocked_sources
            else:
                # For file paths or other identifiers
                return source_location in self.blocked_sources
        except Exception:
            return False
    
    def _find_trusted_source(self, source_id: str, source_location: str) -> Optional[TrustedSource]:
        """Find matching trusted source."""
        # Direct ID match
        if source_id in self.trusted_sources:
            return self.trusted_sources[source_id]
        
        # Pattern matching
        for trusted_source in self.trusted_sources.values():
            if self._matches_source_patterns(source_location, trusted_source):
                return trusted_source
        
        return None
    
    def _matches_source_patterns(self, source_location: str, trusted_source: TrustedSource) -> bool:
        """Check if source location matches trusted source patterns."""
        # URL pattern matching
        for pattern in trusted_source.url_patterns:
            if self._matches_pattern(source_location, pattern):
                return True
        
        # File pattern matching
        for pattern in trusted_source.file_patterns:
            if self._matches_pattern(source_location, pattern):
                return True
        
        # API endpoint matching
        for endpoint in trusted_source.api_endpoints:
            if self._matches_pattern(source_location, endpoint):
                return True
        
        return False
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern (supports wildcards)."""
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f"^{regex_pattern}$", text, re.IGNORECASE))
    
    def _is_source_valid(self, trusted_source: TrustedSource) -> bool:
        """Check if trusted source is still valid."""
        now = datetime.utcnow()
        
        # Check validity period
        if now < trusted_source.valid_from:
            return False
        
        if trusted_source.valid_until and now > trusted_source.valid_until:
            return False
        
        # Check verification freshness
        if trusted_source.last_verified:
            time_since_verification = now - trusted_source.last_verified
            if time_since_verification > trusted_source.verification_frequency:
                return False
        
        return True
    
    def _validate_security(self, source_location: str, content: Optional[bytes]) -> List[str]:
        """Validate security aspects of the source."""
        issues = []
        
        # URL security validation
        if source_location.startswith(('http://', 'https://')):
            parsed_url = urlparse(source_location)
            
            # Require HTTPS
            if self.config.require_https and parsed_url.scheme != 'https':
                issues.append("Non-HTTPS protocol detected")
            
            # Check for suspicious domains
            if self.config.block_suspicious_domains:
                for pattern in self.suspicious_patterns:
                    if pattern.search(source_location):
                        issues.append(f"Suspicious pattern detected: {pattern.pattern}")
        
        # Content security validation
        if content and self.config.enable_content_scanning:
            content_str = content.decode('utf-8', errors='ignore')
            
            for pattern in self.malicious_patterns:
                if pattern.search(content_str):
                    issues.append(f"Malicious content pattern detected: {pattern.pattern}")
        
        return issues
    
    def _validate_integrity(self, content: bytes, metadata: Optional[Dict[str, Any]]) -> List[str]:
        """Validate integrity of the content."""
        issues = []
        
        # File size validation
        if len(content) > self.config.max_file_size:
            issues.append(f"File size exceeds limit: {len(content)} > {self.config.max_file_size}")
        
        # Checksum validation
        if metadata and 'expected_checksum' in metadata:
            actual_checksum = hashlib.sha256(content).hexdigest()
            expected_checksum = metadata['expected_checksum']
            
            if actual_checksum != expected_checksum:
                issues.append("Checksum mismatch detected")
        
        # File format validation
        if metadata and 'filename' in metadata:
            filename = metadata['filename']
            file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
            
            if file_ext not in self.config.allowed_file_extensions:
                issues.append(f"File extension not allowed: {file_ext}")
        
        # Content corruption check
        if len(content) == 0:
            issues.append("Empty content detected")
        
        return issues
    
    def _validate_compliance(
        self, 
        source_type: SourceType, 
        source_location: str, 
        metadata: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Validate compliance requirements."""
        issues = []
        
        # Data classification validation
        if metadata and 'data_classification' in metadata:
            classification = metadata['data_classification']
            if classification in ['CONFIDENTIAL', 'RESTRICTED']:
                # Additional checks for sensitive data
                if not source_location.startswith('https://'):
                    issues.append("Sensitive data requires encrypted transport")
        
        # Retention policy validation
        if metadata and 'created_date' in metadata:
            try:
                created_date = datetime.fromisoformat(metadata['created_date'])
                age_days = (datetime.utcnow() - created_date).days
                
                # Example retention policies
                if source_type == SourceType.POLICY_DOCUMENT and age_days > 1095:  # 3 years
                    issues.append("Policy document exceeds retention period")
                elif source_type == SourceType.EXCEPTION_RULE and age_days > 365:  # 1 year
                    issues.append("Exception rule exceeds retention period")
            except Exception:
                issues.append("Invalid creation date format")
        
        return issues
    
    def _calculate_trust_score(self, source_location: str, issues: Dict[str, List[str]]) -> float:
        """Calculate trust score for non-allowlisted sources."""
        base_score = 0.5  # Neutral starting point
        
        # URL-based scoring
        if source_location.startswith('https://'):
            base_score += 0.2
        elif source_location.startswith('http://'):
            base_score -= 0.2
        
        # Domain reputation (simplified)
        if source_location.startswith(('https://gov.', 'https://edu.')):
            base_score += 0.3
        elif any(pattern.search(source_location) for pattern in self.suspicious_patterns):
            base_score -= 0.4
        
        # Penalty for issues
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        penalty = min(total_issues * 0.1, 0.5)
        
        return max(0.0, min(1.0, base_score - penalty))
    
    def _determine_validation_result(
        self, 
        is_allowlisted: bool, 
        trust_score: float, 
        issues: Dict[str, List[str]]
    ) -> ValidationResult:
        """Determine the final validation result."""
        # Security issues always block
        if issues["security"]:
            return ValidationResult.DENIED
        
        # Allowlisted sources with high trust
        if is_allowlisted and trust_score >= self.config.min_trust_score:
            return ValidationResult.ALLOWED
        
        # High trust score even if not allowlisted
        if trust_score >= 0.8:
            return ValidationResult.ALLOWED
        
        # Medium trust score requires review
        if trust_score >= self.config.min_trust_score:
            return ValidationResult.REQUIRES_REVIEW
        
        # Low trust score is denied
        return ValidationResult.DENIED
    
    def _generate_recommendations(
        self, 
        validation_result: ValidationResult, 
        issues: Dict[str, List[str]], 
        trust_score: float
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if validation_result == ValidationResult.DENIED:
            recommendations.append("Source access denied - do not use")
            if issues["security"]:
                recommendations.append("Security review required before consideration")
            recommendations.append("Consider adding to allowlist if legitimate")
        
        elif validation_result == ValidationResult.REQUIRES_REVIEW:
            recommendations.append("Manual review required before use")
            recommendations.append("Verify source authenticity")
            if trust_score < 0.7:
                recommendations.append("Consider additional verification steps")
        
        elif validation_result == ValidationResult.ALLOWED:
            if not issues["security"] and not issues["integrity"]:
                recommendations.append("Source approved for use")
            else:
                recommendations.append("Monitor for ongoing compliance")
        
        # Specific issue recommendations
        if issues["integrity"]:
            recommendations.append("Verify file integrity before use")
        
        if issues["compliance"]:
            recommendations.append("Review compliance requirements")
        
        return recommendations
    
    def _generate_cache_key(self, source_id: str, source_location: str) -> str:
        """Generate cache key for validation results."""
        combined = f"{source_id}|{source_location}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _log_validation(self, result: SourceValidationResult):
        """Log validation result for audit purposes."""
        log_data = {
            "source_id": result.source_id,
            "source_type": result.source_type.value,
            "validation_result": result.validation_result.value,
            "trust_score": result.trust_score,
            "is_allowlisted": result.is_allowlisted,
            "issues_count": len(result.security_issues) + len(result.integrity_issues) + len(result.compliance_issues),
            "timestamp": result.validation_timestamp.isoformat(),
        }
        
        if result.validation_result == ValidationResult.DENIED:
            logger.warning(f"Source validation denied: {log_data}")
        else:
            logger.info(f"Source validation completed: {log_data}")
    
    def _send_security_alert(self, result: SourceValidationResult):
        """Send security alert for blocked sources."""
        alert_data = {
            "alert_type": "BLOCKED_SOURCE",
            "source_id": result.source_id,
            "source_type": result.source_type.value,
            "security_issues": result.security_issues,
            "timestamp": result.validation_timestamp.isoformat(),
        }
        
        # In production, this would send to security monitoring system
        logger.critical(f"Security alert - blocked source: {alert_data}")
    
    def add_trusted_source(self, trusted_source: TrustedSource):
        """Add a new trusted source to the allowlist."""
        self.trusted_sources[trusted_source.source_id] = trusted_source
        logger.info(f"Added trusted source: {trusted_source.source_id}")
    
    def remove_trusted_source(self, source_id: str) -> bool:
        """Remove a trusted source from the allowlist."""
        if source_id in self.trusted_sources:
            del self.trusted_sources[source_id]
            logger.info(f"Removed trusted source: {source_id}")
            return True
        return False
    
    def block_source(self, source_identifier: str, reason: str):
        """Add a source to the blocked list."""
        self.blocked_sources.add(source_identifier)
        logger.warning(f"Blocked source {source_identifier}: {reason}")
    
    def unblock_source(self, source_identifier: str) -> bool:
        """Remove a source from the blocked list."""
        if source_identifier in self.blocked_sources:
            self.blocked_sources.remove(source_identifier)
            logger.info(f"Unblocked source: {source_identifier}")
            return True
        return False
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total_validations = len(self.validation_cache)
        
        if total_validations == 0:
            return {"total_validations": 0}
        
        results_count = {}
        avg_trust_score = 0.0
        
        for result in self.validation_cache.values():
            result_type = result.validation_result.value
            results_count[result_type] = results_count.get(result_type, 0) + 1
            avg_trust_score += result.trust_score
        
        avg_trust_score /= total_validations
        
        return {
            "total_validations": total_validations,
            "results_breakdown": results_count,
            "average_trust_score": avg_trust_score,
            "trusted_sources_count": len(self.trusted_sources),
            "blocked_sources_count": len(self.blocked_sources),
        }
    
    def clear_cache(self):
        """Clear the validation cache."""
        self.validation_cache.clear()
        logger.info("Source validation cache cleared")


# Factory function
def create_source_validator(config: Optional[SourceValidationConfig] = None) -> SourceValidator:
    """Create a source validator with default or custom configuration."""
    if config is None:
        config = SourceValidationConfig()
    
    return SourceValidator(config)


# Utility functions
def validate_url_source(url: str, validator: SourceValidator) -> bool:
    """Quick validation for URL sources."""
    result = validator.validate_source(
        source_id=url,
        source_type=SourceType.WEB_SERVICE,
        source_location=url
    )
    return result.validation_result == ValidationResult.ALLOWED


def validate_file_source(file_path: str, content: bytes, validator: SourceValidator) -> bool:
    """Quick validation for file sources."""
    result = validator.validate_source(
        source_id=file_path,
        source_type=SourceType.FILE_SYSTEM,
        source_location=file_path,
        content=content
    )
    return result.validation_result == ValidationResult.ALLOWED


def is_trusted_domain(domain: str, validator: SourceValidator) -> bool:
    """Check if a domain is in the trusted sources."""
    for trusted_source in validator.trusted_sources.values():
        for pattern in trusted_source.url_patterns:
            if domain in pattern:
                return True
    return False


def get_source_trust_level(source_id: str, validator: SourceValidator) -> int:
    """Get trust level for a source (1-5 scale)."""
    if source_id in validator.trusted_sources:
        return validator.trusted_sources[source_id].trust_level
    return 1  # Lowest trust for unknown sources
