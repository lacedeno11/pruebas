# DERCAS-ONCO-XAI V1 - API Gateway Health Endpoints
# Health monitoring and status endpoints

import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import structlog

from oncology_xai_common.auth import UserContext
from oncology_xai_common.schemas import HealthStatus
from .config import Settings, get_settings
from .auth import get_current_user, require_permission
from .proxy import ServiceProxy, get_proxy

logger = structlog.get_logger(__name__)


class ServiceHealthStatus(BaseModel):
    """Health status for a single service."""
    
    name: str
    url: str
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[float] = None
    last_check: datetime
    error: Optional[str] = None
    routes: List[str] = []


class GatewayHealthStatus(BaseModel):
    """Overall gateway health status."""
    
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    uptime_seconds: float
    version: str
    services: List[ServiceHealthStatus]
    summary: Dict[str, int]


class AuthHealthStatus(BaseModel):
    """Authentication health status."""
    
    keycloak_reachable: bool
    jwks_accessible: bool
    last_token_validation: Optional[datetime] = None
    error: Optional[str] = None


class UserInfo(BaseModel):
    """Current user information."""
    
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    roles: List[str]
    permissions: List[str]
    session_id: Optional[str] = None
    token_expires_at: Optional[datetime] = None


class HealthChecker:
    """Health checking functionality for the API Gateway."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.start_time = time.time()
        self._last_health_check: Dict[str, datetime] = {}
        self._cached_health: Dict[str, ServiceHealthStatus] = {}
        self._cache_ttl = 30  # Cache health status for 30 seconds
    
    async def check_service_health(self, service_name: str, service_url: str) -> ServiceHealthStatus:
        """
        Check health of a single service.
        
        Args:
            service_name: Name of the service
            service_url: Base URL of the service
            
        Returns:
            ServiceHealthStatus
        """
        start_time = time.time()
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.settings.health_check_timeout) as client:
                health_url = f"{service_url.rstrip('/')}/healthz"
                response = await client.get(health_url)
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return ServiceHealthStatus(
                        name=service_name,
                        url=service_url,
                        status="healthy",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow()
                    )
                else:
                    return ServiceHealthStatus(
                        name=service_name,
                        url=service_url,
                        status="unhealthy",
                        response_time_ms=response_time,
                        last_check=datetime.utcnow(),
                        error=f"HTTP {response.status_code}"
                    )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealthStatus(
                name=service_name,
                url=service_url,
                status="unhealthy",
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_all_services_health(self, proxy: ServiceProxy) -> List[ServiceHealthStatus]:
        """
        Check health of all configured services.
        
        Args:
            proxy: Service proxy instance
            
        Returns:
            List of ServiceHealthStatus
        """
        service_configs = self.settings.get_service_routes()
        services_to_check = {}
        
        # Collect unique services
        for route_prefix, config in service_configs.items():
            service_name = config["service"]
            service_url = config["url"]
            
            if service_name not in services_to_check:
                services_to_check[service_name] = {
                    "url": service_url,
                    "routes": [route_prefix]
                }
            else:
                services_to_check[service_name]["routes"].append(route_prefix)
        
        # Check health of each service
        health_checks = []
        for service_name, service_info in services_to_check.items():
            # Check cache first
            cache_key = f"{service_name}:{service_info['url']}"
            if (cache_key in self._cached_health and 
                cache_key in self._last_health_check and
                datetime.utcnow() - self._last_health_check[cache_key] < timedelta(seconds=self._cache_ttl)):
                
                cached_status = self._cached_health[cache_key]
                cached_status.routes = service_info["routes"]
                health_checks.append(cached_status)
            else:
                # Perform health check
                health_status = await self.check_service_health(service_name, service_info["url"])
                health_status.routes = service_info["routes"]
                
                # Cache result
                self._cached_health[cache_key] = health_status
                self._last_health_check[cache_key] = datetime.utcnow()
                
                health_checks.append(health_status)
        
        return health_checks
    
    async def check_auth_health(self) -> AuthHealthStatus:
        """
        Check authentication system health.
        
        Returns:
            AuthHealthStatus
        """
        try:
            import httpx
            
            # Check Keycloak reachability
            keycloak_reachable = False
            jwks_accessible = False
            error = None
            
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Check Keycloak health
                    keycloak_health_url = f"{self.settings.keycloak_url}/health"
                    response = await client.get(keycloak_health_url)
                    keycloak_reachable = response.status_code == 200
                    
                    # Check JWKS endpoint
                    jwks_response = await client.get(self.settings.jwks_url)
                    jwks_accessible = jwks_response.status_code == 200
                    
            except Exception as e:
                error = str(e)
            
            return AuthHealthStatus(
                keycloak_reachable=keycloak_reachable,
                jwks_accessible=jwks_accessible,
                error=error
            )
            
        except Exception as e:
            return AuthHealthStatus(
                keycloak_reachable=False,
                jwks_accessible=False,
                error=str(e)
            )
    
    async def get_overall_health(self, proxy: ServiceProxy) -> GatewayHealthStatus:
        """
        Get overall gateway health status.
        
        Args:
            proxy: Service proxy instance
            
        Returns:
            GatewayHealthStatus
        """
        # Check all services
        service_statuses = await self.check_all_services_health(proxy)
        
        # Calculate summary
        summary = {
            "healthy": 0,
            "unhealthy": 0,
            "unknown": 0
        }
        
        for service_status in service_statuses:
            summary[service_status.status] = summary.get(service_status.status, 0) + 1
        
        # Determine overall status
        if summary["unhealthy"] == 0:
            overall_status = "healthy"
        elif summary["healthy"] > summary["unhealthy"]:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        uptime = time.time() - self.start_time
        
        return GatewayHealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            version=self.settings.app_version,
            services=service_statuses,
            summary=summary
        )


# Create router for health endpoints
router = APIRouter(prefix="", tags=["Health"])


@router.get("/healthz", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Basic health status
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
        service="api-gateway",
        version="1.0.0"
    )


@router.get("/health", response_model=GatewayHealthStatus)
async def detailed_health_check(
    settings: Settings = Depends(get_settings),
    proxy: ServiceProxy = Depends(get_proxy)
):
    """
    Detailed health check with service status.
    
    Returns:
        Detailed health status including all services
    """
    health_checker = HealthChecker(settings)
    return await health_checker.get_overall_health(proxy)


@router.get("/api/v1/health", response_model=GatewayHealthStatus)
async def api_health_check(
    settings: Settings = Depends(get_settings),
    proxy: ServiceProxy = Depends(get_proxy),
    user_context: UserContext = Depends(require_permission("audit:read"))
):
    """
    API health check endpoint (requires authentication).
    
    Returns:
        Detailed health status for authenticated users
    """
    health_checker = HealthChecker(settings)
    return await health_checker.get_overall_health(proxy)


@router.get("/api/v1/auth/me", response_model=UserInfo)
async def get_current_user_info(
    user_context: UserContext = Depends(get_current_user)
):
    """
    Get current user information.
    
    Returns:
        Current user information
    """
    # Extract token expiration if available
    token_expires_at = None
    if user_context.token_payload:
        exp = user_context.token_payload.get("exp")
        if exp:
            token_expires_at = datetime.fromtimestamp(exp)
    
    return UserInfo(
        user_id=user_context.user_id,
        name=user_context.name,
        email=user_context.email,
        roles=user_context.roles,
        permissions=user_context.permissions,
        session_id=user_context.session_id,
        token_expires_at=token_expires_at
    )


@router.get("/api/v1/auth/health", response_model=AuthHealthStatus)
async def auth_health_check(
    settings: Settings = Depends(get_settings),
    user_context: UserContext = Depends(require_permission("audit:read"))
):
    """
    Authentication system health check.
    
    Returns:
        Authentication system health status
    """
    health_checker = HealthChecker(settings)
    return await health_checker.check_auth_health()


@router.get("/api/v1/services/status")
async def get_services_status(
    settings: Settings = Depends(get_settings),
    proxy: ServiceProxy = Depends(get_proxy),
    user_context: UserContext = Depends(require_permission("audit:read"))
):
    """
    Get status of all configured services.
    
    Returns:
        Service status information
    """
    return await proxy.get_service_status()


@router.post("/api/v1/services/{service_name}/health-check")
async def force_service_health_check(
    service_name: str,
    settings: Settings = Depends(get_settings),
    user_context: UserContext = Depends(require_permission("audit:write"))
):
    """
    Force health check for a specific service.
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        Service health status
    """
    try:
        service_url = settings.get_service_url(service_name)
        health_checker = HealthChecker(settings)
        health_status = await health_checker.check_service_health(service_name, service_url)
        
        logger.info(
            "Forced health check completed",
            service_name=service_name,
            status=health_status.status,
            user_id=user_context.user_id
        )
        
        return health_status
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Health check failed",
            service_name=service_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


# Startup health check
async def startup_health_check(settings: Settings) -> bool:
    """
    Perform startup health checks.
    
    Args:
        settings: Application settings
        
    Returns:
        True if startup checks pass
    """
    logger.info("Performing startup health checks")
    
    health_checker = HealthChecker(settings)
    
    # Check authentication system
    auth_health = await health_checker.check_auth_health()
    if not auth_health.keycloak_reachable:
        logger.warning("Keycloak not reachable during startup")
    
    if not auth_health.jwks_accessible:
        logger.warning("JWKS endpoint not accessible during startup")
    
    # Note: We don't fail startup if services are not available
    # as they might start after the gateway
    
    logger.info("Startup health checks completed")
    return True
