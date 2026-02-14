"""
PEI Agentic Platform - FastAPI Application Entry Point

Main application initialization with:
- FastAPI app setup with OpenAPI documentation
- Router registration (mock, future: ots, cuadrillas, planning, agents, dashboard)
- CORS middleware for frontend communication
- Custom exception handlers for error responses
- Scheduler lifecycle management (startup/shutdown)
- Request logging and correlation ID injection
- Root endpoint and health checks
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import get_logger, set_correlation_id, clear_correlation_id
from app.mock.router import router as mock_router
from app.services.scheduler import (
    get_scheduler_status,
    shutdown_scheduler,
    start_scheduler,
)
from app.utils.exceptions import PEIException, pei_exception_handler

# ============================================================================
# LOGGER SETUP
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI application lifespan context manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database and start scheduler
    - Shutdown: Stop scheduler gracefully
    
    This replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    # Startup
    try:
        settings = get_settings()
        
        logger.info(
            "Starting PEI Agentic Platform",
            extra={
                "version": "1.0.0",
                "system_mode": settings.SYSTEM_MODE,
            },
        )
        
        # Initialize database (run migrations if needed)
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")
        
        # Start background scheduler
        logger.info("Starting background scheduler...")
        await start_scheduler()
        logger.info("Background scheduler started successfully")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(
            f"Failed to start application: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        raise
    
    yield  # Application runs here
    
    # Shutdown
    try:
        logger.info("Shutting down PEI Agentic Platform...")
        
        # Stop background scheduler
        logger.info("Stopping background scheduler...")
        await shutdown_scheduler()
        logger.info("Background scheduler stopped successfully")
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(
            f"Error during application shutdown: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
        )


# ============================================================================
# FASTAPI APPLICATION FACTORY
# ============================================================================


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application instance.
    
    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="PEI Agentic Platform",
        version="1.0.0",
        description="AI-powered order planning and governance platform for TELCONET",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    
    return app


app = create_app()

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)


# Request Correlation ID Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Middleware to inject correlation ID for request tracing.
    
    Extracts correlation ID from header if present, generates new one if not.
    Injects correlation ID into context for logging.
    Adds correlation ID to response headers for client-side tracing.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        
    Returns:
        Response: Response with correlation ID in headers
    """
    # Get correlation ID from request header or generate new one
    correlation_id = request.headers.get(
        "X-Correlation-ID",
        str(uuid.uuid4()),
    )
    
    # Set correlation ID in context for logging
    set_correlation_id(correlation_id)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
        
    finally:
        # Clean up correlation ID context
        clear_correlation_id()


# Request Logging Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Middleware to log incoming requests and outgoing responses.
    
    Logs HTTP method, path, status code, and response time.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        
    Returns:
        Response: Response from handler
    """
    import time
    
    start_time = time.time()
    
    # Log incoming request
    logger.debug(
        f"{request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
        },
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    
    # Log outgoing response
    logger.debug(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        },
    )
    
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

# Custom exception handler for PEIException
app.add_exception_handler(PEIException, pei_exception_handler)


# Generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Generic exception handler for uncaught exceptions.
    
    Logs exception and returns 500 Internal Server Error response.
    
    Args:
        request: FastAPI request
        exc: Exception instance
        
    Returns:
        JSONResponse: Error response with status 500
    """
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
        },
    )


# ============================================================================
# ROUTER REGISTRATION
# ============================================================================

# Mock API router (development/testing)
app.include_router(mock_router)

# Future routers to be included:
# - app.api.ots (Task 24)
# - app.api.cuadrillas (Task 25)
# - app.api.planning (Task 26)
# - app.api.agents (Task 27)
# - app.api.dashboard (Task 28)

# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get(
    "/",
    tags=["Health & Info"],
    summary="API root endpoint",
    description="Returns basic API information and health status",
)
async def root():
    """
    Root endpoint - API information and health status.
    
    Returns basic information about the API and current status.
    Useful for monitoring and debugging.
    
    **Response Example:**
    ```json
    {
        "name": "PEI Agentic Platform",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": "2024-02-13T16:45:30.654321",
        "system_mode": "MOCK",
        "database_status": "connected",
        "scheduler_status": "running"
    }
    ```
    """
    settings = get_settings()
    scheduler = get_scheduler_status()
    
    return {
        "name": "PEI Agentic Platform",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system_mode": settings.SYSTEM_MODE,
        "database_status": "connected",
        "scheduler_status": "running" if scheduler["scheduler_running"] else "stopped",
        "documentation": "/api/docs",
        "openapi_schema": "/api/openapi.json",
    }


@app.get(
    "/health",
    tags=["Health & Info"],
    summary="Health check endpoint",
    description="Simple health check for monitoring services",
)
async def health_check():
    """
    Health check endpoint - returns 200 if application is running.
    
    Used by load balancers and monitoring services to verify
    application health.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get(
    "/api/v1/scheduler/status",
    tags=["Scheduler"],
    summary="Get scheduler status",
    description="Returns current status of background scheduler and registered jobs",
)
async def scheduler_status():
    """
    Get background scheduler status and job information.
    
    Returns detailed information about the scheduler including:
    - Whether scheduler is running
    - Timezone configuration
    - List of registered jobs with next execution times
    - Job counts and status
    
    **Response Example:**
    ```json
    {
        "scheduler_running": true,
        "timezone": "America/Guayaquil",
        "job_count": 3,
        "jobs": [
            {
                "id": "nightly_normalization",
                "name": "Nightly Normalization",
                "next_run_time": "2024-02-14T00:00:00+00:00",
                "trigger": "cron[hour='0', minute='0']",
                "max_instances": 1
            },
            {
                "id": "inactivity_check",
                "name": "Inactivity Check",
                "next_run_time": "2024-02-13T17:00:00+00:00",
                "trigger": "cron[minute='0']",
                "max_instances": 1
            },
            {
                "id": "document_validation",
                "name": "Document Validation",
                "next_run_time": "2024-02-14T08:00:00+00:00",
                "trigger": "cron[hour='8', minute='0']",
                "max_instances": 1
            }
        ]
    }
    ```
    
    Returns:
        dict: Scheduler status with job information
    """
    return await get_scheduler_status()


# ============================================================================
# 404 HANDLER
# ============================================================================


@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def not_found(path_name: str):
    """
    Catch-all 404 handler for undefined routes.
    
    Args:
        path_name: Requested path
        
    Returns:
        JSONResponse: 404 error response
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Endpoint /{path_name} not found",
    )


# ============================================================================
# APPLICATION INFO
# ============================================================================

if __name__ == "__main__":
    """
    Run application with uvicorn.
    
    For development:
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
    
    For production:
        uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    
    Environment variables:
        SYSTEM_MODE: MOCK or PRODUCTION
        DATABASE_URL: Database connection string
        OPENAI_API_KEY: OpenAI API key for LLM
        JWT_SECRET: Secret key for JWT tokens
    """
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.SYSTEM_MODE == "MOCK",
        workers=1 if settings.SYSTEM_MODE == "MOCK" else 4,
    )

