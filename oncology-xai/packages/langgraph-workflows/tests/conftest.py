"""Pytest configuration for langgraph-workflows package."""
import pytest
from uuid import uuid4


@pytest.fixture
def sample_case_id():
    """Sample case ID."""
    return str(uuid4())


@pytest.fixture
def sample_image_id():
    """Sample image ID."""
    return str(uuid4())


@pytest.fixture
def sample_job_id():
    """Sample job ID."""
    return str(uuid4())


@pytest.fixture
def sample_image_data():
    """Sample image data (minimal PNG)."""
    # Minimal valid PNG header
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'


@pytest.fixture
def sample_ehr_text():
    """Sample EHR text for testing."""
    return """
    Patient presents with lung adenocarcinoma. Biopsy shows acinar pattern predominant.
    EGFR mutation positive (L858R). Recommend targeted therapy with osimertinib.
    Stage IIIA based on CT findings. No evidence of distant metastasis.
    """
