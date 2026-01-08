"""
Evidence Anchoring Guardrails Implementation

This module implements evidence anchoring validation guardrails for the Policy Validation
Copilot system as part of UC-OP-10, ensuring all decisions are properly anchored to
verifiable evidence and preventing hallucination.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
import re
import logging
from datetime import datetime

from .base import (
    BaseGuardrail, GuardrailResult, GuardrailContext, GuardrailDecision,
    GuardrailSeverity, GuardrailFlag
)

logger = logging.getLogger(__name__)


class EvidenceReference(BaseModel):
    """Evidence reference validation model"""
    doc_id: str = Field(..., description="Document identifier")
    version: str = Field(..., description="Document version")
    pointer: str = Field(..., description="Specific location pointer")
    excerpt: str = Field(..., description="Relevant text excerpt")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Reference confidence")
    validation_status: str = Field(..., description="Validation status")


class EvidenceAnchoringGuardrail(BaseGuardrail):
    """
    Evidence Anchoring guardrail implementation.
    
    Validates that all decisions and claims are properly anchored to verifiable evidence,
    implementing RB-01: No APROBADO without verifiable evidence (≥1 citation/table with exact reference).
    """
    
    def __init__(self):
        super().__init__("EVIDENCE_ANCHORING", "1.0.0")
        self.citation_patterns = []
        self.hallucination_indicators = set()
        self.required_evidence_types = set()
        self.minimum_evidence_threshold = 1
        self._initialize_citation_patterns()
        self._initialize_hallucination_indicators()
        self._initialize_required_evidence_types()
    
    def _initialize_citation_patterns(self):
        """Initialize citation detection patterns"""
        self.citation_patterns = [
            # Standard citation formats
            r'\[(\d+)\]',  # [1], [2], etc.
            r'\(([^)]+)\)',  # (Source 2024)
            r'(?:según|according to|as per|per|ref\.?)\s+([^.]+)',  # According to X
            r'(?:documento|document|policy|regulation)\s+([A-Z0-9-]+)',  # Document ABC-123
            r'(?:página|page|p\.)\s*(\d+)',  # Page 5
            r'(?:sección|section|sec\.)\s*([0-9.]+)',  # Section 2.1
            r'(?:artículo|article|art\.)\s*(\d+)',  # Article 5
            r'(?:tabla|table|cuadro)\s*(\d+)',  # Table 1
            r'(?:anexo|annex|appendix)\s*([A-Z0-9]+)',  # Annex A
        ]
    
    def _initialize_hallucination_indicators(self):
        """Initialize hallucination detection indicators"""
        self.hallucination_indicators = {
            # Vague references
            "según fuentes internas", "internal sources", "company policy",
            "standard practice", "common knowledge", "generally accepted",
            "it is known that", "typically", "usually", "normally",
            
            # Uncertain language
            "probablemente", "probably", "likely", "possibly", "might be",
            "could be", "seems to", "appears to", "suggests that",
            "indicates that", "implies that",
            
            # Unverifiable claims
            "based on experience", "in my opinion", "I believe",
            "it seems", "apparently", "presumably", "supposedly",
            
            # Generic references
            "various sources", "multiple documents", "several policies",
            "different regulations", "various guidelines",
            
            # Temporal vagueness
            "recently updated", "new policy", "latest version",
            "current guidelines", "updated procedures"
        }
    
    def _initialize_required_evidence_types(self):
        """Initialize required evidence types for different decisions"""
        self.required_evidence_types = {
            "APROBADO": {"policy_reference", "coverage_confirmation", "eligibility_check"},
            "RECHAZADO": {"policy_reference", "exclusion_clause", "limitation_clause"},
            "OBSERVADO": {"policy_reference", "additional_requirement", "clarification_needed"}
        }
    
    def extract_citations(self, text: str) -> List[str]:
        """
        Extract citations from text using pattern matching.
        
        Args:
            text: Text to extract citations from
            
        Returns:
            List of found citations
        """
        citations = []
        
        for pattern in self.citation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations.extend(matches)
        
        return citations
    
    def detect_hallucination_indicators(self, text: str) -> List[str]:
        """
        Detect potential hallucination indicators in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of found hallucination indicators
        """
        text_lower = text.lower()
        found_indicators = []
        
        for indicator in self.hallucination_indicators:
            if indicator in text_lower:
                found_indicators.append(indicator)
        
        return found_indicators
    
    def validate_evidence_reference(self, reference: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an individual evidence reference.
        
        Args:
            reference: Evidence reference to validate
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ["doc_id", "version", "pointer", "excerpt"]
        for field in required_fields:
            if not reference.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate doc_id format
        doc_id = reference.get("doc_id", "")
        if doc_id and not re.match(r'^[A-Z0-9_-]+$', doc_id):
            errors.append(f"Invalid doc_id format: {doc_id}")
        
        # Validate version format
        version = reference.get("version", "")
        if version and not re.match(r'^v?\d+\.\d+(\.\d+)?$', version):
            errors.append(f"Invalid version format: {version}")
        
        # Validate pointer specificity
        pointer = reference.get("pointer", "")
        if pointer:
            # Check for specific location indicators
            specific_indicators = ["page", "section", "paragraph", "table", "figure", "line"]
            if not any(indicator in pointer.lower() for indicator in specific_indicators):
                errors.append("Pointer lacks specific location information")
        
        # Validate excerpt length and content
        excerpt = reference.get("excerpt", "")
        if excerpt:
            if len(excerpt) < 10:
                errors.append("Excerpt too short to be meaningful")
            elif len(excerpt) > 1000:
                errors.append("Excerpt too long, should be more specific")
            
            # Check for hallucination indicators in excerpt
            hallucination_indicators = self.detect_hallucination_indicators(excerpt)
            if hallucination_indicators:
                errors.append(f"Excerpt contains hallucination indicators: {', '.join(hallucination_indicators[:3])}")
        
        return len(errors) == 0, errors
    
    def validate_evidence_pack_completeness(self, evidence_pack: Dict[str, Any], decision_status: str) -> Tuple[bool, List[str]]:
        """
        Validate evidence pack completeness for a given decision.
        
        Args:
            evidence_pack: Evidence pack to validate
            decision_status: Decision status (APROBADO, RECHAZADO, etc.)
            
        Returns:
            Tuple of (is_complete, validation_errors)
        """
        errors = []
        
        evidence_items = evidence_pack.get("items", [])
        
        # Check minimum evidence threshold (RB-01)
        if len(evidence_items) < self.minimum_evidence_threshold:
            errors.append(f"Insufficient evidence: {len(evidence_items)} items, minimum required: {self.minimum_evidence_threshold}")
        
        # Check for required evidence types based on decision
        required_types = self.required_evidence_types.get(decision_status, set())
        if required_types:
            evidence_types = set()
            for item in evidence_items:
                # Extract evidence type from doc_id or metadata
                doc_id = item.get("doc_id", "")
                if "POL_" in doc_id:
                    evidence_types.add("policy_reference")
                elif "COV_" in doc_id:
                    evidence_types.add("coverage_confirmation")
                elif "ELI_" in doc_id:
                    evidence_types.add("eligibility_check")
                elif "EXC_" in doc_id:
                    evidence_types.add("exclusion_clause")
                elif "LIM_" in doc_id:
                    evidence_types.add("limitation_clause")
                elif "REQ_" in doc_id:
                    evidence_types.add("additional_requirement")
            
            missing_types = required_types - evidence_types
            if missing_types:
                errors.append(f"Missing required evidence types for {decision_status}: {', '.join(missing_types)}")
        
        # Check coverage score
        coverage_score = evidence_pack.get("coverage_score", 0.0)
        if coverage_score < 0.8:
            errors.append(f"Low coverage score: {coverage_score}, minimum required: 0.8")
        
        return len(errors) == 0, errors
    
    def validate_decision_evidence_alignment(self, decision: Dict[str, Any], evidence_pack: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate alignment between decision and supporting evidence.
        
        Args:
            decision: Decision to validate
            evidence_pack: Supporting evidence pack
            
        Returns:
            Tuple of (is_aligned, validation_errors)
        """
        errors = []
        
        decision_status = decision.get("status")
        decision_explanation = decision.get("explanation", "")
        evidence_items = evidence_pack.get("items", [])
        
        # Extract citations from decision explanation
        citations = self.extract_citations(decision_explanation)
        
        # Check if decision explanation contains citations
        if not citations:
            errors.append("Decision explanation lacks specific citations to evidence")
        
        # Check for hallucination indicators in explanation
        hallucination_indicators = self.detect_hallucination_indicators(decision_explanation)
        if hallucination_indicators:
            errors.append(f"Decision explanation contains hallucination indicators: {', '.join(hallucination_indicators[:3])}")
        
        # Validate that cited evidence exists
        evidence_doc_ids = {item.get("doc_id") for item in evidence_items}
        for citation in citations:
            # Simple check - in production, would need more sophisticated citation resolution
            if not any(citation in doc_id for doc_id in evidence_doc_ids):
                errors.append(f"Citation '{citation}' not found in evidence pack")
        
        # Check decision-evidence consistency
        if decision_status == "APROBADO":
            # For approval, should have positive evidence
            negative_keywords = ["exclusion", "limitation", "not covered", "excluded", "denied"]
            for item in evidence_items:
                excerpt = item.get("excerpt", "").lower()
                if any(keyword in excerpt for keyword in negative_keywords):
                    errors.append("Approval decision conflicts with negative evidence in excerpt")
        
        elif decision_status == "RECHAZADO":
            # For rejection, should have negative evidence or exclusions
            positive_keywords = ["covered", "approved", "eligible", "included"]
            negative_evidence_found = False
            
            for item in evidence_items:
                excerpt = item.get("excerpt", "").lower()
                if any(keyword in excerpt for keyword in ["exclusion", "limitation", "not covered"]):
                    negative_evidence_found = True
                elif any(keyword in excerpt for keyword in positive_keywords):
                    errors.append("Rejection decision conflicts with positive evidence in excerpt")
            
            if not negative_evidence_found:
                errors.append("Rejection decision lacks supporting negative evidence")
        
        return len(errors) == 0, errors
    
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """Evaluate payload for evidence anchoring compliance"""
        flags = []
        decision = GuardrailDecision.ALLOW
        
        # Extract decision and evidence pack from payload
        decision_data = payload.get("decision", {})
        evidence_pack = payload.get("evidence_pack", {})
        
        if not decision_data:
            # No decision to validate
            return GuardrailResult(
                decision=decision,
                flags=flags,
                security_context={"evidence_anchoring_check": True, "decision_present": False},
                guardrail_version=self.version
            )
        
        decision_status = decision_data.get("status")
        
        # Validate individual evidence references
        evidence_items = evidence_pack.get("items", [])
        invalid_references = []
        
        for i, item in enumerate(evidence_items):
            is_valid, validation_errors = self.validate_evidence_reference(item)
            if not is_valid:
                invalid_references.append({
                    "index": i,
                    "errors": validation_errors
                })
        
        if invalid_references:
            flags.append(await self._create_flag(
                flag_type="INVALID_EVIDENCE_REFERENCES",
                severity=GuardrailSeverity.HIGH,
                message=f"Found {len(invalid_references)} invalid evidence references",
                details={
                    "invalid_count": len(invalid_references),
                    "total_references": len(evidence_items),
                    "invalid_references": invalid_references[:5]  # Limit details
                },
                rule_id="EVIDENCE-001"
            ))
        
        # Validate evidence pack completeness
        if decision_status:
            is_complete, completeness_errors = self.validate_evidence_pack_completeness(
                evidence_pack, decision_status
            )
            
            if not is_complete:
                flags.append(await self._create_flag(
                    flag_type="INSUFFICIENT_EVIDENCE",
                    severity=GuardrailSeverity.CRITICAL,
                    message=f"Evidence pack insufficient for {decision_status} decision",
                    details={
                        "decision_status": decision_status,
                        "evidence_count": len(evidence_items),
                        "errors": completeness_errors
                    },
                    rule_id="EVIDENCE-002"
                ))
                
                # Block APROBADO decisions without sufficient evidence (RB-01)
                if decision_status == "APROBADO":
                    decision = GuardrailDecision.BLOCK
        
        # Validate decision-evidence alignment
        if decision_status and evidence_items:
            is_aligned, alignment_errors = self.validate_decision_evidence_alignment(
                decision_data, evidence_pack
            )
            
            if not is_aligned:
                flags.append(await self._create_flag(
                    flag_type="DECISION_EVIDENCE_MISALIGNMENT",
                    severity=GuardrailSeverity.HIGH,
                    message="Decision not properly aligned with supporting evidence",
                    details={
                        "decision_status": decision_status,
                        "alignment_errors": alignment_errors
                    },
                    rule_id="EVIDENCE-003"
                ))
                
                # Require human review for misaligned decisions
                if decision == GuardrailDecision.ALLOW:
                    decision = GuardrailDecision.REQUIRE_HITL
        
        # Check for hallucination indicators in decision explanation
        explanation = decision_data.get("explanation", "")
        if explanation:
            hallucination_indicators = self.detect_hallucination_indicators(explanation)
            if hallucination_indicators:
                flags.append(await self._create_flag(
                    flag_type="POTENTIAL_HALLUCINATION",
                    severity=GuardrailSeverity.MEDIUM,
                    message=f"Decision explanation contains {len(hallucination_indicators)} hallucination indicators",
                    details={
                        "indicators": hallucination_indicators[:5],
                        "total_indicators": len(hallucination_indicators)
                    },
                    rule_id="EVIDENCE-004"
                ))
        
        # Log evidence anchoring validation event
        if flags:
            await self._log_security_event(
                event_type="EVIDENCE_ANCHORING_CHECK",
                severity=GuardrailSeverity.CRITICAL if decision == GuardrailDecision.BLOCK else GuardrailSeverity.HIGH,
                description=f"Evidence anchoring validation: {len(flags)} issues found",
                context=context,
                flags=flags,
                metadata={
                    "decision_status": decision_status,
                    "evidence_count": len(evidence_items),
                    "invalid_references": len(invalid_references),
                    "validation_passed": len(flags) == 0
                }
            )
        
        return GuardrailResult(
            decision=decision,
            flags=flags,
            security_context={
                "evidence_anchoring_check": True,
                "decision_present": bool(decision_data),
                "evidence_count": len(evidence_items),
                "validation_passed": len(flags) == 0,
                "decision_status": decision_status
            },
            guardrail_version=self.version
        )
    
    def get_rule_ids(self) -> List[str]:
        """Get evidence anchoring rule IDs"""
        return ["EVIDENCE-001", "EVIDENCE-002", "EVIDENCE-003", "EVIDENCE-004"]
    
    def set_minimum_evidence_threshold(self, threshold: int) -> None:
        """Set minimum evidence threshold"""
        self.minimum_evidence_threshold = max(1, threshold)
        logger.info(f"Set minimum evidence threshold to {threshold}")
    
    def add_required_evidence_type(self, decision_status: str, evidence_type: str) -> None:
        """Add required evidence type for a decision status"""
        if decision_status not in self.required_evidence_types:
            self.required_evidence_types[decision_status] = set()
        
        self.required_evidence_types[decision_status].add(evidence_type)
        logger.info(f"Added required evidence type '{evidence_type}' for {decision_status}")
    
    def add_hallucination_indicator(self, indicator: str) -> None:
        """Add a hallucination indicator"""
        self.hallucination_indicators.add(indicator.lower())
        logger.info(f"Added hallucination indicator: {indicator}")
