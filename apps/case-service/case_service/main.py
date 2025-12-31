"""
DERCAS-ONCO-XAI Case Service

Main FastAPI application for case and patient management.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dercas_common.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from dercas_common.errors import DercasError, global_exception_handler
from dercas_events import init_event_publisher

from .config import get_settings
from .database import init_database
from .routers import patients, cases, health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    settings = get_settings()
    
    # Initialize database
    try:
        await init_database(settings.DATABASE_URL)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize event publisher
    try:
        init_event_publisher(settings.RABBITMQ_URL)
        logger.info("Event publisher initialized")
    except Exception as e:
        logger.error(f"Failed to initialize event publisher: {e}")
        raise
    
    logger.info("Case Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Case Service shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="DERCAS-ONCO-XAI Case Service",
        description="Case and patient management service",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"]
    )
    
    # Custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    
    # Exception handlers
    app.add_exception_handler(DercasError, global_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    # Include routers
    app.include_router(health.router, prefix="/healthz", tags=["Health"])
    app.include_router(patients.router, prefix="/patients", tags=["Patients"])
    app.include_router(cases.router, prefix="/cases", tags=["Cases"])
    
    return app


# Create app instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "DERCAS-ONCO-XAI Case Service",
        "version": "0.1.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "case_service.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
