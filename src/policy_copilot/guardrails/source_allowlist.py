"""
Source Allowlist Guardrails Implementation

This module implements source allowlist validation guardrails for the Policy Validation
Copilot system as part of UC-OP-10, ensuring only approved and versioned documents are used.
"""

from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
import hashlib
import re

from .base import (
    BaseGuardrail, GuardrailResult, GuardrailContext, GuardrailDecision,
    GuardrailSeverity, GuardrailFlag
)

logger = logging.getLogger(__name__)


class AllowedSource(BaseModel):
    """Allowed source definition"""
    source_id: str = Field(..., description="Unique source identifier")
    name: str = Field(..., description="Human-readable source name")
    source_type: str = Field(..., description="Type of source (POLICY, REGULATION, GUIDELINE, etc.)")
    base_url: Optional[str] = Field(None, description="Base URL for the source")
    allowed_domains: List[str] = Field(default_factory=list, description="Allowed domains")
    version_pattern: str = Field(..., description="Regex pattern for valid versions")
    current_version: str = Field(..., description="Current approved version")
    deprecated_versions: List[str] = Field(default_factory=list, description="Deprecated versions")
    checksum_algorithm: str = Field(default="sha256", description="Checksum algorithm")
    approved_checksums: Dict[str, str] = Field(default_factory=dict, description="Version -> checksum mapping")
    expiry_date: Optional[datetime] = Field(None, description="Source expiry date")
    approval_date: datetime = Field(..., description="Date source was approved")
    approved_by: str = Field(..., description="Who approved this source")
    tags: List[str] = Field(default_factory=list, description="Source tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SourceAllowlistGuardrail(BaseGuardrail):
    """
    Source Allowlist guardrail implementation.
    
    Validates that all document sources referenced in evidence packs
    are from approved and versioned sources only (RB-02).
    """
    
    def __init__(self):
        super().__init__("SOURCE_ALLOWLIST", "1.0.0")
        self.allowed_sources: Dict[str, AllowedSource] = {}
        self.domain_whitelist: Set[str] = set()
        self.blocked_domains: Set[str] = set()
        self._initialize_default_sources()
        self._initialize_blocked_domains()
    
    def _initialize_default_sources(self):
        """Initialize default approved sources"""
        # Example policy sources
        default_sources = [
            AllowedSource(
                source_id="POL_MED_001",
                name="Medical Coverage Policy Manual",
                source_type="POLICY",
                base_url="https://policies.company.com/medical/",
                allowed_domains=["policies.company.com"],
                version_pattern=r"^v\d+\.\d+\.\d+$",
                current_version="v2.1.0",
                deprecated_versions=["v1.9.0", "v2.0.0"],
                approved_checksums={
                    "v2.1.0": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
                    "v2.0.1": "b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567"
                },
                approval_date=datetime(2024, 1, 1),
                approved_by="policy_committee",
                tags=["medical", "coverage", "primary"]
            ),
            
            AllowedSource(
                source_id="REG_HIPAA_001",
                name="HIPAA Privacy Regulations",
                source_type="REGULATION",
                base_url="https://regulations.gov/hipaa/",
                allowed_domains=["regulations.gov", "hhs.gov"],
                version_pattern=r"^20\d{2}-\d{2}-\d{2}$",
                current_version="2024-01-15",
                approved_checksums={
                    "2024-01-15": "c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"
                },
                approval_date=datetime(2024, 1, 15),
                approved_by="compliance_team",
                tags=["hipaa", "privacy", "regulation"]
            ),
            
            AllowedSource(
                source_id="GUIDE_CLAIMS_001",
                name="Claims Processing Guidelines",
                source_type="GUIDELINE",
                base_url="https://internal.company.com/guidelines/",
                allowed_domains=["internal.company.com"],
                version_pattern=r"^guide-\d{4}-\d{2}$",
                current_version="guide-2024-01",
                approved_checksums={
                    "guide-2024-01": "d4e5f6789012345678901234567890abcdef1234567890abcdef123456789"
                },
                approval_date=datetime(2024, 1, 1),
                approved_by="operations_team",
                tags=["claims", "processing", "internal"]
            )
        ]
        
        for source in default_sources:
            self.add_allowed_source(source)
    
    def _initialize_blocked_domains(self):
        """Initialize blocked domains list"""
        self.blocked_domains = {
            # Known malicious domains
            "malicious-site.com",
            "phishing-example.net",
            "fake-policies.org",
            
            # Public file sharing (not allowed for policies)
            "dropbox.com",
            "drive.google.com",
            "onedrive.live.com",
            "mega.nz",
            
            # Social media and forums
            "facebook.com",
            "twitter.com",
            "reddit.com",
            "stackoverflow.com",
            
            # General file hosting
            "mediafire.com",
            "rapidshare.com",
            "4shared.com"
        }
    
    def add_allowed_source(self, source: AllowedSource) -> None:
        """Add an allowed source to the allowlist"""
        self.allowed_sources[source.source_id] = source
        
        # Add domains to whitelist
        for domain in source.allowed_domains:
            self.domain_whitelist.add(domain.lower())
        
        logger.info(f"Added allowed source: {source.source_id} - {source.name}")
    
    def remove_allowed_source(self, source_id: str) -> bool:
        """Remove a source from the allowlist"""
        if source_id in self.allowed_sources:
            source = self.allowed_sources[source_id]
            
            # Remove domains from whitelist if not used by other sources
            for domain in source.allowed_domains:
                if not any(
                    domain in other_source.allowed_domains 
                    for other_source in self.allowed_sources.values()
                    if other_source.source_id != source_id
                ):
                    self.domain_whitelist.discard(domain.lower())
            
            del self.allowed_sources[source_id]
            logger.info(f"Removed allowed source: {source_id}")
            return True
        
        return False
    
    def validate_source_reference(self, doc_id: str, version: str, checksum: str = None) -> Tuple[bool, List[str]]:
        """
        Validate a source reference against the allowlist.
        
        Args:
            doc_id: Document/source identifier
            version: Document version
            checksum: Document checksum (optional)
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        # Check if source is in allowlist
        if doc_id not in self.allowed_sources:
            errors.append(f"Source {doc_id} is not in the approved allowlist")
            return False, errors
        
        source = self.allowed_sources[doc_id]
        
        # Check if source has expired
        if source.expiry_date and datetime.utcnow() > source.expiry_date:
            errors.append(f"Source {doc_id} has expired on {source.expiry_date}")
        
        # Validate version format
        if not re.match(source.version_pattern, version):
            errors.append(f"Version {version} does not match required pattern {source.version_pattern}")
        
        # Check if version is deprecated
        if version in source.deprecated_versions:
            errors.append(f"Version {version} is deprecated for source {doc_id}")
        
        # Validate checksum if provided
        if checksum and version in source.approved_checksums:
            expected_checksum = source.approved_checksums[version]
            if checksum.lower() != expected_checksum.lower():
                errors.append(f"Checksum mismatch for {doc_id} v{version}")
        elif checksum and version not in source.approved_checksums:
            errors.append(f"No approved checksum found for {doc_id} v{version}")
        
        return len(errors) == 0, errors
    
    def validate_url(self, url: str) -> Tuple[bool, List[str]]:
        """
        Validate a URL against domain allowlist and blocklist.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        # Extract domain from URL
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
        except Exception as e:
            errors.append(f"Invalid URL format: {url}")
            return False, errors
        
        # Check against blocked domains
        if domain in self.blocked_domains:
            errors.append(f"Domain {domain} is explicitly blocked")
            return False, errors
        
        # Check against allowed domains
        if domain not in self.domain_whitelist:
            errors.append(f"Domain {domain} is not in the approved allowlist")
            return False, errors
        
        return len(errors) == 0, errors
    
    def validate_evidence_pack(self, evidence_pack: Dict[str, Any]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Validate all sources in an evidence pack.
        
        Args:
            evidence_pack: Evidence pack to validate
            
        Returns:
            Tuple of (is_valid, errors, invalid_items)
        """
        all_errors = []
        invalid_items = []
        
        evidence_items = evidence_pack.get("items", [])
        
        for i, item in enumerate(evidence_items):
            item_errors = []
            
            doc_id = item.get("doc_id")
            version = item.get("version")
            checksum = item.get("checksum")
            pointer = item.get("pointer")
            
            if not doc_id:
                item_errors.append("Missing doc_id")
            
            if not version:
                item_errors.append("Missing version")
            
            # Validate source reference
            if doc_id and version:
                is_valid, validation_errors = self.validate_source_reference(doc_id, version, checksum)
                if not is_valid:
                    item_errors.extend(validation_errors)
            
            # Validate URL in pointer if present
            if pointer and isinstance(pointer, str) and pointer.startswith(('http://', 'https://')):
                is_valid_url, url_errors = self.validate_url(pointer)
                if not is_valid_url:
                    item_errors.extend(url_errors)
            
            if item_errors:
                invalid_items.append({
                    "index": i,
                    "item": item,
                    "errors": item_errors
                })
                all_errors.extend([f"Item {i}: {error}" for error in item_errors])
        
        return len(all_errors) == 0, all_errors, invalid_items
    
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """Evaluate payload for source allowlist compliance"""
        flags = []
        decision = GuardrailDecision.ALLOW
        
        # Check if payload contains evidence pack
        evidence_pack = payload.get("evidence_pack")
        if not evidence_pack:
            # No evidence pack to validate
            return GuardrailResult(
                decision=decision,
                flags=flags,
                security_context={"source_allowlist_check": True, "evidence_pack_present": False},
                guardrail_version=self.version
            )
        
        # Validate evidence pack sources
        is_valid, errors, invalid_items = self.validate_evidence_pack(evidence_pack)
        
        if not is_valid:
            # Create flags for validation failures
            flags.append(await self._create_flag(
                flag_type="SOURCE_ALLOWLIST_VIOLATION",
                severity=GuardrailSeverity.HIGH,
                message=f"Evidence pack contains {len(invalid_items)} invalid source references",
                details={
                    "total_errors": len(errors),
                    "invalid_items_count": len(invalid_items),
                    "errors": errors[:10],  # Limit to first 10 errors
                    "invalid_items": invalid_items[:5]  # Limit to first 5 invalid items
                },
                rule_id="ALLOWLIST-001"
            ))
            
            # Block processing if sources are not approved
            decision = GuardrailDecision.BLOCK
        
        # Check for deprecated sources
        deprecated_sources = []
        for item in evidence_pack.get("items", []):
            doc_id = item.get("doc_id")
            version = item.get("version")
            
            if doc_id in self.allowed_sources:
                source = self.allowed_sources[doc_id]
                if version in source.deprecated_versions:
                    deprecated_sources.append(f"{doc_id} v{version}")
        
        if deprecated_sources:
            flags.append(await self._create_flag(
                flag_type="DEPRECATED_SOURCE_USAGE",
                severity=GuardrailSeverity.MEDIUM,
                message=f"Evidence pack uses {len(deprecated_sources)} deprecated source versions",
                details={"deprecated_sources": deprecated_sources},
                rule_id="ALLOWLIST-002"
            ))
            
            # Require human review for deprecated sources
            if decision == GuardrailDecision.ALLOW:
                decision = GuardrailDecision.REQUIRE_HITL
        
        # Check for missing checksums
        missing_checksums = []
        for item in evidence_pack.get("items", []):
            if not item.get("checksum"):
                missing_checksums.append(item.get("doc_id", "unknown"))
        
        if missing_checksums:
            flags.append(await self._create_flag(
                flag_type="MISSING_CHECKSUMS",
                severity=GuardrailSeverity.MEDIUM,
                message=f"Evidence pack has {len(missing_checksums)} items without checksums",
                details={"items_without_checksums": missing_checksums},
                rule_id="ALLOWLIST-003"
            ))
        
        # Log source validation event
        if flags:
            await self._log_security_event(
                event_type="SOURCE_ALLOWLIST_CHECK",
                severity=GuardrailSeverity.HIGH if decision == GuardrailDecision.BLOCK else GuardrailSeverity.MEDIUM,
                description=f"Source allowlist validation: {len(flags)} issues found",
                context=context,
                flags=flags,
                metadata={
                    "evidence_items_count": len(evidence_pack.get("items", [])),
                    "validation_passed": is_valid,
                    "deprecated_sources_count": len(deprecated_sources)
                }
            )
        
        return GuardrailResult(
            decision=decision,
            flags=flags,
            security_context={
                "source_allowlist_check": True,
                "evidence_pack_present": True,
                "validation_passed": is_valid,
                "total_sources": len(evidence_pack.get("items", [])),
                "invalid_sources": len(invalid_items),
                "deprecated_sources": len(deprecated_sources)
            },
            guardrail_version=self.version
        )
    
    def get_rule_ids(self) -> List[str]:
        """Get source allowlist rule IDs"""
        return ["ALLOWLIST-001", "ALLOWLIST-002", "ALLOWLIST-003"]
    
    def get_allowed_sources(self) -> Dict[str, AllowedSource]:
        """Get all allowed sources"""
        return self.allowed_sources.copy()
    
    def get_source_info(self, source_id: str) -> Optional[AllowedSource]:
        """Get information about a specific source"""
        return self.allowed_sources.get(source_id)
    
    def update_source_version(self, source_id: str, new_version: str, checksum: str) -> bool:
        """Update the current version of a source"""
        if source_id not in self.allowed_sources:
            return False
        
        source = self.allowed_sources[source_id]
        
        # Validate version format
        if not re.match(source.version_pattern, new_version):
            logger.error(f"Version {new_version} does not match pattern {source.version_pattern}")
            return False
        
        # Move current version to deprecated if different
        if source.current_version != new_version and source.current_version not in source.deprecated_versions:
            source.deprecated_versions.append(source.current_version)
        
        # Update current version and checksum
        source.current_version = new_version
        source.approved_checksums[new_version] = checksum
        
        logger.info(f"Updated {source_id} to version {new_version}")
        return True
    
    def add_blocked_domain(self, domain: str) -> None:
        """Add a domain to the blocklist"""
        self.blocked_domains.add(domain.lower())
        logger.info(f"Added blocked domain: {domain}")
    
    def remove_blocked_domain(self, domain: str) -> bool:
        """Remove a domain from the blocklist"""
        domain_lower = domain.lower()
        if domain_lower in self.blocked_domains:
            self.blocked_domains.remove(domain_lower)
            logger.info(f"Removed blocked domain: {domain}")
            return True
        return False
