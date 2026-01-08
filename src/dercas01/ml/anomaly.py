"""
Anomaly Detection Service for DERCAS 01 Policy Validation Copilot

Implements ML-ANOMALY contract from Anexo B for detecting anomalous cases.
Provides anomaly scoring, flag detection, and recommended actions.
"""

import logging
import pickle
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score

from .base import MLServiceBase, MLConfig, calculate_confidence_score
from ..models.api import AnomalyDetectionRequest, AnomalyDetectionResponse
from ..models.enums import MLModelType

logger = logging.getLogger(__name__)


class AnomalyConfig(MLConfig):
    """Configuration for anomaly detection service."""
    
    model_type: MLModelType = MLModelType.ANOMALY_DETECTION
    
    # Anomaly detection thresholds
    anomaly_threshold: float = 0.7
    high_anomaly_threshold: float = 0.9
    contamination_rate: float = 0.1
    
    # Feature configuration
    numeric_features: List[str] = [
        "service_amount", "patient_age", "days_since_last_service",
        "provider_service_count", "monthly_claim_count", "avg_service_amount"
    ]
    categorical_features: List[str] = [
        "service_code", "provider_id", "diagnosis_code", "service_location"
    ]
    temporal_features: List[str] = [
        "hour_of_day", "day_of_week", "month_of_year"
    ]
    
    # Model parameters
    n_estimators: int = 100
    max_samples: str = "auto"
    random_state: int = 42
    
    # Aggregation windows for historical features
    aggregation_windows: List[int] = [7, 30, 90]  # days
    
    # Anomaly flags configuration
    anomaly_flags: Dict[str, Dict[str, Any]] = {
        "HIGH_AMOUNT": {
            "threshold": 10000,
            "feature": "service_amount",
            "comparison": "greater"
        },
        "UNUSUAL_FREQUENCY": {
            "threshold": 5,
            "feature": "monthly_claim_count",
            "comparison": "greater"
        },
        "OFF_HOURS": {
            "threshold": [22, 6],  # 10 PM to 6 AM
            "feature": "hour_of_day",
            "comparison": "between"
        },
        "NEW_PROVIDER": {
            "threshold": 30,  # days
            "feature": "days_since_first_service_with_provider",
            "comparison": "less"
        },
        "GEOGRAPHIC_ANOMALY": {
            "threshold": 100,  # km
            "feature": "distance_from_usual_location",
            "comparison": "greater"
        }
    }
    
    # Action recommendations
    action_mapping: Dict[str, str] = {
        "low": "ALLOW",
        "medium": "REVIEW",
        "high": "BLOCK",
        "critical": "ESCALATE"
    }


