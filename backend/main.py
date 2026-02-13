"""
DERCAS PEI - FastAPI Application Entry Point
Main application file that sets up the FastAPI server with all routes and middleware.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import database initialization
from backend.database import init_db

# Import routers
from backend.api.routes import ots, cuadrillas, planning, governance, notifications, mock, agents

# Import Orchestrator (placeholder for now, will be fully implemented with agents)
# from backend.agents.orchestrator import Orchestrator

# Get system configuration
SYSTEM_MODE = os.getenv("SYSTEM_MODE", "MOCK")
API_VERSION = "1.0.0"


# ============================================================================
# Startup and Shutdown Events
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle: startup and shutdown events.
    
    Startup:
    - Initialize database tables
    - Seed initial data (cuadrillas)
    - Initialize Orchestrator singleton
    - Schedule governance jobs
    
    Shutdown:
    - Clean up resources
    """
    # Startup
    logger.info("=" * 80)
    logger.info("DERCAS PEI - FastAPI Application Starting")
    logger.info("=" * 80)
    logger.info(f"System Mode: {SYSTEM_MODE}")
    logger.info(f"API Version: {API_VERSION}")

    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db.create_tables()
        logger.info("✅ Database tables created")

        # Seed cuadrillas
        logger.info("Seeding cuadrillas...")
        init_db.seed_cuadrillas()
        logger.info("✅ Cuadrillas seeded")

        # Initialize Orchestrator for agent coordination
        # Note: Orchestrator will be initialized when agents are implemented
        # logger.info("Initializing Agent Orchestrator...")
        # try:
        #     from backend.agents.orchestrator import Orchestrator
        #     orchestrator = Orchestrator()
        #     orchestrator.schedule_governance_jobs()
        #     logger.info("✅ Agent Orchestrator initialized")
        #     logger.info("  - Scheduled: Centroid recalculation at 00:00 (Phase 3)")
        #     logger.info("  - Scheduled: Inactivity checks at 09:00 (GobernanzaAgent)")
        #     app.state.orchestrator = orchestrator
        # except ImportError:
        #     logger.warning("⚠️  Agent Orchestrator not yet implemented")
        # except Exception as e:
        #     logger.error(f"⚠️  Failed to initialize Orchestrator: {e}")

        logger.info("=" * 80)
        logger.info("✅ DERCAS PEI Ready - All systems operational")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("DERCAS PEI - Shutting down...")
    logger.info("✅ Cleanup completed")


# ============================================================================
# FastAPI Application Setup
# ============================================================================


app = FastAPI(
    title="DERCAS PEI API",
    version=API_VERSION,
    description="Agential Platform for Work Order Management - TELCONET",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# CORS Middleware Configuration
# ============================================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Routes Registration
# ============================================================================

app.include_router(ots.router)
app.include_router(cuadrillas.router)
app.include_router(planning.router)
app.include_router(governance.router)
app.include_router(notifications.router)
app.include_router(mock.router)
app.include_router(agents.router)


# ============================================================================
# Root Endpoints
# ============================================================================


@app.get("/")
async def root():
    """
    Root endpoint providing API information and health status.
    
    Returns:
        API metadata and current health status
    """
    return {
        "name": "DERCAS PEI API",
        "version": API_VERSION,
        "description": "Agential Platform for Work Order Management",
        "status": "operational",
        "system_mode": SYSTEM_MODE,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "ots": "/api/ots",
            "cuadrillas": "/api/cuadrillas",
            "planning": "/api/planning",
            "governance": "/api/governance",
            "notifications": "/api/notifications",
            "mock": "/api/mock" if SYSTEM_MODE == "MOCK" else None,
            "agents": "/api/agents",
        },
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Health status and system information
    """
    return {
        "status": "healthy",
        "mode": SYSTEM_MODE,
        "version": API_VERSION,
        "service": "DERCAS PEI API",
    }


@app.get("/config")
async def get_config():
    """
    Get system configuration (public information only).
    
    Returns:
        System mode and API version
    """
    return {
        "system_mode": SYSTEM_MODE,
        "api_version": API_VERSION,
        "is_mock": SYSTEM_MODE == "MOCK",
    }


# ============================================================================
# Application Entry Point
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    # Run the FastAPI application
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=SYSTEM_MODE == "MOCK",  # Enable reload in MOCK mode for development
        log_level="info",
    )




