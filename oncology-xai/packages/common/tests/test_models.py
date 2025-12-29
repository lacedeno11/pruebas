"""Tests for Pydantic models."""

from datetime import datetime
from uuid import uuid4

import pytest

from oncology_common.models.base import (
    BaseModel,
    ErrorResponse,
    PaginatedResponse,
)
from oncology_common.models.entities import (
    Case,
    CaseCreate,
    CaseStatus,
    Patient,
    PatientCreate,
    PatternResult,
    PatternType,
    GeneticResult,
    MutationType,
    MutationStatus,
)


def test_patient_create():
    """Test PatientCreate model."""
    patient = PatientCreate(
        external_id="EXT-001",
        demographics={"age": 65, "gender": "M"},
    )
    assert patient.external_id == "EXT-001"
    assert patient.demographics["age"] == 65


def test_patient():
    """Test Patient model."""
    patient = Patient(
        patient_id=uuid4(),
        external_id="EXT-001",
        demographics={"age": 65},
        created_at=datetime.utcnow(),
    )
    assert patient.external_id == "EXT-001"
    assert patient.patient_id is not None


def test_case_status():
    """Test CaseStatus enum."""
    assert CaseStatus.CREATED == "CREATED"
    assert CaseStatus.REVIEW_REQUIRED == "REVIEW_REQUIRED"


def test_case_create():
    """Test CaseCreate model."""
    patient_id = uuid4()
    case = CaseCreate(
        patient_id=patient_id,
        tags=["lung", "adenocarcinoma"],
        metadata={"notes": "test"},
    )
    assert case.patient_id == patient_id
    assert "lung" in case.tags


def test_case():
    """Test Case model with defaults."""
    case = Case(
        case_id=uuid4(),
        patient_id=uuid4(),
        created_at=datetime.utcnow(),
    )
    assert case.status == CaseStatus.CREATED
    assert case.tags == []


def test_pattern_result():
    """Test PatternResult model."""
    result = PatternResult(
        pattern=PatternType.LEPIDIC,
        score=0.85,
        is_conclusive=True,
        overlay_uri="s3://bucket/overlay.png",
    )
    assert result.pattern == PatternType.LEPIDIC
    assert result.score == 0.85


def test_pattern_result_validation():
    """Test PatternResult score validation."""
    with pytest.raises(ValueError):
        PatternResult(pattern=PatternType.ACINAR, score=1.5)


def test_genetic_result():
    """Test GeneticResult model."""
    result = GeneticResult(
        mutation=MutationType.EGFR,
        score=0.72,
        status=MutationStatus.POSITIVE,
    )
    assert result.mutation == MutationType.EGFR
    assert result.status == MutationStatus.POSITIVE


def test_error_response():
    """Test ErrorResponse model."""
    error = ErrorResponse(
        errorCode="MODEL_UNAVAILABLE",
        message="Pattern model is not available",
        correlationId="corr_123",
        details={"model": "lung_v1"},
    )
    assert error.error_code == "MODEL_UNAVAILABLE"
    assert error.correlation_id == "corr_123"


def test_paginated_response():
    """Test PaginatedResponse model."""
    response = PaginatedResponse[str](
        data=["a", "b", "c"],
        total=10,
        page=1,
        page_size=3,
        has_more=True,
    )
    assert len(response.data) == 3
    assert response.has_more is True
