from fastapi import APIRouter
from app.api.ots import ots_router
from app.api.cuadrillas import cuadrillas_router
from app.api.agents import agents_router

router = APIRouter()

router.include_router(ots_router, prefix="/ots", tags=["OTs"])
router.include_router(cuadrillas_router, prefix="/cuadrillas", tags=["Cuadrillas"])
router.include_router(agents_router, prefix="/agents", tags=["Agents"])


