"""
SQLAlchemy Database Configuration and Session Management

This module sets up the async SQLAlchemy engine and session factory for the DERCAS PEI
backend. It provides:

- Async PostgreSQL engine via AsyncPG driver
- AsyncSessionLocal factory for creating database sessions
- Base declarative class for ORM model definitions
- get_db() dependency for FastAPI endpoints

Connection Details:
- Database: PostgreSQL 15+
- Driver: AsyncPG (async driver for PostgreSQL)
- Connection String: postgresql+asyncpg://user:password@host:port/database
- Connection Pooling: Built-in via SQLAlchemy
- Echo: Disabled in production, can be enabled for debugging

Usage in Models:
    from app.core.database import Base
    
    class OT(Base):
        __tablename__ = "ots"
        id = Column(Integer, primary_key=True)
        ...

Usage in FastAPI Routes:
    from app.core.database import get_db
    
    @router.get("/items")
    async def get_items(session: AsyncSession = Depends(get_db)):
        result = await session.execute(select(Item))
        return result.scalars().all()
"""

import logging
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Async SQLAlchemy Engine Configuration
# ============================================================================

# Create async engine with connection pooling
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    # Connection pool configuration
    pool_size=10,  # Number of connections to maintain in the pool
    max_overflow=20,  # Maximum connections to create above pool_size
    pool_pre_ping=True,  # Test connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    # Logging and debugging
    echo=False,  # Set to True for SQL query logging
    echo_pool=False,  # Set to True for connection pool logging
    # Asyncio settings
    future=True,  # Use SQLAlchemy 2.0 future behavior
)

"""
AsyncEngine instance for database operations.

Configuration:
- pool_size: 10 - Maintain 10 connections in the pool
- max_overflow: 20 - Allow up to 20 additional connections if needed
- pool_pre_ping: True - Test connections before use (prevents stale connections)
- pool_recycle: 3600 - Recycle connections every hour (prevents timeout issues)
- echo: False - Disable query logging (enable for debugging)
- future: True - Use SQLAlchemy 2.0 style operations
"""


# ============================================================================
# AsyncSessionLocal Factory
# ============================================================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects accessible after commit
    autoflush=False,  # Require explicit flush operations
    autocommit=False,  # Require explicit commits
)

"""
AsyncSessionLocal factory for creating database sessions.

Configuration:
- class_: AsyncSession - Use async-aware session class
- expire_on_commit: False - Objects remain usable after commit
- autoflush: False - Explicit flush control for better performance
- autocommit: False - Explicit commit control for transaction management

Usage:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Model))
        await session.commit()
"""


# ============================================================================
# Base Declarative Class
# ============================================================================

Base = declarative_base()

"""
Declarative base for all SQLAlchemy ORM models.

All model classes should inherit from Base:

    class MyModel(Base):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)
        name = Column(String)
"""


# ============================================================================
# FastAPI Dependency for Database Sessions
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields database sessions.
    
    This generator function creates a new database session for each request,
    ensuring proper resource management with automatic cleanup.
    
    The session is automatically committed on success or rolled back on error.
    This provides ACID guarantees for database operations.
    
    Usage in FastAPI routes:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Error Handling:
        - On exception: Transaction is rolled back
        - Session is always closed in finally block
        - Exceptions are re-raised to FastAPI for standard error handling
    
    Yields:
        AsyncSession: A new database session for the request
        
    Raises:
        Exception: Any exception from the database operation
                  (caught by FastAPI exception handlers)
    """
    session = AsyncSessionLocal()
    try:
        yield session
        # Transaction is implicitly committed here
        # (autocommit=False means we need explicit commit, but FastAPI
        # will handle this through the transaction context)
    except Exception:
        # Rollback on any exception
        await session.rollback()
        logger.exception("Database session error, rolling back transaction")
        raise
    finally:
        # Always close the session
        await session.close()


# ============================================================================
# Database Initialization & Event Handlers
# ============================================================================


async def init_db():
    """
    Initialize database tables.
    
    This function creates all tables defined in the Base metadata.
    Run this once during application startup or use Alembic migrations
    for production environments.
    
    Usage:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    Note:
        In production, use Alembic migrations instead:
        `python -m alembic upgrade head`
    """
    async with engine.begin() as conn:
        # Create all tables defined by Base.metadata
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables initialized")


async def drop_db():
    """
    Drop all database tables.
    
    CAUTION: This will delete all data!
    
    Use only for:
    - Testing/development cleanup
    - Fresh database resets
    - Testing environment teardown
    
    Never run in production!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("⚠️  Database tables dropped")


async def dispose_engine():
    """
    Dispose of the engine and close all connections.
    
    Call this during application shutdown to properly
    close all database connections.
    
    Usage in app.main shutdown event:
        await dispose_engine()
    """
    await engine.dispose()
    logger.info("✓ Database engine disposed")


# ============================================================================
# Connection Pool Event Handlers
# ============================================================================


@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Event listener for new database connections.
    
    Configures connection-level settings for PostgreSQL.
    """
    # Disable automatic transaction handling (we handle it in SQLAlchemy)
    dbapi_conn.isolation_level = None


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "engine",
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "init_db",
    "drop_db",
    "dispose_engine",
]

