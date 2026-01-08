"""
Base classes and interfaces for ML service clients.

This module provides the foundational classes and interfaces for all ML service
implementations, including retry logic, error handling, and model versioning.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class MLServiceError(Exception):
    """Base exception for ML service errors."""
    
    def __init__(self, message: str, service_name: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.service_name = service_name
        self.error_code = error_code
        self.timestamp = datetime.utcnow()


class MLServiceTimeoutError(MLServiceError):
    """Exception raised when ML service times out."""
    pass


class MLServiceUnavailableError(MLServiceError):
    """Exception raised when ML service is unavailable."""
    pass


class MLServiceValidationError(MLServiceError):
    """Exception raised when ML service input/output validation fails."""
    pass


class MLModelVersionError(MLServiceError):
    """Exception raised when ML model version is incompatible."""
    pass


class RetryConfig(BaseModel):
    """Configuration for retry logic."""
    
    max_retries: int = Field(default=3, ge=0, le=10)
    initial_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    max_delay: float = Field(default=30.0, ge=1.0, le=300.0)
    exponential_base: float = Field(default=2.0, ge=1.1, le=5.0)
    jitter: bool = Field(default=True)


class MLServiceConfig(BaseModel):
    """Base configuration for ML services."""
    
    service_name: str
    base_url: str
    api_key: Optional[str] = None
    timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    retry_config: RetryConfig = Field(default_factory=RetryConfig)
    enable_circuit_breaker: bool = Field(default=True)
    circuit_breaker_threshold: int = Field(default=5, ge=1, le=20)
    circuit_breaker_timeout: float = Field(default=60.0, ge=10.0, le=600.0)
    model_version: Optional[str] = None
    enable_caching: bool = Field(default=True)
    cache_ttl: int = Field(default=300, ge=60, le=3600)  # 5 minutes default


class MLServiceMetrics(BaseModel):
    """Metrics for ML service performance tracking."""
    
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    retry_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    circuit_breaker_trips: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def update_success(self, response_time: float):
        """Update metrics for successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.last_request_time = datetime.utcnow()
        self.last_success_time = datetime.utcnow()
        
        # Update average response time
        if self.average_response_time == 0.0:
            self.average_response_time = response_time
        else:
            self.average_response_time = (self.average_response_time + response_time) / 2
    
    def update_failure(self, is_timeout: bool = False):
        """Update metrics for failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_request_time = datetime.utcnow()
        self.last_failure_time = datetime.utcnow()
        
        if is_timeout:
            self.timeout_requests += 1
    
    def update_retry(self):
        """Update metrics for retry attempt."""
        self.retry_requests += 1
    
    def update_circuit_breaker_trip(self):
        """Update metrics for circuit breaker trip."""
        self.circuit_breaker_trips += 1
    
    def update_cache_hit(self):
        """Update metrics for cache hit."""
        self.cache_hits += 1
    
    def update_cache_miss(self):
        """Update metrics for cache miss."""
        self.cache_misses += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class CircuitBreaker:
    """Circuit breaker implementation for ML services."""
    
    def __init__(self, threshold: int = 5, timeout: float = 60.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).total_seconds() > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
    
    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.threshold:
            self.state = "OPEN"


class BaseMLServiceClient(ABC):
    """Base class for all ML service clients."""
    
    def __init__(self, config: MLServiceConfig):
        self.config = config
        self.metrics = MLServiceMetrics(service_name=config.service_name)
        self.circuit_breaker = CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout
        ) if config.enable_circuit_breaker else None
        self._cache: Dict[str, Any] = {}
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"PolicyValidationCopilot-MLClient/1.0.0",
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        if self.config.model_version:
            headers["X-Model-Version"] = self.config.model_version
        
        return headers
    
    def _get_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        import hashlib
        import json
        
        # Create deterministic hash of request data
        request_str = json.dumps(request_data, sort_keys=True)
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if available and not expired."""
        if not self.config.enable_caching:
            return None
        
        cached_data = self._cache.get(cache_key)
        if not cached_data:
            self.metrics.update_cache_miss()
            return None
        
        # Check if cache entry is expired
        cached_time, cached_response = cached_data
        if (datetime.utcnow() - cached_time).total_seconds() > self.config.cache_ttl:
            del self._cache[cache_key]
            self.metrics.update_cache_miss()
            return None
        
        self.metrics.update_cache_hit()
        return cached_response
    
    def _cache_response(self, cache_key: str, response: Any):
        """Cache response data."""
        if self.config.enable_caching:
            self._cache[cache_key] = (datetime.utcnow(), response)
    
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        request_data: Dict[str, Any],
        response_model: Type[T]
    ) -> T:
        """Make HTTP request with retry logic."""
        if not self._client:
            raise MLServiceError("Client not initialized", self.config.service_name)
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            raise MLServiceUnavailableError(
                "Circuit breaker is open",
                self.config.service_name,
                "CIRCUIT_BREAKER_OPEN"
            )
        
        # Check cache
        cache_key = self._get_cache_key(request_data)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return response_model(**cached_response)
        
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        retry_count = 0
        last_exception = None
        
        while retry_count <= self.config.retry_config.max_retries:
            try:
                start_time = datetime.utcnow()
                
                # Make HTTP request
                if method.upper() == "POST":
                    response = await self._client.post(url, json=request_data)
                elif method.upper() == "GET":
                    response = await self._client.get(url, params=request_data)
                else:
                    raise MLServiceError(f"Unsupported HTTP method: {method}", self.config.service_name)
                
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Check response status
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Validate response
                    validated_response = response_model(**response_data)
                    
                    # Update metrics and circuit breaker
                    self.metrics.update_success(response_time)
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    
                    # Cache response
                    self._cache_response(cache_key, response_data)
                    
                    return validated_response
                
                elif response.status_code == 422:
                    # Validation error - don't retry
                    error_detail = response.json().get("detail", "Validation error")
                    raise MLServiceValidationError(
                        f"Input validation failed: {error_detail}",
                        self.config.service_name,
                        "VALIDATION_ERROR"
                    )
                
                elif response.status_code == 409:
                    # Model version conflict - don't retry
                    raise MLModelVersionError(
                        f"Model version conflict: {response.text}",
                        self.config.service_name,
                        "MODEL_VERSION_CONFLICT"
                    )
                
                else:
                    # Server error - retry
                    raise MLServiceError(
                        f"HTTP {response.status_code}: {response.text}",
                        self.config.service_name,
                        f"HTTP_{response.status_code}"
                    )
            
            except asyncio.TimeoutError:
                self.metrics.update_failure(is_timeout=True)
                last_exception = MLServiceTimeoutError(
                    f"Request timed out after {self.config.timeout}s",
                    self.config.service_name,
                    "TIMEOUT"
                )
            
            except (MLServiceValidationError, MLModelVersionError):
                # Don't retry validation or version errors
                raise
            
            except Exception as e:
                self.metrics.update_failure()
                if isinstance(e, MLServiceError):
                    last_exception = e
                else:
                    last_exception = MLServiceError(
                        f"Unexpected error: {str(e)}",
                        self.config.service_name,
                        "UNEXPECTED_ERROR"
                    )
            
            # Update circuit breaker on failure
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
                if self.circuit_breaker.state == "OPEN":
                    self.metrics.update_circuit_breaker_trip()
            
            # Check if we should retry
            if retry_count < self.config.retry_config.max_retries:
                retry_count += 1
                self.metrics.update_retry()
                
                # Calculate delay with exponential backoff and jitter
                delay = min(
                    self.config.retry_config.initial_delay * 
                    (self.config.retry_config.exponential_base ** (retry_count - 1)),
                    self.config.retry_config.max_delay
                )
                
                if self.config.retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
                
                logger.warning(
                    f"ML service request failed (attempt {retry_count}/{self.config.retry_config.max_retries}), "
                    f"retrying in {delay:.2f}s: {last_exception}"
                )
                
                await asyncio.sleep(delay)
            else:
                break
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            raise MLServiceError(
                "All retry attempts exhausted",
                self.config.service_name,
                "MAX_RETRIES_EXCEEDED"
            )
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information and version."""
        pass
    
    def get_metrics(self) -> MLServiceMetrics:
        """Get service metrics."""
        return self.metrics
    
    def reset_metrics(self):
        """Reset service metrics."""
        self.metrics = MLServiceMetrics(service_name=self.config.service_name)
    
    def clear_cache(self):
        """Clear response cache."""
        self._cache.clear()


class MockMLServiceClient(BaseMLServiceClient):
    """Mock ML service client for testing and development."""
    
    def __init__(self, config: MLServiceConfig, mock_responses: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.mock_responses = mock_responses or {}
        self.mock_delay = 0.1  # Simulate network delay
    
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        request_data: Dict[str, Any],
        response_model: Type[T]
    ) -> T:
        """Mock implementation of request with retry."""
        # Simulate network delay
        await asyncio.sleep(self.mock_delay)
        
        # Check if we have a mock response for this endpoint
        mock_response = self.mock_responses.get(endpoint)
        if not mock_response:
            raise MLServiceError(
                f"No mock response configured for endpoint: {endpoint}",
                self.config.service_name,
                "MOCK_NOT_CONFIGURED"
            )
        
        # Update metrics
        start_time = datetime.utcnow()
        response_time = self.mock_delay
        self.metrics.update_success(response_time)
        
        # Return mock response
        return response_model(**mock_response)
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "service": self.config.service_name,
            "version": "mock-1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Mock model info."""
        return {
            "model_name": f"mock-{self.config.service_name}",
            "model_version": self.config.model_version or "mock-1.0.0",
            "model_type": "mock",
            "training_date": "2024-01-01T00:00:00Z",
            "performance_metrics": {
                "accuracy": 0.95,
                "precision": 0.94,
                "recall": 0.96
            }
        }
