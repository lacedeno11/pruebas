"""Database connection and session management for PEI Agéntico."""

from sqlalchemy import create_engine, Index
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base, OT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment or use SQLite default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pei.db")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """
    Dependency function for FastAPI to get database session.
    
    Yields:
        Session: Database session for the request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    
    Also creates indexes on frequently queried columns.
    """
    # Create all tables from Base metadata
    Base.metadata.create_all(bind=engine)
    
    # Create specific indexes for performance optimization
    # Index on external_id for fast OT lookups
    try:
        Index('idx_ot_external_id', OT.external_id).create(engine, checkfirst=True)
    except Exception:
        pass  # Index might already exist
    
    # Index on status for status-based filtering
    try:
        Index('idx_ot_status', OT.status).create(engine, checkfirst=True)
    except Exception:
        pass
    
    # Index on cuadrilla_id for crew-based filtering
    try:
        Index('idx_ot_cuadrilla_id', OT.cuadrilla_id).create(engine, checkfirst=True)
    except Exception:
        pass
    
    # Index on created_at for time-based filtering (48h, 30-day rules)
    try:
        Index('idx_ot_created_at', OT.created_at).create(engine, checkfirst=True)
    except Exception:
        pass
    
    # Composite index for common filtering patterns
    try:
        Index('idx_ot_status_cuadrilla', OT.status, OT.cuadrilla_id).create(engine, checkfirst=True)
    except Exception:
        pass
    
    print("Database initialized successfully")

