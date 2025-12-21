"""
Source Validation.

Validates that evidence sources are from approved allowlist.
Based on RB-06-01: only fuentes versionadas/allowlisted.
"""

import logging
from datetime import datetime
from typing import Optional

from policy_validation_copilot.models.evidence import EvidenceItem, EvidencePack

logger = logging.getLogger(__name__)


class SourceValidator:
    """
    Validates evidence sources against allowlist.

    Ensures only approved, versioned documents are used for decisions.
    """

    def __init__(
        self,
        allowlist: Optional[list[str]] = None,
        require_version: bool = True,
        require_checksum: bool = True,
    ):
        self._allowlist: set[str] = set(allowlist or [])
        self.require_version = require_version
        self.require_checksum = require_checksum
        self._approved_prefixes: list[str] = [
            "POL-",  # Policy documents
            "EXC-",  # Exception documents
            "ANX-",  # Anexos
            "COB-",  # Coverage documents
        ]

    def add_to_allowlist(self, doc_id: str) -> None:
        """Add a document to the allowlist."""
        self._allowlist.add(doc_id)

    def remove_from_allowlist(self, doc_id: str) -> None:
        """Remove a document from the allowlist."""
        self._allowlist.discard(doc_id)

    def is_allowed(self, doc_id: str) -> bool:
        """Check if a document ID is in the allowlist."""
        # Check exact match
        if doc_id in self._allowlist:
            return True

        # Check approved prefixes
        for prefix in self._approved_prefixes:
            if doc_id.startswith(prefix):
                return True

        return False

    def validate_item(self, item: EvidenceItem) -> tuple[bool, list[str]]:
        """
        Validate a single evidence item.

        Returns (is_valid, list_of_issues).
        """
        issues = []

        # Check allowlist
        if not self.is_allowed(item.doc_id):
            issues.append(f"Document {item.doc_id} not in allowlist")

        # Check version
        if self.require_version and not item.doc_version:
            issues.append(f"Document {item.doc_id} missing version")

        # Check checksum
        if self.require_checksum and not item.checksum:
            issues.append(f"Document {item.doc_id} missing checksum")

        # Check pointer (for anti-hallucination)
        if not item.pointer:
            issues.append(f"Document {item.doc_id} missing location pointer")

        # Check effective date
        if item.effective_date and item.effective_date > datetime.utcnow():
            issues.append(f"Document {item.doc_id} not yet effective")

        # Check expiration
        if item.expiration_date and item.expiration_date < datetime.utcnow():
            issues.append(f"Document {item.doc_id} has expired")

        return len(issues) == 0, issues

    def validate_pack(self, pack: EvidencePack) -> tuple[bool, dict]:
        """
        Validate all items in an evidence pack.

        Returns (all_valid, validation_report).
        """
        report = {
            "valid_items": [],
            "invalid_items": [],
            "issues": [],
            "non_allowlisted": [],
        }

        all_valid = True
        for item in pack.items:
            is_valid, issues = self.validate_item(item)

            if is_valid:
                report["valid_items"].append(item.evidence_id)
            else:
                report["invalid_items"].append(item.evidence_id)
                report["issues"].extend(issues)
                all_valid = False

            if not self.is_allowed(item.doc_id):
                report["non_allowlisted"].append(item.doc_id)

        return all_valid, report

    def filter_allowed_only(self, pack: EvidencePack) -> EvidencePack:
        """
        Filter evidence pack to only include allowed sources.

        Returns new pack with only valid items.
        """
        filtered_items = [
            item for item in pack.items
            if self.is_allowed(item.doc_id)
        ]

        return EvidencePack(
            pack_id=pack.pack_id,
            case_id=pack.case_id,
            items=filtered_items,
            coverage_score=pack.coverage_score * (len(filtered_items) / max(len(pack.items), 1)),
            missing_sources=pack.missing_sources,
            conflicts=pack.conflicts,
            conflicts_detected=pack.conflicts_detected,
            retrieval_duration_ms=pack.retrieval_duration_ms,
            total_documents_searched=pack.total_documents_searched,
        )
