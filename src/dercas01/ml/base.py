"""
Base ML Service Classes and Utilities for DERCAS 01 Policy Validation Copilot

Provides abstract base classes, common utilities, and shared functionality
for all ML services in the system.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ..models.api import MLServiceError, MLServiceHealth
from ..models.enums import MLDegradationLevel, MLModelType

logger = logging.getLogger(__name__)


class MLConfig(BaseModel):
    """Base configuration for ML services."""
    
    model_type: MLModelType
    model_id: str
    model_version: str = "1.0.0"
    
    # Performance settings
    timeout_seconds: float = 30.0
    max_retries: int = 3
    batch_size: int = 32
    
    # Fallback settings
    enable_fallback: bool = True
    fallback_confidence: float = 0.5
    
    # Quality thresholds
    min_confidence_threshold: float = 0.1
    max_drift_threshold: float = 0.8
    
    # Model paths and endpoints
    model_path: Optional[str] = None
    model_endpoint: Optional[str] = None
    
    # Feature configuration
    required_features: List[str] = Field(default_factory=list)
    optional_features: List[str] = Field(default_factory=list)
    
    # Monitoring
    enable_monitoring: bool = True
    log_predictions: bool = True
    
    class Config:
        use_enum_values = True


class MLMetrics(BaseModel):
    """ML service performance metrics."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_requests: int = 0
    
    avg_response_time_ms: float = 0.0
    avg_confidence: float = 0.0
    avg_drift_score: float = 0.0
    
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    
    def update_success(self, response_time_ms: float, confidence: float, drift_score: Optional[float] = None):
        """Update metrics for successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        
        # Update averages
        self.avg_response_time_ms = self._update_average(
            self.avg_response_time_ms, response_time_ms, self.successful_requests
        )
        self.avg_confidence = self._update_average(
            self.avg_confidence, confidence, self.successful_requests
        )
        
        if drift_score is not None:
            self.avg_drift_score = self._update_average(
                self.avg_drift_score, drift_score, self.successful_requests
            )
        
        self.last_request_time = datetime.utcnow()
        self.last_success_time = datetime.utcnow()
    
    def update_failure(self, is_fallback: bool = False):
        """Update metrics for failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        
        if is_fallback:
            self.fallback_requests += 1
        
        self.last_request_time = datetime.utcnow()
        self.last_failure_time = datetime.utcnow()
    
    def _update_average(self, current_avg: float, new_value: float, count: int) -> float:
        """Update running average."""
        if count == 1:
            return new_value
        return ((current_avg * (count - 1)) + new_value) / count
    
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
    
    @property
    def fallback_rate(self) -> float:
        """Calculate fallback rate."""
        if self.total_requests == 0:
            return 0.0
        return self.fallback_requests / self.total_requests


