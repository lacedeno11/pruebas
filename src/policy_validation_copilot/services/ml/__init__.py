"""
Machine Learning service integrations.

This module contains ML service clients based on Anexo B API contracts:
- Classification service for request type and policy routing
- Anomaly detection service for risk assessment
- ETA prediction service for SLA management
- Base client with retry logic and model versioning
- Mock implementations for testing

Based on Anexo B API contracts:
- ML-CLASSIFY: {case_id, features, model_version?} → {request_type, candidate_policy_ids, route, risk_prior, probabilities, top_features, model_version}
- ML-ANOMALY: {case_id, features, aggregates, model_version?} → {anomaly_score, anomaly_flags, recommended_action, model_version}
- ML-ETA: {case_id, features, model_version?} → {eta_minutes, p50, p90?, model_version}
"""

# Base ML client
from .base import (
    BaseMLServiceClient,
    MLServiceConfig,
    MLServiceMetrics,
    CircuitBreaker,
    MLServiceError,
    MLServiceUnavailableError,
    MLServiceTimeoutError,
    MLModelNotFoundError,
    MLServiceDegradedError
)

# Classification service
from .classification import (
    ClassificationServiceClient,
    MockClassificationServiceClient
)

# Anomaly detection service
from .anomaly import (
    AnomalyServiceClient,
    MockAnomalyServiceClient
)

# ETA prediction service
from .eta import (
    ETAServiceClient,
    MockETAServiceClient
)

__all__ = [
    # Base ML client
    "BaseMLServiceClient",
    "MLServiceConfig",
    "MLServiceMetrics",
    "CircuitBreaker",
    "MLServiceError",
    "MLServiceUnavailableError",
    "MLServiceTimeoutError",
    "MLModelNotFoundError",
    "MLServiceDegradedError",
    
    # Classification service
    "ClassificationServiceClient",
    "MockClassificationServiceClient",
    
    # Anomaly detection service
    "AnomalyServiceClient",
    "MockAnomalyServiceClient",
    
    # ETA prediction service
    "ETAServiceClient",
    "MockETAServiceClient"
]

