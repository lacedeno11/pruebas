"""
ML Classification Service (UC-OP-11)

This module implements the ML-CLASSIFY API contract for case classification and routing.
It provides request type classification, policy candidate identification, routing decisions,
and risk assessment with comprehensive feature extraction and model management.

API Contract:
Input: {case_id, features, model_version?}
Output: {request_type, candidate_policy_ids, route, risk_prior, probabilities, top_features, model_version}
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, validator
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder

from ..data_layer.feature_store import FeatureStore
from ..models.state_schema import CaseState

logger = logging.getLogger(__name__)


class ClassificationRequest(BaseModel):
    """Classification request model"""
    case_id: str
    features: Dict[str, Any]
    model_version: Optional[str] = None
    include_probabilities: bool = True
    include_top_features: bool = True


class ClassificationResponse(BaseModel):
    """Classification response model"""
    case_id: str
    request_type: str
    candidate_policy_ids: List[str]
    route: str
    risk_prior: str
    probabilities: Dict[str, float]
    top_features: List[Dict[str, Any]]
    model_version: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_time_ms: float
    fallback_used: bool = False
    drift_detected: bool = False


class ModelMetadata(BaseModel):
    """Model metadata and versioning information"""
    model_id: str
    version: str
    model_type: str
    training_date: datetime
    performance_metrics: Dict[str, float]
    feature_names: List[str]
    target_classes: List[str]
    hyperparameters: Dict[str, Any]
    data_version: str
    is_active: bool = True
    fallback_model: Optional[str] = None


class FeatureExtractor:
    """Feature extraction for case classification"""
    
    def __init__(self, feature_store: FeatureStore = None):
        self.feature_store = feature_store
        self.feature_definitions = self._load_feature_definitions()
    
    def _load_feature_definitions(self) -> Dict[str, Dict]:
        """Load feature definitions for classification"""
        return {
            # Basic case features
            'case_age_hours': {
                'type': 'numerical',
                'description': 'Hours since case creation',
                'required': True
            },
            'priority_numeric': {
                'type': 'numerical', 
                'description': 'Numeric priority (1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL)',
                'required': True
            },
            'attachment_count': {
                'type': 'numerical',
                'description': 'Number of attachments',
                'required': False
            },
            'service_code_encoded': {
                'type': 'categorical',
                'description': 'Encoded service code',
                'required': True
            },
            'insurer_encoded': {
                'type': 'categorical',
                'description': 'Encoded insurer ID',
                'required': True
            },
            
            # Temporal features
            'hour_of_day': {
                'type': 'numerical',
                'description': 'Hour of day when case was created',
                'required': False
            },
            'day_of_week': {
                'type': 'numerical',
                'description': 'Day of week (0=Monday, 6=Sunday)',
                'required': False
            },
            'is_weekend': {
                'type': 'boolean',
                'description': 'Whether case was created on weekend',
                'required': False
            },
            
            # Historical features
            'customer_case_count_30d': {
                'type': 'numerical',
                'description': 'Customer case count in last 30 days',
                'required': False
            },
            'provider_case_count_30d': {
                'type': 'numerical',
                'description': 'Provider case count in last 30 days',
                'required': False
            },
            'service_frequency_score': {
                'type': 'numerical',
                'description': 'Historical frequency score for service type',
                'required': False
            },
            
            # Content features
            'has_medical_keywords': {
                'type': 'boolean',
                'description': 'Contains medical-related keywords',
                'required': False
            },
            'has_emergency_keywords': {
                'type': 'boolean',
                'description': 'Contains emergency-related keywords',
                'required': False
            },
            'text_length': {
                'type': 'numerical',
                'description': 'Total text length in case description',
                'required': False
            }
        }
    
    def extract_features(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from case data"""
        features = {}
        
        try:
            # Basic case features
            created_at = self._parse_datetime(case_data.get('created_at'))
            if created_at:
                case_age = (datetime.utcnow() - created_at).total_seconds() / 3600
                features['case_age_hours'] = case_age
                features['hour_of_day'] = created_at.hour
                features['day_of_week'] = created_at.weekday()
                features['is_weekend'] = created_at.weekday() >= 5
            
            # Priority encoding
            priority_map = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
            priority = case_data.get('priority', 'MEDIUM')
            features['priority_numeric'] = priority_map.get(priority, 2)
            
            # Attachment count
            attachments = case_data.get('attachments', [])
            features['attachment_count'] = len(attachments) if attachments else 0
            
            # Service and insurer encoding (simplified - in production would use proper encoders)
            service_code = case_data.get('service_code', 'UNKNOWN')
            features['service_code_encoded'] = hash(service_code) % 1000
            
            insurer_id = case_data.get('insurer_id', 'UNKNOWN')
            features['insurer_encoded'] = hash(insurer_id) % 100
            
            # Historical features (mock implementation)
            customer_id = case_data.get('customer_id')
            if customer_id:
                features['customer_case_count_30d'] = self._get_customer_history(customer_id)
            
            provider_id = case_data.get('provider_id')
            if provider_id:
                features['provider_case_count_30d'] = self._get_provider_history(provider_id)
            
            # Service frequency
            features['service_frequency_score'] = self._calculate_service_frequency(service_code)
            
            # Content analysis
            description = case_data.get('service_description', '')
            features.update(self._extract_content_features(description))
            
            # Fill missing values with defaults
            features = self._fill_missing_features(features)
            
            logger.debug(f"Extracted {len(features)} features for case {case_data.get('case_id')}")
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return self._get_default_features()
    
    def _parse_datetime(self, dt_str: Union[str, datetime]) -> Optional[datetime]:
        """Parse datetime string or return datetime object"""
        if isinstance(dt_str, datetime):
            return dt_str
        if isinstance(dt_str, str):
            try:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                return None
        return None
    
    def _get_customer_history(self, customer_id: str) -> int:
        """Get customer case history (mock implementation)"""
        # In production, this would query the database
        return hash(customer_id) % 10
    
    def _get_provider_history(self, provider_id: str) -> int:
        """Get provider case history (mock implementation)"""
        # In production, this would query the database
        return hash(provider_id) % 20
    
    def _calculate_service_frequency(self, service_code: str) -> float:
        """Calculate service frequency score (mock implementation)"""
        # In production, this would calculate based on historical data
        frequency_map = {
            'CONSULTA': 0.8,
            'EMERGENCIA': 0.3,
            'CIRUGIA': 0.1,
            'DIAGNOSTICO': 0.6,
            'MEDICAMENTOS': 0.7
        }
        return frequency_map.get(service_code, 0.5)
    
    def _extract_content_features(self, text: str) -> Dict[str, Any]:
        """Extract content-based features"""
        if not text:
            return {
                'has_medical_keywords': False,
                'has_emergency_keywords': False,
                'text_length': 0
            }
        
        text_lower = text.lower()
        
        medical_keywords = [
            'dolor', 'fiebre', 'medicamento', 'tratamiento', 'diagnostico',
            'sintoma', 'enfermedad', 'hospital', 'clinica', 'medico'
        ]
        
        emergency_keywords = [
            'urgente', 'emergencia', 'grave', 'critico', 'inmediato',
            'ambulancia', 'guardia', 'urgencia'
        ]
        
        has_medical = any(keyword in text_lower for keyword in medical_keywords)
        has_emergency = any(keyword in text_lower for keyword in emergency_keywords)
        
        return {
            'has_medical_keywords': has_medical,
            'has_emergency_keywords': has_emergency,
            'text_length': len(text)
        }
    
    def _fill_missing_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Fill missing features with default values"""
        defaults = {
            'case_age_hours': 0.0,
            'priority_numeric': 2,
            'attachment_count': 0,
            'service_code_encoded': 0,
            'insurer_encoded': 0,
            'hour_of_day': 12,
            'day_of_week': 0,
            'is_weekend': False,
            'customer_case_count_30d': 0,
            'provider_case_count_30d': 0,
            'service_frequency_score': 0.5,
            'has_medical_keywords': False,
            'has_emergency_keywords': False,
            'text_length': 0
        }
        
        for feature_name, default_value in defaults.items():
            if feature_name not in features:
                features[feature_name] = default_value
        
        return features
    
    def _get_default_features(self) -> Dict[str, Any]:
        """Get default features for fallback"""
        return self._fill_missing_features({})


class ModelManager:
    """Manage ML models with versioning and fallback"""
    
    def __init__(self, models_directory: str = "models/classification"):
        self.models_directory = Path(models_directory)
        self.models_directory.mkdir(parents=True, exist_ok=True)
        
        self.models: Dict[str, Any] = {}
        self.metadata: Dict[str, ModelMetadata] = {}
        self.active_model_version: Optional[str] = None
        self.fallback_model_version: Optional[str] = None
        
        self._load_models()
    
    def _load_models(self):
        """Load all available models"""
        try:
            # Load model metadata
            metadata_file = self.models_directory / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                
                for model_id, meta_data in metadata_dict.items():
                    meta_data['training_date'] = datetime.fromisoformat(meta_data['training_date'])
                    self.metadata[model_id] = ModelMetadata(**meta_data)
            
            # Load model files
            for model_file in self.models_directory.glob("*.pkl"):
                model_id = model_file.stem
                try:
                    model = joblib.load(model_file)
                    self.models[model_id] = model
                    logger.info(f"Loaded model: {model_id}")
                except Exception as e:
                    logger.error(f"Failed to load model {model_id}: {e}")
            
            # Set active and fallback models
            self._set_active_models()
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self._create_default_model()
    
    def _set_active_models(self):
        """Set active and fallback models based on metadata"""
        active_models = [
            (model_id, meta) for model_id, meta in self.metadata.items() 
            if meta.is_active
        ]
        
        if active_models:
            # Sort by training date, newest first
            active_models.sort(key=lambda x: x[1].training_date, reverse=True)
            self.active_model_version = active_models[0][0]
            
            # Set fallback model (second newest or specified fallback)
            if len(active_models) > 1:
                self.fallback_model_version = active_models[1][0]
            elif active_models[0][1].fallback_model:
                self.fallback_model_version = active_models[0][1].fallback_model
        
        logger.info(f"Active model: {self.active_model_version}")
        logger.info(f"Fallback model: {self.fallback_model_version}")
    
    def _create_default_model(self):
        """Create a default model for fallback"""
        logger.warning("Creating default fallback model")
        
        # Create simple default model
        model = LogisticRegression(random_state=42)
        
        # Create dummy training data
        X_dummy = np.random.rand(100, 13)  # 13 features
        y_dummy = np.random.choice(['CONSULTA', 'EMERGENCIA', 'CIRUGIA'], 100)
        
        model.fit(X_dummy, y_dummy)
        
        model_id = "default_v1.0.0"
        self.models[model_id] = model
        
        # Create metadata
        metadata = ModelMetadata(
            model_id=model_id,
            version="1.0.0",
            model_type="LogisticRegression",
            training_date=datetime.utcnow(),
            performance_metrics={"accuracy": 0.5, "f1_score": 0.5},
            feature_names=list(FeatureExtractor().feature_definitions.keys()),
            target_classes=['CONSULTA', 'EMERGENCIA', 'CIRUGIA'],
            hyperparameters={"random_state": 42},
            data_version="default",
            is_active=True
        )
        
        self.metadata[model_id] = metadata
        self.active_model_version = model_id
        self.fallback_model_version = model_id
    
    def get_model(self, version: str = None) -> Tuple[Any, ModelMetadata]:
        """Get model by version"""
        if version is None:
            version = self.active_model_version
        
        if version not in self.models:
            logger.warning(f"Model version {version} not found, using fallback")
            version = self.fallback_model_version
        
        if version not in self.models:
            raise ValueError(f"No models available")
        
        return self.models[version], self.metadata[version]
    
    def save_model(self, model: Any, metadata: ModelMetadata):
        """Save model with metadata"""
        try:
            # Save model file
            model_file = self.models_directory / f"{metadata.model_id}.pkl"
            joblib.dump(model, model_file)
            
            # Update in-memory storage
            self.models[metadata.model_id] = model
            self.metadata[metadata.model_id] = metadata
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"Saved model: {metadata.model_id}")
            
        except Exception as e:
            logger.error(f"Failed to save model {metadata.model_id}: {e}")
            raise
    
    def _save_metadata(self):
        """Save metadata to file"""
        metadata_dict = {}
        for model_id, metadata in self.metadata.items():
            meta_dict = metadata.dict()
            meta_dict['training_date'] = metadata.training_date.isoformat()
            metadata_dict[model_id] = meta_dict
        
        metadata_file = self.models_directory / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata_dict, f, indent=2)


class DriftMonitor:
    """Monitor model drift and performance degradation"""
    
    def __init__(self):
        self.baseline_stats: Dict[str, Dict] = {}
        self.recent_predictions: List[Dict] = []
        self.drift_threshold = 0.1
        self.performance_threshold = 0.05
    
    def update_baseline(self, features: Dict[str, Any], model_version: str):
        """Update baseline statistics for drift detection"""
        if model_version not in self.baseline_stats:
            self.baseline_stats[model_version] = {
                'feature_means': {},
                'feature_stds': {},
                'sample_count': 0
            }
        
        stats = self.baseline_stats[model_version]
        
        # Update running statistics
        for feature_name, value in features.items():
            if isinstance(value, (int, float)):
                if feature_name not in stats['feature_means']:
                    stats['feature_means'][feature_name] = value
                    stats['feature_stds'][feature_name] = 0.0
                else:
                    # Update running mean and std
                    n = stats['sample_count']
                    old_mean = stats['feature_means'][feature_name]
                    new_mean = (old_mean * n + value) / (n + 1)
                    stats['feature_means'][feature_name] = new_mean
                    
                    # Simplified std update
                    if n > 0:
                        stats['feature_stds'][feature_name] = abs(value - new_mean)
        
        stats['sample_count'] += 1
    
    def detect_drift(self, features: Dict[str, Any], model_version: str) -> Tuple[bool, Dict]:
        """Detect feature drift"""
        if model_version not in self.baseline_stats:
            return False, {"message": "No baseline available"}
        
        stats = self.baseline_stats[model_version]
        drift_scores = {}
        drift_detected = False
        
        for feature_name, value in features.items():
            if isinstance(value, (int, float)) and feature_name in stats['feature_means']:
                baseline_mean = stats['feature_means'][feature_name]
                baseline_std = stats['feature_stds'][feature_name]
                
                if baseline_std > 0:
                    # Calculate normalized drift score
                    drift_score = abs(value - baseline_mean) / baseline_std
                    drift_scores[feature_name] = drift_score
                    
                    if drift_score > self.drift_threshold:
                        drift_detected = True
        
        return drift_detected, {
            'drift_scores': drift_scores,
            'max_drift': max(drift_scores.values()) if drift_scores else 0.0,
            'drifted_features': [
                f for f, score in drift_scores.items() 
                if score > self.drift_threshold
            ]
        }
    
    def log_prediction(self, case_id: str, features: Dict[str, Any], 
                      prediction: str, confidence: float, model_version: str):
        """Log prediction for monitoring"""
        self.recent_predictions.append({
            'case_id': case_id,
            'timestamp': datetime.utcnow(),
            'prediction': prediction,
            'confidence': confidence,
            'model_version': model_version,
            'features': features
        })
        
        # Keep only recent predictions (last 1000)
        if len(self.recent_predictions) > 1000:
            self.recent_predictions = self.recent_predictions[-1000:]


class ClassificationService:
    """Main ML Classification Service implementing UC-OP-11"""
    
    def __init__(self, models_directory: str = "models/classification",
                 feature_store: FeatureStore = None):
        self.feature_extractor = FeatureExtractor(feature_store)
        self.model_manager = ModelManager(models_directory)
        self.drift_monitor = DriftMonitor()
        
        # Classification mappings
        self.request_type_mapping = {
            'CONSULTA': 'routine_consultation',
            'EMERGENCIA': 'emergency_care',
            'CIRUGIA': 'surgical_procedure',
            'DIAGNOSTICO': 'diagnostic_test',
            'MEDICAMENTOS': 'medication_request'
        }
        
        self.route_mapping = {
            'CONSULTA': 'standard_review',
            'EMERGENCIA': 'priority_review',
            'CIRUGIA': 'specialist_review',
            'DIAGNOSTICO': 'technical_review',
            'MEDICAMENTOS': 'pharmacy_review'
        }
        
        self.risk_mapping = {
            'CONSULTA': 'low',
            'EMERGENCIA': 'high',
            'CIRUGIA': 'high',
            'DIAGNOSTICO': 'medium',
            'MEDICAMENTOS': 'low'
        }
        
        # Policy mapping (simplified)
        self.policy_mapping = {
            'CONSULTA': ['POL_SALUD_001', 'POL_GENERAL_001'],
            'EMERGENCIA': ['POL_EMERGENCIAS_001', 'POL_SALUD_001'],
            'CIRUGIA': ['POL_CIRUGIA_001', 'POL_SALUD_001'],
            'DIAGNOSTICO': ['POL_DIAGNOSTICO_001', 'POL_SALUD_001'],
            'MEDICAMENTOS': ['POL_MEDICAMENTOS_001', 'POL_SALUD_001']
        }
        
        logger.info("Classification service initialized")
    
    def classify(self, request: ClassificationRequest) -> ClassificationResponse:
        """Main classification method implementing ML-CLASSIFY API contract"""
        start_time = datetime.utcnow()
        fallback_used = False
        drift_detected = False
        
        try:
            # Extract features
            features = self.feature_extractor.extract_features(request.features)
            
            # Get model
            model, metadata = self.model_manager.get_model(request.model_version)
            
            # Check for drift
            drift_detected, drift_info = self.drift_monitor.detect_drift(
                features, metadata.model_id
            )
            
            if drift_detected:
                logger.warning(f"Drift detected for case {request.case_id}: {drift_info}")
            
            # Prepare feature vector
            feature_vector = self._prepare_feature_vector(features, metadata.feature_names)
            
            # Make prediction
            try:
                prediction = model.predict([feature_vector])[0]
                probabilities = {}
                
                if hasattr(model, 'predict_proba') and request.include_probabilities:
                    proba = model.predict_proba([feature_vector])[0]
                    probabilities = {
                        class_name: float(prob) 
                        for class_name, prob in zip(metadata.target_classes, proba)
                    }
                
                confidence_score = max(probabilities.values()) if probabilities else 0.5
                
            except Exception as e:
                logger.error(f"Prediction failed with primary model: {e}")
                # Use fallback model
                fallback_model, fallback_metadata = self.model_manager.get_model(
                    self.model_manager.fallback_model_version
                )
                
                prediction = fallback_model.predict([feature_vector])[0]
                probabilities = {}
                confidence_score = 0.3  # Lower confidence for fallback
                fallback_used = True
                metadata = fallback_metadata
            
            # Get top features
            top_features = []
            if request.include_top_features:
                top_features = self._get_top_features(
                    model, features, metadata.feature_names, prediction
                )
            
            # Map prediction to response format
            request_type = self.request_type_mapping.get(prediction, 'unknown')
            route = self.route_mapping.get(prediction, 'manual_review')
            risk_prior = self.risk_mapping.get(prediction, 'medium')
            candidate_policy_ids = self.policy_mapping.get(prediction, [])
            
            # Log prediction for monitoring
            self.drift_monitor.log_prediction(
                request.case_id, features, prediction, confidence_score, metadata.model_id
            )
            
            # Update baseline statistics
            self.drift_monitor.update_baseline(features, metadata.model_id)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            response = ClassificationResponse(
                case_id=request.case_id,
                request_type=request_type,
                candidate_policy_ids=candidate_policy_ids,
                route=route,
                risk_prior=risk_prior,
                probabilities=probabilities,
                top_features=top_features,
                model_version=metadata.model_id,
                confidence_score=confidence_score,
                processing_time_ms=processing_time,
                fallback_used=fallback_used,
                drift_detected=drift_detected
            )
            
            logger.info(f"Classification completed for case {request.case_id}: {request_type}")
            return response
            
        except Exception as e:
            logger.error(f"Classification failed for case {request.case_id}: {e}")
            
            # Return fallback response
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ClassificationResponse(
                case_id=request.case_id,
                request_type='unknown',
                candidate_policy_ids=[],
                route='manual_review',
                risk_prior='high',
                probabilities={},
                top_features=[],
                model_version='fallback',
                confidence_score=0.1,
                processing_time_ms=processing_time,
                fallback_used=True,
                drift_detected=False
            )
    
    def _prepare_feature_vector(self, features: Dict[str, Any], 
                               feature_names: List[str]) -> np.ndarray:
        """Prepare feature vector for model prediction"""
        vector = []
        
        for feature_name in feature_names:
            value = features.get(feature_name, 0)
            
            # Convert boolean to int
            if isinstance(value, bool):
                value = int(value)
            
            # Ensure numeric
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0.0
            
            vector.append(value)
        
        return np.array(vector)
    
    def _get_top_features(self, model: Any, features: Dict[str, Any],
                         feature_names: List[str], prediction: str) -> List[Dict[str, Any]]:
        """Get top contributing features for the prediction"""
        top_features = []
        
        try:
            # For tree-based models, get feature importance
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                
                # Get top 5 features
                top_indices = np.argsort(importances)[-5:][::-1]
                
                for idx in top_indices:
                    if idx < len(feature_names):
                        feature_name = feature_names[idx]
                        top_features.append({
                            'feature_name': feature_name,
                            'importance': float(importances[idx]),
                            'value': features.get(feature_name, 0),
                            'description': self.feature_extractor.feature_definitions.get(
                                feature_name, {}
                            ).get('description', '')
                        })
            
            # For linear models, get coefficients
            elif hasattr(model, 'coef_'):
                if hasattr(model, 'classes_'):
                    # Multi-class case
                    pred_idx = list(model.classes_).index(prediction)
                    coefficients = model.coef_[pred_idx] if model.coef_.ndim > 1 else model.coef_
                else:
                    coefficients = model.coef_
                
                # Get top 5 features by absolute coefficient value
                top_indices = np.argsort(np.abs(coefficients))[-5:][::-1]
                
                for idx in top_indices:
                    if idx < len(feature_names):
                        feature_name = feature_names[idx]
                        top_features.append({
                            'feature_name': feature_name,
                            'coefficient': float(coefficients[idx]),
                            'value': features.get(feature_name, 0),
                            'description': self.feature_extractor.feature_definitions.get(
                                feature_name, {}
                            ).get('description', '')
                        })
        
        except Exception as e:
            logger.warning(f"Failed to extract top features: {e}")
        
        return top_features
    
    def get_model_info(self, version: str = None) -> Dict[str, Any]:
        """Get model information and metadata"""
        try:
            model, metadata = self.model_manager.get_model(version)
            
            return {
                'model_id': metadata.model_id,
                'version': metadata.version,
                'model_type': metadata.model_type,
                'training_date': metadata.training_date.isoformat(),
                'performance_metrics': metadata.performance_metrics,
                'feature_count': len(metadata.feature_names),
                'target_classes': metadata.target_classes,
                'is_active': metadata.is_active,
                'fallback_model': metadata.fallback_model
            }
        
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {'error': str(e)}
    
    def get_drift_status(self) -> Dict[str, Any]:
        """Get drift monitoring status"""
        return {
            'baseline_models': list(self.drift_monitor.baseline_stats.keys()),
            'recent_predictions_count': len(self.drift_monitor.recent_predictions),
            'drift_threshold': self.drift_monitor.drift_threshold,
            'performance_threshold': self.drift_monitor.performance_threshold
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the classification service"""
        try:
            # Test with dummy data
            dummy_request = ClassificationRequest(
                case_id="health_check",
                features={
                    'created_at': datetime.utcnow().isoformat(),
                    'priority': 'MEDIUM',
                    'service_code': 'CONSULTA',
                    'insurer_id': 'TEST_INSURER'
                }
            )
            
            response = self.classify(dummy_request)
            
            return {
                'status': 'healthy',
                'active_model': self.model_manager.active_model_version,
                'fallback_model': self.model_manager.fallback_model_version,
                'test_prediction': response.request_type,
                'processing_time_ms': response.processing_time_ms
            }
        
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Factory function
def create_classification_service(models_directory: str = "models/classification",
                                feature_store: FeatureStore = None) -> ClassificationService:
    """Factory function to create classification service"""
    return ClassificationService(models_directory, feature_store)


# Utility functions
def classify_case(case_data: Dict[str, Any], model_version: str = None,
                 service: ClassificationService = None) -> ClassificationResponse:
    """Utility function to classify a case"""
    if service is None:
        service = create_classification_service()
    
    request = ClassificationRequest(
        case_id=case_data.get('case_id', str(uuid4())),
        features=case_data,
        model_version=model_version
    )
    
    return service.classify(request)


def batch_classify(cases: List[Dict[str, Any]], model_version: str = None,
                  service: ClassificationService = None) -> List[ClassificationResponse]:
    """Batch classification of multiple cases"""
    if service is None:
        service = create_classification_service()
    
    results = []
    for case_data in cases:
        try:
            result = classify_case(case_data, model_version, service)
            results.append(result)
        except Exception as e:
            logger.error(f"Batch classification failed for case {case_data.get('case_id')}: {e}")
            # Add error response
            results.append(ClassificationResponse(
                case_id=case_data.get('case_id', 'unknown'),
                request_type='error',
                candidate_policy_ids=[],
                route='manual_review',
                risk_prior='high',
                probabilities={},
                top_features=[],
                model_version='error',
                confidence_score=0.0,
                processing_time_ms=0.0,
                fallback_used=True
            ))
    
    return results
