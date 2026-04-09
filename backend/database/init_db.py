"""
Database initialization script for DERCAS PEI.
Creates tables and seeds initial data (cuadrillas).
"""

import logging
from datetime import datetime

from backend.database.base import Base, engine, SessionLocal
from backend.database.models import Cuadrilla, CuadrillaType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables() -> None:
    """Create all database tables from SQLAlchemy models."""
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise


def seed_cuadrillas() -> None:
    """Seed initial cuadrilla (crew) data."""
    logger.info("Seeding cuadrillas...")
    
    db = SessionLocal()
    try:
        # Check if cuadrillas already exist
        existing_count = db.query(Cuadrilla).count()
        if existing_count > 0:
            logger.info(f"✅ Cuadrillas already seeded ({existing_count} found)")
            return

        # Create 5 Principal cuadrillas
        for i in range(1, 6):
            cuadrilla = Cuadrilla(
                name=f"Cuadrilla Principal {i}",
                type=CuadrillaType.PRINCIPAL,
                capacity=10,
                current_load=0,
                created_at=datetime.now(),
            )
            db.add(cuadrilla)
            logger.info(f"  • Created {cuadrilla.name}")

        # Create 5 Reserva cuadrillas
        for i in range(1, 6):
            cuadrilla = Cuadrilla(
                name=f"Cuadrilla Reserva {i}",
                type=CuadrillaType.RESERVA,
                capacity=10,
                current_load=0,
                created_at=datetime.now(),
            )
            db.add(cuadrilla)
            logger.info(f"  • Created {cuadrilla.name}")

        # Commit all cuadrillas
        db.commit()
        logger.info("✅ Cuadrillas seeded successfully (10 total)")

    except Exception as e:
        logger.error(f"❌ Error seeding cuadrillas: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Main initialization function."""
    logger.info("=" * 60)
    logger.info("DERCAS PEI - Database Initialization")
    logger.info("=" * 60)
    
    try:
        create_tables()
        seed_cuadrillas()
        logger.info("=" * 60)
        logger.info("✅ Database initialization completed successfully!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Database initialization failed: {e}")
        logger.error("=" * 60)
        raise


if __name__ == "__main__":
    main()

