"""
Classification Service for DERCAS 01 Policy Validation Copilot

Implements ML-CLASSIFY contract from Anexo B for case classification and routing.
Provides request type prediction, candidate policy identification, and risk assessment.
"""

import logging
import pickle
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from .base import MLServiceBase, MLConfig, calculate_confidence_score, extract_top_features
from ..models.api import ClassificationRequest, ClassificationResponse
from ..models.enums import MLModelType

logger = logging.getLogger(__name__)


class ClassificationConfig(MLConfig):
    """Configuration for classification service."""
    
    model_type: MLModelType = MLModelType.CLASSIFICATION
    
    # Classification-specific settings
    max_candidate_policies: int = 5
    min_policy_confidence: float = 0.3
    risk_threshold_high: float = 0.7
    risk_threshold_medium: float = 0.4
    
    # Feature configuration
    text_features: List[str] = ["service_description", "provider_notes"]
    categorical_features: List[str] = ["insurer_id", "plan_id", "service_code", "provider_id"]
    numeric_features: List[str] = ["service_amount", "patient_age", "days_since_last_service"]
    
    # Model parameters
    n_estimators: int = 100
    max_depth: int = 10
    random_state: int = 42
    
    # Routing configuration
    route_mapping: Dict[str, str] = {
        "ROUTINE": "AUTO_PROCESSING",
        "COMPLEX": "HITL_AGENT",
        "HIGH_RISK": "HITL_SUPERVISOR",
        "EMERGENCY": "PRIORITY_QUEUE",
    }


