"""
Base ML Service Components for Policy Validation Copilot

This module provides base classes and utilities for ML services including
feature engineering, model registry, drift detection, and fallback mechanisms.
"""

import logging
import pickle
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from ..models.base import ModelVersion

logger = logging.getLogger(__name__)


class FeatureEngineer(ABC):
    """Abstract base class for feature engineering."""
    
    def __init__(self):
        self.feature_cache = {}
        self.feature_stats = {}
    
    @abstractmethod
    def extract_features(self, data: Dict[str, Any]) -> Any:
        """Extract features from raw data."""
        pass
    
    def normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Normalize features using stored statistics."""
        normalized = {}
        for feature, value in features.items():
            if feature in self.feature_stats:
                mean = self.feature_stats[feature]['mean']
                std = self.feature_stats[feature]['std']
                normalized[feature] = (value - mean) / (std + 1e-8)
            else:
                normalized[feature] = value
        return normalized
    
    def update_feature_stats(self, features: Dict[str, float]) -> None:
        """Update feature statistics for normalization."""
        for feature, value in features.items():
            if feature not in self.feature_stats:
                self.feature_stats[feature] = {
                    'count': 0,
                    'sum': 0.0,
                    'sum_sq': 0.0,
                    'mean': 0.0,
                    'std': 1.0
                }
            
            stats = self.feature_stats[feature]
            stats['count'] += 1
            stats['sum'] += value
            stats['sum_sq'] += value * value
            
            # Update running mean and std
            stats['mean'] = stats['sum'] / stats['count']
            if stats['count'] > 1:
                variance = (stats['sum_sq'] - stats['sum'] * stats['mean']) / (stats['count'] - 1)
                stats['std'] = max(np.sqrt(variance), 1e-8)


class ModelRegistry:
    """Model registry for loading and managing ML models."""
    
    def __init__(self, registry_path: str = "models/"):
        self.registry_path = registry_path
        self.loaded_models = {}
        self.model_metadata = {}
    
    def load_model(self, model_name: str, version: Optional[str] = None) -> Any:
        """Load a model from the registry."""
        model_key = f"{model_name}:{version}" if version else model_name
        
        if model_key in self.loaded_models:
            return self.loaded_models[model_key]
        
        try:
            # In a real implementation, this would load from MLflow, S3, etc.
            # For now, return a mock model
            model = self._create_mock_model(model_name)
            self.loaded_models[model_key] = model
            
            # Store metadata
            self.model_metadata[model_key] = {
                'name': model_name,
                'version': version or '1.0.0',
                'loaded_at': datetime.utcnow(),
                'type': 'mock'
            }
            
            logger.info(f"Loaded model {model_key}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model {model_key}: {e}")
            raise
    
    def get_model_info(self, model_name: str, version: Optional[str] = None) -> ModelVersion:
        """Get model version information."""
        model_key = f"{model_name}:{version}" if version else model_name
        
        if model_key in self.model_metadata:
            metadata = self.model_metadata[model_key]
            return ModelVersion(
                name=metadata['name'],
                version=metadata['version'],
                trained_at=metadata.get('trained_at', datetime(2024, 1, 1)),
                metrics=metadata.get('metrics', {}),
                features_used=metadata.get('features_used', [])
            )
        
        # Return default version info
        return ModelVersion(
            name=model_name,
            version=version or '1.0.0',
            trained_at=datetime(2024, 1, 1),
            metrics={},
            features_used=[]
        )
    
    def register_model(
        self,
        model_name: str,
        model: Any,
        version: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Register a new model in the registry."""
        model_key = f"{model_name}:{version}"
        self.loaded_models[model_key] = model
        self.model_metadata[model_key] = {
            'name': model_name,
            'version': version,
            'loaded_at': datetime.utcnow(),
            **metadata
        }
        logger.info(f"Registered model {model_key}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        return list(self.model_metadata.values())
    
    def _create_mock_model(self, model_name: str) -> Any:
        """Create a mock model for testing/development."""
        return f"mock_{model_name}_model"


class DriftDetector:
    """Model drift detection service."""
    
    def __init__(self, window_size: int = 1000, drift_threshold: float = 0.1):
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        self.reference_data = []
        self.current_data = []
        self.drift_history = []
    
    def add_reference_data(self, features: Dict[str, float]) -> None:
        """Add reference data for drift comparison."""
        self.reference_data.append(features)
        if len(self.reference_data) > self.window_size:
            self.reference_data.pop(0)
    
    def detect_drift(self, features: Dict[str, float]) -> Tuple[bool, float]:
        """Detect drift in current features compared to reference."""
        self.current_data.append(features)
        if len(self.current_data) > self.window_size:
            self.current_data.pop(0)
        
        if len(self.reference_data) < 100 or len(self.current_data) < 100:
            return False, 0.0
        
        # Calculate drift score using statistical distance
        drift_score = self._calculate_drift_score()
        
        # Record drift measurement
        self.drift_history.append({
            'timestamp': datetime.utcnow(),
            'drift_score': drift_score,
            'drift_detected': drift_score > self.drift_threshold
        })
        
        return drift_score > self.drift_threshold, drift_score
    
    def _calculate_drift_score(self) -> float:
        """Calculate drift score between reference and current data."""
        if not self.reference_data or not self.current_data:
            return 0.0
        
        # Get common features
        ref_features = set(self.reference_data[0].keys())
        curr_features = set(self.current_data[0].keys())
        common_features = ref_features.intersection(curr_features)
        
        if not common_features:
            return 1.0  # Maximum drift if no common features
        
        total_drift = 0.0
        
        for feature in common_features:
            # Calculate feature statistics
            ref_values = [d[feature] for d in self.reference_data if feature in d]
            curr_values = [d[feature] for d in self.current_data if feature in d]
            
            if not ref_values or not curr_values:
                continue
            
            # Calculate statistical distance (simplified KL divergence approximation)
            ref_mean = np.mean(ref_values)
            ref_std = np.std(ref_values) + 1e-8
            curr_mean = np.mean(curr_values)
            curr_std = np.std(curr_values) + 1e-8
            
            # Normalized difference in means
            mean_diff = abs(ref_mean - curr_mean) / (ref_std + curr_std)
            
            # Ratio of standard deviations
            std_ratio = max(ref_std / curr_std, curr_std / ref_std)
            
            # Combined drift score for this feature
            feature_drift = (mean_diff + np.log(std_ratio)) / 2
            total_drift += feature_drift
        
        # Average drift across all features
        return total_drift / len(common_features) if common_features else 0.0
    
    def get_drift_report(self) -> Dict[str, Any]:
        """Get drift detection report."""
        if not self.drift_history:
            return {'status': 'no_data'}
        
        recent_drift = self.drift_history[-10:]  # Last 10 measurements
        avg_drift = np.mean([d['drift_score'] for d in recent_drift])
        drift_trend = 'increasing' if len(recent_drift) > 1 and recent_drift[-1]['drift_score'] > recent_drift[0]['drift_score'] else 'stable'
        
        return {
            'status': 'active',
            'current_drift_score': self.drift_history[-1]['drift_score'],
            'average_drift_score': avg_drift,
            'drift_threshold': self.drift_threshold,
            'drift_detected': self.drift_history[-1]['drift_detected'],
            'drift_trend': drift_trend,
            'measurements_count': len(self.drift_history),
            'reference_data_size': len(self.reference_data),
            'current_data_size': len(self.current_data)
        }


class FallbackMechanism:
    """Fallback mechanism for ML service failures."""
    
    def __init__(self):
        self.fallback_rules = {}
        self.failure_counts = {}
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.circuit_breakers = {}
    
    def register_fallback(self, service_name: str, fallback_func: callable) -> None:
        """Register a fallback function for a service."""
        self.fallback_rules[service_name] = fallback_func
        self.failure_counts[service_name] = 0
    
    def should_use_fallback(self, service_name: str) -> bool:
        """Check if fallback should be used based on circuit breaker."""
        if service_name not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[service_name]
        if breaker['state'] == 'open':
            # Check if timeout has passed
            if datetime.utcnow().timestamp() - breaker['opened_at'] > self.circuit_breaker_timeout:
                breaker['state'] = 'half_open'
                return False
            return True
        
        return False
    
    def record_success(self, service_name: str) -> None:
        """Record successful service call."""
        self.failure_counts[service_name] = 0
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name]['state'] = 'closed'
    
    def record_failure(self, service_name: str) -> None:
        """Record failed service call."""
        self.failure_counts[service_name] = self.failure_counts.get(service_name, 0) + 1
        
        if self.failure_counts[service_name] >= self.circuit_breaker_threshold:
            self.circuit_breakers[service_name] = {
                'state': 'open',
                'opened_at': datetime.utcnow().timestamp()
            }
            logger.warning(f"Circuit breaker opened for service {service_name}")
    
    def execute_with_fallback(self, service_name: str, primary_func: callable, *args, **kwargs) -> Any:
        """Execute function with fallback mechanism."""
        if self.should_use_fallback(service_name):
            logger.info(f"Using fallback for service {service_name}")
            return self.fallback_rules[service_name](*args, **kwargs)
        
        try:
            result = primary_func(*args, **kwargs)
            self.record_success(service_name)
            return result
        except Exception as e:
            logger.error(f"Service {service_name} failed: {e}")
            self.record_failure(service_name)
            
            if service_name in self.fallback_rules:
                logger.info(f"Executing fallback for service {service_name}")
                return self.fallback_rules[service_name](*args, **kwargs)
            else:
                raise


