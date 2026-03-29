"""
DERCAS PEI Backend - Main FastAPI Application Entry Point

This module initializes the FastAPI application with:
- CORS middleware for frontend communication
- API router aggregation
- Database session management
- Error handling with custom exception handlers
- Startup/shutdown event handlers for lifecycle management
- Root health check endpoint

Environment Variables (from app.core.config):
- SYSTEM_MODE: 'MOCK' for development, 'PRODUCTION' for live APIs
- DATABASE_URL: PostgreSQL connection string
- FRONTEND_URL: Frontend application URL (for CORS)
- PROJECT_NAME: Application display name (default: 'DERCAS PEI')
- API_V1_STR: API version prefix (default: '/api/v1')

Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import settings
from app.cron_jobs import setup_scheduler, scheduler as cron_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.

    Startup:
    1. Log system information and configuration
    2. Initialize and start the APScheduler cron job scheduler
    3. Register scheduled tasks (inactivity check, detention warnings, route optimization)
    4. Enable automated governance and planning operations

    Shutdown:
    1. Gracefully stop the APScheduler scheduler
    2. Log shutdown message
    """
    # Startup event
    logger.info("=" * 80)
    logger.info("🚀 Starting DERCAS PEI Backend")
    logger.info("=" * 80)
    logger.info(f"System Mode: {settings.SYSTEM_MODE}")
    logger.info(f"Project Name: {settings.PROJECT_NAME}")
    logger.info(f"Frontend URL: {settings.FRONTEND_URL}")
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info("=" * 80)

    # Initialize and start cron job scheduler
    try:
        logger.info("📅 Initializing Cron Job Scheduler...")
        scheduler = setup_scheduler()
        scheduler.start()
        logger.info("=" * 80)
        logger.info("✓ Cron Jobs Initialized and Started")
        logger.info("  • Inactivity Check: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)")
        logger.info("  • Detention Warnings: Daily at 08:00 UTC")
        logger.info("  • Route Optimization: Daily at 00:00 UTC")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(
            f"❌ Failed to start scheduler: {type(e).__name__}: {str(e)}",
            exc_info=True,
        )
        raise

    yield

    # Shutdown event
    try:
        logger.info("=" * 80)
        logger.info("🛑 Shutting down DERCAS PEI Backend")
        logger.info("=" * 80)

        # Stop the scheduler
        if cron_scheduler and cron_scheduler.running:
            logger.info("⏹️  Stopping Cron Job Scheduler...")
            cron_scheduler.shutdown()
            logger.info("✓ Cron Job Scheduler stopped")

        logger.info("✓ Backend shutdown completed")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(
            f"❌ Error during shutdown: {type(e).__name__}: {str(e)}",
            exc_info=True,
        )


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agentic Platform for Telco Work Order Management",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint for health check and API information.

    Returns basic information about the API including system mode
    and documentation links.

    Returns:
        Dict with message, mode, and documentation URL
    """
    return {
        "message": "DERCAS PEI API - Agentic Telco Work Order Management",
        "mode": settings.SYSTEM_MODE,
        "docs": f"{settings.API_V1_STR}/docs",
        "redoc": f"{settings.API_V1_STR}/redoc",
        "openapi": f"{settings.API_V1_STR}/openapi.json",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        Dict with status and system mode
    """
    return {
        "status": "ok",
        "mode": settings.SYSTEM_MODE,
    }


# ============================================================================
# Exception Handlers
# ============================================================================


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    """
    Handle 404 Not Found errors.

    Returns:
        JSON response with error details and status 404
    """
    logger.warning(f"404 Not Found: {request.url.path}")
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested endpoint '{request.url.path}' does not exist",
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors.

    Returns:
        JSON response with validation error details and status 422
    """
    logger.warning(f"Validation error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "path": request.url.path,
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general unhandled exceptions.

    Logs the exception and returns a generic error response.

    Returns:
        JSON response with error message and status 500
    """
    logger.error(
        f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please contact support.",
            "path": request.url.path,
        },
    )


# ============================================================================
# Middleware Logging
# ============================================================================


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming HTTP requests and responses.

    Logs request method, path, and response status code.
    """
    method = request.method
    path = request.url.path

    logger.debug(f"→ {method} {path}")

    response = await call_next(request)

    status_code = response.status_code
    status_emoji = "✓" if 200 <= status_code < 300 else "⚠" if 300 <= status_code < 400 else "✗"

    logger.debug(f"{status_emoji} {method} {path} [{status_code}]")

    return response


# ============================================================================
# Application Information
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Run with: python -m app.main
    # Or: python app/main.py
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )



