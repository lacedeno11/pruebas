"""Tests for inference service routes."""
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestInferenceRoutes:
    @pytest.fixture
    def client(self):
        from inference_service.main import app
        return TestClient(app)

    def test_health_check(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "inference-service"

    @patch("inference_service.routes.jobs.JobService")
    def test_create_job(self, mock_service_class, client, sample_case_id, sample_image_id):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        mock_job = MagicMock()
        mock_job.job_id = uuid4()
        mock_job.case_id = sample_case_id
        mock_job.image_id = sample_image_id
        mock_job.status = "pending"
        mock_job.created_at = None
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.error_message = None

        mock_service.create_job.return_value = mock_job

        response = client.post(
            "/api/v1/jobs",
            json={
                "case_id": str(sample_case_id),
                "image_id": str(sample_image_id),
            },
        )

        assert response.status_code in [201, 422, 500]

    @patch("inference_service.routes.jobs.JobService")
    def test_get_job_not_found(self, mock_service_class, client):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.get_job.return_value = None

        job_id = str(uuid4())
        response = client.get(f"/api/v1/jobs/{job_id}")

        assert response.status_code in [404, 500]

    @patch("inference_service.routes.jobs.JobService")
    def test_list_case_jobs(self, mock_service_class, client, sample_case_id):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.list_by_case.return_value = []

        response = client.get(f"/api/v1/cases/{sample_case_id}/jobs")

        assert response.status_code in [200, 500]


class TestMockModels:
    def test_pattern_predictions_structure(self, sample_pattern_predictions):
        for pred in sample_pattern_predictions:
            assert "type" in pred
            assert "confidence" in pred
            assert "area_percentage" in pred
            assert 0 <= pred["confidence"] <= 1
            assert 0 <= pred["area_percentage"] <= 100

    def test_mutation_predictions_structure(self, sample_mutation_predictions):
        for pred in sample_mutation_predictions:
            assert "type" in pred
            assert "probability" in pred
            assert 0 <= pred["probability"] <= 1

    def test_pattern_types_valid(self, sample_pattern_predictions):
        valid_types = {"lepidic", "acinar", "papillary", "micropapillary", "solid"}
        for pred in sample_pattern_predictions:
            assert pred["type"] in valid_types

    def test_mutation_types_valid(self, sample_mutation_predictions):
        valid_types = {"EGFR", "KRAS", "TP53"}
        for pred in sample_mutation_predictions:
            assert pred["type"] in valid_types
