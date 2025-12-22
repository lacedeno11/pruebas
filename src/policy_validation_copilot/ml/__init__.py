"""
Machine Learning service clients and contracts.

This module contains ML service interfaces for:
- Classification and intelligent routing (UC-OP-11)
- Anomaly detection (UC-OP-12)
- ETA prediction (UC-OP-13)

Following API contracts from Anexo B with retry logic, error handling,
mock implementations, and model versioning.
"""

from .base import (
    BaseMLServiceClient,
    MockMLServiceClient,
    MLServiceConfig,
    MLServiceError,
    MLServiceTimeoutError,
    MLServiceUnavailableError,
    MLServiceValidationError,
    MLModelVersionError,
    RetryConfig,
    MLServiceMetrics,
    CircuitBreaker,
)

from .classification import (
    ClassificationServiceClient,
    MockClassificationServiceClient,
    ClassificationRequest,
    ClassificationResponse,
    create_classification_client,
)

from .anomaly import (
    AnomalyServiceClient,
    MockAnomalyServiceClient,
    AnomalyRequest,
    AnomalyResponse,
    create_anomaly_client,
)

from .eta import (
    ETAServiceClient,
    MockETAServiceClient,
    ETARequest,
    ETAResponse,
    create_eta_client,
)

__all__ = [
    # Base classes and utilities
    "BaseMLServiceClient",
    "MockMLServiceClient",
    "MLServiceConfig",
    "MLServiceError",
    "MLServiceTimeoutError",
    "MLServiceUnavailableError",
    "MLServiceValidationError",
    "MLModelVersionError",
    "RetryConfig",
    "MLServiceMetrics",
    "CircuitBreaker",
    
    # Classification service (UC-OP-11)
    "ClassificationServiceClient",
    "MockClassificationServiceClient",
    "ClassificationRequest",
    "ClassificationResponse",
    "create_classification_client",
    
    # Anomaly detection service (UC-OP-12)
    "AnomalyServiceClient",
    "MockAnomalyServiceClient",
    "AnomalyRequest",
    "AnomalyResponse",
    "create_anomaly_client",
    
    # ETA prediction service (UC-OP-13)
    "ETAServiceClient",
    "MockETAServiceClient",
    "ETARequest",
    "ETAResponse",
    "create_eta_client",
]