class BaseMLService(ABC):
    """Abstract base class for ML services."""
    
    def __init__(self):
        self.drift_detector = DriftDetector()
        self.fallback_mechanism = FallbackMechanism()
        self.performance_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_latency_ms': 0.0,
            'last_request_time': None
        }
    
    def update_performance_metrics(self, latency_ms: int, success: bool) -> None:
        """Update service performance metrics."""
        self.performance_metrics['total_requests'] += 1
        self.performance_metrics['last_request_time'] = datetime.utcnow()
        
        if success:
            self.performance_metrics['successful_requests'] += 1
        else:
            self.performance_metrics['failed_requests'] += 1
        
        # Update average latency (exponential moving average)
        alpha = 0.1
        current_avg = self.performance_metrics['average_latency_ms']
        self.performance_metrics['average_latency_ms'] = (
            alpha * latency_ms + (1 - alpha) * current_avg
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        total = self.performance_metrics['total_requests']
        success_rate = (
            self.performance_metrics['successful_requests'] / total
            if total > 0 else 1.0
        )
        
        # Determine health status
        if success_rate >= 0.95:
            status = 'healthy'
        elif success_rate >= 0.8:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'success_rate': success_rate,
            'total_requests': total,
            'average_latency_ms': self.performance_metrics['average_latency_ms'],
            'last_request_time': self.performance_metrics['last_request_time'],
            'drift_report': self.drift_detector.get_drift_report()
        }
    
    @abstractmethod
    def predict(self, *args, **kwargs) -> Any:
        """Make prediction using the ML service."""
        pass


