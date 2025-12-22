"""
Policy Copilot ML Services Package

This package contains ML service interfaces and implementations:
- MLClassificationService: Request type classification and routing (UC-OP-11)
- MLAnomalyService: Anomaly detection for risk assessment (UC-OP-12)
- MLETAService: ETA prediction for SLA management (UC-OP-13)
- Base ML service interfaces and request/response models
- Mock implementations for development and testing
"""

from .base import (
    BaseMLService,
    BaseMLRequest,
    BaseMLResponse,
    MockMLService,
    MLServiceHealth,
    MLServiceRegistry,
    MLServiceError,
    MLServiceUnavailableError,
    MLModelNotFoundError,
    MLValidationError,
    ml_service_registry
)

from .classification import (
    MLClassificationService,
    MLClassificationRequest,
    MLClassificationResponse,
    MockMLClassificationService
)

from .anomaly import (
    MLAnomalyService,
    MLAnomalyRequest,
    MLAnomalyResponse,
    MockMLAnomalyService
)

from .eta import (
    MLETAService,
    MLETARequest,
    MLETAResponse,
    MockMLETAService
)

__all__ = [
    # Base classes and interfaces
    "BaseMLService",
    "BaseMLRequest", 
    "BaseMLResponse",
    "MockMLService",
    "MLServiceHealth",
    "MLServiceRegistry",
    "ml_service_registry",
    
    # Exceptions
    "MLServiceError",
    "MLServiceUnavailableError", 
    "MLModelNotFoundError",
    "MLValidationError",
    
    # Classification service (UC-OP-11)
    "MLClassificationService",
    "MLClassificationRequest",
    "MLClassificationResponse", 
    "MockMLClassificationService",
    
    # Anomaly detection service (UC-OP-12)
    "MLAnomalyService",
    "MLAnomalyRequest",
    "MLAnomalyResponse",
    "MockMLAnomalyService",
    
    # ETA prediction service (UC-OP-13)
    "MLETAService",
    "MLETARequest",
    "MLETAResponse",
    "MockMLETAService"
]


def create_ml_services(
    use_mock: bool = False,
    classification_endpoint: str = None,
    anomaly_endpoint: str = None,
    eta_endpoint: str = None
) -> MLServiceRegistry:
    """
    Factory function to create and register all ML services.
    
    Args:
        use_mock: Whether to use mock implementations
        classification_endpoint: External endpoint for classification service
        anomaly_endpoint: External endpoint for anomaly service
        eta_endpoint: External endpoint for ETA service
        
    Returns:
        Configured ML service registry
    """
    registry = MLServiceRegistry()
    
    if use_mock:
        # Register mock services for development/testing
        registry.register_service("classification", MockMLClassificationService())
        registry.register_service("anomaly", MockMLAnomalyService())
        registry.register_service("eta", MockMLETAService())
    else:
        # Register production services
        registry.register_service("classification", MLClassificationService(classification_endpoint))
        registry.register_service("anomaly", MLAnomalyService(anomaly_endpoint))
        registry.register_service("eta", MLETAService(eta_endpoint))
    
    return registry


def get_classification_service(use_mock: bool = False, endpoint: str = None) -> BaseMLService:
    """Get classification service instance"""
    if use_mock:
        return MockMLClassificationService()
    return MLClassificationService(endpoint)


def get_anomaly_service(use_mock: bool = False, endpoint: str = None) -> BaseMLService:
    """Get anomaly detection service instance"""
    if use_mock:
        return MockMLAnomalyService()
    return MLAnomalyService(endpoint)


def get_eta_service(use_mock: bool = False, endpoint: str = None) -> BaseMLService:
    """Get ETA prediction service instance"""
    if use_mock:
        return MockMLETAService()
    return MLETAService(endpoint)

