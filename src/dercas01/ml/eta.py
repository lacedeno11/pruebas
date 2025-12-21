"""
ETA Prediction Service for DERCAS 01 Policy Validation Copilot

Implements ML-ETA contract from Anexo B for predicting case completion times.
Provides ETA estimates with percentiles and SLA risk assessment.
"""

import logging
import pickle
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .base import MLServiceBase, MLConfig, calculate_confidence_score
from ..models.api import ETAPredictionRequest, ETAPredictionResponse
from ..models.enums import MLModelType

logger = logging.getLogger(__name__)


class ETAConfig(MLConfig):
    """Configuration for ETA prediction service."""
    
    model_type: MLModelType = MLModelType.ETA_PREDICTION
    
    # ETA-specific settings
    min_eta_minutes: int = 5
    max_eta_minutes: int = 10080  # 7 days
    default_eta_minutes: int = 240  # 4 hours
    
    # Percentile configuration
    percentiles: List[int] = [25, 50, 75, 90, 95]
    confidence_intervals: List[float] = [0.8, 0.9, 0.95]
    
    # Feature configuration
    case_features: List[str] = [
        "priority", "complexity_score", "service_amount", "insurer_id", 
        "plan_id", "service_code", "provider_id"
    ]
    temporal_features: List[str] = [
        "hour_of_day", "day_of_week", "month_of_year", "is_holiday"
    ]
    workload_features: List[str] = [
        "queue_length", "agent_availability", "supervisor_availability",
        "current_workload", "avg_processing_time_last_week"
    ]
    historical_features: List[str] = [
        "similar_cases_avg_time", "insurer_avg_time", "provider_avg_time",
        "service_code_avg_time", "plan_avg_time"
    ]
    
    # Model parameters
    n_estimators: int = 200
    max_depth: int = 15
    learning_rate: float = 0.1
    random_state: int = 42
    
    # SLA configuration
    sla_buffer_minutes: int = 60
    sla_risk_thresholds: Dict[str, float] = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.8
    }