class ClassificationService(MLServiceBase):
    """
    Classification service implementing ML-CLASSIFY contract.
    
    Provides:
    - Request type classification
    - Candidate policy identification
    - Processing route recommendation
    - Risk assessment
    """
    
    def __init__(self, config: ClassificationConfig):
        super().__init__(config)
        self.config: ClassificationConfig = config
        
        # Model components
        self.request_type_classifier = None
        self.risk_classifier = None
        self.text_vectorizer = None
        self.categorical_encoders = {}
        self.numeric_scaler = None
        
        # Policy mapping
        self.policy_index = {}
        self.policy_embeddings = None
        
        # Feature importance tracking
        self.feature_importance = {}
    
    def _load_model(self) -> Dict[str, Any]:
        """Load classification models and preprocessors."""
        try:
            if self.config.model_path:
                # Load from file
                with open(self.config.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.request_type_classifier = model_data['request_type_classifier']
                self.risk_classifier = model_data['risk_classifier']
                self.text_vectorizer = model_data['text_vectorizer']
                self.categorical_encoders = model_data['categorical_encoders']
                self.numeric_scaler = model_data['numeric_scaler']
                self.policy_index = model_data.get('policy_index', {})
                self.policy_embeddings = model_data.get('policy_embeddings')
                self.feature_importance = model_data.get('feature_importance', {})
                
                logger.info(f"Loaded classification model from {self.config.model_path}")
            else:
                # Initialize default models
                self._initialize_default_models()
                logger.info("Initialized default classification models")
            
            return {
                "request_type_classifier": self.request_type_classifier,
                "risk_classifier": self.risk_classifier,
                "text_vectorizer": self.text_vectorizer,
            }
            
        except Exception as e:
            logger.error(f"Failed to load classification model: {e}")
            raise
    
    def _initialize_default_models(self):
        """Initialize default models when no trained model is available."""
        # Request type classifier
        self.request_type_classifier = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state
        )
        
        # Risk classifier
        self.risk_classifier = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state
        )
        
        # Text vectorizer
        self.text_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Numeric scaler
        self.numeric_scaler = StandardScaler()
        
        # Initialize with dummy data for fallback
        self._train_dummy_models()
    
    def _train_dummy_models(self):
        """Train models with dummy data for fallback functionality."""
        try:
            # Create dummy training data
            dummy_data = self._generate_dummy_training_data()
            
            # Extract features
            X, _ = self._extract_features(dummy_data)
            
            # Create dummy labels
            request_types = ['ROUTINE', 'COMPLEX', 'HIGH_RISK', 'EMERGENCY']
            risk_levels = ['LOW', 'MEDIUM', 'HIGH']
            
            y_request = np.random.choice(request_types, size=len(dummy_data))
            y_risk = np.random.choice(risk_levels, size=len(dummy_data))
            
            # Train models
            self.request_type_classifier.fit(X, y_request)
            self.risk_classifier.fit(X, y_risk)
            
            logger.info("Trained dummy classification models")
            
        except Exception as e:
            logger.warning(f"Failed to train dummy models: {e}")
    
    def _generate_dummy_training_data(self) -> List[Dict[str, Any]]:
        """Generate dummy training data for model initialization."""
        dummy_data = []
        
        insurers = ['INS001', 'INS002', 'INS003']
        plans = ['PLAN_A', 'PLAN_B', 'PLAN_C']
        services = ['SRV001', 'SRV002', 'SRV003']
        providers = ['PROV001', 'PROV002', 'PROV003']
        
        for i in range(100):
            dummy_data.append({
                'insurer_id': np.random.choice(insurers),
                'plan_id': np.random.choice(plans),
                'service_code': np.random.choice(services),
                'provider_id': np.random.choice(providers),
                'service_description': f'Medical service {i}',
                'provider_notes': f'Provider notes {i}',
                'service_amount': np.random.uniform(100, 5000),
                'patient_age': np.random.randint(18, 80),
                'days_since_last_service': np.random.randint(0, 365),
            })
        
        return dummy_data
    
    def _predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make classification prediction."""
        try:
            # Extract and transform features
            feature_vector, feature_names = self._extract_features([features])
            
            if len(feature_vector) == 0:
                raise ValueError("No valid features extracted")
            
            # Get request type prediction
            request_type_probs = self.request_type_classifier.predict_proba(feature_vector)[0]
            request_type_classes = self.request_type_classifier.classes_
            request_type = request_type_classes[np.argmax(request_type_probs)]
            
            # Get risk prediction
            risk_probs = self.risk_classifier.predict_proba(feature_vector)[0]
            risk_classes = self.risk_classifier.classes_
            risk_prior = np.max(risk_probs)
            
            # Create probability dictionary
            probabilities = {
                cls: float(prob) for cls, prob in zip(request_type_classes, request_type_probs)
            }
            
            # Get candidate policies
            candidate_policy_ids = self._get_candidate_policies(features)
            
            # Determine processing route
            route = self._determine_route(request_type, risk_prior, features)
            
            # Calculate confidence
            confidence = calculate_confidence_score(probabilities, method="max")
            
            # Get top features
            top_features = self._get_top_features(feature_vector, feature_names)
            
            return {
                "request_type": request_type,
                "candidate_policy_ids": candidate_policy_ids,
                "route": route,
                "risk_prior": float(risk_prior),
                "probabilities": probabilities,
                "top_features": top_features,
                "confidence": confidence,
            }
            
        except Exception as e:
            logger.error(f"Classification prediction failed: {e}")
            raise
    
    def _extract_features(self, data: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
        """Extract and transform features from raw data."""
        try:
            df = pd.DataFrame(data)
            feature_vectors = []
            feature_names = []
            
            # Text features
            text_features = []
            for text_col in self.config.text_features:
                if text_col in df.columns:
                    text_data = df[text_col].fillna('').astype(str)
                    text_features.extend(text_data.tolist())
            
            if text_features:
                if hasattr(self.text_vectorizer, 'vocabulary_'):
                    # Transform using fitted vectorizer
                    text_vectors = self.text_vectorizer.transform(text_features)
                else:
                    # Fit and transform
                    text_vectors = self.text_vectorizer.fit_transform(text_features)
                
                feature_vectors.append(text_vectors.toarray())
                feature_names.extend([f"text_{i}" for i in range(text_vectors.shape[1])])
            
            # Categorical features
            categorical_vectors = []
            for cat_col in self.config.categorical_features:
                if cat_col in df.columns:
                    cat_data = df[cat_col].fillna('UNKNOWN').astype(str)
                    
                    if cat_col not in self.categorical_encoders:
                        self.categorical_encoders[cat_col] = LabelEncoder()
                        encoded = self.categorical_encoders[cat_col].fit_transform(cat_data)
                    else:
                        # Handle unseen categories
                        encoder = self.categorical_encoders[cat_col]
                        encoded = []
                        for value in cat_data:
                            if value in encoder.classes_:
                                encoded.append(encoder.transform([value])[0])
                            else:
                                encoded.append(-1)  # Unknown category
                        encoded = np.array(encoded)
                    
                    categorical_vectors.append(encoded.reshape(-1, 1))
                    feature_names.append(f"cat_{cat_col}")
            
            if categorical_vectors:
                feature_vectors.append(np.hstack(categorical_vectors))
            
            # Numeric features
            numeric_data = []
            for num_col in self.config.numeric_features:
                if num_col in df.columns:
                    numeric_data.append(df[num_col].fillna(0).astype(float))
                    feature_names.append(f"num_{num_col}")
            
            if numeric_data:
                numeric_array = np.column_stack(numeric_data)
                
                if hasattr(self.numeric_scaler, 'scale_'):
                    # Transform using fitted scaler
                    numeric_scaled = self.numeric_scaler.transform(numeric_array)
                else:
                    # Fit and transform
                    numeric_scaled = self.numeric_scaler.fit_transform(numeric_array)
                
                feature_vectors.append(numeric_scaled)
            
            # Combine all features
            if feature_vectors:
                combined_features = np.hstack(feature_vectors)
            else:
                combined_features = np.array([]).reshape(len(data), 0)
            
            return combined_features, feature_names
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise
    
    def _get_candidate_policies(self, features: Dict[str, Any]) -> List[str]:
        """Get candidate policy IDs based on features."""
        try:
            # Simple rule-based policy matching
            candidates = []
            
            insurer_id = features.get('insurer_id')
            plan_id = features.get('plan_id')
            service_code = features.get('service_code')
            
            # Generate candidate policy IDs based on business rules
            if insurer_id and plan_id:
                # Primary policy for insurer-plan combination
                primary_policy = f"POL_{insurer_id}_{plan_id}_MAIN"
                candidates.append(primary_policy)
                
                # Service-specific policies
                if service_code:
                    service_policy = f"POL_{insurer_id}_{plan_id}_{service_code}"
                    candidates.append(service_policy)
                
                # General policies
                general_policy = f"POL_{insurer_id}_GENERAL"
                candidates.append(general_policy)
            
            # Limit to max candidates
            candidates = candidates[:self.config.max_candidate_policies]
            
            # Add confidence-based filtering if policy embeddings are available
            if self.policy_embeddings is not None:
                candidates = self._filter_policies_by_similarity(features, candidates)
            
            return candidates
            
        except Exception as e:
            logger.warning(f"Failed to get candidate policies: {e}")
            return []
    
    def _filter_policies_by_similarity(self, features: Dict[str, Any], candidates: List[str]) -> List[str]:
        """Filter policies by similarity to case features."""
        # Placeholder for semantic similarity filtering
        # In production, this would use policy embeddings and case feature embeddings
        return candidates
    
    def _determine_route(self, request_type: str, risk_prior: float, features: Dict[str, Any]) -> str:
        """Determine processing route based on classification results."""
        try:
            # Check for emergency conditions
            if self._is_emergency_case(features):
                return self.config.route_mapping.get("EMERGENCY", "PRIORITY_QUEUE")
            
            # Route based on risk level
            if risk_prior >= self.config.risk_threshold_high:
                return self.config.route_mapping.get("HIGH_RISK", "HITL_SUPERVISOR")
            elif risk_prior >= self.config.risk_threshold_medium:
                return self.config.route_mapping.get("COMPLEX", "HITL_AGENT")
            
            # Route based on request type
            return self.config.route_mapping.get(request_type, "AUTO_PROCESSING")
            
        except Exception as e:
            logger.warning(f"Failed to determine route: {e}")
            return "AUTO_PROCESSING"
    
    def _is_emergency_case(self, features: Dict[str, Any]) -> bool:
        """Check if case requires emergency processing."""
        # Emergency conditions
        service_amount = features.get('service_amount', 0)
        if service_amount > 50000:  # High-value services
            return True
        
        service_description = features.get('service_description', '').lower()
        emergency_keywords = ['emergency', 'urgent', 'critical', 'life-threatening']
        if any(keyword in service_description for keyword in emergency_keywords):
            return True
        
        return False
    
    def _get_top_features(self, feature_vector: np.ndarray, feature_names: List[str]) -> List[Dict[str, Any]]:
        """Get top contributing features for the prediction."""
        try:
            if hasattr(self.request_type_classifier, 'feature_importances_'):
                importance_scores = self.request_type_classifier.feature_importances_
                
                # Create feature importance dictionary
                feature_importance = {}
                for i, name in enumerate(feature_names):
                    if i < len(importance_scores):
                        feature_importance[name] = float(importance_scores[i])
                
                return extract_top_features(feature_importance, top_k=5)
            else:
                return []
                
        except Exception as e:
            logger.warning(f"Failed to get top features: {e}")
            return []
    
    def _get_fallback_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback prediction when main model fails."""
        try:
            # Simple rule-based fallback
            insurer_id = features.get('insurer_id', 'UNKNOWN')
            service_amount = features.get('service_amount', 0)
            
            # Determine request type based on simple rules
            if service_amount > 10000:
                request_type = "COMPLEX"
                risk_prior = 0.7
            elif service_amount > 5000:
                request_type = "ROUTINE"
                risk_prior = 0.4
            else:
                request_type = "ROUTINE"
                risk_prior = 0.2
            
            # Generate basic candidate policies
            candidate_policy_ids = [f"POL_{insurer_id}_FALLBACK"]
            
            # Determine route
            route = self._determine_route(request_type, risk_prior, features)
            
            return {
                "request_type": request_type,
                "candidate_policy_ids": candidate_policy_ids,
                "route": route,
                "risk_prior": risk_prior,
                "probabilities": {request_type: 1.0},
                "top_features": [],
                "confidence": self.config.fallback_confidence,
            }
            
        except Exception as e:
            logger.error(f"Fallback prediction failed: {e}")
            raise
    
    def train_model(self, training_data: List[Dict[str, Any]], labels: Dict[str, List[str]]) -> Dict[str, float]:
        """
        Train the classification model with new data.
        
        Args:
            training_data: List of training examples
            labels: Dictionary with 'request_type' and 'risk_level' labels
            
        Returns:
            Training metrics
        """
        try:
            logger.info(f"Training classification model with {len(training_data)} examples")
            
            # Extract features
            X, feature_names = self._extract_features(training_data)
            
            # Get labels
            y_request = labels['request_type']
            y_risk = labels['risk_level']
            
            # Split data
            X_train, X_test, y_req_train, y_req_test, y_risk_train, y_risk_test = train_test_split(
                X, y_request, y_risk, test_size=0.2, random_state=self.config.random_state
            )
            
            # Train request type classifier
            self.request_type_classifier.fit(X_train, y_req_train)
            req_pred = self.request_type_classifier.predict(X_test)
            req_accuracy = accuracy_score(y_req_test, req_pred)
            
            # Train risk classifier
            self.risk_classifier.fit(X_train, y_risk_train)
            risk_pred = self.risk_classifier.predict(X_test)
            risk_accuracy = accuracy_score(y_risk_test, risk_pred)
            
            # Update feature importance
            if hasattr(self.request_type_classifier, 'feature_importances_'):
                self.feature_importance = {
                    name: float(importance) 
                    for name, importance in zip(feature_names, self.request_type_classifier.feature_importances_)
                }
            
            metrics = {
                "request_type_accuracy": req_accuracy,
                "risk_accuracy": risk_accuracy,
                "training_samples": len(training_data),
                "feature_count": X.shape[1],
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
                'request_type_classifier': self.request_type_classifier,
                'risk_classifier': self.risk_classifier,
                'text_vectorizer': self.text_vectorizer,
                'categorical_encoders': self.categorical_encoders,
                'numeric_scaler': self.numeric_scaler,
                'policy_index': self.policy_index,
                'policy_embeddings': self.policy_embeddings,
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
    
    def update_policy_index(self, policy_mappings: Dict[str, Dict[str, Any]]):
        """Update the policy index for candidate selection."""
        try:
            self.policy_index = policy_mappings
            logger.info(f"Updated policy index with {len(policy_mappings)} policies")
            
        except Exception as e:
            logger.error(f"Failed to update policy index: {e}")
            raise


# Factory function
def create_classification_service(config: Optional[ClassificationConfig] = None) -> ClassificationService:
    """Create a classification service with default or custom configuration."""
    if config is None:
        config = ClassificationConfig()
    
    return ClassificationService(config)


# Utility functions for classification
def preprocess_case_for_classification(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess case data for classification."""
    processed = {}
    
    # Extract relevant fields
    field_mapping = {
        'insurer_id': 'insurer_id',
        'plan_id': 'plan_id',
        'service_code': 'service_code',
        'provider_id': 'provider_id',
        'service_description': 'service_description',
    }
    
    for source_field, target_field in field_mapping.items():
        if source_field in case_data:
            processed[target_field] = case_data[source_field]
    
    # Calculate derived features
    if 'service_date' in case_data and case_data['service_date']:
        service_date = pd.to_datetime(case_data['service_date'])
        processed['days_since_service'] = (datetime.now() - service_date).days
    
    # Add context features
    if 'context' in case_data and isinstance(case_data['context'], dict):
        context = case_data['context']
        processed['service_amount'] = context.get('service_amount', 0)
        processed['patient_age'] = context.get('patient_age', 0)
        processed['provider_notes'] = context.get('provider_notes', '')
    
    return processed


def validate_classification_response(response: Dict[str, Any]) -> bool:
    """Validate classification response format."""
    required_fields = [
        'request_type', 'candidate_policy_ids', 'route', 
        'risk_prior', 'probabilities', 'top_features'
    ]
    
    for field in required_fields:
        if field not in response:
            return False
    
    # Validate probabilities sum to ~1.0
    probs = response.get('probabilities', {})
    if probs and abs(sum(probs.values()) - 1.0) > 0.1:
        return False
    
    # Validate risk_prior is in [0, 1]
    risk_prior = response.get('risk_prior', 0)
    if not (0 <= risk_prior <= 1):
        return False
    
    return True
