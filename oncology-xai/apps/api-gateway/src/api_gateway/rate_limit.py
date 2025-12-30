# DERCAS-ONCO-XAI V1 - API Gateway Rate Limiting
# Rate limiting and throttling implementation

import time
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from oncology_xai_common.auth import UserContext
from .config import Settings

logger = structlog.get_logger(__name__)


def get_user_id_or_ip(request: Request) -> str:
    """
    Get user ID for authenticated requests or IP address for anonymous requests.
    
    Args:
        request: FastAPI request
        
    Returns:
        User identifier for rate limiting
    """
    # Try to get user context from request state
    user_context = getattr(request.state, 'user_context', None)
    if user_context and isinstance(user_context, UserContext):
        return f"user:{user_context.user_id}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_user_role(request: Request) -> Optional[str]:
    """
    Get user role for role-based rate limiting.
    
    Args:
        request: FastAPI request
        
    Returns:
        User role or None
    """
    user_context = getattr(request.state, 'user_context', None)
    if user_context and isinstance(user_context, UserContext):
        # Return the highest priority role
        role_priority = {"admin": 3, "clinician": 2, "auditor": 1}
        user_roles = user_context.roles
        
        if user_roles:
            # Get the role with highest priority
            sorted_roles = sorted(user_roles, key=lambda r: role_priority.get(r, 0), reverse=True)
            return sorted_roles[0]
    
    return None


