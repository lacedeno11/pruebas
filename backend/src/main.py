"""
FastAPI application entry point for PEI Agent Platform.

This module initializes the FastAPI application with:
- CORS middleware for frontend integration
- All API route routers
- Database initialization and lifecycle management
- Scheduler initialization for background jobs
- Health check endpoints
- Configuration endpoint for frontend
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import agent_endpoints, cuadrillas_endpoints, dashboard_endpoints, ots_endpoints
from src.config.settings import settings
from src.database import close_db, init_db
from src.scheduler import init_scheduler, shutdown_scheduler

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown events.

    Startup:
    - Initialize database and create tables
    - Initialize APScheduler for background jobs

    Shutdown:
    - Shutdown scheduler gracefully
    - Close database connections
    """
    # Startup
    logger.info("=== PEI Agent Platform Starting ===")
    logger.info(f"System Mode: {settings.system_mode}")
    logger.info(f"Database: {settings.database_url}")

    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")

        # Initialize scheduler
        logger.info("Initializing scheduler...")
        init_scheduler()
        logger.info("Scheduler initialized successfully")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("=== PEI Agent Platform Shutting Down ===")

    try:
        # Shutdown scheduler
        logger.info("Shutting down scheduler...")
        await shutdown_scheduler()

        # Close database
        logger.info("Closing database connections...")
        await close_db()

        logger.info("Shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="PEI Agent Platform",
    description="Plataforma de Ejecución de Instalaciones - AI-agentic work order management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend dev port
        "http://localhost:5173",  # Vite dev port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured for frontend integration")


# Include API routers
app.include_router(ots_endpoints.router)
app.include_router(cuadrillas_endpoints.router)
app.include_router(agent_endpoints.router)
app.include_router(dashboard_endpoints.router)

logger.info("API routers registered:")
logger.info("  - /api/ots (OT management)")
logger.info("  - /api/cuadrillas (Cuadrilla management)")
logger.info("  - /api/agents (Agent operations & WebSocket chat)")
logger.info("  - /api/dashboard (Analytics & visualization)")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Health status and system mode
    """
    return {
        "status": "ok",
        "mode": settings.system_mode,
        "service": "pei-agent-platform",
    }


# Configuration endpoint for frontend
@app.get("/api/config", tags=["Configuration"])
async def get_config():
    """
    Get system configuration for frontend initialization.

    This endpoint provides frontend with:
    - Map center coordinates and zoom level
    - Available project types
    - OT statuses for UI rendering
    - System mode for feature flags

    Returns:
        dict: Frontend configuration
    """
    return {
        "system_mode": settings.system_mode,
        "is_mock_mode": settings.is_mock_mode,
        "map": {
            "center": {"latitude": -1.8312, "longitude": -78.1834},
            "zoom": 7,
            "bounds": {
                "north": 2.0,
                "south": -5.0,
                "east": -75.0,
                "west": -81.0,
            },
        },
        "project_types": ["PUBLICO", "PRIVADO", "TERCERIZADO"],
        "ot_statuses": [
            "PREPLANIFICADA",
            "PLANIFICADA",
            "ASIGNADO_TAREA",
            "DETENIDA",
            "ANULADA",
            "FINALIZADA",
        ],
        "cuadrilla_types": ["PRINCIPAL", "RESERVA"],
        "features": {
            "kanban_view": True,
            "map_view": True,
            "agent_chat": True,
            "drag_drop_planning": True,
            "governance_alerts": True,
        },
        "api_version": "1.0.0",
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing API information.

    Returns:
        dict: API information and available endpoints
    """
    return {
        "name": "PEI Agent Platform API",
        "version": "1.0.0",
        "description": "AI-agentic platform for work order (OT) management",
        "mode": settings.system_mode,
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "config": "/api/config",
            "ots": "/api/ots",
            "cuadrillas": "/api/cuadrillas",
            "agents": "/api/agents",
            "dashboard": "/api/dashboard",
        },
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.is_mock_mode else "An error occurred",
    }


if __name__ == "__main__":
    import uvicorn

    # Run development server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_mock_mode,
        log_level="info",
    )

