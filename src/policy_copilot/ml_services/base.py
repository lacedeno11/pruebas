"""
Base ML Service Interface

This module defines the base interface and common components for all ML services
in the Policy Validation Copilot system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """Base exception for ML service errors"""
    pass


class MLServiceUnavailableError(MLServiceError):
    """Raised when ML service is unavailable"""
    pass


class MLModelNotFoundError(MLServiceError):
    """Raised when requested ML model is not found"""
    pass


class MLValidationError(MLServiceError):
    """Raised when ML service input validation fails"""
    pass


class BaseMLRequest(BaseModel):
    """Base request model for all ML services"""
    case_id: str = Field(..., description="Unique case identifier")
    model_version: Optional[str] = Field(None, description="Specific model version to use")
    
    class Config:
        extra = "forbid"


class BaseMLResponse(BaseModel):
    """Base response model for all ML services"""
    model_version: str = Field(..., description="Version of the model used")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    
    class Config:
        extra = "forbid"


class MLServiceHealth(BaseModel):
    """ML service health status"""
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    model_version: str
    last_check: datetime
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None


class BaseMLService(ABC):
    """
    Abstract base class for all ML services.
    
    Provides common functionality for model management, health checks,
    error handling, and fallback mechanisms.
    """
    
    def __init__(self, service_name: str, default_model_version: str = "latest"):
        self.service_name = service_name
        self.default_model_version = default_model_version
        self.is_healthy = True
        self.last_health_check = datetime.utcnow()
        self.error_count = 0
        self.max_errors = 5
        
    @abstractmethod
    async def predict(self, request: BaseMLRequest) -> BaseMLResponse:
        """
        Make a prediction using the ML service.
        
        Args:
            request: ML service request
            
        Returns:
            ML service response
            
        Raises:
            MLServiceError: If prediction fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> MLServiceHealth:
        """
        Check the health of the ML service.
        
        Returns:
            Health status of the service
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """
        Get list of available model versions.
        
        Returns:
            List of available model versions
        """
        pass
    
    async def _handle_error(self, error: Exception) -> None:
        """
        Handle ML service errors and update health status.
        
        Args:
            error: Exception that occurred
        """
        self.error_count += 1
        logger.error(f"ML service {self.service_name} error: {error}")
        
        if self.error_count >= self.max_errors:
            self.is_healthy = False
            logger.warning(f"ML service {self.service_name} marked as unhealthy after {self.error_count} errors")
    
    async def _reset_error_count(self) -> None:
        """Reset error count after successful operation"""
        if self.error_count > 0:
            self.error_count = 0
            self.is_healthy = True
            logger.info(f"ML service {self.service_name} error count reset")
    
    def _get_model_version(self, request: BaseMLRequest) -> str:
        """
        Get the model version to use for the request.
        
        Args:
            request: ML service request
            
        Returns:
            Model version to use
        """
        return request.model_version or self.default_model_version
    
    async def _validate_request(self, request: BaseMLRequest) -> None:
        """
        Validate ML service request.
        
        Args:
            request: Request to validate
            
        Raises:
            MLValidationError: If validation fails
        """
        if not request.case_id:
            raise MLValidationError("case_id is required")
        
        if request.model_version:
            available_models = await self.get_available_models()
            if request.model_version not in available_models:
                raise MLModelNotFoundError(f"Model version {request.model_version} not found")


class MockMLService(BaseMLService):
    """
    Mock ML service implementation for development and testing.
    
    Provides deterministic responses based on input patterns
    for consistent testing and development.
    """
    
    def __init__(self, service_name: str, default_model_version: str = "mock-1.0.0"):
        super().__init__(service_name, default_model_version)
        self.mock_responses = {}
        self.mock_delay_ms = 100  # Simulate processing time
    
    async def predict(self, request: BaseMLRequest) -> BaseMLResponse:
        """Mock prediction implementation"""
        await self._validate_request(request)
        
        # Simulate processing delay
        import asyncio
        await asyncio.sleep(self.mock_delay_ms / 1000)
        
        # Return mock response (to be overridden by specific services)
        return BaseMLResponse(
            model_version=self._get_model_version(request),
            processing_time_ms=self.mock_delay_ms
        )
    
    async def health_check(self) -> MLServiceHealth:
        """Mock health check implementation"""
        self.last_health_check = datetime.utcnow()
        
        return MLServiceHealth(
            service_name=self.service_name,
            status="healthy" if self.is_healthy else "unhealthy",
            model_version=self.default_model_version,
            last_check=self.last_health_check,
            response_time_ms=self.mock_delay_ms
        )
    
    async def get_available_models(self) -> List[str]:
        """Mock available models"""
        return [self.default_model_version, "mock-0.9.0", "mock-0.8.0"]
    
    def set_mock_response(self, case_id: str, response: BaseMLResponse) -> None:
        """Set mock response for specific case ID"""
        self.mock_responses[case_id] = response
    
    def get_mock_response(self, case_id: str) -> Optional[BaseMLResponse]:
        """Get mock response for specific case ID"""
        return self.mock_responses.get(case_id)


class MLServiceRegistry:
    """
    Registry for managing multiple ML services.
    
    Provides centralized access to all ML services with health monitoring
    and fallback capabilities.
    """
    
    def __init__(self):
        self._services: Dict[str, BaseMLService] = {}
        self._fallback_enabled = True
    
    def register_service(self, service_name: str, service: BaseMLService) -> None:
        """
        Register an ML service.
        
        Args:
            service_name: Name of the service
            service: ML service instance
        """
        self._services[service_name] = service
        logger.info(f"Registered ML service: {service_name}")
    
    def get_service(self, service_name: str) -> Optional[BaseMLService]:
        """
        Get an ML service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ML service instance or None if not found
        """
        return self._services.get(service_name)
    
    async def get_all_health_status(self) -> Dict[str, MLServiceHealth]:
        """
        Get health status for all registered services.
        
        Returns:
            Dictionary mapping service names to health status
        """
        health_status = {}
        
        for service_name, service in self._services.items():
            try:
                health_status[service_name] = await service.health_check()
            except Exception as e:
                health_status[service_name] = MLServiceHealth(
                    service_name=service_name,
                    status="unhealthy",
                    model_version="unknown",
                    last_check=datetime.utcnow(),
                    error_message=str(e)
                )
        
        return health_status
    
    def enable_fallback(self) -> None:
        """Enable fallback mode for degraded services"""
        self._fallback_enabled = True
    
    def disable_fallback(self) -> None:
        """Disable fallback mode"""
        self._fallback_enabled = False
    
    def is_fallback_enabled(self) -> bool:
        """Check if fallback mode is enabled"""
        return self._fallback_enabled


# Global ML service registry instance
ml_service_registry = MLServiceRegistry()
