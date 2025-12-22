"""
Base ML service client with common functionality.

This module provides the base client implementation for all ML services including:
- HTTP client with retry logic and timeout handling
- Model versioning and drift monitoring
- Health checking and service discovery
- Error handling and fallback mechanisms
- Metrics collection and performance monitoring
- Authentication and security controls
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, Generic
from uuid import UUID, uuid4

import aiohttp
import backoff
from pydantic import BaseModel, Field, validator

from ...models.ml import (
    MLServiceType, ModelStatus, MLModelInfo, MLServiceHealth, DriftMetrics
)


logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class MLServiceError(Exception):
    """Base exception for ML service errors."""
    pass


class MLServiceUnavailableError(MLServiceError):
    """Raised when ML service is unavailable."""
    pass


class MLServiceTimeoutError(MLServiceError):
    """Raised when ML service request times out."""
    pass


class MLModelNotFoundError(MLServiceError):
    """Raised when requested model is not found."""
    pass


class MLServiceDegradedError(MLServiceError):
    """Raised when ML service is in degraded state."""
    pass


class MLServiceConfig(BaseModel):
    """Configuration for ML service client."""
    service_name: str = Field(..., description="Name of the ML service")
    base_url: str = Field(..., description="Base URL for the ML service")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    
    # Timeout configuration
    request_timeout: float = Field(default=30.0, ge=1.0, description="Request timeout in seconds")
    connect_timeout: float = Field(default=10.0, ge=1.0, description="Connection timeout in seconds")
    
    # Retry configuration
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of retries")
    retry_backoff_factor: float = Field(default=2.0, ge=1.0, description="Backoff factor for retries")
    retry_max_delay: float = Field(default=60.0, ge=1.0, description="Maximum retry delay")
    
    # Health check configuration
    health_check_interval: int = Field(default=60, ge=10, description="Health check interval in seconds")
    health_check_timeout: float = Field(default=5.0, ge=1.0, description="Health check timeout")
    
    # Model versioning
    default_model_version: Optional[str] = Field(None, description="Default model version")
    model_version_header: str = Field(default="X-Model-Version", description="Header for model version")
    
    # Drift monitoring
    drift_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Drift detection threshold")
    drift_check_interval: int = Field(default=300, ge=60, description="Drift check interval in seconds")
    
    # Circuit breaker
    circuit_breaker_enabled: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_threshold: int = Field(default=5, ge=1, description="Circuit breaker failure threshold")
    circuit_breaker_timeout: int = Field(default=60, ge=10, description="Circuit breaker timeout in seconds")


class MLServiceMetrics(BaseModel):
    """Metrics for ML service performance."""
    service_name: str = Field(..., description="Service name")
    
    # Request metrics
    total_requests: int = Field(default=0, ge=0, description="Total requests made")
    successful_requests: int = Field(default=0, ge=0, description="Successful requests")
    failed_requests: int = Field(default=0, ge=0, description="Failed requests")
    timeout_requests: int = Field(default=0, ge=0, description="Timed out requests")
    
    # Performance metrics
    avg_response_time_ms: float = Field(default=0.0, ge=0.0, description="Average response time")
    p95_response_time_ms: float = Field(default=0.0, ge=0.0, description="95th percentile response time")
    p99_response_time_ms: float = Field(default=0.0, ge=0.0, description="99th percentile response time")
    
    # Error metrics
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Error rate")
    timeout_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Timeout rate")
    
    # Circuit breaker metrics
    circuit_breaker_open: bool = Field(default=False, description="Circuit breaker status")
    circuit_breaker_failures: int = Field(default=0, ge=0, description="Circuit breaker failures")
    
    # Timestamps
    last_request_at: Optional[datetime] = Field(None, description="Last request timestamp")
    last_success_at: Optional[datetime] = Field(None, description="Last successful request")
    last_failure_at: Optional[datetime] = Field(None, description="Last failure timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CircuitBreaker:
    """Circuit breaker implementation for ML service resilience."""
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise MLServiceUnavailableError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout
    
    def _on_success(self):
        """Handle successful request."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.threshold:
            self.state = "OPEN"


