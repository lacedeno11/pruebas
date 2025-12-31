"""
DERCAS-ONCO-XAI API Gateway Health Router

Health check endpoints for the API Gateway and downstream services.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..services import ServiceRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


def get_service_registry(request: Request) -> ServiceRegistry:
    """Get service registry from app state."""
    return request.app.state.service_registry


@router.get("/")
async def health_check():
    """Basic health check for the API Gateway."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "0.1.0"
    }


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {
        "status": "alive",
        "service": "api-gateway"
    }


@router.get("/ready")
async def readiness_check(
    service_registry: ServiceRegistry = Depends(get_service_registry)
):
    """Kubernetes readiness probe endpoint."""
    try:
        # Check if we can reach at least one critical service
        case_service_healthy = await service_registry.health_check_service("cases")
        
        if case_service_healthy:
            return {
                "status": "ready",
                "service": "api-gateway"
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "service": "api-gateway",
                    "reason": "Critical services unavailable"
                }
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "api-gateway",
                "error": str(e)
            }
        )


@router.get("/services")
async def services_health(
    service_registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get health status of all downstream services."""
    try:
        health_summary = await service_registry.get_service_health_summary()
        
        status_code = 200 if health_summary["summary"]["overall_healthy"] else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if health_summary["summary"]["overall_healthy"] else "degraded",
                "service": "api-gateway",
                "downstream_services": health_summary
            }
        )
    except Exception as e:
        logger.error(f"Services health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "api-gateway",
                "error": str(e)
            }
        )


@router.get("/detailed")
async def detailed_health(
    service_registry: ServiceRegistry = Depends(get_service_registry)
):
    """Detailed health check with service information."""
    try:
        health_summary = await service_registry.get_service_health_summary()
        
        # Get service URLs for reference
        service_urls = {}
        for service_name in service_registry.services:
            service_urls[service_name] = service_registry.get_service_url(service_name)
        
        return {
            "status": "healthy" if health_summary["summary"]["overall_healthy"] else "degraded",
            "service": "api-gateway",
            "version": "0.1.0",
            "timestamp": "2024-01-01T12:00:00Z",  # Would use actual timestamp
            "downstream_services": health_summary,
            "service_urls": service_urls,
            "gateway_info": {
                "rate_limiting": "enabled",
                "request_size_limit": "100MB",
                "authentication": "keycloak_jwt",
                "cors": "enabled"
            }
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "api-gateway",
                "error": str(e)
            }
        )
