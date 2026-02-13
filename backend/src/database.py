"""
Async database connection setup for PEI Platform.

This module configures SQLAlchemy's async engine and session management
for PostgreSQL using asyncpg driver. Provides dependency injection for
FastAPI route handlers and initialization utilities.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import async_sessionmaker

from src.config.settings import settings
from src.models import Base

logger = logging.getLogger(__name__)

# Create async engine with settings-based configuration
engine = create_async_engine(
    settings.database_url,
    echo=settings.get_db_echo(),  # Echo SQL in MOCK mode for debugging
    future=True,
    pool_pre_ping=True,  # Test connections before using them
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function for FastAPI route handlers.

    Yields a database session for the duration of the request,
    and ensures proper cleanup on completion or error.

    Usage in FastAPI:
        @app.get("/api/ots")
        async def get_ots(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass

    Yields:
        AsyncSession: Database session for the request
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database by creating all tables.

    This function:
    1. Creates the async engine connection
    2. Creates all tables defined in Base.metadata
    3. Logs success/failure

    Should be called during FastAPI startup event.

    Example in main.py:
        @app.on_event("startup")
        async def startup():
            await init_db()
    """
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def drop_all_tables() -> None:
    """
    Drop all tables from the database.

    WARNING: This will delete all data. Use only for testing/development.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {str(e)}")
        raise


async def close_db() -> None:
    """
    Close the database engine and clean up connections.

    Should be called during FastAPI shutdown event.

    Example in main.py:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db()
    """
    try:
        await engine.dispose()
        logger.info("Database engine closed")
    except Exception as e:
        logger.error(f"Failed to close database engine: {str(e)}")
        raise


# Health check function
async def check_db_connection() -> bool:
    """
    Check if the database connection is healthy.

    Used for health check endpoints and startup validation.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        logger.info("Database connection check passed")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False

