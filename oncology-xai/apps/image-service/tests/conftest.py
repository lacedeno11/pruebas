"""Pytest configuration for image-service tests."""
import pytest
import asyncio
from uuid import uuid4
from io import BytesIO


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_image_bytes():
    """Minimal valid PNG bytes."""
    # 1x1 transparent PNG
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return png_data


@pytest.fixture
def sample_case_id():
    """Sample case ID."""
    return uuid4()


@pytest.fixture
def sample_image_upload(sample_image_bytes):
    """Sample image upload file-like object."""
    return BytesIO(sample_image_bytes)
