from fastapi import APIRouter

from backend.app.api import ots, cuadrillas, agents, mock

router = APIRouter()

# Include OT endpoints with /ots prefix
router.include_router(ots.router, tags=["OTs"])

# Include Cuadrilla endpoints with /cuadrillas prefix
router.include_router(cuadrillas.router, tags=["Cuadrillas"])

# Include Agent endpoints with /agents prefix
router.include_router(agents.router, tags=["Agents"])

# Include Mock endpoints with /mock prefix (only available in MOCK mode)
router.include_router(mock.router, tags=["Mock"])

__all__ = ["router"]

