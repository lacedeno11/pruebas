"""
Hallucination Detection.

Verifies that claims are anchored to evidence.
Based on anti-hallucination requirements (RB-10-01).
"""

import logging
import re
from typing import Optional

from policy_validation_copilot.models.evidence import EvidencePack, EvidenceItem

logger = logging.getLogger(__name__)


class HallucinationChecker:
    """
    Checks for unanchored claims (potential hallucinations).

    Ensures all decision-relevant statements have evidence support.
    """

    def __init__(
        self,
        min_evidence_match_ratio: float = 0.7,
        require_explicit_citations: bool = True,
    ):
        self.min_evidence_match_ratio = min_evidence_match_ratio
        self.require_explicit_citations = require_explicit_citations

    def extract_claims(self, text: str) -> list[str]:
        """
        Extract factual claims from text.

        Identifies statements that require evidence backing.
        """
        claims = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        # Patterns indicating factual claims
        claim_patterns = [
            r'\b(?:is|are|was|were)\s+(?:covered|excluded|included|required)',
            r'\b(?:limit|maximum|minimum|cap)\s+(?:is|of)\b',
            r'\b(?:requires?|must|shall|should)\b',
            r'\b(?:according to|as per|based on)\b',
            r'\b(?:policy|contract|agreement)\s+(?:states?|specifies?|requires?)',
            r'\b\d+\s*%\b',  # Percentages
            r'\b\$?\d+(?:,\d{3})*(?:\.\d{2})?\b',  # Money amounts
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            for pattern in claim_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append(sentence)
                    break

        return claims

    def check_claim_against_evidence(
        self,
        claim: str,
        evidence_pack: EvidencePack,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a claim is supported by evidence.

        Returns (is_supported, evidence_id).
        """
        claim_lower = claim.lower()

        # Extract key terms from claim
        key_terms = self._extract_key_terms(claim)

        best_match_score = 0.0
        best_match_id = None

        for item in evidence_pack.items:
            if not item.excerpt:
                continue

            excerpt_lower = item.excerpt.lower()

            # Calculate term overlap
            matched_terms = sum(1 for term in key_terms if term in excerpt_lower)
            match_ratio = matched_terms / max(len(key_terms), 1)

            if match_ratio > best_match_score:
                best_match_score = match_ratio
                best_match_id = item.evidence_id

        is_supported = best_match_score >= self.min_evidence_match_ratio
        return is_supported, best_match_id if is_supported else None

    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract key terms from text for matching."""
        # Remove common words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "under", "and", "or", "but",
            "if", "then", "else", "when", "where", "which", "that",
            "this", "these", "those", "it", "its",
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-z]+\b', text.lower())
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]

        return key_terms

    def check_text(
        self,
        text: str,
        evidence_pack: EvidencePack,
    ) -> tuple[bool, list[dict]]:
        """
        Check text for unsupported claims.

        Returns (all_supported, list_of_unanchored_claims).
        """
        claims = self.extract_claims(text)
        unanchored = []

        for claim in claims:
            is_supported, evidence_id = self.check_claim_against_evidence(
                claim, evidence_pack
            )

            if not is_supported:
                unanchored.append({
                    "claim": claim,
                    "evidence_id": evidence_id,
                    "supported": False,
                })
            else:
                logger.debug(f"Claim supported by {evidence_id}: {claim[:50]}...")

        all_supported = len(unanchored) == 0
        return all_supported, unanchored

    def validate_decision_explanation(
        self,
        explanation: str,
        evidence_pack: EvidencePack,
        strict: bool = True,
    ) -> tuple[bool, dict]:
        """
        Validate that a decision explanation is fully anchored.

        Returns (is_valid, validation_report).
        """
        all_supported, unanchored = self.check_text(explanation, evidence_pack)

        report = {
            "is_valid": all_supported,
            "total_claims": len(self.extract_claims(explanation)),
            "unanchored_claims": unanchored,
            "evidence_items_used": len(evidence_pack.items),
        }

        if strict and not all_supported:
            report["action"] = "REQUIRE_HITL"
            report["reason"] = "Unanchored claims detected in explanation"
        else:
            report["action"] = "ALLOW" if all_supported else "WARN"

        return all_supported, report
