"""
DERCAS-ONCO-XAI Case Service Database

SQLAlchemy 2.0 database configuration and session management.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Global variables for database engine and session factory
engine = None
async_session_factory = None


async def init_database(database_url: str) -> None:
    """Initialize database engine and session factory."""
    global engine, async_session_factory
    
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL logging in development
        poolclass=NullPool,  # Use NullPool for async
        future=True
    )
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info("Database engine and session factory initialized")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    if not async_session_factory:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all database tables."""
    if not engine:
        raise RuntimeError("Database engine not initialized")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def drop_tables() -> None:
    """Drop all database tables."""
    if not engine:
        raise RuntimeError("Database engine not initialized")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Database tables dropped")


async def close_database() -> None:
    """Close database connections."""
    global engine
    
    if engine:
        await engine.dispose()
        engine = None
        logger.info("Database connections closed")