class FeatureValidator:
    """Validates and preprocesses features for ML models."""
    
    def __init__(self, required_features: List[str], optional_features: List[str] = None):
        self.required_features = set(required_features)
        self.optional_features = set(optional_features or [])
        self.all_features = self.required_features | self.optional_features
    
    def validate_features(self, features: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate feature completeness.
        
        Returns:
            Tuple of (is_valid, missing_features)
        """
        missing_features = []
        
        for feature in self.required_features:
            if feature not in features or features[feature] is None:
                missing_features.append(feature)
        
        is_valid = len(missing_features) == 0
        return is_valid, missing_features
    
    def preprocess_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess and clean features.
        
        Args:
            features: Raw feature dictionary
            
        Returns:
            Preprocessed features
        """
        processed = {}
        
        for feature_name in self.all_features:
            if feature_name in features:
                value = features[feature_name]
                processed[feature_name] = self._clean_feature_value(value)
        
        return processed
    
    def _clean_feature_value(self, value: Any) -> Any:
        """Clean individual feature value."""
        if value is None:
            return None
        
        # Handle numeric values
        if isinstance(value, (int, float)):
            if np.isnan(value) or np.isinf(value):
                return None
            return float(value)
        
        # Handle string values
        if isinstance(value, str):
            value = value.strip()
            if value == "" or value.lower() in ["null", "none", "nan"]:
                return None
            return value
        
        # Handle boolean values
        if isinstance(value, bool):
            return value
        
        # Handle lists/arrays
        if isinstance(value, (list, tuple)):
            return [self._clean_feature_value(v) for v in value]
        
        # Handle dictionaries
        if isinstance(value, dict):
            return {k: self._clean_feature_value(v) for k, v in value.items()}
        
        return value
    
    def get_feature_summary(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of feature completeness."""
        is_valid, missing_features = self.validate_features(features)
        
        present_required = len(self.required_features) - len(missing_features)
        present_optional = len([f for f in self.optional_features if f in features and features[f] is not None])
        
        return {
            "is_valid": is_valid,
            "missing_features": missing_features,
            "required_features_present": present_required,
            "required_features_total": len(self.required_features),
            "optional_features_present": present_optional,
            "optional_features_total": len(self.optional_features),
            "completeness_score": present_required / len(self.required_features) if self.required_features else 1.0,
        }


class DriftDetector:
    """Detects data drift in ML features."""
    
    def __init__(self, reference_stats: Optional[Dict[str, Any]] = None):
        self.reference_stats = reference_stats or {}
    
    def calculate_drift_score(self, features: Dict[str, Any]) -> float:
        """
        Calculate drift score for features.
        
        Returns:
            Drift score between 0.0 (no drift) and 1.0 (maximum drift)
        """
        if not self.reference_stats:
            return 0.0  # No reference to compare against
        
        drift_scores = []
        
        for feature_name, value in features.items():
            if feature_name in self.reference_stats:
                feature_drift = self._calculate_feature_drift(
                    feature_name, value, self.reference_stats[feature_name]
                )
                drift_scores.append(feature_drift)
        
        if not drift_scores:
            return 0.0
        
        # Return average drift score
        return sum(drift_scores) / len(drift_scores)
    
    def _calculate_feature_drift(self, feature_name: str, value: Any, reference_stats: Dict[str, Any]) -> float:
        """Calculate drift for a single feature."""
        try:
            if isinstance(value, (int, float)) and not np.isnan(value):
                # Numeric feature drift
                ref_mean = reference_stats.get("mean", 0.0)
                ref_std = reference_stats.get("std", 1.0)
                
                if ref_std == 0:
                    return 0.0 if value == ref_mean else 1.0
                
                # Z-score based drift
                z_score = abs((value - ref_mean) / ref_std)
                return min(z_score / 3.0, 1.0)  # Normalize to [0, 1]
            
            elif isinstance(value, str):
                # Categorical feature drift
                ref_categories = set(reference_stats.get("categories", []))
                if not ref_categories:
                    return 0.0
                
                return 0.0 if value in ref_categories else 1.0
            
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Error calculating drift for feature {feature_name}: {e}")
            return 0.0
    
    def update_reference_stats(self, features_batch: List[Dict[str, Any]]):
        """Update reference statistics from a batch of features."""
        if not features_batch:
            return
        
        # Convert to DataFrame for easier statistics calculation
        df = pd.DataFrame(features_batch)
        
        for column in df.columns:
            if df[column].dtype in ['int64', 'float64']:
                # Numeric feature
                self.reference_stats[column] = {
                    "mean": float(df[column].mean()),
                    "std": float(df[column].std()),
                    "min": float(df[column].min()),
                    "max": float(df[column].max()),
                }
            else:
                # Categorical feature
                self.reference_stats[column] = {
                    "categories": df[column].unique().tolist(),
                    "value_counts": df[column].value_counts().to_dict(),
                }


class MLServiceBase(ABC):
    """Abstract base class for all ML services."""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.metrics = MLMetrics()
        self.feature_validator = FeatureValidator(
            required_features=config.required_features,
            optional_features=config.optional_features
        )
        self.drift_detector = DriftDetector()
        self.degradation_level = MLDegradationLevel.NORMAL
        self._model = None
        self._last_health_check = None
    
    @abstractmethod
    def _load_model(self) -> Any:
        """Load the ML model. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make prediction with the model. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_fallback_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback prediction when model fails. Must be implemented by subclasses."""
        pass
    
    def predict(self, case_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make prediction with error handling and monitoring.
        
        Args:
            case_id: Case identifier
            features: Feature dictionary
            
        Returns:
            Prediction result with metadata
        """
        start_time = time.time()
        
        try:
            # Validate features
            is_valid, missing_features = self.feature_validator.validate_features(features)
            if not is_valid:
                raise ValueError(f"Missing required features: {missing_features}")
            
            # Preprocess features
            processed_features = self.feature_validator.preprocess_features(features)
            
            # Calculate drift score
            drift_score = self.drift_detector.calculate_drift_score(processed_features)
            
            # Check if we should use fallback due to high drift
            if drift_score > self.config.max_drift_threshold:
                logger.warning(f"High drift detected ({drift_score:.3f}), using fallback for case {case_id}")
                return self._handle_fallback_prediction(case_id, processed_features, "high_drift")
            
            # Load model if not already loaded
            if self._model is None:
                self._model = self._load_model()
            
            # Make prediction
            prediction = self._predict(processed_features)
            
            # Add metadata
            processing_time_ms = (time.time() - start_time) * 1000
            result = {
                **prediction,
                "case_id": case_id,
                "model_version": self.config.model_version,
                "processing_time_ms": processing_time_ms,
                "drift_score": drift_score,
                "fallback_used": False,
                "inference_timestamp": datetime.utcnow(),
            }
            
            # Update metrics
            confidence = prediction.get("confidence", 0.0)
            self.metrics.update_success(processing_time_ms, confidence, drift_score)
            
            # Log prediction if enabled
            if self.config.log_predictions:
                logger.info(f"Prediction for case {case_id}: confidence={confidence:.3f}, drift={drift_score:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for case {case_id}: {e}")
            
            if self.config.enable_fallback:
                return self._handle_fallback_prediction(case_id, features, str(e))
            else:
                self.metrics.update_failure()
                raise
    
    def _handle_fallback_prediction(self, case_id: str, features: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Handle fallback prediction."""
        try:
            start_time = time.time()
            
            fallback_prediction = self._get_fallback_prediction(features)
            processing_time_ms = (time.time() - start_time) * 1000
            
            result = {
                **fallback_prediction,
                "case_id": case_id,
                "model_version": f"{self.config.model_version}-fallback",
                "processing_time_ms": processing_time_ms,
                "drift_score": None,
                "fallback_used": True,
                "fallback_reason": reason,
                "inference_timestamp": datetime.utcnow(),
                "confidence": self.config.fallback_confidence,
            }
            
            self.metrics.update_failure(is_fallback=True)
            
            logger.warning(f"Fallback prediction for case {case_id}: reason={reason}")
            return result
            
        except Exception as e:
            logger.error(f"Fallback prediction failed for case {case_id}: {e}")
            self.metrics.update_failure()
            raise
    
    def health_check(self) -> MLServiceHealth:
        """Perform health check on the ML service."""
        try:
            # Basic health metrics
            health = MLServiceHealth(
                service_name=f"{self.config.model_type.value}_service",
                status="healthy",
                model_version=self.config.model_version,
                last_updated=datetime.utcnow(),
                avg_response_time_ms=self.metrics.avg_response_time_ms,
                requests_per_minute=self._calculate_requests_per_minute(),
                error_rate=self.metrics.failure_rate,
                model_accuracy=None,  # Would need validation data
                drift_score=self.metrics.avg_drift_score,
            )
            
            # Determine status based on metrics
            if self.metrics.failure_rate > 0.5:
                health.status = "unhealthy"
                self.degradation_level = MLDegradationLevel.FAILED
            elif self.metrics.failure_rate > 0.2 or self.metrics.avg_drift_score > 0.7:
                health.status = "degraded"
                self.degradation_level = MLDegradationLevel.DEGRADED
            else:
                self.degradation_level = MLDegradationLevel.NORMAL
            
            self._last_health_check = datetime.utcnow()
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return MLServiceHealth(
                service_name=f"{self.config.model_type.value}_service",
                status="unhealthy",
                model_version=self.config.model_version,
                last_updated=datetime.utcnow(),
                avg_response_time_ms=0.0,
                requests_per_minute=0.0,
                error_rate=1.0,
            )
    
    def _calculate_requests_per_minute(self) -> float:
        """Calculate requests per minute based on recent activity."""
        if not self.metrics.last_request_time:
            return 0.0
        
        # Simple approximation - would need more sophisticated tracking in production
        time_diff = (datetime.utcnow() - self.metrics.last_request_time).total_seconds()
        if time_diff > 60:
            return 0.0
        
        return self.metrics.total_requests / max(time_diff / 60, 1.0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "model_type": self.config.model_type.value,
            "model_version": self.config.model_version,
            "degradation_level": self.degradation_level.value,
            "metrics": self.metrics.dict(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
        }
    
    def reset_metrics(self):
        """Reset service metrics."""
        self.metrics = MLMetrics()
    
    def update_drift_reference(self, features_batch: List[Dict[str, Any]]):
        """Update drift detection reference statistics."""
        self.drift_detector.update_reference_stats(features_batch)


# Utility functions

def create_ml_error(error_code: str, error_message: str, correlation_id: Optional[str] = None) -> MLServiceError:
    """Create standardized ML service error."""
    return MLServiceError(
        error_code=error_code,
        error_message=error_message,
        correlation_id=correlation_id,
    )


def validate_model_version(version: str) -> bool:
    """Validate model version format."""
    try:
        parts = version.split(".")
        return len(parts) >= 2 and all(part.isdigit() for part in parts[:2])
    except Exception:
        return False


def calculate_confidence_score(raw_scores: Dict[str, float], method: str = "max") -> float:
    """
    Calculate confidence score from raw model outputs.
    
    Args:
        raw_scores: Dictionary of raw scores
        method: Method to calculate confidence ("max", "entropy", "margin")
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not raw_scores:
        return 0.0
    
    scores = list(raw_scores.values())
    
    if method == "max":
        return max(scores)
    
    elif method == "entropy":
        # Calculate entropy-based confidence
        scores_array = np.array(scores)
        scores_array = scores_array / scores_array.sum()  # Normalize
        entropy = -np.sum(scores_array * np.log(scores_array + 1e-10))
        max_entropy = np.log(len(scores))
        return 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0
    
    elif method == "margin":
        # Calculate margin-based confidence
        sorted_scores = sorted(scores, reverse=True)
        if len(sorted_scores) >= 2:
            return sorted_scores[0] - sorted_scores[1]
        else:
            return sorted_scores[0] if sorted_scores else 0.0
    
    else:
        raise ValueError(f"Unknown confidence calculation method: {method}")


def normalize_features(features: Dict[str, Any], feature_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
    """
    Normalize numeric features to [0, 1] range.
    
    Args:
        features: Feature dictionary
        feature_ranges: Dictionary of (min, max) ranges for each feature
        
    Returns:
        Normalized features
    """
    normalized = features.copy()
    
    for feature_name, (min_val, max_val) in feature_ranges.items():
        if feature_name in features and isinstance(features[feature_name], (int, float)):
            value = features[feature_name]
            if max_val > min_val:
                normalized[feature_name] = (value - min_val) / (max_val - min_val)
            else:
                normalized[feature_name] = 0.0
    
    return normalized


def extract_top_features(feature_importance: Dict[str, float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Extract top K most important features.
    
    Args:
        feature_importance: Dictionary of feature importance scores
        top_k: Number of top features to return
        
    Returns:
        List of top features with names and importance scores
    """
    sorted_features = sorted(
        feature_importance.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return [
        {"feature_name": name, "importance": importance}
        for name, importance in sorted_features[:top_k]
    ]
