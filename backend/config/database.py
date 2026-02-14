"""
Database configuration and connection setup.
Creates engine, session factory, and provides FastAPI dependency for database access.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.config import Settings
from backend.models import Base

# Get settings
settings = Settings()

# Create async engine (using asyncio-compatible database URL)
# For SQLite with async support, use aiosqlite
if "sqlite" in settings.database_url.lower():
    # Convert sqlite:// to sqlite+aiosqlite://
    async_database_url = settings.database_url.replace(
        "sqlite:///", "sqlite+aiosqlite:///"
    )
else:
    # For PostgreSQL: convert postgresql:// to postgresql+asyncpg://
    async_database_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

engine = create_async_engine(
    async_database_url,
    echo=settings.log_level.upper() == "DEBUG",
    future=True,
)

# Session factory for async sessions
SessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    Dependency function for FastAPI routes to get database session.
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()

