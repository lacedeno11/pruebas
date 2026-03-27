"""Database Session Management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings

# Create database engine with settings
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # Set to True for SQL query logging in development
)

# Create SessionLocal factory for creating new database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """
    Get a database session for dependency injection in FastAPI routes.

    This generator function creates a new database session for each request,
    and ensures it's properly closed after the request is complete.

    Yields:
        SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

