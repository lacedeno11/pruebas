"""
FastAPI application for DERCAS TO-BE AGÉNTICO system.

Initializes the FastAPI app with:
- CORS middleware for frontend integration
- Exception handlers for common errors
- Database initialization and migrations on startup
- Health check endpoint
- API routes aggregation
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database utilities
from backend.app.db.base import engine, SessionLocal, get_db

# Import scheduler (will be initialized in startup)
from backend.app.scheduler.scheduler import start_scheduler, stop_scheduler


# ============================================================================
# Application Lifecycle Events
# ============================================================================

async def lifespan(app: FastAPI):
    """
    Manage application lifecycle: startup and shutdown events.
    
    Startup:
    - Initialize database connection
    - Run pending Alembic migrations
    - Start background scheduler
    
    Shutdown:
    - Stop background scheduler
    - Close database connections
    """
    # ========== STARTUP ==========
    try:
        logger.info("Starting DERCAS TO-BE AGÉNTICO application...")
        
        # Initialize database and run migrations
        logger.info("Running database migrations...")
        _run_migrations()
        logger.info("Database migrations completed successfully")
        
        # Start background scheduler for periodic jobs
        logger.info("Starting background scheduler...")
        await start_scheduler()
        logger.info("Background scheduler started")
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}", exc_info=True)
        raise
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    try:
        logger.info("Shutting down DERCAS TO-BE AGÉNTICO application...")
        
        # Stop background scheduler
        logger.info("Stopping background scheduler...")
        await stop_scheduler()
        logger.info("Background scheduler stopped")
        
        # Close database engine
        logger.info("Closing database connections...")
        engine.dispose()
        logger.info("Database connections closed")
        
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during application shutdown: {str(e)}", exc_info=True)


def _run_migrations() -> None:
    """
    Run Alembic migrations programmatically.
    
    This ensures the database schema is up-to-date before the application starts.
    """
    from alembic.config import Config
    from alembic import command
    
    # Get the alembic.ini path (relative to backend directory)
    alembic_ini_path = os.path.join(os.path.dirname(__file__), '..', 'alembic.ini')
    
    if not os.path.exists(alembic_ini_path):
        logger.warning(f"alembic.ini not found at {alembic_ini_path}, skipping migrations")
        return
    
    try:
        alembic_cfg = Config(alembic_ini_path)
        # Ensure the sqlalchemy.url is set from environment
        alembic_cfg.set_main_option('sqlalchemy.url', os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/dercas'
        ))
        
        # Run migrations
        command.upgrade(alembic_cfg, 'head')
        logger.info("Migrations executed successfully")
    except Exception as e:
        logger.warning(f"Migration execution failed: {str(e)}. Application may not have a valid schema.")
        # Don't re-raise - allow app to start even if migrations fail
        # This helps with development and testing


# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title="DERCAS TO-BE AGÉNTICO",
    description="AI-powered work order management and planning system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# CORS Middleware
# ============================================================================

# Configure CORS to allow frontend requests
cors_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative frontend port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Add production origins if specified in environment
if os.getenv("FRONTEND_URL"):
    cors_origins.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Type"],
)

logger.info(f"CORS configured for origins: {cors_origins}")


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTPException and return JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error": {
                "status": exc.status_code,
                "type": "HTTPException",
            },
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc: SQLAlchemyError):
    """Handle SQLAlchemy errors and return 500 error."""
    logger.error(f"Database error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Database error occurred",
            "error": {
                "status": 500,
                "type": "DatabaseError",
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle any uncaught exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "error": {
                "status": 500,
                "type": type(exc).__name__,
            },
        },
    )


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint returning application status.
    
    Returns:
    - status: Application health status (ok, degraded, error)
    - timestamp: Current server timestamp
    - system_mode: Current operation mode (MOCK or PRODUCTION)
    - version: API version
    - database: Database connection status
    """
    system_mode = os.getenv("SYSTEM_MODE", "MOCK")
    db_status = "connected"
    
    # Try to get a database connection to verify database is accessible
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        logger.warning(f"Database health check failed: {str(e)}")
        db_status = f"error: {str(e)}"
    
    return {
        "success": True,
        "status": "ok" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "DERCAS TO-BE AGÉNTICO",
        "version": "1.0.0",
        "system_mode": system_mode,
        "database": db_status,
        "environment": {
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        },
    }


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root endpoint providing API information."""
    return {
        "message": "DERCAS TO-BE AGÉNTICO API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
    }


# ============================================================================
# Include API Routers
# ============================================================================

def include_routers():
    """
    Include all API routers.
    
    This is separated into a function to allow for lazy loading of routers
    and to keep main.py clean.
    """
    # Import the router aggregation function
    # Note: This will be created in task 79 (api/routes/__init__.py)
    try:
        from backend.app.api.routes import include_routers as _include_routers
        logger.info("Including API routers...")
        _include_routers(app)
        logger.info("API routers included successfully")
    except ImportError as e:
        logger.warning(f"Could not import routers: {str(e)}. API endpoints will not be available.")
    except Exception as e:
        logger.error(f"Error including routers: {str(e)}", exc_info=True)
        raise


# Include routers when app starts
include_routers()


# ============================================================================
# Startup and Shutdown Helpers (Fallback)
# ============================================================================

# These are fallback event handlers in case the lifespan context manager
# doesn't work as expected (for older versions of FastAPI)

@app.on_event("startup")
async def startup_event():
    """Fallback startup event handler."""
    logger.info("Running startup event handlers...")


@app.on_event("shutdown")
async def shutdown_event():
    """Fallback shutdown event handler."""
    logger.info("Running shutdown event handlers...")
    engine.dispose()


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))
    
    logger.info(f"Starting DERCAS TO-BE AGÉNTICO server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Workers: {workers}")
    
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=debug,
        workers=workers,
        log_level="info",
    )

