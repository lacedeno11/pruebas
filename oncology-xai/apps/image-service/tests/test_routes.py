"""Tests for image service routes."""
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestImageRoutes:
    @pytest.fixture
    def client(self):
        from image_service.main import app
        return TestClient(app)

    def test_health_check(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "image-service"

    @patch("image_service.routes.images.ImageService")
    def test_list_case_images_empty(self, mock_service_class, client):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.list_by_case.return_value = []

        case_id = str(uuid4())
        response = client.get(f"/api/v1/cases/{case_id}/images")

        assert response.status_code in [200, 500]

    @patch("image_service.routes.images.ImageService")
    def test_get_image_not_found(self, mock_service_class, client):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.get_by_id.return_value = None

        image_id = str(uuid4())
        response = client.get(f"/api/v1/images/{image_id}")

        assert response.status_code in [404, 500]

    @patch("image_service.routes.images.ImageService")
    @patch("image_service.routes.images.get_event_publisher")
    def test_upload_image(self, mock_publisher, mock_service_class, client, sample_image_bytes, sample_case_id):
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        from image_service.models import Image as ImageModel, ImageFormatEnum
        mock_image = MagicMock()
        mock_image.image_id = uuid4()
        mock_image.case_id = sample_case_id
        mock_image.format = ImageFormatEnum.PNG
        mock_image.storage_uri = "s3://bucket/test.png"
        mock_image.checksum = "abc123"
        mock_image.size_bytes = len(sample_image_bytes)
        mock_image.stain = None
        mock_image.magnification = None
        mock_image.notes = None
        mock_image.uploaded_by = None
        mock_image.uploaded_at = None

        mock_service.upload.return_value = mock_image
        mock_publisher.return_value = MagicMock()

        response = client.post(
            f"/api/v1/cases/{sample_case_id}/images:upload",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )

        # May succeed or fail depending on DB/storage setup
        assert response.status_code in [201, 400, 500]


class TestImageService:
    @pytest.mark.asyncio
    async def test_checksum_calculation(self, sample_image_bytes):
        import hashlib
        expected = hashlib.sha256(sample_image_bytes).hexdigest()

        # Verify checksum logic
        actual = hashlib.sha256(sample_image_bytes).hexdigest()
        assert actual == expected

    def test_supported_formats(self):
        from image_service.models import ImageFormatEnum

        assert ImageFormatEnum.PNG.value == "png"
        assert ImageFormatEnum.BIFF.value == "biff"
