"""Planning API Endpoints - Stub Implementation"""
from fastapi import APIRouter

router = APIRouter(prefix="/planning", tags=["planning"])

@router.post("/auto-assign")
async def auto_assign():
    """Trigger automatic OT planning with 3 phases"""
    return {"message": "planning auto-assign endpoint - to be implemented"}

@router.post("/assign-to-crew")
async def assign_to_crew():
    """Manual OT assignment to crew"""
    return {"message": "planning assign-to-crew endpoint - to be implemented"}

__all__ = ["router"]

