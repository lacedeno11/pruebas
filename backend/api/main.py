"""
FastAPI main application setup.
Includes CORS middleware, all API routes, startup/shutdown events, health check, and APScheduler for cron jobs.
"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings
from backend.config.database import init_db, close_db, engine
from backend.models import Base

# Import routers (create stubs for now)
# from backend.api.routes import api_router

logger = logging.getLogger(__name__)
settings = Settings()

# Initialize APScheduler
scheduler = BackgroundScheduler()


def setup_scheduler():
    """Setup APScheduler for governance agent cron jobs."""
    try:
        # Job to check inactive OTs every hour
        scheduler.add_job(
            func="backend.agents.gobernanza_agent.check_inactive_ots_job",
            trigger="interval",
            hours=1,
            id="check_inactive_ots",
            name="Check inactive OTs",
            replace_existing=True,
        )

        # Job to check PREPLANIFICADA timeout every 6 hours
        scheduler.add_job(
            func="backend.agents.gobernanza_agent.check_preplanificada_timeout_job",
            trigger="interval",
            hours=6,
            id="check_preplanificada_timeout",
            name="Check PREPLANIFICADA timeout",
            replace_existing=True,
        )

        # Job for night normalization at 00:00
        scheduler.add_job(
            func="backend.agents.planificacion_agent.night_normalization_job",
            trigger="cron",
            hour=0,
            minute=0,
            id="night_normalization",
            name="Night normalization",
            replace_existing=True,
        )

        if not scheduler.running:
            scheduler.start()
        logger.info("APScheduler initialized with governance and planning jobs")

    except Exception as e:
        logger.error(f"Failed to setup APScheduler: {str(e)}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    try:
        await init_db()
        # Create database tables using SQLAlchemy
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized and tables created")

        # Setup APScheduler for governance agent cron jobs
        setup_scheduler()

        logger.info("PEI Platform API started successfully")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}", exc_info=True)
        raise

    yield

    # Shutdown
    try:
        if scheduler.running:
            scheduler.shutdown()
        await close_db()
        logger.info("PEI Platform API shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="PEI Platform API",
    version="1.0.0",
    description="DERCAS TO-BE AGÉNTICO - AI-Powered Work Order Management System",
    lifespan=lifespan,
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint returning system status."""
    return {
        "status": "healthy",
        "mode": settings.system_mode,
        "version": "1.0.0",
    }


# API health check endpoint
@app.get("/api/health", tags=["Health"])
async def api_health():
    """API health check with detailed status."""
    return {
        "status": "operational",
        "system_mode": settings.system_mode,
        "database": "configured",
        "agents": "initialized",
        "scheduler": "running" if scheduler.running else "stopped",
    }


# Include API routers (uncomment when routes are fully implemented)
# app.include_router(api_router, prefix="/api")


