"""
Pytest configuration and fixtures for PEI Agentic Platform tests.
Provides test database setup, FastAPI test client, and sample data fixtures.
"""

import asyncio
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from main import app


# ============================================================================
# SETTINGS OVERRIDE FOR TESTING
# ============================================================================


class TestSettings(Settings):
    """Override settings for testing."""

    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    SYSTEM_MODE: str = "MOCK"
    LOG_LEVEL: str = "WARNING"
    MOCK_API_LATENCY_MS: int = 0  # No latency in tests


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test SQLite database in memory.
    
    Returns:
        AsyncGenerator[AsyncSession]: Async database session for tests
        
    Yields:
        AsyncSession: Session connected to test database
    """
    # Create in-memory SQLite engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    SessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )
    
    async with SessionLocal() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
def mock_settings() -> Generator[TestSettings, None, None]:
    """
    Override application settings for testing.
    
    Yields:
        TestSettings: Test configuration
    """
    original_settings = get_settings()
    test_settings = TestSettings()
    
    # Patch get_settings to return test settings
    def override_get_settings():
        return test_settings
    
    app.dependency_overrides[get_settings] = override_get_settings
    
    yield test_settings
    
    # Restore original settings
    del app.dependency_overrides[get_settings]


# ============================================================================
# FASTAPI TEST CLIENT FIXTURE
# ============================================================================


@pytest.fixture
def test_client(mock_settings) -> TestClient:
    """
    Create a FastAPI test client with test database.
    
    Args:
        mock_settings: Test settings fixture
        
    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_ot():
    """
    Create a sample OT for testing.
    
    Returns:
        dict: Sample OT data
    """
    return {
        "id": str(uuid.uuid4()),
        "external_id": "OT-TEST-001",
        "status": "PREPLANIFICADA",
        "project_type": "PUBLICO",
        "cliente_id": "CLI-TEST-001",
        "login_id": "LOGIN-TEST-001",
        "lat": -0.22,
        "long": -78.51,
        "created_at": "2024-02-13T15:30:45",
        "updated_at": "2024-02-13T15:30:45",
        "cuadrilla_id": None,
        "geo_error": False,
        "detention_reason": None,
    }


@pytest.fixture
def sample_cuadrilla():
    """
    Create a sample Cuadrilla (crew) for testing.
    
    Returns:
        dict: Sample Cuadrilla data
    """
    return {
        "id": str(uuid.uuid4()),
        "name": "Cuadrilla Test-01",
        "type": "PRINCIPAL",
        "last_centroid_lat": -0.22,
        "last_centroid_long": -78.51,
        "daily_capacity": 10,
        "current_load": 0,
        "active": True,
        "created_at": "2024-02-13T10:00:00",
    }


@pytest.fixture
def sample_invalid_ot():
    """
    Create a sample OT with invalid coordinates for testing geo_error.
    
    Returns:
        dict: Sample OT with invalid coordinates
    """
    return {
        "id": str(uuid.uuid4()),
        "external_id": "OT-INVALID-GEO",
        "status": "PREPLANIFICADA",
        "project_type": "PRIVADO",
        "cliente_id": "CLI-GEO-ERR",
        "login_id": "LOGIN-GEO-ERR",
        "lat": 91.0,  # Invalid latitude
        "long": 200.0,  # Invalid longitude
        "created_at": "2024-02-13T15:30:45",
        "updated_at": "2024-02-13T15:30:45",
        "cuadrilla_id": None,
        "geo_error": True,
    }


@pytest.fixture
def sample_log_entry():
    """
    Create a sample log entry for testing.
    
    Returns:
        dict: Sample log data
    """
    return {
        "id": str(uuid.uuid4()),
        "agente_name": "RouterAgent",
        "accion": "CLASSIFY_INTENT",
        "resultado": "SUCCESS",
        "ot_id": None,
        "raw_llm_response": '{"intent": "PLAN_OTS"}',
        "timestamp": "2024-02-13T15:30:45",
        "correlation_id": str(uuid.uuid4()),
        "metadata": {"intent": "PLAN_OTS"},
    }


@pytest.fixture
def sample_assignment():
    """
    Create a sample assignment for testing.
    
    Returns:
        dict: Sample assignment data
    """
    return {
        "id": str(uuid.uuid4()),
        "ot_id": str(uuid.uuid4()),
        "cuadrilla_id": str(uuid.uuid4()),
        "assigned_at": "2024-02-13T15:30:45",
        "assigned_by": "PlanificacionAgent",
        "distance_from_centroid": 5.3,
        "phase": "PROXIMITY",
        "status": "ACTIVE",
        "completed_at": None,
        "notes": None,
    }


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.
    
    Returns:
        asyncio.AbstractEventLoop: Event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# PYTEST MARKERS
# ============================================================================


def pytest_configure(config):
    """Register custom markers for pytest."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test",
    )

