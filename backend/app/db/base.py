"""
SQLAlchemy database configuration and session management.

This module provides:
- Declarative base for all SQLAlchemy models
- Engine configuration using DATABASE_URL from environment
- SessionLocal factory for creating database sessions
- get_db() dependency function for FastAPI endpoints
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/dercas_db"
)

# SQLAlchemy declarative base for all models
Base = declarative_base()

# Determine engine configuration based on environment
# For development/testing, use QueuePool (default)
# For single-threaded testing, use NullPool
SQLALCHEMY_POOL_CLASS = os.getenv("SQLALCHEMY_POOL_CLASS", "QueuePool")

# Create database engine with appropriate configuration
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,  # SQLite doesn't support connection pooling well
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        # Connection pooling configuration
        pool_size=10,  # Number of connections to maintain
        max_overflow=20,  # Max overflow connections
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Test connections before using them
        # Performance optimizations
        echo=False,  # Set to True for SQL logging
        echo_pool=False,  # Set to True for pool logging
        # Connection timeout
        connect_args={
            "connect_timeout": 10,
        }
    )


# Add event listeners for connection management
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Configure connection upon creation.
    
    Sets up:
    - Foreign key constraints (PostgreSQL)
    - Isolation level settings
    """
    if not DATABASE_URL.startswith("sqlite"):
        # Enable foreign key constraints for PostgreSQL
        cursor = dbapi_conn.cursor()
        cursor.execute("SET session_replication_role = 'origin'")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI endpoints.
    
    Provides a database session for each request and ensures proper cleanup.
    
    Usage in FastAPI:
    ```python
    @app.get("/items/")
    def read_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    ```
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    
    This function should be called during application startup.
    In production, use Alembic migrations instead.
    
    Usage:
    ```python
    from backend.app.db.base import init_db
    
    @app.on_event("startup")
    def startup():
        init_db()
    ```
    """
    # Import all models to ensure they're registered with Base
    # This prevents SQLAlchemy from missing any models
    try:
        from backend.app.models.ot import OrdenTrabajo
        from backend.app.models.cuadrilla import Cuadrilla
        from backend.app.models.log_agente import LogAgente
        from backend.app.models.asignacion import Asignacion
    except ImportError:
        # Models may not be available yet during initial setup
        pass
    
    # Create all tables
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all tables from the database.
    
    WARNING: This will delete all data!
    
    Usage:
    ```python
    from backend.app.db.base import drop_db
    
    drop_db()  # Caution: Irreversible!
    ```
    """
    Base.metadata.drop_all(bind=engine)


def get_engine():
    """
    Get the SQLAlchemy engine instance.
    
    Useful for advanced operations and raw SQL execution.
    
    Returns:
        sqlalchemy.engine.Engine: The database engine
    """
    return engine


def close_db():
    """
    Close all database connections.
    
    This function should be called during application shutdown.
    
    Usage:
    ```python
    from backend.app.db.base import close_db
    
    @app.on_event("shutdown")
    def shutdown():
        close_db()
    ```
    """
    engine.dispose()


# Database connection status check
def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Useful for health checks and startup verification.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            # Simple query to verify connection
            if DATABASE_URL.startswith("sqlite"):
                connection.execute("SELECT 1")
            else:
                connection.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

