"""Structured logging middleware."""

import time
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from oncology_common.middleware.correlation import get_correlation_id


logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    def __init__(self, app, service_name: str = "unknown"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Log request
        await logger.ainfo(
            "request_started",
            service=self.service_name,
            method=request.method,
            path=request.url.path,
            correlation_id=get_correlation_id(),
            client_host=request.client.host if request.client else None,
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration = time.perf_counter() - start_time
            await logger.aerror(
                "request_failed",
                service=self.service_name,
                method=request.method,
                path=request.url.path,
                correlation_id=get_correlation_id(),
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Log response
        duration = time.perf_counter() - start_time
        await logger.ainfo(
            "request_completed",
            service=self.service_name,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            correlation_id=get_correlation_id(),
            duration_ms=round(duration * 1000, 2),
        )

        return response


def configure_logging(service_name: str, log_level: str = "INFO") -> None:
    """Configure structured logging for a service."""
    import logging
    import sys

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(log_level),
    )
