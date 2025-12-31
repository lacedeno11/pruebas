"""
DERCAS-ONCO-XAI API Gateway

Main FastAPI application with JWT validation, RBAC, and request routing.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from dercas_common.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from dercas_common.errors import DercasError, global_exception_handler
from dercas_common.auth import init_auth_system

from .config import get_settings
from .middleware import RateLimitMiddleware, RequestSizeLimitMiddleware
from .routers import health, auth, proxy
from .services import ServiceRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    settings = get_settings()
    
    # Initialize authentication system
    try:
        await init_auth_system(
            jwks_url=settings.KEYCLOAK_JWKS_URL,
            issuer=settings.KEYCLOAK_ISSUER,
            audience=settings.KEYCLOAK_AUDIENCE
        )
        logger.info("Authentication system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize auth system: {e}")
        raise
    
    # Initialize service registry
    service_registry = ServiceRegistry(settings)
    app.state.service_registry = service_registry
    
    # Health check for downstream services
    await service_registry.health_check_all()
    
    logger.info("API Gateway started successfully")
    
    yield
    
    # Cleanup
    await service_registry.close()
    logger.info("API Gateway shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="DERCAS-ONCO-XAI API Gateway",
        description="API Gateway for DERCAS Explainable AI Oncology Platform",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Request-ID"]
    )
    
    # Custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=settings.MAX_REQUEST_SIZE_BYTES
    )
    
    # Exception handlers
    app.add_exception_handler(DercasError, global_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    # Include routers
    app.include_router(health.router, prefix="/healthz", tags=["Health"])
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(proxy.router, prefix="/api/v1", tags=["Services"])
    
    return app


# Create app instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "DERCAS-ONCO-XAI API Gateway",
        "version": "0.1.0",
        "status": "running",
        "docs_url": "/docs" if get_settings().DEBUG else None
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            'correlation_id': correlation_id,
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params),
            'user_agent': request.headers.get('user-agent'),
            'remote_addr': request.client.host if request.client else None
        }
    )
    
    response = await call_next(request)
    
    logger.info(
        f"Response: {response.status_code}",
        extra={
            'correlation_id': correlation_id,
            'status_code': response.status_code,
            'response_time_ms': getattr(request.state, 'response_time_ms', 0)
        }
    )
    
    return response


if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "api_gateway.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
