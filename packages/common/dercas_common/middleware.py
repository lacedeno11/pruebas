"""
DERCAS-ONCO-XAI Middleware

Correlation ID middleware and utilities for request tracing.
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID for request tracing."""
    
    def __init__(self, app, header_name: str = "X-Correlation-Id"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and ensure correlation ID is present."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            logger.debug(f"Generated new correlation ID: {correlation_id}")
        else:
            logger.debug(f"Using existing correlation ID: {correlation_id}")
        
        # Set correlation ID in context
        token = _correlation_id.set(correlation_id)
        
        try:
            # Add correlation ID to request state for easy access
            request.state.correlation_id = correlation_id
            
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request with correlation ID {correlation_id}: {e}")
            raise
        finally:
            # Reset context
            _correlation_id.reset(token)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def add_correlation_id(correlation_id: str) -> None:
    """Add correlation ID to current context."""
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""
    
    def __init__(self, app, log_level: str = "INFO"):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response with correlation ID."""
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        # Log request
        logger.log(
            self.log_level,
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            logger.log(
                self.log_level,
                f"Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "response_size": response.headers.get("content-length"),
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                f"Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                },
                exc_info=True
            )
            raise


class CaseIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle case ID extraction and validation."""
    
    def __init__(self, app, header_name: str = "X-Case-Id"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract and validate case ID from headers or path."""
        case_id = request.headers.get(self.header_name)
        
        # Try to extract case ID from path if not in headers
        if not case_id:
            path_parts = request.url.path.split('/')
            for i, part in enumerate(path_parts):
                if part == 'cases' and i + 1 < len(path_parts):
                    case_id = path_parts[i + 1]
                    break
        
        # Add case ID to request state
        if case_id:
            request.state.case_id = case_id
            logger.debug(f"Case ID extracted: {case_id}")
        
        response = await call_next(request)
        
        # Add case ID to response headers if present
        if case_id:
            response.headers[self.header_name] = case_id
        
        return response


def get_case_id(request: Request) -> Optional[str]:
    """Get case ID from request state."""
    return getattr(request.state, 'case_id', None)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class PHIRedactionMiddleware(BaseHTTPMiddleware):
    """Middleware to redact PHI from logs and responses in non-production environments."""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.phi_patterns = [
            # Add regex patterns for PHI detection
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card pattern
            # Add more patterns as needed
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with PHI redaction if enabled."""
        if not self.enabled:
            return await call_next(request)
        
        # TODO: Implement PHI redaction logic
        # This would involve scanning request/response data for PHI patterns
        # and redacting them before logging or returning responses
        
        response = await call_next(request)
        return response


# Utility functions for middleware setup
def setup_middleware(app, config: dict = None):
    """Setup common middleware for DERCAS services."""
    config = config or {}
    
    # Security headers (always first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Correlation ID middleware
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=config.get("correlation_header", "X-Correlation-Id")
    )
    
    # Case ID middleware
    app.add_middleware(
        CaseIdMiddleware,
        header_name=config.get("case_header", "X-Case-Id")
    )
    
    # Request logging
    if config.get("enable_request_logging", True):
        app.add_middleware(
            RequestLoggingMiddleware,
            log_level=config.get("log_level", "INFO")
        )
    
    # PHI redaction
    if config.get("enable_phi_redaction", False):
        app.add_middleware(
            PHIRedactionMiddleware,
            enabled=config.get("phi_redaction_enabled", True)
        )


# Context managers for correlation ID
class CorrelationContext:
    """Context manager for correlation ID."""
    
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.token = None
    
    def __enter__(self):
        self.token = _correlation_id.set(self.correlation_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            _correlation_id.reset(self.token)


def with_correlation_id(correlation_id: str):
    """Decorator to run function with specific correlation ID."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with CorrelationContext(correlation_id):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with CorrelationContext(correlation_id):
                return func(*args, **kwargs)
        
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
