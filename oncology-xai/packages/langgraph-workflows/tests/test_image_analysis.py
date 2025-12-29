"""Tests for image analysis workflow."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langgraph_workflows.graphs.image_analysis import (
    ImageAnalysisState,
    validate_input,
    load_image,
    run_pattern_model,
    run_mutation_model,
    generate_xai,
    assemble_result_bundle,
    policy_check,
)


class TestImageAnalysisState:
    def test_state_initialization(self, sample_case_id, sample_image_id, sample_job_id):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
        )
        assert state.case_id == sample_case_id
        assert state.error is None
        assert state.pattern_results == []
        assert state.mutation_results == []


class TestValidateInput:
    @pytest.mark.asyncio
    async def test_validate_input_success(self, sample_case_id, sample_image_id, sample_job_id):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
        )

        result = await validate_input(state)

        assert result.get("error") is None

    @pytest.mark.asyncio
    async def test_validate_input_missing_uri(self, sample_case_id, sample_image_id, sample_job_id):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="",
        )

        result = await validate_input(state)

        assert result.get("error") is not None


class TestLoadImage:
    @pytest.mark.asyncio
    async def test_load_image_success(self, sample_case_id, sample_image_id, sample_job_id, sample_image_data):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
        )

        with patch("langgraph_workflows.graphs.image_analysis.load_from_storage") as mock_load:
            mock_load.return_value = sample_image_data
            result = await load_image(state)

        assert result.get("image_data") is not None


class TestRunPatternModel:
    @pytest.mark.asyncio
    async def test_run_pattern_model(self, sample_case_id, sample_image_id, sample_job_id, sample_image_data):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
            image_data=sample_image_data,
        )

        with patch("langgraph_workflows.graphs.image_analysis.pattern_model_client") as mock_client:
            mock_client.predict.return_value = {
                "patterns": [
                    {"type": "acinar", "confidence": 0.85, "area_percentage": 45.0},
                    {"type": "lepidic", "confidence": 0.72, "area_percentage": 30.0},
                ]
            }
            result = await run_pattern_model(state)

        assert len(result.get("pattern_results", [])) > 0


class TestRunMutationModel:
    @pytest.mark.asyncio
    async def test_run_mutation_model(self, sample_case_id, sample_image_id, sample_job_id, sample_image_data):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
            image_data=sample_image_data,
        )

        with patch("langgraph_workflows.graphs.image_analysis.mutation_model_client") as mock_client:
            mock_client.predict.return_value = {
                "mutations": [
                    {"type": "EGFR", "probability": 0.78, "variant": "L858R"},
                ]
            }
            result = await run_mutation_model(state)

        assert len(result.get("mutation_results", [])) > 0


class TestGenerateXAI:
    @pytest.mark.asyncio
    async def test_generate_xai_artifacts(self, sample_case_id, sample_image_id, sample_job_id):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
            pattern_results=[
                {"type": "acinar", "confidence": 0.85, "area_percentage": 45.0},
            ],
            mutation_results=[
                {"type": "EGFR", "probability": 0.78},
            ],
        )

        result = await generate_xai(state)

        assert result.get("xai_artifacts") is not None


class TestPolicyCheck:
    @pytest.mark.asyncio
    async def test_policy_check_passes(self, sample_case_id, sample_image_id, sample_job_id):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
            pattern_results=[
                {"type": "acinar", "confidence": 0.85, "area_percentage": 45.0},
            ],
            xai_artifacts={"heatmap_uri": "s3://bucket/heatmap.png"},
        )

        result = await policy_check(state)

        assert result.get("policy_passed", False) is True

    @pytest.mark.asyncio
    async def test_policy_check_low_confidence(self, sample_case_id, sample_image_id, sample_job_id):
        state = ImageAnalysisState(
            case_id=sample_case_id,
            image_id=sample_image_id,
            job_id=sample_job_id,
            image_uri="s3://bucket/image.png",
            pattern_results=[
                {"type": "acinar", "confidence": 0.25, "area_percentage": 45.0},  # Low confidence
            ],
        )

        result = await policy_check(state)

        # Should still pass but with warning
        assert "policy_warnings" in result or result.get("policy_passed") is True
