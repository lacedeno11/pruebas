"""
DERCAS-ONCO-XAI V1 - Middleware Components

Correlation ID tracking and other middleware for the oncology platform.
"""

import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Header names
CORRELATION_ID_HEADER = "X-Correlation-Id"
CASE_ID_HEADER = "X-Case-Id"
REQUEST_ID_HEADER = "X-Request-Id"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation ID tracking across requests.
    
    This middleware:
    1. Extracts correlation ID from incoming requests
    2. Generates a new correlation ID if none exists
    3. Adds correlation ID to response headers
    4. Makes correlation ID available in request state
    5. Logs request/response with correlation ID
    """
    
    def __init__(self, app, header_name: str = CORRELATION_ID_HEADER):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Store in request state for access by endpoints
        request.state.correlation_id = correlation_id
        
        # Extract case ID if present
        case_id = request.headers.get(CASE_ID_HEADER)
        if case_id:
            request.state.case_id = case_id
        
        # Generate request ID for this specific request
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log incoming request
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "request_id": request_id,
                "case_id": case_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": request.client.host if request.client else None
            }
        )
        
        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Add correlation headers to response
            response.headers[self.header_name] = correlation_id
            response.headers[REQUEST_ID_HEADER] = request_id
            if case_id:
                response.headers[CASE_ID_HEADER] = case_id
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "case_id": case_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "processing_time_ms": round(processing_time * 1000, 2)
                }
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} -> {type(e).__name__}: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "case_id": case_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "processing_time_ms": round(processing_time * 1000, 2)
                },
                exc_info=True
            )
            
            raise


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and store request context information.
    
    This middleware extracts common context information from requests
    and makes it available throughout the request lifecycle.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract user information from headers (set by API Gateway)
        user_id = request.headers.get("X-User-Id")
        username = request.headers.get("X-Username")
        user_roles = request.headers.get("X-User-Roles", "").split(",") if request.headers.get("X-User-Roles") else []
        
        # Store in request state
        request.state.user_id = user_id
        request.state.username = username
        request.state.user_roles = [role.strip() for role in user_roles if role.strip()]
        
        # Extract service information
        service_name = request.headers.get("X-Service-Name")
        service_version = request.headers.get("X-Service-Version")
        
        request.state.service_name = service_name
        request.state.service_version = service_version
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    def __init__(self, app, enable_cors: bool = True):
        super().__init__(app)
        self.enable_cors = enable_cors
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add CORS headers if enabled (for development)
        if self.enable_cors:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = f"{CORRELATION_ID_HEADER}, {CASE_ID_HEADER}, Authorization, Content-Type"
            response.headers["Access-Control-Expose-Headers"] = f"{CORRELATION_ID_HEADER}, {REQUEST_ID_HEADER}, {CASE_ID_HEADER}"
        
        return response


# Utility functions for accessing request context
def get_correlation_id(request: Request) -> Optional[str]:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", None)


def get_case_id(request: Request) -> Optional[str]:
    """Get case ID from request state."""
    return getattr(request.state, "case_id", None)


def get_request_id(request: Request) -> Optional[str]:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", None)


def get_user_id(request: Request) -> Optional[str]:
    """Get user ID from request state."""
    return getattr(request.state, "user_id", None)


def get_username(request: Request) -> Optional[str]:
    """Get username from request state."""
    return getattr(request.state, "username", None)


def get_user_roles(request: Request) -> list[str]:
    """Get user roles from request state."""
    return getattr(request.state, "user_roles", [])


def get_service_name(request: Request) -> Optional[str]:
    """Get service name from request state."""
    return getattr(request.state, "service_name", None)


def get_service_version(request: Request) -> Optional[str]:
    """Get service version from request state."""
    return getattr(request.state, "service_version", None)


# Context manager for correlation ID in background tasks
class CorrelationContext:
    """Context manager for maintaining correlation ID in background tasks."""
    
    def __init__(self, correlation_id: str, case_id: Optional[str] = None):
        self.correlation_id = correlation_id
        self.case_id = case_id
        self._old_correlation_id = None
        self._old_case_id = None
    
    def __enter__(self):
        # Store current context (if any)
        self._old_correlation_id = getattr(CorrelationContext, "_current_correlation_id", None)
        self._old_case_id = getattr(CorrelationContext, "_current_case_id", None)
        
        # Set new context
        CorrelationContext._current_correlation_id = self.correlation_id
        CorrelationContext._current_case_id = self.case_id
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        CorrelationContext._current_correlation_id = self._old_correlation_id
        CorrelationContext._current_case_id = self._old_case_id
    
    @classmethod
    def get_current_correlation_id(cls) -> Optional[str]:
        """Get current correlation ID from context."""
        return getattr(cls, "_current_correlation_id", None)
    
    @classmethod
    def get_current_case_id(cls) -> Optional[str]:
        """Get current case ID from context."""
        return getattr(cls, "_current_case_id", None)


# Logging formatter that includes correlation ID
class CorrelationIdFormatter(logging.Formatter):
    """Custom logging formatter that includes correlation ID."""
    
    def format(self, record):
        # Add correlation ID to log record if available
        correlation_id = CorrelationContext.get_current_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "N/A"
        
        case_id = CorrelationContext.get_current_case_id()
        if case_id:
            record.case_id = case_id
        else:
            record.case_id = "N/A"
        
        return super().format(record)


def setup_correlation_logging():
    """Setup logging with correlation ID support."""
    formatter = CorrelationIdFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] [%(case_id)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    return formatter
