"""Cuadrilla (Work Crew) API Endpoints - Stub Implementation"""
from fastapi import APIRouter

router = APIRouter(prefix="/cuadrillas", tags=["cuadrillas"])

@router.get("/")
async def list_cuadrillas():
    """List all work crews"""
    return {"message": "cuadrillas list endpoint - to be implemented"}

@router.post("/")
async def create_cuadrilla():
    """Create a new work crew"""
    return {"message": "cuadrilla create endpoint - to be implemented"}

__all__ = ["router"]

