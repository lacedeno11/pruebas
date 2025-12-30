# DERCAS-ONCO-XAI V1 - Case Service Database
# Database configuration and session management

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import structlog

from .config import Settings, get_settings
from .models import Base

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Database manager for async SQLAlchemy operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Create async engine
        self.engine = create_async_engine(
            settings.get_async_database_url(),
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            poolclass=NullPool if settings.environment == "test" else None,
        )
        
        # Create session factory
        self.async_session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        
        logger.info("Database manager initialized", database_url=settings.get_async_database_url())
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.async_session_factory()
    
    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager
_db_manager: DatabaseManager = None


def get_database_manager(settings: Settings = None) -> DatabaseManager:
    """Get database manager instance."""
    global _db_manager
    if _db_manager is None:
        if settings is None:
            settings = get_settings()
        _db_manager = DatabaseManager(settings)
    return _db_manager


async def get_db_session(settings: Settings = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    db_manager = get_database_manager(settings)
    async with db_manager.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database(settings: Settings = None) -> None:
    """Initialize database on startup."""
    if settings is None:
        settings = get_settings()
    
    db_manager = get_database_manager(settings)
    
    # Create tables if they don't exist
    if settings.environment in ["development", "test"]:
        await db_manager.create_tables()
    
    logger.info("Database initialized")


async def cleanup_database() -> None:
    """Cleanup database on shutdown."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
    logger.info("Database cleanup completed")
