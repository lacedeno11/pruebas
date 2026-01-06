# DERCAS-ONCO-XAI V1 - Case Service Main Application
# FastAPI application for case and patient management

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Response, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from oncology_xai_common.middleware import CorrelationIdMiddleware, get_correlation_id
from oncology_xai_common.exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    ValidationError
)
from oncology_xai_common.auth import get_user_context

from .config import Settings, get_settings
from .database import init_database, cleanup_database, get_db_session
from .events import get_event_emitter, cleanup_event_emitter
from .api import patients_router, cases_router
from .schemas import HealthCheck
from .seed import seed_database

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
    logger.info("Starting Case Service")
    
    settings = app.state.settings
    
    # Initialize database
    await init_database(settings)
    
    # Initialize event emitter
    await get_event_emitter(settings)
    
    # Seed database if in development mode
    if settings.environment == "development":
        try:
            async with get_db_session(settings).__anext__() as db:
                await seed_database(db, "system")
            logger.info("Development seed data loaded")
        except Exception as e:
            logger.warning("Failed to load seed data", error=str(e))
    
    # Store startup time
    app.state.start_time = time.time()
    
    logger.info("Case Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Case Service")
    
    # Cleanup resources
    await cleanup_event_emitter()
    await cleanup_database()
    
    logger.info("Case Service shutdown complete")


def create_app(settings: Settings = None) -> FastAPI:
    """
    Create FastAPI application.
    
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
        description="Case and patient management service for DERCAS-ONCO-XAI V1 platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Store settings in app state
    app.state.settings = settings
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add correlation ID middleware
    app.add_middleware(CorrelationIdMiddleware)
    
    # Add custom exception handlers
    add_exception_handlers(app)
    
    # Add middleware for request/response logging
    app.middleware("http")(request_logging_middleware)
    
    # Include routers
    app.include_router(patients_router, prefix="/api/v1")
    app.include_router(cases_router, prefix="/api/v1")
    
    # Add health check endpoint
    @app.get("/healthz", response_model=HealthCheck)
    async def health_check():
        """Health check endpoint."""
        return HealthCheck(
            status="healthy",
            timestamp=datetime.utcnow(),
            service="case-service",
            version=settings.app_version,
            database="connected"
        )
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "DERCAS-ONCO-XAI Case Service",
            "version": settings.app_version,
            "status": "running",
            "timestamp": time.time()
        }
    
    # Add service info endpoint
    @app.get("/api/v1/info")
    async def service_info(
        settings: Settings = Depends(get_settings),
        user_context = Depends(get_user_context)
    ):
        """Get service information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime_seconds": time.time() - app.state.start_time,
            "user": {
                "user_id": user_context.user_id,
                "roles": user_context.roles
            }
        }
    
    # Add seed data endpoint for development
    if settings.debug:
        @app.post("/api/v1/seed")
        async def seed_data(
            user_context = Depends(get_user_context)
        ):
            """Seed development data."""
            try:
                async with get_db_session(settings).__anext__() as db:
                    result = await seed_database(db, user_context.user_id)
                
                logger.info(
                    "Seed data created via API",
                    user_id=user_context.user_id,
                    **result
                )
                
                return {
                    "message": "Seed data created successfully",
                    **result
                }
                
            except Exception as e:
                logger.error(
                    "Failed to create seed data",
                    error=str(e),
                    user_id=user_context.user_id
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create seed data"
                )
    
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
            }
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


# Create the application instance
app = create_app()


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