class BaseMLServiceClient(ABC, Generic[T]):
    """
    Base ML service client with common functionality.
    
    Provides common functionality for all ML service clients including:
    - HTTP client with retry logic
    - Model versioning and health checking
    - Metrics collection and monitoring
    - Circuit breaker pattern
    - Drift monitoring
    """
    
    def __init__(self, config: MLServiceConfig):
        """
        Initialize ML service client.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics = MLServiceMetrics(service_name=config.service_name)
        self.circuit_breaker = CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout
        ) if config.circuit_breaker_enabled else None
        
        # Model tracking
        self.current_model_info: Optional[MLModelInfo] = None
        self.drift_metrics: List[DriftMetrics] = []
        self.last_health_check: Optional[datetime] = None
        self.service_health: Optional[MLServiceHealth] = None
        
        # Performance tracking
        self.response_times: List[float] = []
        self.max_response_times = 1000  # Keep last 1000 response times
        
        logger.info(f"Initialized ML service client for {config.service_name}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self):
        """Start the ML service client."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(
                total=self.config.request_timeout,
                connect=self.config.connect_timeout
            )
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"PolicyValidationCopilot-MLClient/{self.config.service_name}"
            }
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
            
            # Perform initial health check
            await self.health_check()
            
            logger.info(f"Started ML service client for {self.config.service_name}")

    async def stop(self):
        """Stop the ML service client."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info(f"Stopped ML service client for {self.config.service_name}")

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to ML service with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            model_version: Specific model version to use
            
        Returns:
            Response data
            
        Raises:
            MLServiceError: If request fails
        """
        if not self.session:
            await self.start()
        
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Add model version header if specified
        headers = {}
        if model_version:
            headers[self.config.model_version_header] = model_version
        elif self.config.default_model_version:
            headers[self.config.model_version_header] = self.config.default_model_version
        
        start_time = time.time()
        
        try:
            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.last_request_at = datetime.utcnow()
            
            # Use circuit breaker if enabled
            if self.circuit_breaker:
                response = await self.circuit_breaker.call(
                    self._execute_request, method, url, data, params, headers
                )
            else:
                response = await self._execute_request(method, url, data, params, headers)
            
            # Record successful request
            response_time = (time.time() - start_time) * 1000
            self._record_response_time(response_time)
            
            self.metrics.successful_requests += 1
            self.metrics.last_success_at = datetime.utcnow()
            
            return response
            
        except asyncio.TimeoutError as e:
            self.metrics.timeout_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.last_failure_at = datetime.utcnow()
            logger.error(f"Request timeout for {self.config.service_name}: {e}")
            raise MLServiceTimeoutError(f"Request timeout: {e}")
            
        except aiohttp.ClientError as e:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_at = datetime.utcnow()
            logger.error(f"Request failed for {self.config.service_name}: {e}")
            raise MLServiceError(f"Request failed: {e}")
            
        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_at = datetime.utcnow()
            logger.error(f"Unexpected error for {self.config.service_name}: {e}")
            raise MLServiceError(f"Unexpected error: {e}")

    async def _execute_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute the actual HTTP request."""
        async with self.session.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=headers
        ) as response:
            if response.status >= 400:
                error_text = await response.text()
                if response.status == 404:
                    raise MLModelNotFoundError(f"Model not found: {error_text}")
                elif response.status >= 500:
                    raise MLServiceUnavailableError(f"Service unavailable: {error_text}")
                else:
                    raise MLServiceError(f"Request failed with status {response.status}: {error_text}")
            
            return await response.json()

    def _record_response_time(self, response_time_ms: float):
        """Record response time for metrics calculation."""
        self.response_times.append(response_time_ms)
        
        # Keep only recent response times
        if len(self.response_times) > self.max_response_times:
            self.response_times = self.response_times[-self.max_response_times:]
        
        # Update metrics
        if self.response_times:
            self.metrics.avg_response_time_ms = sum(self.response_times) / len(self.response_times)
            sorted_times = sorted(self.response_times)
            self.metrics.p95_response_time_ms = sorted_times[int(len(sorted_times) * 0.95)]
            self.metrics.p99_response_time_ms = sorted_times[int(len(sorted_times) * 0.99)]
        
        # Update error rates
        total = self.metrics.total_requests
        if total > 0:
            self.metrics.error_rate = self.metrics.failed_requests / total
            self.metrics.timeout_rate = self.metrics.timeout_requests / total

    async def health_check(self) -> MLServiceHealth:
        """
        Perform health check on ML service.
        
        Returns:
            Service health status
        """
        try:
            start_time = time.time()
            response = await self._make_request("GET", "/health")
            response_time = (time.time() - start_time) * 1000
            
            self.service_health = MLServiceHealth(
                service_name=self.config.service_name,
                status=ModelStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow(),
                version=response.get("version", "unknown"),
                models_available=response.get("models", []),
                error_message=None
            )
            
            self.last_health_check = datetime.utcnow()
            logger.debug(f"Health check successful for {self.config.service_name}")
            
        except Exception as e:
            self.service_health = MLServiceHealth(
                service_name=self.config.service_name,
                status=ModelStatus.UNHEALTHY,
                response_time_ms=None,
                last_check=datetime.utcnow(),
                version=None,
                models_available=[],
                error_message=str(e)
            )
            
            logger.error(f"Health check failed for {self.config.service_name}: {e}")
        
        return self.service_health

    async def get_model_info(self, model_version: Optional[str] = None) -> MLModelInfo:
        """
        Get information about the ML model.
        
        Args:
            model_version: Specific model version
            
        Returns:
            Model information
        """
        try:
            params = {}
            if model_version:
                params["version"] = model_version
            
            response = await self._make_request("GET", "/model/info", params=params)
            
            self.current_model_info = MLModelInfo(
                model_id=response["model_id"],
                model_version=response["version"],
                model_type=self.get_service_type(),
                training_date=datetime.fromisoformat(response["training_date"]),
                deployment_date=datetime.fromisoformat(response["deployment_date"]),
                performance_metrics=response.get("performance_metrics", {}),
                feature_schema=response.get("feature_schema", {}),
                status=ModelStatus(response.get("status", "HEALTHY"))
            )
            
            return self.current_model_info
            
        except Exception as e:
            logger.error(f"Failed to get model info for {self.config.service_name}: {e}")
            raise MLServiceError(f"Failed to get model info: {e}")

    async def check_drift(self, features: Dict[str, Any]) -> DriftMetrics:
        """
        Check for model drift using current features.
        
        Args:
            features: Feature vector to check for drift
            
        Returns:
            Drift metrics
        """
        try:
            data = {"features": features}
            response = await self._make_request("POST", "/model/drift", data=data)
            
            drift_metrics = DriftMetrics(
                model_version=response["model_version"],
                drift_score=response["drift_score"],
                drift_threshold=self.config.drift_threshold,
                drift_detected=response["drift_score"] > self.config.drift_threshold,
                feature_drift=response.get("feature_drift", {}),
                timestamp=datetime.utcnow(),
                recommendation=response.get("recommendation", "")
            )
            
            self.drift_metrics.append(drift_metrics)
            
            # Keep only recent drift metrics
            if len(self.drift_metrics) > 100:
                self.drift_metrics = self.drift_metrics[-50:]
            
            if drift_metrics.drift_detected:
                logger.warning(
                    f"Drift detected for {self.config.service_name}: "
                    f"score={drift_metrics.drift_score:.3f}, "
                    f"threshold={self.config.drift_threshold:.3f}"
                )
            
            return drift_metrics
            
        except Exception as e:
            logger.error(f"Failed to check drift for {self.config.service_name}: {e}")
            # Return default drift metrics on error
            return DriftMetrics(
                model_version=self.config.default_model_version or "unknown",
                drift_score=0.0,
                drift_threshold=self.config.drift_threshold,
                drift_detected=False,
                feature_drift={},
                timestamp=datetime.utcnow(),
                recommendation="Drift check failed"
            )

    def get_metrics(self) -> MLServiceMetrics:
        """Get current service metrics."""
        # Update circuit breaker metrics
        if self.circuit_breaker:
            self.metrics.circuit_breaker_open = self.circuit_breaker.state == "OPEN"
            self.metrics.circuit_breaker_failures = self.circuit_breaker.failure_count
        
        return self.metrics

    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        if not self.service_health:
            return False
        
        # Check if health check is recent
        if self.last_health_check:
            age = datetime.utcnow() - self.last_health_check
            if age.total_seconds() > self.config.health_check_interval * 2:
                return False
        
        return self.service_health.status == ModelStatus.HEALTHY

    def is_degraded(self) -> bool:
        """Check if service is in degraded state."""
        # Check error rate
        if self.metrics.error_rate > 0.1:  # 10% error rate
            return True
        
        # Check response time
        if self.metrics.p95_response_time_ms > self.config.request_timeout * 1000 * 0.8:
            return True
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.state != "CLOSED":
            return True
        
        return False

    @abstractmethod
    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        pass

    @abstractmethod
    async def predict(self, request: BaseModel, **kwargs) -> T:
        """Make prediction request."""
        pass

    async def batch_predict(self, requests: List[BaseModel], **kwargs) -> List[T]:
        """
        Make batch prediction requests.
        
        Args:
            requests: List of prediction requests
            **kwargs: Additional arguments
            
        Returns:
            List of prediction responses
        """
        # Default implementation - can be overridden for optimized batch processing
        results = []
        for request in requests:
            try:
                result = await self.predict(request, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch prediction failed for request: {e}")
                # Add None or error result - specific implementation can handle this
                results.append(None)
        
        return results

    async def warmup(self) -> bool:
        """
        Warm up the ML service.
        
        Returns:
            True if warmup successful
        """
        try:
            await self.health_check()
            await self.get_model_info()
            return self.is_healthy()
        except Exception as e:
            logger.error(f"Warmup failed for {self.config.service_name}: {e}")
            return False


__all__ = [
    "BaseMLServiceClient",
    "MLServiceConfig",
    "MLServiceMetrics",
    "CircuitBreaker",
    "MLServiceError",
    "MLServiceUnavailableError",
    "MLServiceTimeoutError",
    "MLModelNotFoundError",
    "MLServiceDegradedError"
]
