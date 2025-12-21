"""
Feature Store for DERCAS 01 Policy Validation Copilot

Provides feature engineering, storage, and retrieval capabilities for ML services.
Supports feature computation, caching, versioning, and monitoring.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ..models.entities import Case
from ..models.enums import MLModelType
from ..storage.repositories import RepositoryManager

logger = logging.getLogger(__name__)


class FeatureConfig(BaseModel):
    """Configuration for feature engineering."""
    
    # Feature computation settings
    cache_ttl_hours: int = 24
    batch_size: int = 1000
    max_lookback_days: int = 365
    
    # Aggregation windows
    aggregation_windows: List[int] = [1, 7, 30, 90]  # days
    
    # Feature categories
    case_features: List[str] = [
        "priority", "service_amount", "patient_age", "service_code",
        "insurer_id", "plan_id", "provider_id"
    ]
    
    temporal_features: List[str] = [
        "hour_of_day", "day_of_week", "month_of_year", "is_weekend",
        "is_holiday", "quarter", "days_since_epoch"
    ]
    
    aggregation_features: List[str] = [
        "provider_service_count", "customer_claim_count", "insurer_volume",
        "avg_service_amount", "service_frequency", "provider_diversity"
    ]
    
    derived_features: List[str] = [
        "amount_zscore", "frequency_score", "complexity_score",
        "risk_score", "novelty_score"
    ]
    
    # Feature validation
    enable_validation: bool = True
    outlier_threshold: float = 3.0
    missing_value_threshold: float = 0.1


class FeatureMetadata(BaseModel):
    """Metadata for a feature."""
    
    feature_name: str
    feature_type: str  # numeric, categorical, boolean, datetime
    description: str
    computation_method: str
    dependencies: List[str] = Field(default_factory=list)
    
    # Statistics
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    null_percentage: Optional[float] = None
    unique_count: Optional[int] = None
    
    # Versioning
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    drift_score: Optional[float] = None
    importance_score: Optional[float] = None


class FeatureVector(BaseModel):
    """A computed feature vector for a case."""
    
    case_id: str
    feature_set_version: str
    features: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    computation_time_ms: Optional[float] = None
    
    # Quality indicators
    completeness_score: float = 0.0
    quality_flags: List[str] = Field(default_factory=list)
    
    def get_feature_hash(self) -> str:
        """Get hash of feature values for caching."""
        feature_str = json.dumps(self.features, sort_keys=True, default=str)
        return hashlib.md5(feature_str.encode()).hexdigest()


class FeatureStore:
    """
    Feature store for ML feature engineering and storage.
    
    Provides:
    - Feature computation and caching
    - Feature versioning and metadata
    - Aggregation and derived features
    - Feature quality monitoring
    """
    
    def __init__(self, config: FeatureConfig, repo_manager: RepositoryManager):
        self.config = config
        self.repo_manager = repo_manager
        
        # Feature cache
        self.feature_cache: Dict[str, FeatureVector] = {}
        self.metadata_cache: Dict[str, FeatureMetadata] = {}
        
        # Feature computation functions
        self.feature_functions = self._initialize_feature_functions()
        
        # Statistics for normalization and validation
        self.feature_stats: Dict[str, Dict[str, float]] = {}
    
    def _initialize_feature_functions(self) -> Dict[str, callable]:
        """Initialize feature computation functions."""
        return {
            # Case features
            "priority_encoded": self._compute_priority_encoded,
            "service_amount_normalized": self._compute_service_amount_normalized,
            "patient_age_binned": self._compute_patient_age_binned,
            
            # Temporal features
            "hour_of_day": self._compute_hour_of_day,
            "day_of_week": self._compute_day_of_week,
            "is_weekend": self._compute_is_weekend,
            "is_holiday": self._compute_is_holiday,
            "quarter": self._compute_quarter,
            "days_since_epoch": self._compute_days_since_epoch,
            
            # Aggregation features
            "provider_service_count_7d": lambda case_data: self._compute_provider_service_count(case_data, 7),
            "provider_service_count_30d": lambda case_data: self._compute_provider_service_count(case_data, 30),
            "customer_claim_count_30d": lambda case_data: self._compute_customer_claim_count(case_data, 30),
            "customer_claim_count_90d": lambda case_data: self._compute_customer_claim_count(case_data, 90),
            "avg_service_amount_30d": lambda case_data: self._compute_avg_service_amount(case_data, 30),
            "service_frequency_30d": lambda case_data: self._compute_service_frequency(case_data, 30),
            
            # Derived features
            "amount_zscore": self._compute_amount_zscore,
            "frequency_score": self._compute_frequency_score,
            "complexity_score": self._compute_complexity_score,
            "risk_score": self._compute_risk_score,
            "novelty_score": self._compute_novelty_score,
        }
    
    def compute_features(
        self, 
        case_data: Dict[str, Any], 
        feature_set: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> FeatureVector:
        """
        Compute features for a case.
        
        Args:
            case_data: Case data dictionary
            feature_set: Specific features to compute (None for all)
            use_cache: Whether to use cached features
            
        Returns:
            FeatureVector with computed features
        """
        try:
            case_id = case_data.get('case_id', str(uuid4()))
            
            # Check cache first
            if use_cache and case_id in self.feature_cache:
                cached_features = self.feature_cache[case_id]
                cache_age = (datetime.utcnow() - cached_features.computed_at).total_seconds() / 3600
                
                if cache_age < self.config.cache_ttl_hours:
                    logger.debug(f"Using cached features for case {case_id}")
                    return cached_features
            
            start_time = datetime.utcnow()
            
            # Determine features to compute
            if feature_set is None:
                feature_set = list(self.feature_functions.keys())
            
            # Compute features
            computed_features = {}
            quality_flags = []
            
            for feature_name in feature_set:
                try:
                    if feature_name in self.feature_functions:
                        feature_value = self.feature_functions[feature_name](case_data)
                        computed_features[feature_name] = feature_value
                        
                        # Validate feature
                        if self.config.enable_validation:
                            validation_flags = self._validate_feature(feature_name, feature_value)
                            quality_flags.extend(validation_flags)
                    else:
                        logger.warning(f"Unknown feature: {feature_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to compute feature {feature_name}: {e}")
                    computed_features[feature_name] = None
                    quality_flags.append(f"computation_failed_{feature_name}")
            
            # Calculate completeness score
            completeness_score = self._calculate_completeness_score(computed_features)
            
            # Create feature vector
            computation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            feature_vector = FeatureVector(
                case_id=case_id,
                feature_set_version="1.0.0",
                features=computed_features,
                metadata={
                    "source_data_keys": list(case_data.keys()),
                    "computation_method": "batch",
                    "feature_count": len(computed_features),
                },
                computation_time_ms=computation_time,
                completeness_score=completeness_score,
                quality_flags=quality_flags,
            )
            
            # Cache the result
            if use_cache:
                self.feature_cache[case_id] = feature_vector
            
            logger.info(f"Computed {len(computed_features)} features for case {case_id}")
            return feature_vector
            
        except Exception as e:
            logger.error(f"Feature computation failed for case {case_data.get('case_id', 'unknown')}: {e}")
            raise
    
    def batch_compute_features(
        self, 
        cases_data: List[Dict[str, Any]], 
        feature_set: Optional[List[str]] = None
    ) -> List[FeatureVector]:
        """
        Compute features for multiple cases in batch.
        
        Args:
            cases_data: List of case data dictionaries
            feature_set: Specific features to compute
            
        Returns:
            List of FeatureVector objects
        """
        try:
            logger.info(f"Batch computing features for {len(cases_data)} cases")
            
            feature_vectors = []
            
            # Process in batches
            for i in range(0, len(cases_data), self.config.batch_size):
                batch = cases_data[i:i + self.config.batch_size]
                
                for case_data in batch:
                    try:
                        feature_vector = self.compute_features(case_data, feature_set, use_cache=False)
                        feature_vectors.append(feature_vector)
                    except Exception as e:
                        logger.error(f"Failed to compute features for case {case_data.get('case_id')}: {e}")
                        continue
                
                logger.info(f"Processed batch {i // self.config.batch_size + 1}")
            
            # Update feature statistics
            self._update_feature_statistics(feature_vectors)
            
            return feature_vectors
            
        except Exception as e:
            logger.error(f"Batch feature computation failed: {e}")
            raise
    
    def get_feature_metadata(self, feature_name: str) -> Optional[FeatureMetadata]:
        """Get metadata for a specific feature."""
        return self.metadata_cache.get(feature_name)
    
    def update_feature_metadata(self, metadata: FeatureMetadata):
        """Update metadata for a feature."""
        metadata.updated_at = datetime.utcnow()
        self.metadata_cache[metadata.feature_name] = metadata
    
    def get_feature_statistics(self, feature_name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a feature."""
        return self.feature_stats.get(feature_name)
    
    def _calculate_completeness_score(self, features: Dict[str, Any]) -> float:
        """Calculate completeness score for features."""
        if not features:
            return 0.0
        
        non_null_count = sum(1 for value in features.values() if value is not None)
        return non_null_count / len(features)
    
    def _validate_feature(self, feature_name: str, feature_value: Any) -> List[str]:
        """Validate a computed feature value."""
        flags = []
        
        try:
            # Check for null values
            if feature_value is None:
                flags.append(f"null_value_{feature_name}")
                return flags
            
            # Check for numeric features
            if isinstance(feature_value, (int, float)):
                # Check for infinite or NaN values
                if np.isnan(feature_value) or np.isinf(feature_value):
                    flags.append(f"invalid_numeric_{feature_name}")
                
                # Check for outliers
                if feature_name in self.feature_stats:
                    stats = self.feature_stats[feature_name]
                    mean = stats.get('mean', 0)
                    std = stats.get('std', 1)
                    
                    if std > 0:
                        z_score = abs((feature_value - mean) / std)
                        if z_score > self.config.outlier_threshold:
                            flags.append(f"outlier_{feature_name}")
            
            # Check for categorical features
            elif isinstance(feature_value, str):
                if len(feature_value) == 0:
                    flags.append(f"empty_string_{feature_name}")
                elif len(feature_value) > 1000:  # Suspiciously long string
                    flags.append(f"long_string_{feature_name}")
            
        except Exception as e:
            logger.warning(f"Feature validation failed for {feature_name}: {e}")
            flags.append(f"validation_error_{feature_name}")
        
        return flags
    
    def _update_feature_statistics(self, feature_vectors: List[FeatureVector]):
        """Update feature statistics from a batch of feature vectors."""
        try:
            # Collect all feature values
            feature_data = {}
            
            for fv in feature_vectors:
                for feature_name, value in fv.features.items():
                    if feature_name not in feature_data:
                        feature_data[feature_name] = []
                    
                    if value is not None and isinstance(value, (int, float)):
                        feature_data[feature_name].append(value)
            
            # Calculate statistics
            for feature_name, values in feature_data.items():
                if values:
                    values_array = np.array(values)
                    
                    self.feature_stats[feature_name] = {
                        'mean': float(np.mean(values_array)),
                        'std': float(np.std(values_array)),
                        'min': float(np.min(values_array)),
                        'max': float(np.max(values_array)),
                        'median': float(np.median(values_array)),
                        'count': len(values),
                    }
            
        except Exception as e:
            logger.warning(f"Failed to update feature statistics: {e}")
    
    # Feature computation functions
    
    def _compute_priority_encoded(self, case_data: Dict[str, Any]) -> float:
        """Encode priority as numeric value."""
        priority_mapping = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        priority = case_data.get('priority', 'MEDIUM')
        return float(priority_mapping.get(priority, 2))
    
    def _compute_service_amount_normalized(self, case_data: Dict[str, Any]) -> float:
        """Normalize service amount using log transformation."""
        amount = case_data.get('service_amount', 0)
        if amount <= 0:
            return 0.0
        return float(np.log1p(amount))  # log(1 + amount)
    
    def _compute_patient_age_binned(self, case_data: Dict[str, Any]) -> float:
        """Bin patient age into categories."""
        age = case_data.get('patient_age', 0)
        
        if age < 18:
            return 1.0  # Minor
        elif age < 30:
            return 2.0  # Young adult
        elif age < 50:
            return 3.0  # Adult
        elif age < 65:
            return 4.0  # Middle-aged
        else:
            return 5.0  # Senior
    
    def _compute_hour_of_day(self, case_data: Dict[str, Any]) -> float:
        """Extract hour of day from service date."""
        service_date = case_data.get('service_date')
        if service_date:
            if isinstance(service_date, str):
                service_date = pd.to_datetime(service_date)
            return float(service_date.hour)
        return 12.0  # Default to noon
    
    def _compute_day_of_week(self, case_data: Dict[str, Any]) -> float:
        """Extract day of week from service date."""
        service_date = case_data.get('service_date')
        if service_date:
            if isinstance(service_date, str):
                service_date = pd.to_datetime(service_date)
            return float(service_date.dayofweek + 1)  # 1-7
        return 1.0  # Default to Monday
    
    def _compute_is_weekend(self, case_data: Dict[str, Any]) -> float:
        """Check if service date is on weekend."""
        service_date = case_data.get('service_date')
        if service_date:
            if isinstance(service_date, str):
                service_date = pd.to_datetime(service_date)
            return float(service_date.dayofweek >= 5)  # Saturday or Sunday
        return 0.0
    
    def _compute_is_holiday(self, case_data: Dict[str, Any]) -> float:
        """Check if service date is a holiday (simplified)."""
        # In production, this would use a holiday calendar
        service_date = case_data.get('service_date')
        if service_date:
            if isinstance(service_date, str):
                service_date = pd.to_datetime(service_date)
            
            # Simple check for major holidays
            if (service_date.month == 12 and service_date.day == 25) or \
               (service_date.month == 1 and service_date.day == 1) or \
               (service_date.month == 7 and service_date.day == 4):
                return 1.0
        
        return 0.0
    
    def _compute_quarter(self, case_data: Dict[str, Any]) -> float:
        """Extract quarter from service date."""
        service_date = case_data.get('service_date')
        if service_date:
            if isinstance(service_date, str):
                service_date = pd.to_datetime(service_date)
            return float(service_date.quarter)
        return 1.0  # Default to Q1
    
    def _compute_days_since_epoch(self, case_data: Dict[str, Any]) -> float:
        """Compute days since epoch for service date."""
        service_date = case_data.get('service_date')
        if service_date:
            if isinstance(service_date, str):
                service_date = pd.to_datetime(service_date)
            epoch = pd.to_datetime('1970-01-01')
            return float((service_date - epoch).days)
        return 0.0
    
    def _compute_provider_service_count(self, case_data: Dict[str, Any], window_days: int) -> float:
        """Compute provider service count in time window."""
        try:
            provider_id = case_data.get('provider_id')
            if not provider_id:
                return 0.0
            
            # Query historical data (simplified - would use repository in production)
            # For now, return a simulated value
            base_count = hash(provider_id) % 100
            window_factor = window_days / 30.0
            return float(base_count * window_factor)
            
        except Exception as e:
            logger.warning(f"Failed to compute provider service count: {e}")
            return 0.0
    
    def _compute_customer_claim_count(self, case_data: Dict[str, Any], window_days: int) -> float:
        """Compute customer claim count in time window."""
        try:
            customer_id = case_data.get('customer_id')
            if not customer_id:
                return 0.0
            
            # Query historical data (simplified)
            base_count = hash(customer_id) % 20
            window_factor = window_days / 30.0
            return float(base_count * window_factor)
            
        except Exception as e:
            logger.warning(f"Failed to compute customer claim count: {e}")
            return 0.0
    
    def _compute_avg_service_amount(self, case_data: Dict[str, Any], window_days: int) -> float:
        """Compute average service amount in time window."""
        try:
            customer_id = case_data.get('customer_id')
            if not customer_id:
                return 0.0
            
            # Query historical data (simplified)
            base_amount = (hash(customer_id) % 1000) + 500
            return float(base_amount)
            
        except Exception as e:
            logger.warning(f"Failed to compute average service amount: {e}")
            return 0.0
    
    def _compute_service_frequency(self, case_data: Dict[str, Any], window_days: int) -> float:
        """Compute service frequency score."""
        try:
            claim_count = self._compute_customer_claim_count(case_data, window_days)
            if window_days > 0:
                return float(claim_count / window_days * 30)  # Claims per month
            return 0.0
            
        except Exception as e:
            logger.warning(f"Failed to compute service frequency: {e}")
            return 0.0
    
    def _compute_amount_zscore(self, case_data: Dict[str, Any]) -> float:
        """Compute z-score for service amount."""
        try:
            amount = case_data.get('service_amount', 0)
            avg_amount = self._compute_avg_service_amount(case_data, 30)
            
            if avg_amount > 0:
                # Simplified z-score calculation
                std_amount = avg_amount * 0.5  # Assume 50% std
                return float((amount - avg_amount) / std_amount)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Failed to compute amount z-score: {e}")
            return 0.0
    
    def _compute_frequency_score(self, case_data: Dict[str, Any]) -> float:
        """Compute frequency anomaly score."""
        try:
            frequency_30d = self._compute_service_frequency(case_data, 30)
            
            # Score based on frequency (higher frequency = higher score)
            if frequency_30d > 10:
                return 1.0  # Very high frequency
            elif frequency_30d > 5:
                return 0.7  # High frequency
            elif frequency_30d > 2:
                return 0.4  # Medium frequency
            else:
                return 0.1  # Low frequency
                
        except Exception as e:
            logger.warning(f"Failed to compute frequency score: {e}")
            return 0.0
    
    def _compute_complexity_score(self, case_data: Dict[str, Any]) -> float:
        """Compute case complexity score."""
        try:
            complexity_factors = []
            
            # Service amount factor
            amount = case_data.get('service_amount', 0)
            if amount > 5000:
                complexity_factors.append(0.3)
            elif amount > 1000:
                complexity_factors.append(0.1)
            
            # Attachments factor
            attachments = case_data.get('attachments', [])
            if len(attachments) > 5:
                complexity_factors.append(0.2)
            elif len(attachments) > 2:
                complexity_factors.append(0.1)
            
            # Service code complexity (simplified)
            service_code = case_data.get('service_code', '')
            if 'COMPLEX' in service_code.upper():
                complexity_factors.append(0.4)
            
            return min(sum(complexity_factors), 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to compute complexity score: {e}")
            return 0.5
    
    def _compute_risk_score(self, case_data: Dict[str, Any]) -> float:
        """Compute risk score based on multiple factors."""
        try:
            risk_factors = []
            
            # Amount risk
            amount_zscore = abs(self._compute_amount_zscore(case_data))
            if amount_zscore > 2:
                risk_factors.append(0.4)
            elif amount_zscore > 1:
                risk_factors.append(0.2)
            
            # Frequency risk
            frequency_score = self._compute_frequency_score(case_data)
            if frequency_score > 0.7:
                risk_factors.append(0.3)
            
            # Temporal risk (off-hours)
            hour = self._compute_hour_of_day(case_data)
            if hour < 6 or hour > 22:
                risk_factors.append(0.2)
            
            # Weekend risk
            if self._compute_is_weekend(case_data) > 0:
                risk_factors.append(0.1)
            
            return min(sum(risk_factors), 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to compute risk score: {e}")
            return 0.0
    
    def _compute_novelty_score(self, case_data: Dict[str, Any]) -> float:
        """Compute novelty score for new patterns."""
        try:
            novelty_factors = []
            
            # New provider
            provider_count = self._compute_provider_service_count(case_data, 90)
            if provider_count < 5:
                novelty_factors.append(0.3)
            
            # Unusual service code for customer
            # (simplified - would need historical analysis)
            service_code = case_data.get('service_code', '')
            if len(service_code) > 0:
                novelty_factors.append(0.1)
            
            # Geographic novelty (placeholder)
            # Would need location data and historical patterns
            
            return min(sum(novelty_factors), 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to compute novelty score: {e}")
            return 0.0
    
    def clear_cache(self):
        """Clear the feature cache."""
        self.feature_cache.clear()
        logger.info("Feature cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get feature cache statistics."""
        return {
            "cache_size": len(self.feature_cache),
            "cache_hit_rate": 0.0,  # Would need to track hits/misses
            "oldest_entry": min(
                (fv.computed_at for fv in self.feature_cache.values()),
                default=None
            ),
            "newest_entry": max(
                (fv.computed_at for fv in self.feature_cache.values()),
                default=None
            ),
        }
    
    def export_features(
        self, 
        case_ids: List[str], 
        format: str = "pandas"
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Export features for multiple cases.
        
        Args:
            case_ids: List of case IDs to export
            format: Export format ("pandas" or "dict")
            
        Returns:
            Features in requested format
        """
        try:
            feature_data = []
            
            for case_id in case_ids:
                if case_id in self.feature_cache:
                    fv = self.feature_cache[case_id]
                    feature_row = {
                        "case_id": case_id,
                        **fv.features,
                        "computed_at": fv.computed_at,
                        "completeness_score": fv.completeness_score,
                    }
                    feature_data.append(feature_row)
            
            if format == "pandas":
                return pd.DataFrame(feature_data)
            else:
                return feature_data
                
        except Exception as e:
            logger.error(f"Failed to export features: {e}")
            raise


# Factory function
def create_feature_store(config: Optional[FeatureConfig] = None, repo_manager: Optional[RepositoryManager] = None) -> FeatureStore:
    """Create a feature store with default or custom configuration."""
    if config is None:
        config = FeatureConfig()
    
    if repo_manager is None:
        # Would need to create a repository manager in production
        raise ValueError("Repository manager is required")
    
    return FeatureStore(config, repo_manager)


# Utility functions

def validate_feature_vector(feature_vector: FeatureVector, required_features: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that a feature vector contains required features.
    
    Args:
        feature_vector: Feature vector to validate
        required_features: List of required feature names
        
    Returns:
        Tuple of (is_valid, missing_features)
    """
    missing_features = []
    
    for feature in required_features:
        if feature not in feature_vector.features or feature_vector.features[feature] is None:
            missing_features.append(feature)
    
    is_valid = len(missing_features) == 0
    return is_valid, missing_features


def merge_feature_vectors(feature_vectors: List[FeatureVector]) -> FeatureVector:
    """
    Merge multiple feature vectors into one.
    
    Args:
        feature_vectors: List of feature vectors to merge
        
    Returns:
        Merged feature vector
    """
    if not feature_vectors:
        raise ValueError("No feature vectors to merge")
    
    # Use first vector as base
    base_vector = feature_vectors[0]
    merged_features = base_vector.features.copy()
    merged_quality_flags = base_vector.quality_flags.copy()
    
    # Merge features from other vectors
    for fv in feature_vectors[1:]:
        merged_features.update(fv.features)
        merged_quality_flags.extend(fv.quality_flags)
    
    # Calculate new completeness score
    completeness_score = sum(1 for v in merged_features.values() if v is not None) / len(merged_features)
    
    return FeatureVector(
        case_id=base_vector.case_id,
        feature_set_version="merged",
        features=merged_features,
        metadata={
            "merged_from": len(feature_vectors),
            "source_vectors": [fv.feature_set_version for fv in feature_vectors],
        },
        completeness_score=completeness_score,
        quality_flags=list(set(merged_quality_flags)),  # Remove duplicates
    )


def compute_feature_importance(
    feature_vectors: List[FeatureVector], 
    target_values: List[float],
    method: str = "correlation"
) -> Dict[str, float]:
    """
    Compute feature importance scores.
    
    Args:
        feature_vectors: List of feature vectors
        target_values: Target values for importance calculation
        method: Method to use ("correlation", "mutual_info")
        
    Returns:
        Dictionary of feature importance scores
    """
    try:
        # Convert to DataFrame
        feature_data = []
        for fv in feature_vectors:
            feature_data.append(fv.features)
        
        df = pd.DataFrame(feature_data)
        
        # Calculate importance based on method
        importance_scores = {}
        
        if method == "correlation":
            for column in df.columns:
                if df[column].dtype in ['int64', 'float64']:
                    correlation = df[column].corr(pd.Series(target_values))
                    importance_scores[column] = abs(correlation) if not pd.isna(correlation) else 0.0
        
        elif method == "mutual_info":
            # Would need sklearn.feature_selection.mutual_info_regression
            # Simplified implementation
            for column in df.columns:
                if df[column].dtype in ['int64', 'float64']:
                    # Placeholder - use correlation as approximation
                    correlation = df[column].corr(pd.Series(target_values))
                    importance_scores[column] = abs(correlation) if not pd.isna(correlation) else 0.0
        
        return importance_scores
        
    except Exception as e:
        logger.error(f"Failed to compute feature importance: {e}")
        return {}


def detect_feature_drift(
    reference_vectors: List[FeatureVector],
    current_vectors: List[FeatureVector],
    threshold: float = 0.1
) -> Dict[str, float]:
    """
    Detect feature drift between reference and current data.
    
    Args:
        reference_vectors: Reference feature vectors
        current_vectors: Current feature vectors
        threshold: Drift detection threshold
        
    Returns:
        Dictionary of drift scores by feature
    """
    try:
        # Convert to DataFrames
        ref_data = pd.DataFrame([fv.features for fv in reference_vectors])
        curr_data = pd.DataFrame([fv.features for fv in current_vectors])
        
        drift_scores = {}
        
        for column in ref_data.columns:
            if column in curr_data.columns and ref_data[column].dtype in ['int64', 'float64']:
                # Calculate statistical distance (simplified)
                ref_mean = ref_data[column].mean()
                curr_mean = curr_data[column].mean()
                ref_std = ref_data[column].std()
                
                if ref_std > 0:
                    drift_score = abs(curr_mean - ref_mean) / ref_std
                    drift_scores[column] = min(drift_score, 1.0)
                else:
                    drift_scores[column] = 0.0
        
        return drift_scores
        
    except Exception as e:
        logger.error(f"Failed to detect feature drift: {e}")
        return {}
