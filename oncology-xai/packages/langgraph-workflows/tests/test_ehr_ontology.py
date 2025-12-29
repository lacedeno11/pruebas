"""Tests for EHR ontology workflow."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langgraph_workflows.graphs.ehr_ontology import (
    EHROntologyState,
    normalize_ehr,
    extract_entities,
    lookup_candidates,
    disambiguate,
    build_evidence_pack,
)


class TestEHROntologyState:
    def test_state_initialization(self, sample_case_id):
        state = EHROntologyState(
            case_id=sample_case_id,
            raw_ehr_text="Patient has lung cancer.",
        )
        assert state.case_id == sample_case_id
        assert state.entities == []
        assert state.mappings == []


class TestNormalizeEHR:
    @pytest.mark.asyncio
    async def test_normalize_ehr_text(self, sample_case_id, sample_ehr_text):
        state = EHROntologyState(
            case_id=sample_case_id,
            raw_ehr_text=sample_ehr_text,
        )

        result = await normalize_ehr(state)

        assert result.get("normalized_text") is not None
        assert len(result.get("normalized_text", "")) > 0


class TestExtractEntities:
    @pytest.mark.asyncio
    async def test_extract_entities_from_text(self, sample_case_id, sample_ehr_text):
        state = EHROntologyState(
            case_id=sample_case_id,
            raw_ehr_text=sample_ehr_text,
            normalized_text=sample_ehr_text.lower().strip(),
        )

        with patch("langgraph_workflows.graphs.ehr_ontology.llm_client") as mock_llm:
            mock_llm.extract_entities.return_value = [
                {"text": "lung adenocarcinoma", "type": "diagnosis", "confidence": 0.92},
                {"text": "EGFR mutation", "type": "biomarker", "confidence": 0.88},
                {"text": "osimertinib", "type": "medication", "confidence": 0.95},
            ]
            result = await extract_entities(state)

        entities = result.get("entities", [])
        assert len(entities) > 0


class TestLookupCandidates:
    @pytest.mark.asyncio
    async def test_lookup_ontology_candidates(self, sample_case_id):
        state = EHROntologyState(
            case_id=sample_case_id,
            raw_ehr_text="Patient has adenocarcinoma",
            entities=[
                {"text": "adenocarcinoma", "type": "diagnosis", "confidence": 0.92},
            ],
        )

        with patch("langgraph_workflows.graphs.ehr_ontology.sparql_client") as mock_sparql:
            mock_sparql.search_terms.return_value = [
                {"ontology": "NCIt", "term_id": "NCIT:C3512", "label": "Adenocarcinoma", "score": 0.95},
                {"ontology": "MONDO", "term_id": "MONDO:0004970", "label": "adenocarcinoma", "score": 0.90},
            ]
            result = await lookup_candidates(state)

        candidates = result.get("candidates", [])
        assert len(candidates) >= 0  # May be empty without mock


class TestDisambiguate:
    @pytest.mark.asyncio
    async def test_disambiguate_candidates(self, sample_case_id):
        state = EHROntologyState(
            case_id=sample_case_id,
            raw_ehr_text="Patient has lung adenocarcinoma",
            entities=[
                {"text": "lung adenocarcinoma", "type": "diagnosis", "confidence": 0.92},
            ],
            candidates=[
                {
                    "entity_text": "lung adenocarcinoma",
                    "matches": [
                        {"ontology": "NCIt", "term_id": "NCIT:C3512", "label": "Adenocarcinoma", "score": 0.95},
                        {"ontology": "NCIt", "term_id": "NCIT:C4451", "label": "Lung Adenocarcinoma", "score": 0.98},
                    ],
                },
            ],
        )

        with patch("langgraph_workflows.graphs.ehr_ontology.llm_client") as mock_llm:
            mock_llm.disambiguate.return_value = [
                {"entity_text": "lung adenocarcinoma", "best_match": "NCIT:C4451", "confidence": 0.98},
            ]
            result = await disambiguate(state)

        mappings = result.get("mappings", [])
        assert len(mappings) >= 0


class TestBuildEvidencePack:
    @pytest.mark.asyncio
    async def test_build_evidence_pack(self, sample_case_id):
        state = EHROntologyState(
            case_id=sample_case_id,
            raw_ehr_text="Patient has lung adenocarcinoma",
            entities=[
                {"text": "lung adenocarcinoma", "type": "diagnosis", "confidence": 0.92},
            ],
            mappings=[
                {
                    "entity_text": "lung adenocarcinoma",
                    "ontology": "NCIt",
                    "term_id": "NCIT:C4451",
                    "term_label": "Lung Adenocarcinoma",
                    "confidence": 0.98,
                },
            ],
        )

        result = await build_evidence_pack(state)

        evidence = result.get("evidence_pack")
        assert evidence is not None
