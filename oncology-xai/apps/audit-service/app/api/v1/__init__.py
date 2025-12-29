"""API v1 module."""
from fastapi import APIRouter
from app.api.v1 import audit

api_router = APIRouter()

# Include routers
api_router.include_router(audit.router)

__all__ = ["api_router"]
