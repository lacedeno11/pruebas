"""Correlation ID middleware for request tracing."""

import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Header names
CORRELATION_ID_HEADER = "X-Correlation-Id"
CASE_ID_HEADER = "X-Case-Id"


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for distributed tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)

        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:16]}"

        # Set in context
        set_correlation_id(correlation_id)

        # Store in request state for easy access
        request.state.correlation_id = correlation_id
        request.state.case_id = request.headers.get(CASE_ID_HEADER)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response
