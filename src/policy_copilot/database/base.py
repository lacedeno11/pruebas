"""
Database Base Configuration

This module provides the base database configuration, connection management,
and common utilities for the Policy Validation Copilot system.
"""

from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any
import logging
import os
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# SQLAlchemy declarative base
Base = declarative_base()

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=convention)


class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.echo = self._get_echo_setting()
        self.pool_size = self._get_pool_size()
        self.max_overflow = self._get_max_overflow()
        self.pool_timeout = self._get_pool_timeout()
        self.pool_recycle = self._get_pool_recycle()
    
    def _get_database_url(self) -> str:
        """Get database URL from environment"""
        return os.getenv(
            "DATABASE_URL",
            "postgresql://policy_user:policy_pass@localhost:5432/policy_copilot"
        )
    
    def _get_echo_setting(self) -> bool:
        """Get SQL echo setting from environment"""
        return os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    def _get_pool_size(self) -> int:
        """Get connection pool size"""
        return int(os.getenv("DATABASE_POOL_SIZE", "10"))
    
    def _get_max_overflow(self) -> int:
        """Get max overflow connections"""
        return int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    
    def _get_pool_timeout(self) -> int:
        """Get pool timeout in seconds"""
        return int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    
    def _get_pool_recycle(self) -> int:
        """Get pool recycle time in seconds"""
        return int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine"""
        engine_kwargs = {
            "echo": self.config.echo,
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "pool_timeout": self.config.pool_timeout,
            "pool_recycle": self.config.pool_recycle,
        }
        
        # Handle SQLite for testing
        if self.config.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False}
            })
            # Remove PostgreSQL-specific settings
            engine_kwargs.pop("pool_size", None)
            engine_kwargs.pop("max_overflow", None)
            engine_kwargs.pop("pool_timeout", None)
            engine_kwargs.pop("pool_recycle", None)
        
        self.engine = create_engine(self.config.database_url, **engine_kwargs)
        
        # Add connection event listeners
        self._add_event_listeners()
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database engine initialized: {self.config.database_url}")
    
    def _add_event_listeners(self):
        """Add SQLAlchemy event listeners"""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and integrity"""
            if self.config.database_url.startswith("sqlite"):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=1000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
        
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries"""
            context._query_start_time = datetime.utcnow()
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time"""
            total = (datetime.utcnow() - context._query_start_time).total_seconds()
            if total > 1.0:  # Log queries taking more than 1 second
                logger.warning(f"Slow query detected: {total:.2f}s - {statement[:100]}...")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_all_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("All database tables created")
    
    def drop_all_tables(self):
        """Drop all database tables"""
        Base.metadata.drop_all(bind=self.engine)
        logger.info("All database tables dropped")
    
    def get_engine(self):
        """Get SQLAlchemy engine"""
        return self.engine
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.get_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1")
                
                return {
                    "status": "healthy",
                    "database_url": self.config.database_url.split("@")[-1],  # Hide credentials
                    "pool_size": self.config.pool_size,
                    "checked_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency function for FastAPI to get database session"""
    with db_manager.get_session() as session:
        yield session


def init_database(config: DatabaseConfig = None) -> DatabaseManager:
    """Initialize database with custom configuration"""
    global db_manager
    db_manager = DatabaseManager(config)
    return db_manager


class TimestampMixin:
    """Mixin for adding timestamp fields to models"""
    
    created_at = None  # Will be defined in actual models
    updated_at = None  # Will be defined in actual models
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Add timestamp columns to subclasses
        from sqlalchemy import Column, DateTime
        from sqlalchemy.sql import func
        
        if not hasattr(cls, 'created_at') or cls.created_at is None:
            cls.created_at = Column(
                DateTime(timezone=True),
                server_default=func.now(),
                nullable=False,
                comment="Record creation timestamp"
            )
        
        if not hasattr(cls, 'updated_at') or cls.updated_at is None:
            cls.updated_at = Column(
                DateTime(timezone=True),
                server_default=func.now(),
                onupdate=func.now(),
                nullable=False,
                comment="Record last update timestamp"
            )


class UUIDMixin:
    """Mixin for adding UUID primary key to models"""
    
    id = None  # Will be defined in actual models
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Add UUID primary key to subclasses
        from sqlalchemy import Column, String
        from sqlalchemy.dialects.postgresql import UUID
        import uuid
        
        if not hasattr(cls, 'id') or cls.id is None:
            # Use String for SQLite compatibility, UUID for PostgreSQL
            cls.id = Column(
                String(36),  # UUID string length
                primary_key=True,
                default=lambda: str(uuid.uuid4()),
                nullable=False,
                comment="Unique identifier"
            )


class AuditMixin:
    """Mixin for adding audit fields to models"""
    
    created_by = None
    updated_by = None
    version = None
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        from sqlalchemy import Column, String, Integer
        
        if not hasattr(cls, 'created_by') or cls.created_by is None:
            cls.created_by = Column(
                String(255),
                nullable=True,
                comment="User who created the record"
            )
        
        if not hasattr(cls, 'updated_by') or cls.updated_by is None:
            cls.updated_by = Column(
                String(255),
                nullable=True,
                comment="User who last updated the record"
            )
        
        if not hasattr(cls, 'version') or cls.version is None:
            cls.version = Column(
                Integer,
                default=1,
                nullable=False,
                comment="Record version for optimistic locking"
            )


def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(uuid.uuid4())


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.utcnow()


# Database session dependency for dependency injection
def get_database_session():
    """Get database session for dependency injection"""
    return get_db_session()
