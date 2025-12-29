"""Pytest configuration for common package."""
import pytest


@pytest.fixture
def sample_jwt_payload():
    """Sample JWT payload for testing."""
    return {
        "sub": "test-user-id",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "realm_access": {"roles": ["clinician"]},
        "exp": 9999999999,
        "iat": 1704067200,
    }


@pytest.fixture
def sample_correlation_id():
    """Sample correlation ID."""
    return "test-correlation-id-12345"
