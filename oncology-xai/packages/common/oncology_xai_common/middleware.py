# DERCAS-ONCO-XAI V1 - Middleware Components
# Correlation ID middleware and context management

import uuid
from typing import Optional, Callable
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

# Header name for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-Id"
CASE_ID_HEADER = "X-Case-Id"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation ID for request tracing.
    
    This middleware:
    1. Extracts correlation ID from request headers
    2. Generates a new correlation ID if none provided
    3. Sets the correlation ID in context for the request
    4. Adds correlation ID to response headers
    5. Logs request information with correlation ID
    """
    
    def __init__(self, app, header_name: str = CORRELATION_ID_HEADER):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract correlation ID from request headers
        correlation_id = request.headers.get(self.header_name)
        
        # Generate new correlation ID if none provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            logger.debug(f"Generated new correlation ID: {correlation_id}")
        else:
            logger.debug(f"Using existing correlation ID: {correlation_id}")
        
        # Set correlation ID in context
        correlation_id_token = correlation_id_context.set(correlation_id)
        
        # Extract case ID if present
        case_id = request.headers.get(CASE_ID_HEADER)
        
        # Log request start
        logger.info(
            f"Request started - Method: {request.method}, "
            f"URL: {request.url}, "
            f"Correlation ID: {correlation_id}, "
            f"Case ID: {case_id or 'N/A'}"
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            # Add case ID to response headers if present
            if case_id:
                response.headers[CASE_ID_HEADER] = case_id
            
            # Log request completion
            logger.info(
                f"Request completed - Status: {response.status_code}, "
                f"Correlation ID: {correlation_id}"
            )
            
            return response
            
        except Exception as e:
            # Log request error
            logger.error(
                f"Request failed - Error: {str(e)}, "
                f"Correlation ID: {correlation_id}"
            )
            raise
        finally:
            # Reset correlation ID context
            correlation_id_context.reset(correlation_id_token)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_context.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    correlation_id_context.set(correlation_id)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logging middleware with correlation ID support.
    """
    
    def __init__(self, app, log_body: bool = False, max_body_size: int = 1024):
        super().__init__(app)
        self.log_body = log_body
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = get_correlation_id()
        
        # Log request details
        log_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "correlation_id": correlation_id,
        }
        
        # Optionally log request body (be careful with sensitive data)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    log_data["body"] = body.decode("utf-8", errors="ignore")
                else:
                    log_data["body"] = f"<body too large: {len(body)} bytes>"
            except Exception as e:
                log_data["body"] = f"<error reading body: {e}>"
        
        logger.debug(f"Request details: {log_data}")
        
        # Process request
        response = await call_next(request)
        
        # Log response details
        logger.debug(
            f"Response - Status: {response.status_code}, "
            f"Headers: {dict(response.headers)}, "
            f"Correlation ID: {correlation_id}"
        )
        
        return response


class CaseContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and manage case context from requests.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract case ID from headers or path
        case_id = request.headers.get(CASE_ID_HEADER)
        
        # Try to extract case ID from path if not in headers
        if not case_id and "/cases/" in str(request.url.path):
            path_parts = request.url.path.split("/")
            try:
                case_index = path_parts.index("cases")
                if case_index + 1 < len(path_parts):
                    case_id = path_parts[case_index + 1]
            except (ValueError, IndexError):
                pass
        
        # Set case ID in request state for later access
        if case_id:
            request.state.case_id = case_id
            logger.debug(f"Case context set: {case_id}")
        
        return await call_next(request)


def get_case_id_from_request(request: Request) -> Optional[str]:
    """Extract case ID from request state or headers."""
    # Try request state first (set by middleware)
    if hasattr(request.state, "case_id"):
        return request.state.case_id
    
    # Fallback to headers
    return request.headers.get(CASE_ID_HEADER)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request performance metrics.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import time
        
        start_time = time.time()
        correlation_id = get_correlation_id()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log performance metrics
        logger.info(
            f"Performance - Duration: {process_time:.4f}s, "
            f"Method: {request.method}, "
            f"Path: {request.url.path}, "
            f"Status: {response.status_code}, "
            f"Correlation ID: {correlation_id}"
        )
        
        return response