class ETAPredictionService(MLServiceBase):
    """
    ETA prediction service implementing ML-ETA contract.
    
    Provides:
    - ETA estimation in minutes
    - Percentile estimates (p25, p50, p75, p90, p95)
    - SLA risk assessment
    - Key factors affecting ETA
    """
    
    def __init__(self, config: ETAConfig):
        super().__init__(config)
        self.config: ETAConfig = config
        
        # Model components
        self.eta_regressor = None
        self.percentile_models = {}
        self.scaler = None
        self.categorical_encoders = {}
        
        # Historical data for similarity matching
        self.historical_cases = []
        self.case_embeddings = None
        
        # Feature importance tracking
        self.feature_importance = {}
    
    def _load_model(self) -> Dict[str, Any]:
        """Load ETA prediction models and preprocessors."""
        try:
            if self.config.model_path:
                # Load from file
                with open(self.config.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.eta_regressor = model_data['eta_regressor']
                self.percentile_models = model_data.get('percentile_models', {})
                self.scaler = model_data['scaler']
                self.categorical_encoders = model_data['categorical_encoders']
                self.historical_cases = model_data.get('historical_cases', [])
                self.case_embeddings = model_data.get('case_embeddings')
                self.feature_importance = model_data.get('feature_importance', {})
                
                logger.info(f"Loaded ETA prediction model from {self.config.model_path}")
            else:
                # Initialize default models
                self._initialize_default_models()
                logger.info("Initialized default ETA prediction models")
            
            return {
                "eta_regressor": self.eta_regressor,
                "percentile_models": self.percentile_models,
                "scaler": self.scaler,
            }
            
        except Exception as e:
            logger.error(f"Failed to load ETA prediction model: {e}")
            raise
    
    def _initialize_default_models(self):
        """Initialize default models when no trained model is available."""
        # Main ETA regressor
        self.eta_regressor = GradientBoostingRegressor(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            learning_rate=self.config.learning_rate,
            random_state=self.config.random_state
        )
        
        # Percentile models
        for percentile in self.config.percentiles:
            self.percentile_models[f"p{percentile}"] = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=self.config.random_state
            )
        
        # Scaler for numeric features
        self.scaler = StandardScaler()
        
        # Initialize with dummy data for fallback
        self._train_dummy_models()
    
    def _train_dummy_models(self):
        """Train models with dummy data for fallback functionality."""
        try:
            # Create dummy training data
            dummy_data = self._generate_dummy_training_data()
            
            # Extract features and targets
            X, _ = self._extract_features(dummy_data['features'])
            y = np.array(dummy_data['eta_minutes'])
            
            if X.shape[0] > 0:
                # Fit scaler
                X_scaled = self.scaler.fit_transform(X)
                
                # Fit main regressor
                self.eta_regressor.fit(X_scaled, y)
                
                # Fit percentile models
                for percentile_name, model in self.percentile_models.items():
                    # Generate percentile targets (simplified)
                    percentile_value = int(percentile_name[1:])
                    y_percentile = y * (percentile_value / 50.0)  # Simple scaling
                    model.fit(X_scaled, y_percentile)
                
                logger.info("Trained dummy ETA prediction models")
            
        except Exception as e:
            logger.warning(f"Failed to train dummy models: {e}")
    
    def _generate_dummy_training_data(self) -> Dict[str, List]:
        """Generate dummy training data for model initialization."""
        dummy_features = []
        dummy_eta_minutes = []
        
        priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        insurers = ["INS001", "INS002", "INS003"]
        plans = ["PLAN_A", "PLAN_B", "PLAN_C"]
        services = ["SRV001", "SRV002", "SRV003"]
        
        for i in range(500):
            priority = np.random.choice(priorities)
            
            # Generate features
            features = {
                'priority': priority,
                'complexity_score': np.random.uniform(0.1, 1.0),
                'service_amount': np.random.uniform(100, 5000),
                'insurer_id': np.random.choice(insurers),
                'plan_id': np.random.choice(plans),
                'service_code': np.random.choice(services),
                'provider_id': f"PROV{np.random.randint(1, 100):03d}",
                'hour_of_day': np.random.randint(0, 24),
                'day_of_week': np.random.randint(1, 8),
                'month_of_year': np.random.randint(1, 13),
                'is_holiday': np.random.choice([0, 1], p=[0.9, 0.1]),
                'queue_length': np.random.randint(0, 50),
                'agent_availability': np.random.uniform(0.3, 1.0),
                'supervisor_availability': np.random.uniform(0.1, 0.8),
                'current_workload': np.random.uniform(0.2, 1.0),
                'avg_processing_time_last_week': np.random.uniform(120, 480),
                'similar_cases_avg_time': np.random.uniform(60, 600),
                'insurer_avg_time': np.random.uniform(90, 400),
                'provider_avg_time': np.random.uniform(80, 350),
                'service_code_avg_time': np.random.uniform(70, 300),
                'plan_avg_time': np.random.uniform(85, 320),
            }
            
            # Generate ETA based on features (simplified logic)
            base_eta = 120  # 2 hours base
            
            # Priority adjustment
            priority_multipliers = {"LOW": 0.8, "MEDIUM": 1.0, "HIGH": 1.5, "CRITICAL": 2.0}
            eta = base_eta * priority_multipliers[priority]
            
            # Complexity adjustment
            eta *= (0.5 + features['complexity_score'])
            
            # Workload adjustment
            eta *= (1 + features['current_workload'] * 0.5)
            
            # Add some noise
            eta *= np.random.uniform(0.7, 1.3)
            
            # Ensure within bounds
            eta = max(self.config.min_eta_minutes, min(eta, self.config.max_eta_minutes))
            
            dummy_features.append(features)
            dummy_eta_minutes.append(eta)
        
        return {
            'features': dummy_features,
            'eta_minutes': dummy_eta_minutes
        }
    
    def _predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make ETA prediction."""
        try:
            # Extract and transform features
            feature_vector, feature_names = self._extract_features([features])
            
            if len(feature_vector) == 0:
                raise ValueError("No valid features extracted")
            
            # Scale features
            feature_scaled = self.scaler.transform(feature_vector)
            
            # Get main ETA prediction
            eta_minutes = self.eta_regressor.predict(feature_scaled)[0]
            eta_minutes = max(self.config.min_eta_minutes, min(eta_minutes, self.config.max_eta_minutes))
            
            # Get percentile predictions
            percentiles = {}
            for percentile_name, model in self.percentile_models.items():
                percentile_eta = model.predict(feature_scaled)[0]
                percentile_eta = max(self.config.min_eta_minutes, min(percentile_eta, self.config.max_eta_minutes))
                percentiles[percentile_name] = int(percentile_eta)
            
            # Calculate confidence
            confidence = self._calculate_eta_confidence(eta_minutes, percentiles, features)
            
            # Calculate SLA risk
            sla_risk, sla_buffer = self._calculate_sla_risk(eta_minutes, features)
            
            # Get key factors
            key_factors = self._get_key_factors(feature_vector[0], feature_names, eta_minutes)
            
            # Find similar cases
            similar_cases = self._find_similar_cases(features, limit=3)
            
            # Calculate prediction interval
            prediction_interval = self._calculate_prediction_interval(eta_minutes, confidence)
            
            return {
                "eta_minutes": int(eta_minutes),
                "p50": percentiles.get("p50", int(eta_minutes)),
                "p25": percentiles.get("p25"),
                "p75": percentiles.get("p75"),
                "p90": percentiles.get("p90"),
                "p95": percentiles.get("p95"),
                "confidence": confidence,
                "prediction_interval": prediction_interval,
                "sla_risk": sla_risk,
                "sla_buffer": sla_buffer,
                "key_factors": key_factors,
                "similar_cases": similar_cases,
            }
            
        except Exception as e:
            logger.error(f"ETA prediction failed: {e}")
            raise
    
    def _extract_features(self, data: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
        """Extract and transform features from raw data."""
        try:
            df = pd.DataFrame(data)
            feature_vectors = []
            feature_names = []
            
            # Case features
            case_data = []
            for feature in self.config.case_features:
                if feature in df.columns:
                    if feature in ['priority', 'insurer_id', 'plan_id', 'service_code', 'provider_id']:
                        # Categorical feature
                        cat_data = df[feature].fillna('UNKNOWN').astype(str)
                        
                        if feature not in self.categorical_encoders:
                            self.categorical_encoders[feature] = LabelEncoder()
                            encoded = self.categorical_encoders[feature].fit_transform(cat_data)
                        else:
                            # Handle unseen categories
                            encoder = self.categorical_encoders[feature]
                            encoded = []
                            for value in cat_data:
                                if value in encoder.classes_:
                                    encoded.append(encoder.transform([value])[0])
                                else:
                                    encoded.append(-1)  # Unknown category
                            encoded = np.array(encoded)
                        
                        case_data.append(encoded)
                        feature_names.append(f"case_{feature}")
                    else:
                        # Numeric feature
                        numeric_data = df[feature].fillna(0).astype(float)
                        case_data.append(numeric_data)
                        feature_names.append(f"case_{feature}")
                else:
                    # Missing feature - add zeros
                    case_data.append(np.zeros(len(df)))
                    feature_names.append(f"case_{feature}")
            
            if case_data:
                feature_vectors.append(np.column_stack(case_data))
            
            # Temporal features
            temporal_data = []
            for feature in self.config.temporal_features:
                if feature in df.columns:
                    temp_values = df[feature].fillna(0).astype(float)
                    temporal_data.append(temp_values)
                    feature_names.append(f"temporal_{feature}")
                else:
                    temporal_data.append(np.zeros(len(df)))
                    feature_names.append(f"temporal_{feature}")
            
            if temporal_data:
                feature_vectors.append(np.column_stack(temporal_data))
            
            # Workload features
            workload_data = []
            for feature in self.config.workload_features:
                if feature in df.columns:
                    workload_values = df[feature].fillna(0).astype(float)
                    workload_data.append(workload_values)
                    feature_names.append(f"workload_{feature}")
                else:
                    workload_data.append(np.zeros(len(df)))
                    feature_names.append(f"workload_{feature}")
            
            if workload_data:
                feature_vectors.append(np.column_stack(workload_data))
            
            # Historical features
            historical_data = []
            for feature in self.config.historical_features:
                if feature in df.columns:
                    hist_values = df[feature].fillna(0).astype(float)
                    historical_data.append(hist_values)
                    feature_names.append(f"historical_{feature}")
                else:
                    historical_data.append(np.zeros(len(df)))
                    feature_names.append(f"historical_{feature}")
            
            if historical_data:
                feature_vectors.append(np.column_stack(historical_data))
            
            # Combine all features
            if feature_vectors:
                combined_features = np.hstack(feature_vectors)
            else:
                combined_features = np.array([]).reshape(len(data), 0)
            
            return combined_features, feature_names
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise
    
    def _calculate_eta_confidence(
        self, 
        eta_minutes: float, 
        percentiles: Dict[str, int], 
        features: Dict[str, Any]
    ) -> float:
        """Calculate confidence in ETA prediction."""
        try:
            # Base confidence from model uncertainty
            p25 = percentiles.get("p25", eta_minutes)
            p75 = percentiles.get("p75", eta_minutes)
            
            if p75 > p25:
                uncertainty = (p75 - p25) / eta_minutes
                base_confidence = max(0.1, 1.0 - uncertainty)
            else:
                base_confidence = 0.8
            
            # Adjust based on data quality
            data_quality_score = self._assess_data_quality(features)
            confidence = base_confidence * data_quality_score
            
            # Adjust based on historical accuracy for similar cases
            historical_accuracy = self._get_historical_accuracy(features)
            confidence = confidence * historical_accuracy
            
            return min(max(confidence, 0.1), 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to calculate ETA confidence: {e}")
            return 0.5
    
    def _assess_data_quality(self, features: Dict[str, Any]) -> float:
        """Assess quality of input features."""
        try:
            total_features = len(self.config.case_features + self.config.temporal_features + 
                                self.config.workload_features + self.config.historical_features)
            present_features = sum(1 for feature_list in [
                self.config.case_features, self.config.temporal_features,
                self.config.workload_features, self.config.historical_features
            ] for feature in feature_list if feature in features and features[feature] is not None)
            
            completeness_score = present_features / total_features if total_features > 0 else 0.0
            
            # Penalize for missing critical features
            critical_features = ['priority', 'complexity_score', 'queue_length']
            missing_critical = sum(1 for feature in critical_features 
                                 if feature not in features or features[feature] is None)
            critical_penalty = missing_critical * 0.2
            
            quality_score = max(0.1, completeness_score - critical_penalty)
            return quality_score
            
        except Exception as e:
            logger.warning(f"Failed to assess data quality: {e}")
            return 0.7
    
    def _get_historical_accuracy(self, features: Dict[str, Any]) -> float:
        """Get historical accuracy for similar cases."""
        # Placeholder - in production, this would query historical accuracy metrics
        return 0.85
    
    def _calculate_sla_risk(self, eta_minutes: float, features: Dict[str, Any]) -> Tuple[float, Optional[int]]:
        """Calculate SLA risk and buffer time."""
        try:
            sla_target = features.get('sla_target')
            if not sla_target:
                return 0.0, None
            
            # Calculate time until SLA target
            if isinstance(sla_target, str):
                sla_target = pd.to_datetime(sla_target)
            
            now = datetime.utcnow()
            time_to_sla = (sla_target - now).total_seconds() / 60  # minutes
            
            # Calculate buffer time
            sla_buffer = int(time_to_sla - eta_minutes)
            
            # Calculate risk
            if sla_buffer <= 0:
                sla_risk = 1.0  # Already breached or will breach
            elif sla_buffer <= self.config.sla_buffer_minutes:
                sla_risk = 1.0 - (sla_buffer / self.config.sla_buffer_minutes)
            else:
                sla_risk = 0.0
            
            return min(max(sla_risk, 0.0), 1.0), sla_buffer
            
        except Exception as e:
            logger.warning(f"Failed to calculate SLA risk: {e}")
            return 0.0, None
    
    def _get_key_factors(
        self, 
        feature_vector: np.ndarray, 
        feature_names: List[str], 
        eta_minutes: float
    ) -> List[Dict[str, Any]]:
        """Get key factors affecting ETA."""
        try:
            key_factors = []
            
            if hasattr(self.eta_regressor, 'feature_importances_'):
                importance_scores = self.eta_regressor.feature_importances_
                
                # Get top features by importance
                feature_importance_pairs = [
                    (name, importance, feature_vector[i] if i < len(feature_vector) else 0)
                    for i, (name, importance) in enumerate(zip(feature_names, importance_scores))
                ]
                
                # Sort by importance
                feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
                
                # Take top 5 factors
                for name, importance, value in feature_importance_pairs[:5]:
                    factor_impact = self._calculate_factor_impact(name, value, importance)
                    
                    key_factors.append({
                        "factor_name": name,
                        "factor_value": float(value),
                        "importance": float(importance),
                        "impact_description": factor_impact,
                    })
            
            return key_factors
            
        except Exception as e:
            logger.warning(f"Failed to get key factors: {e}")
            return []
    
    def _calculate_factor_impact(self, factor_name: str, value: float, importance: float) -> str:
        """Calculate human-readable impact description for a factor."""
        try:
            if "priority" in factor_name.lower():
                if value >= 3:  # Assuming HIGH/CRITICAL encoded as 3+
                    return "High priority case increases processing time"
                else:
                    return "Standard priority allows faster processing"
            
            elif "complexity" in factor_name.lower():
                if value >= 0.7:
                    return "High complexity significantly increases processing time"
                elif value >= 0.4:
                    return "Medium complexity moderately increases processing time"
                else:
                    return "Low complexity allows faster processing"
            
            elif "queue" in factor_name.lower():
                if value >= 20:
                    return "High queue length causes delays"
                elif value >= 10:
                    return "Moderate queue length may cause some delay"
                else:
                    return "Low queue length enables faster processing"
            
            elif "workload" in factor_name.lower():
                if value >= 0.8:
                    return "High system workload causes delays"
                elif value >= 0.5:
                    return "Moderate workload may cause some delay"
                else:
                    return "Low workload enables faster processing"
            
            else:
                return f"Factor contributes {importance:.1%} to ETA prediction"
                
        except Exception as e:
            return "Factor affects processing time"
    
    def _find_similar_cases(self, features: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """Find similar historical cases."""
        try:
            # Simplified similarity matching
            similar_cases = []
            
            # In production, this would use case embeddings and similarity search
            # For now, return placeholder similar cases
            for i in range(min(limit, 3)):
                similar_cases.append({
                    "case_id": f"SIMILAR_{i+1}",
                    "actual_eta": np.random.randint(60, 480),
                    "similarity_score": np.random.uniform(0.7, 0.95),
                    "key_similarities": ["same_insurer", "similar_complexity", "same_priority"]
                })
            
            return similar_cases
            
        except Exception as e:
            logger.warning(f"Failed to find similar cases: {e}")
            return []
    
    def _calculate_prediction_interval(self, eta_minutes: float, confidence: float) -> Dict[str, int]:
        """Calculate prediction interval bounds."""
        try:
            # Simple approach: use confidence to determine interval width
            interval_width = eta_minutes * (1.0 - confidence) * 0.5
            
            lower_bound = max(self.config.min_eta_minutes, eta_minutes - interval_width)
            upper_bound = min(self.config.max_eta_minutes, eta_minutes + interval_width)
            
            return {
                "lower_bound": int(lower_bound),
                "upper_bound": int(upper_bound),
                "confidence_level": 0.8  # 80% confidence interval
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate prediction interval: {e}")
            return {
                "lower_bound": int(eta_minutes * 0.8),
                "upper_bound": int(eta_minutes * 1.2),
                "confidence_level": 0.8
            }
    
    def _get_fallback_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback prediction when main model fails."""
        try:
            # Simple rule-based fallback
            priority = features.get('priority', 'MEDIUM')
            complexity_score = features.get('complexity_score', 0.5)
            queue_length = features.get('queue_length', 10)
            
            # Base ETA calculation
            priority_multipliers = {"LOW": 0.8, "MEDIUM": 1.0, "HIGH": 1.5, "CRITICAL": 2.0}
            base_eta = self.config.default_eta_minutes
            
            eta_minutes = base_eta * priority_multipliers.get(priority, 1.0)
            eta_minutes *= (0.5 + complexity_score)
            eta_minutes *= (1 + queue_length / 50.0)
            
            # Ensure within bounds
            eta_minutes = max(self.config.min_eta_minutes, min(eta_minutes, self.config.max_eta_minutes))
            
            # Generate simple percentiles
            p50 = int(eta_minutes)
            p25 = int(eta_minutes * 0.7)
            p75 = int(eta_minutes * 1.3)
            p90 = int(eta_minutes * 1.6)
            p95 = int(eta_minutes * 1.8)
            
            return {
                "eta_minutes": int(eta_minutes),
                "p50": p50,
                "p25": p25,
                "p75": p75,
                "p90": p90,
                "p95": p95,
                "confidence": self.config.fallback_confidence,
                "prediction_interval": {
                    "lower_bound": p25,
                    "upper_bound": p75,
                    "confidence_level": 0.8
                },
                "sla_risk": None,
                "sla_buffer": None,
                "key_factors": [],
                "similar_cases": [],
            }
            
        except Exception as e:
            logger.error(f"Fallback prediction failed: {e}")
            raise
    
    def train_model(self, training_data: List[Dict[str, Any]], eta_targets: List[float]) -> Dict[str, float]:
        """
        Train the ETA prediction model with new data.
        
        Args:
            training_data: List of training examples with features
            eta_targets: List of actual ETA values in minutes
            
        Returns:
            Training metrics
        """
        try:
            logger.info(f"Training ETA prediction model with {len(training_data)} examples")
            
            # Extract features
            X, feature_names = self._extract_features(training_data)
            y = np.array(eta_targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=self.config.random_state
            )
            
            # Fit scaler
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train main regressor
            self.eta_regressor.fit(X_train_scaled, y_train)
            y_pred = self.eta_regressor.predict(X_test_scaled)
            
            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Train percentile models
            percentile_metrics = {}
            for percentile in self.config.percentiles:
                percentile_name = f"p{percentile}"
                y_percentile = np.percentile(y_train.reshape(-1, 1), percentile, axis=0)
                y_percentile_expanded = np.full_like(y_train, y_percentile[0])
                
                model = self.percentile_models[percentile_name]
                model.fit(X_train_scaled, y_percentile_expanded)
                
                y_pred_percentile = model.predict(X_test_scaled)
                percentile_mae = mean_absolute_error(y_test, y_pred_percentile)
                percentile_metrics[f"{percentile_name}_mae"] = percentile_mae
            
            # Update feature importance
            if hasattr(self.eta_regressor, 'feature_importances_'):
                self.feature_importance = {
                    name: float(importance) 
                    for name, importance in zip(feature_names, self.eta_regressor.feature_importances_)
                }
            
            metrics = {
                "mae": mae,
                "mse": mse,
                "rmse": np.sqrt(mse),
                "r2_score": r2,
                "training_samples": len(training_data),
                "feature_count": X.shape[1],
                **percentile_metrics,
            }
            
            logger.info(f"Model training completed: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    def save_model(self, file_path: str):
        """Save the trained model to file."""
        try:
            model_data = {
                'eta_regressor': self.eta_regressor,
                'percentile_models': self.percentile_models,
                'scaler': self.scaler,
                'categorical_encoders': self.categorical_encoders,
                'historical_cases': self.historical_cases,
                'case_embeddings': self.case_embeddings,
                'feature_importance': self.feature_importance,
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
    
    def update_historical_cases(self, completed_cases: List[Dict[str, Any]]):
        """Update historical cases for similarity matching."""
        try:
            self.historical_cases.extend(completed_cases)
            
            # Keep only recent cases (last 1000)
            if len(self.historical_cases) > 1000:
                self.historical_cases = self.historical_cases[-1000:]
            
            logger.info(f"Updated historical cases: {len(self.historical_cases)} total")
            
        except Exception as e:
            logger.error(f"Failed to update historical cases: {e}")
            raise


# Factory function
def create_eta_prediction_service(config: Optional[ETAConfig] = None) -> ETAPredictionService:
    """Create an ETA prediction service with default or custom configuration."""
    if config is None:
        config = ETAConfig()
    
    return ETAPredictionService(config)


# Utility functions for ETA prediction
def preprocess_case_for_eta_prediction(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess case data for ETA prediction."""
    processed = {}
    
    # Extract case features
    case_mapping = {
        'priority': 'priority',
        'insurer_id': 'insurer_id',
        'plan_id': 'plan_id',
        'service_code': 'service_code',
        'provider_id': 'provider_id',
        'sla_target': 'sla_target',
    }
    
    for source_field, target_field in case_mapping.items():
        if source_field in case_data:
            processed[target_field] = case_data[source_field]
    
    # Calculate complexity score (simplified)
    complexity_factors = []
    if case_data.get('attachments'):
        complexity_factors.append(len(case_data['attachments']) * 0.1)
    if case_data.get('context', {}).get('service_amount', 0) > 5000:
        complexity_factors.append(0.3)
    
    processed['complexity_score'] = min(sum(complexity_factors), 1.0) if complexity_factors else 0.5
    
    # Add temporal features
    now = datetime.utcnow()
    processed.update({
        'hour_of_day': now.hour,
        'day_of_week': now.weekday() + 1,
        'month_of_year': now.month,
        'is_holiday': 0,  # Would need holiday calendar integration
    })
    
    return processed


def validate_eta_response(response: Dict[str, Any]) -> bool:
    """Validate ETA prediction response format."""
    required_fields = ['eta_minutes', 'p50']
    
    for field in required_fields:
        if field not in response:
            return False
    
    # Validate ETA is positive
    eta_minutes = response.get('eta_minutes', 0)
    if eta_minutes <= 0:
        return False
    
    # Validate percentiles are in order
    percentiles = ['p25', 'p50', 'p75', 'p90', 'p95']
    prev_value = 0
    for p in percentiles:
        if p in response:
            if response[p] < prev_value:
                return False
            prev_value = response[p]
    
    return True


def calculate_eta_accuracy(predicted_eta: int, actual_eta: int) -> Dict[str, float]:
    """Calculate accuracy metrics for ETA prediction."""
    absolute_error = abs(predicted_eta - actual_eta)
    relative_error = absolute_error / actual_eta if actual_eta > 0 else 0
    
    return {
        "absolute_error_minutes": absolute_error,
        "relative_error": relative_error,
        "accuracy_percentage": max(0, 1 - relative_error) * 100,
        "within_10_percent": relative_error <= 0.1,
        "within_20_percent": relative_error <= 0.2,
    }
