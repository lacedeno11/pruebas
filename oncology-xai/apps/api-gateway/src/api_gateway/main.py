"""API Gateway main application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from oncology_common.auth.jwt import JWTValidator
from oncology_common.middleware.correlation import CorrelationMiddleware
from oncology_common.middleware.logging import LoggingMiddleware, configure_logging
from oncology_common.observability.tracing import setup_tracing, instrument_fastapi
from oncology_common.observability.metrics import setup_metrics, MetricsMiddleware
from oncology_common.models.base import HealthResponse, ErrorResponse

from api_gateway.config import settings
from api_gateway.routes import router
from api_gateway.proxy import ProxyRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    configure_logging(settings.service_name, settings.log_level)

    if settings.otel_exporter_otlp_endpoint:
        setup_tracing(
            settings.service_name,
            settings.otel_exporter_otlp_endpoint,
        )

    # Setup JWT validator
    app.state.jwt_validator = JWTValidator(
        jwks_url=settings.jwks_url,
    )

    yield

    # Shutdown
    pass


app = FastAPI(
    title="Oncology XAI API Gateway",
    description="API Gateway for Oncology XAI platform",
    version=settings.version,
    lifespan=lifespan,
)

# Middleware (order matters - last added is executed first)
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware, service_name=settings.service_name)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup metrics endpoint
setup_metrics(app)

# Setup tracing instrumentation
instrument_fastapi(app)

# Include routes
app.include_router(router)

# Setup proxy router for downstream services
proxy_router = ProxyRouter(settings)
app.include_router(proxy_router.router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            errorCode=f"HTTP_{exc.status_code}",
            message=exc.detail,
            correlationId=correlation_id,
        ).model_dump(by_alias=True),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            errorCode="INTERNAL_ERROR",
            message="An unexpected error occurred",
            correlationId=correlation_id,
        ).model_dump(by_alias=True),
    )


@app.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.version,
    )