class RateLimitConfig:
    """Rate limiting configuration for different user types and endpoints."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Default rate limits
        self.default_limits = {
            "anonymous": "50/minute",
            "authenticated": "200/minute",
            "clinician": "300/minute",
            "admin": "500/minute",
            "auditor": "100/minute"
        }
        
        # Endpoint-specific rate limits
        self.endpoint_limits = {
            # Authentication endpoints
            "/api/v1/auth/login": "10/minute",
            "/api/v1/auth/refresh": "20/minute",
            
            # Upload endpoints (more restrictive)
            "/api/v1/images": "20/minute",
            "/api/v1/ehr": "30/minute",
            
            # Inference endpoints (resource intensive)
            "/api/v1/inference": "10/minute",
            "/api/v1/jobs": "50/minute",
            
            # Admin endpoints
            "/api/v1/ontology": "50/minute",
            
            # Health endpoints (less restrictive)
            "/healthz": "100/minute",
            "/api/v1/health": "100/minute",
        }
        
        # Burst limits for specific operations
        self.burst_limits = {
            "/api/v1/images": "5/10seconds",
            "/api/v1/inference": "3/10seconds",
        }
    
    def get_rate_limit(self, request: Request) -> str:
        """
        Get rate limit for a request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Rate limit string (e.g., "100/minute")
        """
        path = request.url.path
        
        # Check for endpoint-specific limits first
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check for pattern-based limits
        for endpoint_pattern, limit in self.endpoint_limits.items():
            if path.startswith(endpoint_pattern):
                return limit
        
        # Use role-based limits
        user_role = get_user_role(request)
        if user_role and user_role in self.default_limits:
            return self.default_limits[user_role]
        
        # Check if user is authenticated
        user_context = getattr(request.state, 'user_context', None)
        if user_context:
            return self.default_limits["authenticated"]
        
        # Default to anonymous limits
        return self.default_limits["anonymous"]
    
    def get_burst_limit(self, request: Request) -> Optional[str]:
        """
        Get burst limit for a request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Burst limit string or None
        """
        path = request.url.path
        
        for endpoint_pattern, limit in self.burst_limits.items():
            if path.startswith(endpoint_pattern):
                return limit
        
        return None


class CustomRateLimiter:
    """Custom rate limiter with enhanced features."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config = RateLimitConfig(settings)
        
        # Create base limiter
        self.limiter = Limiter(
            key_func=get_user_id_or_ip,
            default_limits=[],  # We'll set limits dynamically
            enabled=settings.rate_limit_enabled
        )
        
        # Rate limit tracking
        self._rate_limit_hits: Dict[str, int] = {}
        self._last_reset: Dict[str, float] = {}
    
    def get_limiter(self) -> Limiter:
        """Get the underlying limiter instance."""
        return self.limiter
    
    async def check_rate_limit(self, request: Request) -> None:
        """
        Check rate limit for a request.
        
        Args:
            request: FastAPI request
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        if not self.settings.rate_limit_enabled:
            return
        
        # Get rate limits
        primary_limit = self.config.get_rate_limit(request)
        burst_limit = self.config.get_burst_limit(request)
        
        # Get user identifier
        user_id = get_user_id_or_ip(request)
        
        try:
            # Check primary rate limit
            self.limiter.check_request_limit(request, primary_limit)
            
            # Check burst limit if applicable
            if burst_limit:
                self.limiter.check_request_limit(request, burst_limit)
            
            # Track successful requests
            self._track_request(user_id, request.url.path)
            
        except RateLimitExceeded as e:
            # Log rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                user_id=user_id,
                path=request.url.path,
                limit=str(e.detail),
                retry_after=e.retry_after
            )
            
            # Track rate limit hits
            self._track_rate_limit_hit(user_id)
            
            # Return appropriate error
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {primary_limit}",
                    "retry_after": e.retry_after,
                    "user_id": user_id.split(":", 1)[1] if ":" in user_id else None
                },
                headers={"Retry-After": str(e.retry_after)}
            )
    
    def _track_request(self, user_id: str, path: str) -> None:
        """Track successful request for monitoring."""
        # This could be extended to track request patterns
        pass
    
    def _track_rate_limit_hit(self, user_id: str) -> None:
        """Track rate limit hits for monitoring."""
        current_time = time.time()
        
        # Reset counters every hour
        if user_id not in self._last_reset or current_time - self._last_reset[user_id] > 3600:
            self._rate_limit_hits[user_id] = 0
            self._last_reset[user_id] = current_time
        
        self._rate_limit_hits[user_id] = self._rate_limit_hits.get(user_id, 0) + 1
        
        # Log if user is hitting rate limits frequently
        if self._rate_limit_hits[user_id] > 10:
            logger.warning(
                "Frequent rate limit violations",
                user_id=user_id,
                hits_in_hour=self._rate_limit_hits[user_id]
            )
    
    def get_rate_limit_stats(self) -> Dict[str, int]:
        """Get rate limit statistics."""
        return dict(self._rate_limit_hits)
    
    def reset_user_limits(self, user_id: str) -> None:
        """Reset rate limits for a specific user (admin function)."""
        if user_id in self._rate_limit_hits:
            del self._rate_limit_hits[user_id]
        if user_id in self._last_reset:
            del self._last_reset[user_id]
        
        logger.info("Rate limits reset for user", user_id=user_id)


# Global rate limiter instance
_rate_limiter: Optional[CustomRateLimiter] = None


def get_rate_limiter(settings: Settings) -> CustomRateLimiter:
    """Get rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = CustomRateLimiter(settings)
    return _rate_limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler."""
    user_id = get_user_id_or_ip(request)
    
    logger.warning(
        "Rate limit exceeded",
        user_id=user_id,
        path=request.url.path,
        detail=exc.detail
    )
    
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after
        },
        headers={"Retry-After": str(exc.retry_after)}
    )


# Rate limiting decorators for specific endpoints

def require_rate_limit(limit: str):
    """
    Decorator to apply specific rate limit to an endpoint.
    
    Args:
        limit: Rate limit string (e.g., "10/minute")
    """
    def decorator(func):
        # Add rate limit metadata to function
        func._rate_limit = limit
        return func
    return decorator


def require_burst_limit(limit: str):
    """
    Decorator to apply burst limit to an endpoint.
    
    Args:
        limit: Burst limit string (e.g., "5/10seconds")
    """
    def decorator(func):
        # Add burst limit metadata to function
        func._burst_limit = limit
        return func
    return decorator


# Middleware for automatic rate limiting

async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to automatically apply rate limiting.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint
        
    Returns:
        Response
    """
    # Skip rate limiting for health checks in development
    if request.url.path in ["/healthz", "/health"] and request.app.debug:
        return await call_next(request)
    
    # Get rate limiter
    settings = request.app.state.settings
    rate_limiter = get_rate_limiter(settings)
    
    # Check rate limits
    await rate_limiter.check_rate_limit(request)
    
    # Continue with request
    response = await call_next(request)
    
    # Add rate limit headers to response
    user_id = get_user_id_or_ip(request)
    limit = rate_limiter.config.get_rate_limit(request)
    
    response.headers["X-RateLimit-Limit"] = limit
    response.headers["X-RateLimit-Remaining"] = "unknown"  # Would need Redis for accurate tracking
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)  # Approximate
    
    return response
