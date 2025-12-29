"""Prometheus metrics setup."""

import time
from typing import Callable

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

JOB_COUNT = Counter(
    "jobs_total",
    "Total background jobs",
    ["job_type", "status"],
)

JOB_DURATION = Histogram(
    "job_duration_seconds",
    "Background job duration in seconds",
    ["job_type"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

INFERENCE_COUNT = Counter(
    "inference_requests_total",
    "Total inference requests",
    ["model", "status"],
)

INFERENCE_LATENCY = Histogram(
    "inference_duration_seconds",
    "Inference latency in seconds",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time

        # Normalize endpoint for metrics (avoid high cardinality)
        endpoint = request.url.path
        if "{" in endpoint:
            # Path has parameters, use route template
            for route in request.app.routes:
                if hasattr(route, "path") and route.path == endpoint:
                    endpoint = route.path
                    break

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response


def setup_metrics(app) -> None:
    """Setup metrics endpoint for a FastAPI app."""
    from fastapi import FastAPI
    from fastapi.responses import Response as FastAPIResponse

    if isinstance(app, FastAPI):
        @app.get("/metrics", include_in_schema=False)
        async def metrics():
            return FastAPIResponse(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST,
            )


def record_job(job_type: str, status: str, duration: float | None = None) -> None:
    """Record job metrics."""
    JOB_COUNT.labels(job_type=job_type, status=status).inc()
    if duration is not None:
        JOB_DURATION.labels(job_type=job_type).observe(duration)


def record_inference(model: str, status: str, duration: float | None = None) -> None:
    """Record inference metrics."""
    INFERENCE_COUNT.labels(model=model, status=status).inc()
    if duration is not None:
        INFERENCE_LATENCY.labels(model=model).observe(duration)
