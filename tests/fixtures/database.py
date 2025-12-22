"""
Database Test Fixtures

This module provides pytest fixtures for database testing including
test database setup, teardown, and data management.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from policy_copilot.database.base import Base
from policy_copilot.database.models import *
from policy_copilot.database.repositories import RepositoryFactory
from policy_copilot.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL."""
    return "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
async def test_engine(test_database_url: str):
    """Create test database engine."""
    engine = create_async_engine(
        test_database_url,
        echo=False,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Start a transaction
        transaction = await session.begin()
        
        yield session
        
        # Rollback transaction to clean up
        await transaction.rollback()


@pytest.fixture(scope="function")
async def repository_factory(db_session: AsyncSession) -> RepositoryFactory:
    """Create repository factory with test session."""
    return RepositoryFactory(db_session)


@pytest.fixture(scope="function")
async def sample_case(db_session: AsyncSession) -> Case:
    """Create a sample case for testing."""
    case = Case(
        id="550e8400-e29b-41d4-a716-446655440000",
        crm_ticket_id="CRM-12345",
        customer_id="CUST-67890",
        contract_id="CONT-11111",
        insurer_id="INS001",
        plan_id="PLAN_BASIC",
        service_code="CONSULTATION_GENERAL",
        service_date=datetime.utcnow(),
        service_amount=150.0,
        provider_id="PROV_001",
        priority="MEDIUM",
        status="NUEVO",
        queue="STANDARD",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    
    return case


@pytest.fixture(scope="function")
async def sample_policy(db_session: AsyncSession) -> Policy:
    """Create a sample policy for testing."""
    policy = Policy(
        id="POL-001",
        title="Basic Medical Consultation Policy",
        version="1.0.0",
        content="This policy covers basic medical consultations...",
        document_type="POLICY",
        source="INTERNAL",
        status="ACTIVE",
        effective_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db_session.add(policy)
    await db_session.commit()
    await db_session.refresh(policy)
    
    return policy


@pytest.fixture(scope="function")
async def sample_decision(db_session: AsyncSession, sample_case: Case) -> Decision:
    """Create a sample decision for testing."""
    decision = Decision(
        id="DEC-001",
        case_id=sample_case.id,
        status="APROBADO",
        confidence_score=0.85,
        risk_score=0.15,
        explanation="Case approved based on policy compliance",
        evidence_references=["POL-001", "DOC-123"],
        decided_by="SYSTEM",
        decided_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db_session.add(decision)
    await db_session.commit()
    await db_session.refresh(decision)
    
    return decision


@pytest.fixture(scope="function")
async def sample_audit_log(db_session: AsyncSession, sample_case: Case) -> AuditLog:
    """Create a sample audit log for testing."""
    audit_log = AuditLog(
        id="AUDIT-001",
        case_id=sample_case.id,
        event_type="CASE_CREATED",
        event_category="CASE",
        event_description="Case created from CRM webhook",
        user_id="SYSTEM",
        event_data={"crm_ticket_id": sample_case.crm_ticket_id},
        processing_time_ms=100,
        security_level="NORMAL",
        created_at=datetime.utcnow()
    )
    
    db_session.add(audit_log)
    await db_session.commit()
    await db_session.refresh(audit_log)
    
    return audit_log


@pytest.fixture(scope="function")
async def sample_ml_prediction(db_session: AsyncSession, sample_case: Case) -> MLPrediction:
    """Create a sample ML prediction for testing."""
    ml_prediction = MLPrediction(
        id="ML-001",
        case_id=sample_case.id,
        service_name="classification",
        model_version="v2.1.0",
        prediction_type="CLASSIFICATION",
        input_features={"service_code": "CONSULTATION_GENERAL"},
        prediction_result={
            "request_type": "MEDICAL_CONSULTATION",
            "confidence": 0.85
        },
        confidence_score=0.85,
        processing_time_ms=150,
        created_at=datetime.utcnow()
    )
    
    db_session.add(ml_prediction)
    await db_session.commit()
    await db_session.refresh(ml_prediction)
    
    return ml_prediction


@pytest.fixture(scope="function")
async def clean_database(db_session: AsyncSession):
    """Clean all data from test database."""
    # Delete in reverse dependency order
    await db_session.execute(text("DELETE FROM ml_predictions"))
    await db_session.execute(text("DELETE FROM audit_logs"))
    await db_session.execute(text("DELETE FROM decisions"))
    await db_session.execute(text("DELETE FROM policy_exceptions"))
    await db_session.execute(text("DELETE FROM policies"))
    await db_session.execute(text("DELETE FROM cases"))
    await db_session.commit()


@pytest.fixture(scope="function")
async def populated_database(
    db_session: AsyncSession,
    sample_case: Case,
    sample_policy: Policy,
    sample_decision: Decision,
    sample_audit_log: AuditLog,
    sample_ml_prediction: MLPrediction
):
    """Database populated with sample data."""
    return {
        "case": sample_case,
        "policy": sample_policy,
        "decision": sample_decision,
        "audit_log": sample_audit_log,
        "ml_prediction": sample_ml_prediction
    }


class DatabaseTestHelper:
    """Helper class for database testing operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_test_case(self, **kwargs) -> Case:
        """Create a test case with custom attributes."""
        defaults = {
            "id": f"test-case-{datetime.utcnow().timestamp()}",
            "crm_ticket_id": f"CRM-{datetime.utcnow().timestamp()}",
            "customer_id": "CUST-TEST",
            "contract_id": "CONT-TEST",
            "insurer_id": "INS001",
            "plan_id": "PLAN_TEST",
            "service_code": "TEST_SERVICE",
            "service_date": datetime.utcnow(),
            "service_amount": 100.0,
            "provider_id": "PROV_TEST",
            "priority": "MEDIUM",
            "status": "NUEVO",
            "queue": "STANDARD",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        
        case = Case(**defaults)
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        
        return case
    
    async def create_test_policy(self, **kwargs) -> Policy:
        """Create a test policy with custom attributes."""
        defaults = {
            "id": f"POL-{datetime.utcnow().timestamp()}",
            "title": "Test Policy",
            "version": "1.0.0",
            "content": "Test policy content",
            "document_type": "POLICY",
            "source": "INTERNAL",
            "status": "ACTIVE",
            "effective_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        
        policy = Policy(**defaults)
        self.session.add(policy)
        await self.session.commit()
        await self.session.refresh(policy)
        
        return policy
    
    async def count_records(self, model_class) -> int:
        """Count records in a table."""
        result = await self.session.execute(
            text(f"SELECT COUNT(*) FROM {model_class.__tablename__}")
        )
        return result.scalar()


@pytest.fixture(scope="function")
async def db_helper(db_session: AsyncSession) -> DatabaseTestHelper:
    """Create database test helper."""
    return DatabaseTestHelper(db_session)