class MLServiceConfig(BaseModel):
    """Base configuration for ML services."""
    
    # Model settings
    model_name: str = Field(..., description="Primary model name")
    model_version: Optional[str] = Field(None, description="Model version")
    fallback_model: Optional[str] = Field(None, description="Fallback model name")
    
    # Performance settings
    max_inference_time_ms: int = Field(5000, description="Maximum inference time in milliseconds")
    batch_size: int = Field(32, description="Batch size for predictions")
    
    # Drift detection
    enable_drift_detection: bool = Field(True, description="Enable drift detection")
    drift_threshold: float = Field(0.1, description="Drift detection threshold")
    drift_window_size: int = Field(1000, description="Window size for drift detection")
    
    # Fallback settings
    enable_fallback: bool = Field(True, description="Enable fallback mechanisms")
    circuit_breaker_threshold: int = Field(5, description="Circuit breaker failure threshold")
    circuit_breaker_timeout: int = Field(300, description="Circuit breaker timeout in seconds")
    
    # Feature engineering
    enable_feature_caching: bool = Field(True, description="Enable feature caching")
    feature_cache_ttl: int = Field(3600, description="Feature cache TTL in seconds")
    
    # Monitoring
    enable_performance_monitoring: bool = Field(True, description="Enable performance monitoring")
    log_predictions: bool = Field(False, description="Log all predictions for debugging")


# Utility functions
def validate_features(features: Dict[str, Any], required_features: List[str]) -> Tuple[bool, List[str]]:
    """Validate that required features are present."""
    missing_features = [f for f in required_features if f not in features]
    return len(missing_features) == 0, missing_features


def normalize_numerical_features(features: Dict[str, float], feature_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    """Normalize numerical features to [0, 1] range."""
    normalized = {}
    for feature, value in features.items():
        if feature in feature_ranges:
            min_val, max_val = feature_ranges[feature]
            normalized[feature] = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.0
        else:
            normalized[feature] = value
    return normalized


def calculate_feature_importance(features: Dict[str, float], weights: Dict[str, float]) -> List[Dict[str, float]]:
    """Calculate feature importance scores."""
    importance_scores = []
    total_weight = sum(weights.values())
    
    for feature, value in features.items():
        weight = weights.get(feature, 0.0)
        importance = (weight / total_weight) * abs(value) if total_weight > 0 else 0.0
        importance_scores.append({
            'feature': feature,
            'importance': importance
        })
    
    # Sort by importance
    importance_scores.sort(key=lambda x: x['importance'], reverse=True)
    return importance_scores
