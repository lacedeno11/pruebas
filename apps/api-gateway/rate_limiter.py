"""
DERCAS-ONCO-XAI V1 - Rate Limiter

Rate limiting functionality using Redis for the API Gateway.
"""

import asyncio
import logging
import time
from typing import Optional

import redis.asyncio as redis
from fastapi import HTTPException, status

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.errors import ErrorCode, create_http_exception

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter for API requests."""
    
    def __init__(
        self,
        redis_url: str,
        default_rate_limit: int = 100,
        image_upload_rate_limit: int = 10,
        window_size: int = 60  # 1 minute window
    ):
        self.redis_url = redis_url
        self.default_rate_limit = default_rate_limit
        self.image_upload_rate_limit = image_upload_rate_limit
        self.window_size = window_size
        self.redis_client: Optional[redis.Redis] = None
        
        logger.info(
            f"Initialized rate limiter: default={default_rate_limit}/min, "
            f"image_upload={image_upload_rate_limit}/min"
        )
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self.redis_client.ping()
                logger.info("Connected to Redis for rate limiting")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                # Fallback to in-memory rate limiting (not recommended for production)
                raise
        
        return self.redis_client
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Closed Redis connection")
    
    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit key (usually user ID or IP)
            limit: Rate limit (requests per minute), uses default if None
            correlation_id: Request correlation ID for logging
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        if limit is None:
            limit = self.default_rate_limit
        
        try:
            redis_client = await self._get_redis_client()
            current_time = int(time.time())
            window_start = current_time - self.window_size
            
            # Use sliding window rate limiting with Redis sorted sets
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window_size + 1)
            
            results = await pipe.execute()
            current_count = results[1]  # Count after removing old entries
            
            if current_count >= limit:
                logger.warning(
                    f"Rate limit exceeded for key {key}: {current_count}/{limit}",
                    extra={"correlation_id": correlation_id}
                )
                
                raise create_http_exception(
                    error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    message=f"Rate limit exceeded: {current_count}/{limit} requests per minute",
                    correlation_id=correlation_id
                )
            
            logger.debug(
                f"Rate limit check passed for key {key}: {current_count}/{limit}",
                extra={"correlation_id": correlation_id}
            )
            
        except redis.RedisError as e:
            logger.error(
                f"Redis error during rate limiting: {e}",
                extra={"correlation_id": correlation_id}
            )
            # In case of Redis failure, allow the request but log the error
            # In production, you might want to implement a fallback strategy
            pass
        except HTTPException:
            # Re-raise HTTP exceptions (rate limit exceeded)
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during rate limiting: {e}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            # Allow request to proceed on unexpected errors
            pass
    
    async def get_rate_limit_status(self, key: str, limit: Optional[int] = None) -> dict:
        """
        Get current rate limit status for a key.
        
        Args:
            key: Rate limit key
            limit: Rate limit to check against
            
        Returns:
            dict: Rate limit status information
        """
        if limit is None:
            limit = self.default_rate_limit
        
        try:
            redis_client = await self._get_redis_client()
            current_time = int(time.time())
            window_start = current_time - self.window_size
            
            # Remove old entries and count current
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()
            
            current_count = results[1]
            remaining = max(0, limit - current_count)
            
            # Get time until window resets (oldest entry + window size)
            oldest_entries = await redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_time = int(oldest_entries[0][1])
                reset_time = oldest_time + self.window_size
            else:
                reset_time = current_time + self.window_size
            
            return {
                "limit": limit,
                "remaining": remaining,
                "used": current_count,
                "reset_time": reset_time,
                "window_size": self.window_size
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {
                "limit": limit,
                "remaining": limit,
                "used": 0,
                "reset_time": int(time.time()) + self.window_size,
                "window_size": self.window_size
            }
    
    async def reset_rate_limit(self, key: str):
        """Reset rate limit for a specific key."""
        try:
            redis_client = await self._get_redis_client()
            await redis_client.delete(key)
            logger.info(f"Reset rate limit for key: {key}")
        except Exception as e:
            logger.error(f"Error resetting rate limit for key {key}: {e}")
    
    async def health_check(self) -> bool:
        """Check if Redis is available for rate limiting."""
        try:
            redis_client = await self._get_redis_client()
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Rate limiter health check failed: {e}")
            return False


class InMemoryRateLimiter:
    """
    Fallback in-memory rate limiter.
    
    Note: This is not suitable for production with multiple instances,
    but can be used as a fallback when Redis is unavailable.
    """
    
    def __init__(
        self,
        default_rate_limit: int = 100,
        image_upload_rate_limit: int = 10,
        window_size: int = 60
    ):
        self.default_rate_limit = default_rate_limit
        self.image_upload_rate_limit = image_upload_rate_limit
        self.window_size = window_size
        self.requests = {}  # key -> list of timestamps
        self._cleanup_task = None
        
        logger.warning("Using in-memory rate limiter - not suitable for production")
    
    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        correlation_id: Optional[str] = None
    ):
        """Check rate limit using in-memory storage."""
        if limit is None:
            limit = self.default_rate_limit
        
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Clean up old entries for this key
        if key in self.requests:
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if timestamp > window_start
            ]
        else:
            self.requests[key] = []
        
        # Check limit
        current_count = len(self.requests[key])
        if current_count >= limit:
            logger.warning(
                f"Rate limit exceeded for key {key}: {current_count}/{limit}",
                extra={"correlation_id": correlation_id}
            )
            
            raise create_http_exception(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message=f"Rate limit exceeded: {current_count}/{limit} requests per minute",
                correlation_id=correlation_id
            )
        
        # Add current request
        self.requests[key].append(current_time)
        
        logger.debug(
            f"Rate limit check passed for key {key}: {current_count + 1}/{limit}",
            extra={"correlation_id": correlation_id}
        )
    
    async def get_rate_limit_status(self, key: str, limit: Optional[int] = None) -> dict:
        """Get rate limit status from in-memory storage."""
        if limit is None:
            limit = self.default_rate_limit
        
        current_time = time.time()
        window_start = current_time - self.window_size
        
        if key in self.requests:
            # Clean up old entries
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if timestamp > window_start
            ]
            current_count = len(self.requests[key])
            
            # Calculate reset time
            if self.requests[key]:
                oldest_time = min(self.requests[key])
                reset_time = oldest_time + self.window_size
            else:
                reset_time = current_time + self.window_size
        else:
            current_count = 0
            reset_time = current_time + self.window_size
        
        remaining = max(0, limit - current_count)
        
        return {
            "limit": limit,
            "remaining": remaining,
            "used": current_count,
            "reset_time": int(reset_time),
            "window_size": self.window_size
        }
    
    async def reset_rate_limit(self, key: str):
        """Reset rate limit for a key."""
        if key in self.requests:
            del self.requests[key]
            logger.info(f"Reset rate limit for key: {key}")
    
    async def close(self):
        """Cleanup method for compatibility."""
        pass
    
    async def health_check(self) -> bool:
        """Always healthy for in-memory limiter."""
        return True
    
    def _cleanup_old_entries(self):
        """Periodic cleanup of old entries."""
        current_time = time.time()
        window_start = current_time - self.window_size
        
        keys_to_remove = []
        for key, timestamps in self.requests.items():
            # Filter out old timestamps
            self.requests[key] = [
                timestamp for timestamp in timestamps
                if timestamp > window_start
            ]
            
            # Remove empty keys
            if not self.requests[key]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]


def create_rate_limiter(
    redis_url: str,
    default_rate_limit: int = 100,
    image_upload_rate_limit: int = 10,
    fallback_to_memory: bool = True
) -> RateLimiter:
    """
    Create rate limiter with Redis backend and optional in-memory fallback.
    
    Args:
        redis_url: Redis connection URL
        default_rate_limit: Default requests per minute
        image_upload_rate_limit: Image upload requests per minute
        fallback_to_memory: Whether to fallback to in-memory limiter on Redis failure
        
    Returns:
        RateLimiter: Configured rate limiter instance
    """
    try:
        return RateLimiter(
            redis_url=redis_url,
            default_rate_limit=default_rate_limit,
            image_upload_rate_limit=image_upload_rate_limit
        )
    except Exception as e:
        logger.error(f"Failed to create Redis rate limiter: {e}")
        
        if fallback_to_memory:
            logger.warning("Falling back to in-memory rate limiter")
            return InMemoryRateLimiter(
                default_rate_limit=default_rate_limit,
                image_upload_rate_limit=image_upload_rate_limit
            )
        else:
            raise
