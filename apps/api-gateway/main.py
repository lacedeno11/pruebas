"""
DERCAS-ONCO-XAI V1 - API Gateway

FastAPI gateway with JWT validation, RBAC routing, and request proxying.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.auth import JWTValidator, create_jwt_validator, PermissionChecker
from packages.common.middleware import (
    CorrelationIdMiddleware, 
    RequestContextMiddleware, 
    SecurityHeadersMiddleware,
    get_correlation_id,
    get_user_id
)
from packages.common.errors import (
    ErrorCode,
    create_http_exception,
    AuthenticationError,
    AuthorizationError,
    platform_exception_to_http_exception
)
from packages.common.models import HealthCheckResponse

from .config import get_settings
from .proxy import ServiceProxy
from .rate_limiter import RateLimiter
from .auth import AuthHandler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting API Gateway...")
    
    # Initialize components
    settings = get_settings()
    
    # Initialize JWT validator
    app.state.jwt_validator = create_jwt_validator(
        keycloak_url=settings.keycloak_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id
    )
    
    # Initialize service proxy
    app.state.service_proxy = ServiceProxy(settings.service_urls)
    
    # Initialize rate limiter
    app.state.rate_limiter = RateLimiter(
        redis_url=settings.redis_url,
        default_rate_limit=settings.default_rate_limit,
        image_upload_rate_limit=settings.image_upload_rate_limit
    )
    
    # Initialize auth handler
    app.state.auth_handler = AuthHandler(app.state.jwt_validator)
    
    logger.info("API Gateway started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down API Gateway...")
    await app.state.service_proxy.close()
    await app.state.rate_limiter.close()
    logger.info("API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DERCAS-ONCO-XAI API Gateway",
    description="API Gateway for the Explainable AI Oncology Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware, enable_cors=True)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CorrelationIdMiddleware)


# Exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=exc.to_error_response().model_dump()
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=exc.to_error_response().model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    correlation_id = get_correlation_id(request)
    
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"correlation_id": correlation_id},
        exc_info=True
    )
    
    return create_http_exception(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="Internal server error",
        correlation_id=correlation_id,
        service="api-gateway"
    )


# Health check endpoint
@app.get("/healthz", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        dependencies={
            "keycloak": "healthy",  # TODO: Add actual health checks
            "redis": "healthy",
            "services": "healthy"
        }
    )


# Authentication endpoints
@app.get("/auth/me")
async def get_current_user(request: Request):
    """Get current authenticated user information."""
    # Authenticate user
    user_claims = await app.state.auth_handler.authenticate_request(request)
    
    return {
        "user_id": user_claims.sub,
        "username": user_claims.preferred_username,
        "email": user_claims.email,
        "name": user_claims.name,
        "roles": user_claims.realm_access.get("roles", []) if user_claims.realm_access else [],
        "groups": user_claims.groups or []
    }


# Service proxy routes
@app.api_route("/api/v1/cases/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_case_service(request: Request, path: str):
    """Proxy requests to case service."""
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="case-service",
        path=f"/api/v1/cases/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


@app.api_route("/api/v1/patients/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_patient_endpoints(request: Request, path: str):
    """Proxy patient-related requests to case service."""
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="case-service",
        path=f"/api/v1/patients/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


@app.api_route("/api/v1/images/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_image_service(request: Request, path: str):
    """Proxy requests to image service with special handling for uploads."""
    # Apply stricter rate limiting for image uploads
    if request.method == "POST" and "upload" in path:
        rate_limit_key = f"image_upload:{get_user_id(request) or 'anonymous'}"
        await app.state.rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=app.state.rate_limiter.image_upload_rate_limit
        )
    
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="image-service",
        path=f"/api/v1/images/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter,
        max_content_length=100 * 1024 * 1024  # 100MB for image uploads
    )


@app.api_route("/api/v1/inference/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_inference_service(request: Request, path: str):
    """Proxy requests to inference service."""
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="inference-service",
        path=f"/api/v1/inference/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


@app.api_route("/api/v1/ehr/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_ehr_service(request: Request, path: str):
    """Proxy requests to EHR service."""
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="ehr-service",
        path=f"/api/v1/ehr/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


@app.api_route("/api/v1/graphs/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_graph_service(request: Request, path: str):
    """Proxy requests to graph service."""
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="graph-service",
        path=f"/api/v1/graphs/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


@app.api_route("/api/v1/admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_ontology_admin_service(request: Request, path: str):
    """Proxy requests to ontology admin service."""
    # Require admin permissions for ontology management
    user_claims = await app.state.auth_handler.authenticate_request(request)
    
    if not PermissionChecker.can_manage_ontologies(user_claims):
        raise AuthorizationError(
            message="Insufficient permissions for ontology management",
            correlation_id=get_correlation_id(request)
        )
    
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="ontology-admin-service",
        path=f"/api/v1/admin/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


@app.api_route("/api/v1/audit/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_audit_service(request: Request, path: str):
    """Proxy requests to audit service."""
    # Require audit permissions
    user_claims = await app.state.auth_handler.authenticate_request(request)
    
    if not PermissionChecker.can_view_audit_logs(user_claims):
        raise AuthorizationError(
            message="Insufficient permissions for audit log access",
            correlation_id=get_correlation_id(request)
        )
    
    return await app.state.service_proxy.proxy_request(
        request=request,
        service_name="audit-service",
        path=f"/api/v1/audit/{path}",
        auth_handler=app.state.auth_handler,
        rate_limiter=app.state.rate_limiter
    )


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
