"""
Tests for Guardrails service.
"""

import pytest

from policy_validation_copilot.guardrails.pii_detector import PIIDetector
from policy_validation_copilot.guardrails.source_validator import SourceValidator
from policy_validation_copilot.guardrails.hallucination_checker import HallucinationChecker


class TestPIIDetector:
    """Tests for PII detection."""

    def test_detect_email(self):
        """Test email detection."""
        detector = PIIDetector()
        text = "Contact me at john.doe@example.com for more info."

        detections = detector.detect(text)

        assert len(detections) == 1
        assert detections[0]["type"] == "EMAIL"
        assert "john.doe@example.com" in detections[0]["value"]

    def test_detect_phone(self):
        """Test phone number detection."""
        detector = PIIDetector()
        text = "Call me at 555-123-4567."

        detections = detector.detect(text)

        assert len(detections) == 1
        assert detections[0]["type"] == "PHONE"

    def test_detect_multiple_pii(self):
        """Test multiple PII detection."""
        detector = PIIDetector()
        text = "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789"

        detections = detector.detect(text)

        assert len(detections) == 3
        types = {d["type"] for d in detections}
        assert "EMAIL" in types
        assert "PHONE" in types
        assert "SSN" in types

    def test_mask_pii(self):
        """Test PII masking."""
        detector = PIIDetector()
        text = "Contact john.doe@example.com"

        masked, redactions = detector.mask(text)

        assert "john.doe@example.com" not in masked
        assert len(redactions) == 1

    def test_contains_pii(self):
        """Test PII presence check."""
        detector = PIIDetector()

        assert detector.contains_pii("Email: test@example.com")
        assert not detector.contains_pii("No PII here")


class TestSourceValidator:
    """Tests for source validation."""

    def test_allowlist_check(self):
        """Test allowlist checking."""
        validator = SourceValidator(allowlist=["DOC-001", "DOC-002"])

        assert validator.is_allowed("DOC-001")
        assert not validator.is_allowed("DOC-999")

    def test_approved_prefix(self):
        """Test approved prefix checking."""
        validator = SourceValidator()

        assert validator.is_allowed("POL-001")  # Policy prefix
        assert validator.is_allowed("EXC-001")  # Exception prefix
        assert not validator.is_allowed("UNKNOWN-001")

    def test_add_to_allowlist(self):
        """Test adding to allowlist."""
        validator = SourceValidator()

        assert not validator.is_allowed("CUSTOM-001")

        validator.add_to_allowlist("CUSTOM-001")

        assert validator.is_allowed("CUSTOM-001")


class TestHallucinationChecker:
    """Tests for hallucination detection."""

    def test_extract_claims(self):
        """Test claim extraction."""
        checker = HallucinationChecker()
        text = "The service is covered under the basic plan. The limit is $5000."

        claims = checker.extract_claims(text)

        assert len(claims) >= 1  # Should find at least one claim

    def test_no_claims_in_simple_text(self):
        """Test that simple text has no claims."""
        checker = HallucinationChecker()
        text = "Hello, how are you today?"

        claims = checker.extract_claims(text)

        assert len(claims) == 0
