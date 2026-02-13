"""
FastAPI main application setup.
Includes CORS middleware, all API routes, startup/shutdown events, and health check.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings
from backend.config.database import init_db, close_db
from backend.models import Base

# Import routers (create stubs for now)
# from backend.api.routes import api_router

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": settings.system_mode,
        "version": "1.0.0",
    }


# Include API routers (uncomment when routes are fully implemented)
# app.include_router(api_router)


# Additional endpoints placeholder
@app.get("/api/health", tags=["Health"])
async def api_health():
    """API health check with detailed status."""
    return {
        "status": "operational",
        "system_mode": settings.system_mode,
        "database": "configured",
        "agents": "initialized",
    }

