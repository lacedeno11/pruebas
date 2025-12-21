"""
PII Detection and Masking.

Detects and masks personally identifiable information.
"""

import re
import logging
from typing import Optional

from policy_validation_copilot.models.guardrails import RedactionRecord

logger = logging.getLogger(__name__)


class PIIDetector:
    """
    Detects and masks PII in text and structured data.

    Uses pattern matching and optional Presidio integration.
    """

    def __init__(self, use_presidio: bool = False):
        self.use_presidio = use_presidio
        self._patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, re.Pattern]:
        """Compile regex patterns for PII detection."""
        return {
            "EMAIL": re.compile(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            ),
            "PHONE": re.compile(
                r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
            ),
            "SSN": re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"),
            "CREDIT_CARD": re.compile(r"\b(?:\d{4}[-.\s]?){3}\d{4}\b"),
            "DATE_OF_BIRTH": re.compile(
                r"\b(?:0[1-9]|1[0-2])[/.-](?:0[1-9]|[12]\d|3[01])[/.-](?:19|20)\d{2}\b"
            ),
            "IP_ADDRESS": re.compile(
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
            ),
            # Mexican CURP
            "CURP": re.compile(
                r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b"
            ),
            # Mexican RFC
            "RFC": re.compile(
                r"\b[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}\b"
            ),
        }

    def detect(self, text: str) -> list[dict]:
        """
        Detect PII in text.

        Returns list of detected PII with type and position.
        """
        detections = []

        for pii_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                detections.append({
                    "type": pii_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })

        return detections

    def mask(
        self,
        text: str,
        mask_char: str = "*",
        preserve_length: bool = True,
    ) -> tuple[str, list[RedactionRecord]]:
        """
        Mask PII in text.

        Returns masked text and redaction records.
        """
        detections = self.detect(text)
        redactions: list[RedactionRecord] = []

        # Sort by position descending to preserve indices during replacement
        detections.sort(key=lambda x: x["start"], reverse=True)

        masked_text = text
        for detection in detections:
            original = detection["value"]
            if preserve_length:
                masked = mask_char * len(original)
            else:
                masked = f"[{detection['type']}]"

            masked_text = (
                masked_text[: detection["start"]]
                + masked
                + masked_text[detection["end"]:]
            )

            redactions.append(
                RedactionRecord(
                    field_path=f"text:{detection['start']}-{detection['end']}",
                    original_type=detection["type"],
                    redaction_method="MASK",
                    redacted_value=masked,
                )
            )

        return masked_text, redactions

    def mask_dict(
        self,
        data: dict,
        path: str = "",
    ) -> tuple[dict, list[RedactionRecord]]:
        """
        Recursively mask PII in dictionary.

        Returns masked dict and all redaction records.
        """
        redactions: list[RedactionRecord] = []
        masked_data = {}

        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, str):
                masked_value, recs = self.mask(value)
                masked_data[key] = masked_value
                for rec in recs:
                    rec.field_path = current_path
                redactions.extend(recs)

            elif isinstance(value, dict):
                masked_value, recs = self.mask_dict(value, current_path)
                masked_data[key] = masked_value
                redactions.extend(recs)

            elif isinstance(value, list):
                masked_list = []
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        masked_item, recs = self.mask(item)
                        masked_list.append(masked_item)
                        for rec in recs:
                            rec.field_path = f"{current_path}[{i}]"
                        redactions.extend(recs)
                    elif isinstance(item, dict):
                        masked_item, recs = self.mask_dict(
                            item, f"{current_path}[{i}]"
                        )
                        masked_list.append(masked_item)
                        redactions.extend(recs)
                    else:
                        masked_list.append(item)
                masked_data[key] = masked_list

            else:
                masked_data[key] = value

        return masked_data, redactions

    def contains_pii(self, text: str) -> bool:
        """Quick check if text contains any PII."""
        return len(self.detect(text)) > 0
