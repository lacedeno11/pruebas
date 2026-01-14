"""
Machine Learning Services for Policy Validation Copilot

This module implements UC-OP-11/12/13 with ML services for classification/routing,
anomaly detection/pattern analysis, and ETA prediction with feature engineering,
model registry integration, fallback mechanisms, drift detection, and model
versioning per Anexo B API contracts.
"""

# Base ML service components
from .base import (
    BaseMLService,
    FeatureEngineer,
    ModelRegistry,
    DriftDetector,
    FallbackMechanism,
    MLServiceConfig,
    validate_features,
    normalize_numerical_features,
    calculate_feature_importance
)

# Classification service (UC-OP-11)
from .classification import (
    ClassificationService,
    ClassificationConfig,
    ClassificationFeatures,
    ClassificationFeatureEngineer,
    create_classification_service
)

# Anomaly detection service (UC-OP-12)
from .anomaly import (
    AnomalyDetectionService,
    AnomalyConfig,
    AnomalyFeatures,
    AnomalyFeatureEngineer,
    create_anomaly_service
)

# ETA prediction service (UC-OP-13)
from .eta import (
    ETAPredictionService,
    ETAConfig,
    ETAFeatures,
    ETAFeatureEngineer,
    create_eta_service
)

# ML service orchestrator
class MLServiceOrchestrator:
    """
    Orchestrator for all ML services with unified interface.
    
    Provides a single entry point for all ML predictions with
    consistent error handling, monitoring, and fallback mechanisms.
    """
    
    def __init__(
        self,
        classification_config: ClassificationConfig = None,
        anomaly_config: AnomalyConfig = None,
        eta_config: ETAConfig = None,
        model_registry: ModelRegistry = None
    ):
        self.model_registry = model_registry or ModelRegistry()
        
        # Initialize services
        self.classification_service = ClassificationService(
            classification_config, self.model_registry
        )
        self.anomaly_service = AnomalyDetectionService(
            anomaly_config, self.model_registry
        )
        self.eta_service = ETAPredictionService(
            eta_config, self.model_registry
        )
        
        # Performance tracking
        self.service_metrics = {
            'classification': {'requests': 0, 'errors': 0, 'avg_latency': 0.0},
            'anomaly': {'requests': 0, 'errors': 0, 'avg_latency': 0.0},
            'eta': {'requests': 0, 'errors': 0, 'avg_latency': 0.0}
        }
    
    def run_all_predictions(
        self,
        case_id: str,
        features: dict,
        aggregates: dict = None,
        model_versions: dict = None
    ) -> dict:
        """
        Run all ML predictions for a case.
        
        Returns a dictionary with all ML service outputs.
        """
        results = {}
        model_versions = model_versions or {}
        aggregates = aggregates or {}
        
        try:
            # Classification
            classification_result = self.classification_service.classify(
                case_id=case_id,
                features=features,
                model_version=model_versions.get('classification')
            )
            results['classification'] = classification_result
            
            # Anomaly detection
            anomaly_result = self.anomaly_service.detect_anomaly(
                case_id=case_id,
                features=features,
                aggregates=aggregates,
                model_version=model_versions.get('anomaly')
            )
            results['anomaly'] = anomaly_result
            
            # ETA prediction
            eta_result = self.eta_service.predict_eta(
                case_id=case_id,
                features=features,
                model_version=model_versions.get('eta')
            )
            results['eta'] = eta_result
            
            return results
            
        except Exception as e:
            logger.error(f"ML orchestrator failed for case {case_id}: {e}")
            raise
    
    def get_service_health(self) -> dict:
        """Get health status of all ML services."""
        return {
            'classification': self.classification_service.get_health_status(),
            'anomaly': self.anomaly_service.get_health_status(),
            'eta': self.eta_service.get_health_status(),
            'orchestrator_metrics': self.service_metrics
        }
    
    def get_model_versions(self) -> dict:
        """Get version information for all loaded models."""
        return {
            'classification': self.classification_service._get_model_version_info(),
            'anomaly': self.anomaly_service._get_model_version_info(),
            'eta': self.eta_service._get_model_version_info()
        }


# Factory functions for easy setup
def create_ml_orchestrator(
    classification_config: ClassificationConfig = None,
    anomaly_config: AnomalyConfig = None,
    eta_config: ETAConfig = None
) -> MLServiceOrchestrator:
    """Create an ML service orchestrator with all services."""
    return MLServiceOrchestrator(
        classification_config=classification_config,
        anomaly_config=anomaly_config,
        eta_config=eta_config
    )


def setup_ml_services(config_dict: dict = None) -> dict:
    """
    Setup all ML services with configuration.
    
    Returns a dictionary with all ML service instances.
    """
    config_dict = config_dict or {}
    
    # Create model registry
    model_registry = ModelRegistry()
    
    # Create services
    classification_service = create_classification_service(
        config_dict.get('classification_config')
    )
    anomaly_service = create_anomaly_service(
        config_dict.get('anomaly_config')
    )
    eta_service = create_eta_service(
        config_dict.get('eta_config')
    )
    
    # Create orchestrator
    orchestrator = MLServiceOrchestrator(
        classification_config=config_dict.get('classification_config'),
        anomaly_config=config_dict.get('anomaly_config'),
        eta_config=config_dict.get('eta_config'),
        model_registry=model_registry
    )
    
    return {
        'classification_service': classification_service,
        'anomaly_service': anomaly_service,
        'eta_service': eta_service,
        'orchestrator': orchestrator,
        'model_registry': model_registry
    }


def get_ml_service_status() -> dict:
    """Get status of all ML services."""
    # Create temporary orchestrator for status check
    orchestrator = create_ml_orchestrator()
    return orchestrator.get_service_health()


# Convenience functions for individual predictions
def classify_case(case_id: str, features: dict, model_version: str = None):
    """Convenience function for case classification."""
    service = create_classification_service()
    return service.classify(case_id, features, model_version)


def detect_anomaly(case_id: str, features: dict, aggregates: dict = None, model_version: str = None):
    """Convenience function for anomaly detection."""
    service = create_anomaly_service()
    return service.detect_anomaly(case_id, features, aggregates or {}, model_version)


def predict_eta(case_id: str, features: dict, model_version: str = None):
    """Convenience function for ETA prediction."""
    service = create_eta_service()
    return service.predict_eta(case_id, features, model_version)


__all__ = [
    # Base components
    'BaseMLService',
    'FeatureEngineer',
    'ModelRegistry',
    'DriftDetector',
    'FallbackMechanism',
    'MLServiceConfig',
    'validate_features',
    'normalize_numerical_features',
    'calculate_feature_importance',
    
    # Classification service (UC-OP-11)
    'ClassificationService',
    'ClassificationConfig',
    'ClassificationFeatures',
    'ClassificationFeatureEngineer',
    'create_classification_service',
    
    # Anomaly detection service (UC-OP-12)
    'AnomalyDetectionService',
    'AnomalyConfig',
    'AnomalyFeatures',
    'AnomalyFeatureEngineer',
    'create_anomaly_service',
    
    # ETA prediction service (UC-OP-13)
    'ETAPredictionService',
    'ETAConfig',
    'ETAFeatures',
    'ETAFeatureEngineer',
    'create_eta_service',
    
    # Orchestration and setup
    'MLServiceOrchestrator',
    'create_ml_orchestrator',
    'setup_ml_services',
    'get_ml_service_status',
    
    # Convenience functions
    'classify_case',
    'detect_anomaly',
    'predict_eta'
]

