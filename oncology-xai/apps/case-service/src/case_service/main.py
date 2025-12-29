"""Case Service main application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from oncology_common.middleware.correlation import CorrelationMiddleware
from oncology_common.middleware.logging import LoggingMiddleware, configure_logging
from oncology_common.observability.tracing import setup_tracing, instrument_fastapi
from oncology_common.observability.metrics import setup_metrics, MetricsMiddleware
from oncology_common.models.base import HealthResponse, ErrorResponse

from case_service.config import settings
from case_service.routes import patients_router, cases_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    configure_logging(settings.service_name, settings.log_level)

    if settings.otel_exporter_otlp_endpoint:
        setup_tracing(
            settings.service_name,
            settings.otel_exporter_otlp_endpoint,
        )

    yield


app = FastAPI(
    title="Oncology XAI Case Service",
    description="Patient and case management service",
    version=settings.version,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware, service_name=settings.service_name)
app.add_middleware(CorrelationMiddleware)

# Metrics
setup_metrics(app)

# Tracing
instrument_fastapi(app)

# Routes
app.include_router(patients_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")


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
