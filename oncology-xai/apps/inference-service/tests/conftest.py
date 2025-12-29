"""Pytest configuration for inference-service tests."""
import pytest
import asyncio
from uuid import uuid4


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_case_id():
    """Sample case ID."""
    return uuid4()


@pytest.fixture
def sample_image_id():
    """Sample image ID."""
    return uuid4()


@pytest.fixture
def sample_job_id():
    """Sample job ID."""
    return uuid4()


@pytest.fixture
def sample_pattern_predictions():
    """Sample pattern model predictions."""
    return [
        {"type": "acinar", "confidence": 0.85, "area_percentage": 45.0},
        {"type": "lepidic", "confidence": 0.72, "area_percentage": 30.0},
        {"type": "solid", "confidence": 0.15, "area_percentage": 15.0},
        {"type": "papillary", "confidence": 0.08, "area_percentage": 8.0},
        {"type": "micropapillary", "confidence": 0.02, "area_percentage": 2.0},
    ]


@pytest.fixture
def sample_mutation_predictions():
    """Sample mutation model predictions."""
    return [
        {"type": "EGFR", "probability": 0.78, "variant": "L858R"},
        {"type": "KRAS", "probability": 0.15, "variant": None},
        {"type": "TP53", "probability": 0.45, "variant": "R248W"},
    ]
