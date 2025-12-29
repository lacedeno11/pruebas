"""Tests for clinical guardrails."""
import pytest
from langgraph_workflows.guardrails import (
    validate_explanation_text,
    check_prohibited_phrases,
    check_required_sections,
    GuardrailResult,
)


class TestProhibitedPhrases:
    def test_detects_definitive_diagnosis(self):
        text = "This patient has cancer. The diagnosis is confirmed."
        result = check_prohibited_phrases(text)

        assert result.passed is False
        assert len(result.violations) > 0
        assert any("definitive" in v.lower() or "diagnosis" in v.lower() for v in result.violations)

    def test_detects_certainty_language(self):
        text = "The patient definitely has EGFR mutation. This is certain."
        result = check_prohibited_phrases(text)

        assert result.passed is False

    def test_allows_suggestive_language(self):
        text = "Findings suggest possible adenocarcinoma pattern. Further investigation recommended."
        result = check_prohibited_phrases(text)

        assert result.passed is True

    def test_allows_probability_language(self):
        text = "Model indicates 85% probability of EGFR mutation. Clinical correlation advised."
        result = check_prohibited_phrases(text)

        assert result.passed is True


class TestRequiredSections:
    def test_detects_missing_disclaimer(self):
        text = """
        ## Summary
        The analysis shows acinar pattern predominant.

        ## Findings
        - Pattern: Acinar (85%)
        - Mutation: EGFR (78%)
        """
        result = check_required_sections(text)

        assert result.passed is False
        assert any("disclaimer" in v.lower() for v in result.violations)

    def test_passes_with_all_sections(self):
        text = """
        ## Summary
        The analysis shows acinar pattern predominant.

        ## Findings
        - Pattern: Acinar (85%)
        - Mutation: EGFR (78%)

        ## Disclaimer
        This is an AI-assisted analysis and should not be used as a definitive diagnosis.
        Clinical correlation is required. Final interpretation must be made by a qualified pathologist.
        """
        result = check_required_sections(text)

        assert result.passed is True

    def test_detects_missing_clinical_correlation(self):
        text = """
        ## Summary
        Analysis complete.

        ## Disclaimer
        AI-generated content.
        """
        result = check_required_sections(text)

        # Should fail due to missing clinical correlation language
        assert "clinical" in text.lower() or result.passed is False


class TestValidateExplanationText:
    def test_full_validation_passes(self):
        text = """
        ## Summary
        Analysis suggests possible acinar-predominant adenocarcinoma pattern.

        ## Findings
        The model indicates the following observations:
        - Acinar pattern: 85% confidence (45% area)
        - EGFR mutation probability: 78%

        These findings should be correlated with clinical presentation.

        ## Disclaimer
        This is an AI-assisted analysis tool. The results presented here are computational
        predictions and should not be used as a definitive diagnosis. All findings require
        validation by a qualified pathologist. Clinical correlation is strongly recommended.
        """
        result = validate_explanation_text(text)

        assert result.passed is True
        assert len(result.violations) == 0

    def test_full_validation_fails_prohibited(self):
        text = """
        ## Diagnosis
        The patient has confirmed lung adenocarcinoma.

        ## Disclaimer
        AI analysis - clinical correlation required.
        """
        result = validate_explanation_text(text)

        assert result.passed is False

    def test_returns_all_violations(self):
        text = "Patient definitely has cancer. No doubt about it."
        result = validate_explanation_text(text)

        assert result.passed is False
        assert len(result.violations) > 0


class TestGuardrailResult:
    def test_guardrail_result_creation(self):
        result = GuardrailResult(
            passed=True,
            violations=[],
            warnings=["Low confidence detected"],
        )
        assert result.passed is True
        assert len(result.warnings) == 1

    def test_guardrail_result_with_violations(self):
        result = GuardrailResult(
            passed=False,
            violations=["Prohibited phrase detected", "Missing disclaimer"],
            warnings=[],
        )
        assert result.passed is False
        assert len(result.violations) == 2
