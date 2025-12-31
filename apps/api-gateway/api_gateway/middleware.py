"""
DERCAS-ONCO-XAI API Gateway Middleware

Custom middleware for rate limiting and request size limits.
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm."""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute in seconds
        self.request_times: Dict[str, deque] = defaultdict(deque)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use user ID if authenticated, otherwise use IP
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP address
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        client_requests = self.request_times[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_size:
            client_requests.popleft()
        
        # Check if limit exceeded
        if len(client_requests) >= self.requests_per_minute:
            return True
        
        # Add current request
        client_requests.append(now)
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path.startswith('/healthz'):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        
        if self._is_rate_limited(client_id):
            logger.warning(
                f"Rate limit exceeded for client: {client_id}",
                extra={
                    'client_id': client_id,
                    'path': request.url.path,
                    'method': request.method
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {self.requests_per_minute} requests per minute exceeded",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Request size limiting middleware."""
    
    def __init__(self, app, max_size_bytes: int = 100 * 1024 * 1024):  # 100MB default
        super().__init__(app)
        self.max_size_bytes = max_size_bytes
    
    async def dispatch(self, request: Request, call_next):
        """Process request with size limiting."""
        # Check Content-Length header
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size_bytes:
                    logger.warning(
                        f"Request size {size} exceeds limit {self.max_size_bytes}",
                        extra={
                            'content_length': size,
                            'max_size': self.max_size_bytes,
                            'path': request.url.path,
                            'method': request.method
                        }
                    )
                    
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "REQUEST_TOO_LARGE",
                            "message": f"Request size {size} bytes exceeds maximum allowed size {self.max_size_bytes} bytes",
                            "max_size_bytes": self.max_size_bytes
                        }
                    )
            except ValueError:
                # Invalid Content-Length header
                pass
        
        return await call_next(request)


class ServiceHealthMiddleware(BaseHTTPMiddleware):
    """Middleware to check service health before routing."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with service health checks."""
        # Skip health checks for non-API routes
        if not request.url.path.startswith('/api/v1/'):
            return await call_next(request)
        
        # Extract service from path
        path_parts = request.url.path.split('/')
        if len(path_parts) >= 4:
            service_name = path_parts[3]  # /api/v1/{service}/...
            
            # Check if service is healthy
            service_registry = getattr(request.app.state, 'service_registry', None)
            if service_registry and not await service_registry.is_service_healthy(service_name):
                logger.error(
                    f"Service {service_name} is unhealthy",
                    extra={
                        'service': service_name,
                        'path': request.url.path,
                        'method': request.method
                    }
                )
                
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "SERVICE_UNAVAILABLE",
                        "message": f"Service {service_name} is currently unavailable",
                        "service": service_name
                    }
                )
        
        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with timing."""
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)
        
        # Add timing to request state for logging
        request.state.response_time_ms = process_time_ms
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time_ms)
        
        return response


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Circuit breaker middleware for service resilience."""
    
    def __init__(self, app, failure_threshold: int = 5, recovery_timeout: int = 60):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.service_states: Dict[str, Dict] = defaultdict(lambda: {
            'failures': 0,
            'last_failure': 0,
            'state': 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        })
    
    def _get_service_from_path(self, path: str) -> Optional[str]:
        """Extract service name from request path."""
        if not path.startswith('/api/v1/'):
            return None
        
        path_parts = path.split('/')
        if len(path_parts) >= 4:
            return path_parts[3]
        
        return None
    
    def _should_allow_request(self, service: str) -> bool:
        """Check if request should be allowed based on circuit breaker state."""
        state = self.service_states[service]
        now = time.time()
        
        if state['state'] == 'CLOSED':
            return True
        elif state['state'] == 'OPEN':
            if now - state['last_failure'] > self.recovery_timeout:
                state['state'] = 'HALF_OPEN'
                return True
            return False
        elif state['state'] == 'HALF_OPEN':
            return True
        
        return False
    
    def _record_success(self, service: str):
        """Record successful request."""
        state = self.service_states[service]
        state['failures'] = 0
        state['state'] = 'CLOSED'
    
    def _record_failure(self, service: str):
        """Record failed request."""
        state = self.service_states[service]
        state['failures'] += 1
        state['last_failure'] = time.time()
        
        if state['failures'] >= self.failure_threshold:
            state['state'] = 'OPEN'
            logger.warning(
                f"Circuit breaker opened for service: {service}",
                extra={
                    'service': service,
                    'failures': state['failures'],
                    'threshold': self.failure_threshold
                }
            )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with circuit breaker logic."""
        service = self._get_service_from_path(request.url.path)
        
        if service and not self._should_allow_request(service):
            logger.warning(
                f"Circuit breaker open for service: {service}",
                extra={
                    'service': service,
                    'path': request.url.path,
                    'method': request.method
                }
            )
            
            return JSONResponse(
                status_code=503,
                content={
                    "error": "CIRCUIT_BREAKER_OPEN",
                    "message": f"Service {service} is temporarily unavailable due to repeated failures",
                    "service": service,
                    "retry_after": self.recovery_timeout
                },
                headers={"Retry-After": str(self.recovery_timeout)}
            )
        
        try:
            response = await call_next(request)
            
            # Record success for 2xx responses
            if service and 200 <= response.status_code < 300:
                self._record_success(service)
            # Record failure for 5xx responses
            elif service and response.status_code >= 500:
                self._record_failure(service)
            
            return response
            
        except Exception as e:
            # Record failure for exceptions
            if service:
                self._record_failure(service)
            raise
