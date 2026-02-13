"""
API Router Aggregation Module

This module aggregates all API routers (ots, cuadrillas, planning, system)
into a single api_router that is included in the FastAPI application.

The aggregated router is prefixed with /api/v1 as the base path for all endpoints.

Usage in app.main:
    from app.api import api_router
    app.include_router(api_router)
    
This makes all endpoints available under /api/v1/...
"""

from fastapi import APIRouter

from app.api import ots, cuadrillas, planning, system

# Create main API router with version prefix
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
# These routers have their own prefixes (e.g., /ots) that will be appended
api_router.include_router(ots.router)  # /api/v1/ots
api_router.include_router(cuadrillas.router)  # /api/v1/cuadrillas
api_router.include_router(planning.router)  # /api/v1/planning
api_router.include_router(system.router)  # /api/v1/system

__all__ = ["api_router"]

