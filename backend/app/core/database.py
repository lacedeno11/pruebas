"""
Database configuration and session management for PEI Agentic Platform.
Uses SQLAlchemy async engine with connection pooling and Alembic migrations.
"""

import os
from typing import AsyncGenerator

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

# ============================================================================
# DATABASE BASE & DECLARATIVE
# ============================================================================

Base = declarative_base()
"""
SQLAlchemy declarative base for all ORM models.
All database models should inherit from this Base class.
"""

# ============================================================================
# ASYNC ENGINE & SESSION FACTORY
# ============================================================================

def _get_database_url() -> str:
    """
    Get database URL from settings, converting SQLite to async format if needed.
    
    Returns:
        str: Async-compatible database URL
        
    Examples:
        - sqlite:///./pei.db -> sqlite+aiosqlite:///./pei.db
        - postgresql://... -> postgresql+asyncpg://...
    """
    settings = get_settings()
    db_url = settings.DATABASE_URL
    
    # Convert SQLite to async format
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    # Convert PostgreSQL to async format
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Return as-is if already async-compatible
    return db_url


def _create_async_engine():
    """
    Create SQLAlchemy async engine with connection pooling.
    
    Configuration:
    - pool_size: Number of persistent connections to maintain (default 20)
    - max_overflow: Maximum overflow connections above pool_size (default 10)
    - echo: Log all SQL statements (debug mode only)
    - future: Use SQLAlchemy 2.0 style (required for async)
    - pool_pre_ping: Verify connection before using (detect stale connections)
    
    Returns:
        AsyncEngine: Configured async database engine
    """
    settings = get_settings()
    db_url = _get_database_url()
    
    # Use appropriate pool class based on database type
    poolclass = (
        pool.NullPool
        if "sqlite" in db_url
        else pool.QueuePool
    )
    
    engine = create_async_engine(
        db_url,
        echo=settings.SYSTEM_MODE == "DEBUG",
        future=True,
        pool_pre_ping=True,
        poolclass=poolclass,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        connect_args={
            "timeout": settings.REQUEST_TIMEOUT_SECONDS,
            "check_same_thread": False,  # For SQLite compatibility
        } if "sqlite" in db_url else {
            "timeout": settings.REQUEST_TIMEOUT_SECONDS,
        },
    )
    
    return engine


# Create global async engine instance
engine = _create_async_engine()

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ============================================================================
# FASTAPI DEPENDENCY: get_db()
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session management.
    
    Usage in route handlers:
        @router.get("/ots")
        async def list_ots(db: AsyncSession = Depends(get_db)):
            ots = await db.execute(select(OT))
            return ots.scalars().all()
    
    Yields:
        AsyncSession: Database session for the request
        
    Guarantees:
        - Session is created for each request
        - Session is rolled back on any exception
        - Session is properly closed after request completes
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# DATABASE INITIALIZATION & MIGRATIONS
# ============================================================================

async def init_db() -> None:
    """
    Initialize database with Alembic migrations on application startup.
    
    This function:
    1. Checks if Alembic is available
    2. Runs all pending migrations
    3. Falls back to create_all() for development/testing
    
    Call this from FastAPI lifespan startup event:
        @app.lifespan
        @contextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await init_db()
            yield
            # Shutdown
            await close_db()
    
    Raises:
        RuntimeError: If both migrations and create_all() fail
    """
    try:
        # Try to run Alembic migrations
        await _run_alembic_migrations()
    except ImportError:
        # Alembic not available, fall back to create_all()
        await _create_all_tables()
    except Exception as e:
        # If migrations fail, try create_all() as fallback
        try:
            await _create_all_tables()
        except Exception as fallback_error:
            raise RuntimeError(
                f"Failed to initialize database. "
                f"Migration error: {e}, "
                f"create_all() error: {fallback_error}"
            )


async def _create_all_tables() -> None:
    """
    Create all database tables using SQLAlchemy's create_all().
    
    Used for development mode or when Alembic is not available.
    Requires all models to be imported before calling.
    
    Note: This should NOT be used in production. Always use Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _run_alembic_migrations() -> None:
    """
    Run Alembic migrations programmatically.
    
    This requires:
    1. alembic.ini in backend directory
    2. alembic/env.py configured with DATABASE_URL
    3. Alembic installed (pip install alembic)
    
    Raises:
        ImportError: If alembic is not installed
        Exception: If migration execution fails
    """
    from alembic import command
    from alembic.config import Config as AlembicConfig
    
    # Determine alembic.ini path
    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    
    if not os.path.exists(alembic_ini):
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")
    
    # Create Alembic config
    alembic_config = AlembicConfig(alembic_ini)
    
    # Set sqlalchemy.url from environment
    alembic_config.set_main_option(
        "sqlalchemy.url",
        _get_database_url()
    )
    
    # Run migrations (upgrade to head)
    command.upgrade(alembic_config, "head")


async def close_db() -> None:
    """
    Close database connections on application shutdown.
    
    Call this from FastAPI lifespan shutdown event:
        @app.lifespan
        @contextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await init_db()
            yield
            # Shutdown
            await close_db()
    
    Ensures:
        - All connection pools are properly drained
        - All async resources are released
    """
    await engine.dispose()


# ============================================================================
# DATABASE CONTEXT MANAGER (for scripts/tests)
# ============================================================================

class DatabaseSession:
    """
    Context manager for database session in scripts or background tasks.
    
    Usage:
        async with DatabaseSession() as session:
            ots = await session.execute(select(OT))
            ots_list = ots.scalars().all()
    """
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self) -> AsyncSession:
        self.session = AsyncSessionLocal()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


# ============================================================================
# DATABASE TESTING UTILITIES
# ============================================================================

async def create_test_db() -> AsyncSession:
    """
    Create an in-memory test database for testing.
    
    Returns:
        AsyncSession: Test database session
        
    Note:
        Remember to call teardown_test_db() to clean up.
    """
    # Create in-memory SQLite engine for testing
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    TestSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    return TestSessionLocal()


async def teardown_test_db(session: AsyncSession) -> None:
    """
    Clean up test database and session.
    
    Args:
        session: Test database session to clean up
    """
    await session.close()

