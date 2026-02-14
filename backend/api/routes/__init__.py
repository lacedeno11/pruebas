"""
API routes module for PEI Platform.
Includes all sub-routers for OTs, cuadrillas, planning, governance, and agent interactions.
"""

from fastapi import APIRouter

# Import routers (will be created)
# from backend.api.routes.ots import router as ots_router
# from backend.api.routes.cuadrillas import router as cuadrillas_router
# from backend.api.routes.planning import router as planning_router
# from backend.api.routes.governance import router as governance_router
# from backend.api.routes.agent import router as agent_router

# Create main API router
api_router = APIRouter(prefix="/api", tags=["api"])

# Include sub-routers (uncomment when routes are created)
# api_router.include_router(ots_router, prefix="/ots", tags=["OTs"])
# api_router.include_router(cuadrillas_router, prefix="/cuadrillas", tags=["Cuadrillas"])
# api_router.include_router(planning_router, prefix="/planning", tags=["Planning"])
# api_router.include_router(governance_router, prefix="/governance", tags=["Governance"])
# api_router.include_router(agent_router, prefix="/agent", tags=["Agent"])

__all__ = ["api_router"]

