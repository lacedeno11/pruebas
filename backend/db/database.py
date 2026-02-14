"""
Database configuration and setup for PEI Platform using SQLAlchemy.
Provides engine, session factory, and database utilities for ORM operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from backend.config import get_settings

# Get configuration settings
settings = get_settings()

# Create database engine
# For SQLite (development), use StaticPool to avoid threading issues
# For PostgreSQL (production), use default connection pooling
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL or other database
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before use
        echo=False,  # Set to True for SQL query logging
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Create declarative base for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to provide database sessions.
    
    Creates a new database session for each request and ensures it's
    properly closed after the request completes.
    
    Usage in FastAPI routes:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        SQLAlchemy Session for database operations
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """
    Create all database tables based on defined models.
    
    This function creates database tables for all models that inherit
    from Base. Should be called during application startup to ensure
    the database schema is initialized.
    
    This is idempotent - calling it multiple times is safe as SQLAlchemy
    won't recreate tables that already exist.
    
    Usage:
        >>> from backend.db.database import create_all_tables
        >>> create_all_tables()
        
    Note:
        For production, consider using Alembic for database migrations
        instead of calling this function directly.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified successfully")


def drop_all_tables():
    """
    Drop all database tables.
    
    WARNING: This is a destructive operation and should only be used
    in development/testing environments. It will delete all tables
    and their data.
    
    Usage:
        >>> from backend.db.database import drop_all_tables
        >>> drop_all_tables()  # Only use in development!
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All database tables dropped successfully")


def reset_database():
    """
    Reset the entire database by dropping all tables and recreating them.
    
    WARNING: This is a destructive operation that deletes all data.
    Only use in development/testing environments.
    
    Usage:
        >>> from backend.db.database import reset_database
        >>> reset_database()  # Only use in development!
    """
    drop_all_tables()
    create_all_tables()
    print("✅ Database reset successfully")

