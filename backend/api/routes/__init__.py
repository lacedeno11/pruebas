"""
API routes package for PEI Platform.
Aggregates all APIRouter instances for easy registration in the FastAPI application.
"""

from backend.api.routes.ots import router as ots_router
from backend.api.routes.cuadrillas import router as cuadrillas_router
from backend.api.routes.agents import router as agents_router

# Aggregate all routers for easy registration in FastAPI app
all_routers = [
    ots_router,
    cuadrillas_router,
    agents_router,
]

__all__ = [
    "ots_router",
    "cuadrillas_router",
    "agents_router",
    "all_routers",
]

