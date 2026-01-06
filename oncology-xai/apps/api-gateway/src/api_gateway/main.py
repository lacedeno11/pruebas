# DERCAS-ONCO-XAI V1 - API Gateway Main Application
# FastAPI application with all middleware and routing

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
import structlog

from oncology_xai_common.middleware import CorrelationIdMiddleware, get_correlation_id
from oncology_xai_common.exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    ValidationError,
    ClinicalGuardrailError
)
from oncology_xai_common.auth import UserContext

from .config import Settings, get_settings
from .auth import get_current_user, check_route_permission, APIGatewayAuth, get_auth
from .proxy import ServiceProxy, get_proxy, cleanup_proxy
from .rate_limit import get_rate_limiter, rate_limit_exceeded_handler
from .health import router as health_router, startup_health_check

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting API Gateway")
    
    # Perform startup health checks
    settings = app.state.settings
    await startup_health_check(settings)
    
    # Initialize services
    app.state.start_time = time.time()
    
    logger.info("API Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway")
    
    # Cleanup resources
    await cleanup_proxy()
    
    logger.info("API Gateway shutdown complete")


def create_app(settings: Settings = None) -> FastAPI:
    """
    Create FastAPI application with all middleware and routing.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API Gateway for DERCAS-ONCO-XAI V1 platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Store settings in app state
    app.state.settings = settings
    
    # Add trusted host middleware (security)
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure appropriately for production
        )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )
    
    # Add correlation ID middleware
    app.add_middleware(CorrelationIdMiddleware)
    
    # Add rate limiting
    rate_limiter = get_rate_limiter(settings)
    app.state.limiter = rate_limiter.get_limiter()
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Add custom exception handlers
    add_exception_handlers(app)
    
    # Add middleware for request/response logging
    app.middleware("http")(request_logging_middleware)
    
    # Add authentication middleware
    app.middleware("http")(authentication_middleware)
    
    # Add proxy middleware (must be last)
    app.middleware("http")(proxy_middleware)
    
    # Include health router
    app.include_router(health_router)
    
    # Add custom OpenAPI schema
    if settings.debug:
        setup_openapi(app, settings)
    
    return app


def add_exception_handlers(app: FastAPI):
    """Add custom exception handlers."""
    
    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.warning(
            "Authentication error",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication failed",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        """Handle authorization errors."""
        logger.warning(
            "Authorization error",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Access denied",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handle validation errors."""
        logger.warning(
            "Validation error",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation failed",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(ClinicalGuardrailError)
    async def clinical_guardrail_error_handler(request: Request, exc: ClinicalGuardrailError):
        """Handle clinical guardrail errors."""
        logger.error(
            "Clinical guardrail violation",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Clinical guardrail violation",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "message": exc.detail,
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id(),
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "correlation_id": get_correlation_id()
            }
        )


async def request_logging_middleware(request: Request, call_next):
    """Middleware for request/response logging."""
    start_time = time.time()
    correlation_id = get_correlation_id()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        query=str(request.url.query) if request.url.query else None,
        correlation_id=correlation_id,
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
        correlation_id=correlation_id
    )
    
    return response


async def authentication_middleware(request: Request, call_next):
    """Middleware for authentication and authorization."""
    path = request.url.path
    method = request.method
    
    # Skip authentication for health endpoints and docs
    if path in ["/healthz", "/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Skip authentication for static files
    if path.startswith("/static/"):
        return await call_next(request)
    
    # Check if this is an API endpoint that requires authentication
    if path.startswith("/api/v1/"):
        try:
            # Get authentication handler
            settings = request.app.state.settings
            auth = APIGatewayAuth(settings)
            
            # Extract authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Validate token
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=auth_header.split(" ", 1)[1]
            )
            
            user_context = await auth.validate_token(credentials)
            
            # Check route permissions
            has_permission = await check_route_permission(method, path, user_context)
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for this endpoint"
                )
            
            # Store user context in request state
            request.state.user_context = user_context
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Authentication middleware error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    return await call_next(request)


async def proxy_middleware(request: Request, call_next):
    """Middleware for proxying requests to internal services."""
    path = request.url.path
    
    # Skip proxying for non-API endpoints
    if not path.startswith("/api/v1/"):
        return await call_next(request)
    
    # Skip proxying for gateway-specific endpoints
    gateway_endpoints = ["/api/v1/health", "/api/v1/auth/me", "/api/v1/auth/health", "/api/v1/services/"]
    if any(path.startswith(endpoint) for endpoint in gateway_endpoints):
        return await call_next(request)
    
    # Proxy to internal service
    try:
        settings = request.app.state.settings
        proxy = ServiceProxy(settings)
        
        # Get user context if available
        user_context = getattr(request.state, 'user_context', None)
        
        # Proxy the request
        response = await proxy.proxy_request(request, user_context)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Proxy middleware error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Proxy request failed"
        )


def setup_openapi(app: FastAPI, settings: Settings):
    """Setup custom OpenAPI documentation."""
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token from Keycloak"
            }
        }
        
        # Add security requirement to all endpoints
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                if method != "options":
                    openapi_schema["paths"][path][method]["security"] = [
                        {"BearerAuth": []}
                    ]
        
        # Add server information
        openapi_schema["servers"] = [
            {
                "url": f"http://localhost:{settings.port}",
                "description": "Development server"
            }
        ]
        
        # Add additional info
        openapi_schema["info"]["contact"] = {
            "name": "DERCAS Team",
            "email": "team@dercas.com"
        }
        
        openapi_schema["info"]["license"] = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi


# Create the application instance
app = create_app()


# Additional endpoints for gateway-specific functionality

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "DERCAS-ONCO-XAI API Gateway",
        "version": "1.0.0",
        "status": "running",
        "timestamp": time.time()
    }


@app.get("/api/v1/gateway/info")
async def gateway_info(
    settings: Settings = Depends(get_settings),
    user_context: UserContext = Depends(get_current_user)
):
    """Get gateway information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": time.time() - app.state.start_time,
        "services": list(settings.get_service_routes().keys()),
        "user": {
            "user_id": user_context.user_id,
            "roles": user_context.roles,
            "permissions": user_context.permissions
        }
    }


@app.get("/api/v1/gateway/routes")
async def gateway_routes(
    settings: Settings = Depends(get_settings),
    user_context: UserContext = Depends(get_current_user)
):
    """Get configured routes."""
    return {
        "routes": settings.get_service_routes(),
        "permissions": settings.get_role_permissions()
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )
