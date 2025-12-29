"""Pytest configuration for case-service tests."""
import pytest
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from case_service.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_patient_data():
    """Sample patient data."""
    return {
        "mrn": "MRN123456",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1980-01-15",
    }


@pytest.fixture
def sample_case_data():
    """Sample case data."""
    return {
        "patient_id": str(uuid4()),
        "description": "Lung biopsy case",
    }
