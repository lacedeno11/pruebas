"""Routes for Case Service."""

from case_service.routes.patients import router as patients_router
from case_service.routes.cases import router as cases_router

__all__ = ["patients_router", "cases_router"]
