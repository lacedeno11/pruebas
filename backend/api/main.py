"""
PEI Platform FastAPI application entry point.
Configures the main FastAPI app with middleware, routes, startup/shutdown events,
and health check endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.api.routes import all_routers
from backend.db.database import create_all_tables
from backend.services.scheduler import start_scheduler, stop_scheduler
from backend.config import get_settings


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    
    Startup:
        - Initialize database schema (create_all_tables)
        - Start the APScheduler for scheduled jobs
    
    Shutdown:
        - Stop the APScheduler gracefully
    """
    # Startup event
    print("🚀 Starting PEI Platform API...")
    try:
        create_all_tables()
        print("✅ Database schema initialized")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise

    try:
        start_scheduler()
        print("✅ Scheduler started")
    except Exception as e:
        print(f"⚠️ Warning: Scheduler failed to start: {e}")
        # Don't raise here - app should still work without scheduler

    yield

    # Shutdown event
    print("🛑 Shutting down PEI Platform API...")
    try:
        stop_scheduler()
        print("✅ Scheduler stopped")
    except Exception as e:
        print(f"⚠️ Warning: Scheduler failed to stop cleanly: {e}")


# Create FastAPI application instance
app = FastAPI(
    title="PEI Platform API",
    version="1.0.0",
    description="Agentic orchestration platform for work order management (OT) assignment and execution",
    lifespan=lifespan,
)


# Configure CORS middleware for development
# Allows all origins, credentials, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all API routers
for router in all_routers:
    app.include_router(router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """
    Health check endpoint for monitoring API availability.

    Returns:
        Dictionary with status information:
        - status: "healthy" or "unhealthy"
        - service: Service name
        - version: API version
        - system_mode: MOCK or PRODUCTION mode
    """
    try:
        settings = get_settings()
        return {
            "status": "healthy",
            "service": "PEI Platform API",
            "version": "1.0.0",
            "system_mode": settings.SYSTEM_MODE,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}",
        )


@app.get("/", tags=["root"])
async def root() -> dict:
    """
    Root endpoint providing API information.

    Returns:
        Dictionary with API details and documentation links
    """
    return {
        "message": "Welcome to PEI Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi_json": "/openapi.json",
        "health": "/health",
        "agents": "/docs#/agents",
        "ots": "/docs#/ots",
        "cuadrillas": "/docs#/cuadrillas",
    }


# Startup and shutdown event handlers (alternative to lifespan context manager)
# These are kept here as documentation but the lifespan context manager above handles both


if __name__ == "__main__":
    # This allows running the app directly: python backend/api/main.py
    # In production, use: python backend/run.py (uvicorn runner)
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.SYSTEM_MODE == "MOCK",  # Auto-reload in MOCK mode only
    )