class AnomalyDetectionService(MLServiceBase):
    """
    Anomaly detection service implementing ML-ANOMALY contract.
    
    Provides:
    - Anomaly score calculation
    - Anomaly flag detection
    - Recommended actions
    - Historical pattern analysis
    """
    
    def __init__(self, config: AnomalyConfig):
        super().__init__(config)
        self.config: AnomalyConfig = config
        
        # Model components
        self.isolation_forest = None
        self.scaler = None
        self.pca = None
        self.clustering_model = None
        
        # Historical data for comparison
        self.baseline_stats = {}
        self.historical_patterns = {}
        
        # Feature importance tracking
        self.anomaly_feature_weights = {}
    
    def _load_model(self) -> Dict[str, Any]:
        """Load anomaly detection models and preprocessors."""
        try:
            if self.config.model_path:
                # Load from file
                with open(self.config.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.isolation_forest = model_data['isolation_forest']
                self.scaler = model_data['scaler']
                self.pca = model_data.get('pca')
                self.clustering_model = model_data.get('clustering_model')
                self.baseline_stats = model_data.get('baseline_stats', {})
                self.historical_patterns = model_data.get('historical_patterns', {})
                self.anomaly_feature_weights = model_data.get('anomaly_feature_weights', {})
                
                logger.info(f"Loaded anomaly detection model from {self.config.model_path}")
            else:
                # Initialize default models
                self._initialize_default_models()
                logger.info("Initialized default anomaly detection models")
            
            return {
                "isolation_forest": self.isolation_forest,
                "scaler": self.scaler,
                "pca": self.pca,
            }
            
        except Exception as e:
            logger.error(f"Failed to load anomaly detection model: {e}")
            raise
    
    def _initialize_default_models(self):
        """Initialize default models when no trained model is available."""
        # Isolation Forest for anomaly detection
        self.isolation_forest = IsolationForest(
            n_estimators=self.config.n_estimators,
            max_samples=self.config.max_samples,
            contamination=self.config.contamination_rate,
            random_state=self.config.random_state,
            n_jobs=-1
        )
        
        # Robust scaler for preprocessing
        self.scaler = RobustScaler()
        
        # PCA for dimensionality reduction
        self.pca = PCA(n_components=0.95)  # Keep 95% of variance
        
        # DBSCAN for clustering-based anomaly detection
        self.clustering_model = DBSCAN(eps=0.5, min_samples=5)
        
        # Initialize with dummy data for fallback
        self._train_dummy_models()
    
    def _train_dummy_models(self):
        """Train models with dummy data for fallback functionality."""
        try:
            # Create dummy training data
            dummy_data = self._generate_dummy_training_data()
            
            # Extract features
            X, _ = self._extract_features(dummy_data)
            
            if X.shape[0] > 0:
                # Fit scaler
                X_scaled = self.scaler.fit_transform(X)
                
                # Fit PCA
                if X_scaled.shape[1] > 2:
                    X_pca = self.pca.fit_transform(X_scaled)
                else:
                    X_pca = X_scaled
                
                # Fit isolation forest
                self.isolation_forest.fit(X_pca)
                
                # Fit clustering model
                self.clustering_model.fit(X_pca)
                
                logger.info("Trained dummy anomaly detection models")
            
        except Exception as e:
            logger.warning(f"Failed to train dummy models: {e}")
    
    def _generate_dummy_training_data(self) -> List[Dict[str, Any]]:
        """Generate dummy training data for model initialization."""
        dummy_data = []
        
        for i in range(200):
            # Generate normal cases
            if i < 180:
                dummy_data.append({
                    'service_amount': np.random.normal(1000, 300),
                    'patient_age': np.random.normal(45, 15),
                    'days_since_last_service': np.random.exponential(30),
                    'provider_service_count': np.random.poisson(50),
                    'monthly_claim_count': np.random.poisson(2),
                    'avg_service_amount': np.random.normal(800, 200),
                    'hour_of_day': np.random.choice(range(8, 18)),  # Business hours
                    'day_of_week': np.random.choice(range(1, 6)),   # Weekdays
                    'month_of_year': np.random.choice(range(1, 13)),
                })
            # Generate anomalous cases
            else:
                dummy_data.append({
                    'service_amount': np.random.normal(5000, 1000),  # Higher amounts
                    'patient_age': np.random.normal(45, 15),
                    'days_since_last_service': np.random.exponential(5),  # More frequent
                    'provider_service_count': np.random.poisson(200),  # High volume provider
                    'monthly_claim_count': np.random.poisson(10),  # High frequency
                    'avg_service_amount': np.random.normal(3000, 500),
                    'hour_of_day': np.random.choice([23, 0, 1, 2, 3]),  # Off hours
                    'day_of_week': np.random.choice([6, 7]),  # Weekends
                    'month_of_year': np.random.choice(range(1, 13)),
                })
        
        return dummy_data
    
    def _predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make anomaly detection prediction."""
        try:
            # Extract and transform features
            feature_vector, feature_names = self._extract_features([features])
            
            if len(feature_vector) == 0:
                raise ValueError("No valid features extracted")
            
            # Scale features
            feature_scaled = self.scaler.transform(feature_vector)
            
            # Apply PCA if available
            if self.pca is not None and feature_scaled.shape[1] > 2:
                feature_pca = self.pca.transform(feature_scaled)
            else:
                feature_pca = feature_scaled
            
            # Get anomaly score from isolation forest
            anomaly_score_raw = self.isolation_forest.decision_function(feature_pca)[0]
            # Convert to [0, 1] range where 1 is most anomalous
            anomaly_score = max(0.0, min(1.0, (0.5 - anomaly_score_raw) / 1.0))
            
            # Detect specific anomaly flags
            anomaly_flags = self._detect_anomaly_flags(features)
            
            # Determine recommended action
            recommended_action = self._determine_action(anomaly_score, anomaly_flags)
            
            # Get contributing features
            contributing_features = self._get_contributing_features(
                feature_vector[0], feature_names, anomaly_score
            )
            
            # Calculate confidence
            confidence = self._calculate_anomaly_confidence(anomaly_score, anomaly_flags)
            
            return {
                "anomaly_score": float(anomaly_score),
                "anomaly_flags": anomaly_flags,
                "recommended_action": recommended_action,
                "anomaly_details": {
                    "isolation_forest_score": float(anomaly_score_raw),
                    "contributing_features": contributing_features,
                    "baseline_comparison": self._compare_to_baseline(features),
                },
                "confidence": confidence,
            }
            
        except Exception as e:
            logger.error(f"Anomaly detection prediction failed: {e}")
            raise
    
    def _extract_features(self, data: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
        """Extract and transform features from raw data."""
        try:
            df = pd.DataFrame(data)
            feature_vectors = []
            feature_names = []
            
            # Numeric features
            numeric_data = []
            for num_col in self.config.numeric_features:
                if num_col in df.columns:
                    # Handle missing values and outliers
                    values = df[num_col].fillna(df[num_col].median() if not df[num_col].empty else 0)
                    # Cap extreme outliers
                    q99 = values.quantile(0.99) if not values.empty else 0
                    values = values.clip(upper=q99 * 3)
                    numeric_data.append(values.astype(float))
                    feature_names.append(f"num_{num_col}")
                else:
                    # Add zero column for missing features
                    numeric_data.append(pd.Series([0.0] * len(df)))
                    feature_names.append(f"num_{num_col}")
            
            if numeric_data:
                feature_vectors.append(np.column_stack(numeric_data))
            
            # Categorical features (one-hot encoded)
            categorical_data = []
            for cat_col in self.config.categorical_features:
                if cat_col in df.columns:
                    # Simple frequency encoding for anomaly detection
                    cat_values = df[cat_col].fillna('UNKNOWN')
                    value_counts = cat_values.value_counts()
                    frequency_encoded = cat_values.map(value_counts).astype(float)
                    categorical_data.append(frequency_encoded)
                    feature_names.append(f"cat_{cat_col}_freq")
                else:
                    categorical_data.append(pd.Series([0.0] * len(df)))
                    feature_names.append(f"cat_{cat_col}_freq")
            
            if categorical_data:
                feature_vectors.append(np.column_stack(categorical_data))
            
            # Temporal features
            temporal_data = []
            for temp_col in self.config.temporal_features:
                if temp_col in df.columns:
                    temp_values = df[temp_col].fillna(0).astype(float)
                    temporal_data.append(temp_values)
                    feature_names.append(f"temp_{temp_col}")
                else:
                    temporal_data.append(pd.Series([0.0] * len(df)))
                    feature_names.append(f"temp_{temp_col}")
            
            if temporal_data:
                feature_vectors.append(np.column_stack(temporal_data))
            
            # Combine all features
            if feature_vectors:
                combined_features = np.hstack(feature_vectors)
            else:
                combined_features = np.array([]).reshape(len(data), 0)
            
            return combined_features, feature_names
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise
    
    def _detect_anomaly_flags(self, features: Dict[str, Any]) -> List[str]:
        """Detect specific anomaly flags based on business rules."""
        flags = []
        
        try:
            for flag_name, flag_config in self.config.anomaly_flags.items():
                feature_name = flag_config["feature"]
                threshold = flag_config["threshold"]
                comparison = flag_config["comparison"]
                
                if feature_name in features:
                    value = features[feature_name]
                    
                    if comparison == "greater" and value > threshold:
                        flags.append(flag_name)
                    elif comparison == "less" and value < threshold:
                        flags.append(flag_name)
                    elif comparison == "between" and isinstance(threshold, list):
                        if len(threshold) == 2:
                            if threshold[0] <= value <= threshold[1]:
                                flags.append(flag_name)
                    elif comparison == "outside" and isinstance(threshold, list):
                        if len(threshold) == 2:
                            if value < threshold[0] or value > threshold[1]:
                                flags.append(flag_name)
            
        except Exception as e:
            logger.warning(f"Failed to detect anomaly flags: {e}")
        
        return flags
    
    def _determine_action(self, anomaly_score: float, anomaly_flags: List[str]) -> str:
        """Determine recommended action based on anomaly score and flags."""
        try:
            # Critical flags that require immediate escalation
            critical_flags = ["HIGH_AMOUNT", "GEOGRAPHIC_ANOMALY"]
            if any(flag in critical_flags for flag in anomaly_flags):
                return self.config.action_mapping.get("critical", "ESCALATE")
            
            # High anomaly score
            if anomaly_score >= self.config.high_anomaly_threshold:
                return self.config.action_mapping.get("high", "BLOCK")
            
            # Medium anomaly score or multiple flags
            if anomaly_score >= self.config.anomaly_threshold or len(anomaly_flags) >= 2:
                return self.config.action_mapping.get("medium", "REVIEW")
            
            # Low anomaly score
            return self.config.action_mapping.get("low", "ALLOW")
            
        except Exception as e:
            logger.warning(f"Failed to determine action: {e}")
            return "REVIEW"
    
    def _get_contributing_features(
        self, 
        feature_vector: np.ndarray, 
        feature_names: List[str], 
        anomaly_score: float
    ) -> List[Dict[str, Any]]:
        """Get features that contribute most to the anomaly score."""
        try:
            contributing_features = []
            
            # Simple approach: use feature weights if available
            if self.anomaly_feature_weights:
                for i, name in enumerate(feature_names):
                    if i < len(feature_vector) and name in self.anomaly_feature_weights:
                        weight = self.anomaly_feature_weights[name]
                        contribution = abs(feature_vector[i] * weight)
                        
                        contributing_features.append({
                            "feature_name": name,
                            "value": float(feature_vector[i]),
                            "contribution": float(contribution),
                            "weight": float(weight),
                        })
            
            # Sort by contribution and return top features
            contributing_features.sort(key=lambda x: x["contribution"], reverse=True)
            return contributing_features[:5]
            
        except Exception as e:
            logger.warning(f"Failed to get contributing features: {e}")
            return []
    
    def _compare_to_baseline(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Compare features to historical baseline."""
        try:
            comparison = {}
            
            for feature_name, value in features.items():
                if feature_name in self.baseline_stats:
                    baseline = self.baseline_stats[feature_name]
                    
                    if isinstance(value, (int, float)):
                        mean = baseline.get("mean", 0)
                        std = baseline.get("std", 1)
                        
                        if std > 0:
                            z_score = (value - mean) / std
                            comparison[feature_name] = {
                                "current_value": float(value),
                                "baseline_mean": float(mean),
                                "baseline_std": float(std),
                                "z_score": float(z_score),
                                "deviation": "high" if z_score > 2 else "low" if z_score < -2 else "normal"
                            }
            
            return comparison
            
        except Exception as e:
            logger.warning(f"Failed to compare to baseline: {e}")
            return {}
    
    def _calculate_anomaly_confidence(self, anomaly_score: float, anomaly_flags: List[str]) -> float:
        """Calculate confidence in anomaly detection."""
        try:
            # Base confidence from anomaly score
            base_confidence = anomaly_score
            
            # Boost confidence if multiple flags are present
            flag_boost = min(len(anomaly_flags) * 0.1, 0.3)
            
            # Boost confidence if critical flags are present
            critical_flags = ["HIGH_AMOUNT", "GEOGRAPHIC_ANOMALY"]
            critical_boost = 0.2 if any(flag in critical_flags for flag in anomaly_flags) else 0.0
            
            confidence = min(base_confidence + flag_boost + critical_boost, 1.0)
            return confidence
            
        except Exception as e:
            logger.warning(f"Failed to calculate confidence: {e}")
            return 0.5
    
    def _get_fallback_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback prediction when main model fails."""
        try:
            # Simple rule-based fallback
            anomaly_flags = self._detect_anomaly_flags(features)
            
            # Calculate simple anomaly score based on flags
            anomaly_score = min(len(anomaly_flags) * 0.3, 1.0)
            
            # Determine action
            recommended_action = self._determine_action(anomaly_score, anomaly_flags)
            
            return {
                "anomaly_score": anomaly_score,
                "anomaly_flags": anomaly_flags,
                "recommended_action": recommended_action,
                "anomaly_details": {
                    "fallback_mode": True,
                    "contributing_features": [],
                    "baseline_comparison": {},
                },
                "confidence": self.config.fallback_confidence,
            }
            
        except Exception as e:
            logger.error(f"Fallback prediction failed: {e}")
            raise
    
    def train_model(self, training_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Train the anomaly detection model with new data.
        
        Args:
            training_data: List of training examples (normal cases)
            
        Returns:
            Training metrics
        """
        try:
            logger.info(f"Training anomaly detection model with {len(training_data)} examples")
            
            # Extract features
            X, feature_names = self._extract_features(training_data)
            
            # Fit scaler
            X_scaled = self.scaler.fit_transform(X)
            
            # Fit PCA
            if X_scaled.shape[1] > 2:
                X_pca = self.pca.fit_transform(X_scaled)
            else:
                X_pca = X_scaled
            
            # Fit isolation forest
            self.isolation_forest.fit(X_pca)
            
            # Fit clustering model
            cluster_labels = self.clustering_model.fit_predict(X_pca)
            
            # Calculate baseline statistics
            self._calculate_baseline_stats(training_data)
            
            # Calculate feature weights (simplified)
            self._calculate_feature_weights(X_scaled, feature_names)
            
            # Calculate training metrics
            anomaly_scores = self.isolation_forest.decision_function(X_pca)
            outlier_fraction = np.sum(anomaly_scores < 0) / len(anomaly_scores)
            
            # Silhouette score for clustering (if we have clusters)
            silhouette = 0.0
            if len(set(cluster_labels)) > 1:
                silhouette = silhouette_score(X_pca, cluster_labels)
            
            metrics = {
                "training_samples": len(training_data),
                "feature_count": X.shape[1],
                "outlier_fraction": float(outlier_fraction),
                "silhouette_score": float(silhouette),
                "pca_explained_variance": float(np.sum(self.pca.explained_variance_ratio_)) if self.pca else 0.0,
            }
            
            logger.info(f"Model training completed: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    def _calculate_baseline_stats(self, training_data: List[Dict[str, Any]]):
        """Calculate baseline statistics for comparison."""
        try:
            df = pd.DataFrame(training_data)
            
            for column in df.columns:
                if df[column].dtype in ['int64', 'float64']:
                    self.baseline_stats[column] = {
                        "mean": float(df[column].mean()),
                        "std": float(df[column].std()),
                        "median": float(df[column].median()),
                        "q25": float(df[column].quantile(0.25)),
                        "q75": float(df[column].quantile(0.75)),
                        "min": float(df[column].min()),
                        "max": float(df[column].max()),
                    }
                else:
                    value_counts = df[column].value_counts()
                    self.baseline_stats[column] = {
                        "mode": value_counts.index[0] if not value_counts.empty else None,
                        "unique_count": len(value_counts),
                        "top_values": value_counts.head(10).to_dict(),
                    }
            
        except Exception as e:
            logger.warning(f"Failed to calculate baseline stats: {e}")
    
    def _calculate_feature_weights(self, X_scaled: np.ndarray, feature_names: List[str]):
        """Calculate feature weights for anomaly contribution."""
        try:
            # Simple approach: use variance as weight
            feature_variances = np.var(X_scaled, axis=0)
            
            for i, name in enumerate(feature_names):
                if i < len(feature_variances):
                    self.anomaly_feature_weights[name] = float(feature_variances[i])
            
        except Exception as e:
            logger.warning(f"Failed to calculate feature weights: {e}")
    
    def save_model(self, file_path: str):
        """Save the trained model to file."""
        try:
            model_data = {
                'isolation_forest': self.isolation_forest,
                'scaler': self.scaler,
                'pca': self.pca,
                'clustering_model': self.clustering_model,
                'baseline_stats': self.baseline_stats,
                'historical_patterns': self.historical_patterns,
                'anomaly_feature_weights': self.anomaly_feature_weights,
                'config': self.config.dict(),
                'model_version': self.config.model_version,
                'saved_at': datetime.utcnow().isoformat(),
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            raise
    
    def update_baseline(self, recent_data: List[Dict[str, Any]], window_days: int = 30):
        """Update baseline statistics with recent data."""
        try:
            # Filter recent data
            cutoff_date = datetime.utcnow() - timedelta(days=window_days)
            
            # Recalculate baseline stats
            self._calculate_baseline_stats(recent_data)
            
            logger.info(f"Updated baseline with {len(recent_data)} recent samples")
            
        except Exception as e:
            logger.error(f"Failed to update baseline: {e}")
            raise


# Factory function
def create_anomaly_detection_service(config: Optional[AnomalyConfig] = None) -> AnomalyDetectionService:
    """Create an anomaly detection service with default or custom configuration."""
    if config is None:
        config = AnomalyConfig()
    
    return AnomalyDetectionService(config)


# Utility functions for anomaly detection
def preprocess_case_for_anomaly_detection(
    case_data: Dict[str, Any], 
    aggregates: Dict[str, Any]
) -> Dict[str, Any]:
    """Preprocess case data and aggregates for anomaly detection."""
    processed = {}
    
    # Extract case features
    case_mapping = {
        'service_amount': 'service_amount',
        'patient_age': 'patient_age',
        'service_code': 'service_code',
        'provider_id': 'provider_id',
        'service_date': 'service_date',
    }
    
    for source_field, target_field in case_mapping.items():
        if source_field in case_data:
            processed[target_field] = case_data[source_field]
    
    # Extract aggregate features
    if aggregates:
        processed.update({
            'provider_service_count': aggregates.get('provider_service_count', 0),
            'monthly_claim_count': aggregates.get('monthly_claim_count', 0),
            'avg_service_amount': aggregates.get('avg_service_amount', 0),
            'days_since_last_service': aggregates.get('days_since_last_service', 0),
        })
    
    # Calculate temporal features
    if 'service_date' in processed and processed['service_date']:
        service_date = pd.to_datetime(processed['service_date'])
        processed.update({
            'hour_of_day': service_date.hour,
            'day_of_week': service_date.dayofweek + 1,
            'month_of_year': service_date.month,
        })
    
    return processed


def validate_anomaly_response(response: Dict[str, Any]) -> bool:
    """Validate anomaly detection response format."""
    required_fields = [
        'anomaly_score', 'anomaly_flags', 'recommended_action'
    ]
    
    for field in required_fields:
        if field not in response:
            return False
    
    # Validate anomaly_score is in [0, 1]
    anomaly_score = response.get('anomaly_score', -1)
    if not (0 <= anomaly_score <= 1):
        return False
    
    # Validate recommended_action is valid
    valid_actions = ["ALLOW", "REVIEW", "BLOCK", "ESCALATE"]
    if response.get('recommended_action') not in valid_actions:
        return False
    
    return True


def calculate_risk_level(anomaly_score: float, anomaly_flags: List[str]) -> str:
    """Calculate risk level based on anomaly score and flags."""
    critical_flags = ["HIGH_AMOUNT", "GEOGRAPHIC_ANOMALY"]
    
    if any(flag in critical_flags for flag in anomaly_flags):
        return "CRITICAL"
    elif anomaly_score >= 0.8:
        return "HIGH"
    elif anomaly_score >= 0.5 or len(anomaly_flags) >= 2:
        return "MEDIUM"
    else:
        return "LOW"
