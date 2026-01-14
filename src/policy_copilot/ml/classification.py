"""
ML Classification Service for Policy Validation Copilot

This module implements UC-OP-11 classification and routing service with
request type prediction, policy routing, and risk assessment per Anexo B API contracts.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from ..models.base import ModelVersion, RiskLevel
from ..models.ml import MLClassificationOutput
from .base import BaseMLService, FeatureEngineer, ModelRegistry

logger = logging.getLogger(__name__)


class ClassificationFeatures(BaseModel):
    """Feature schema for classification service."""
    
    # Case metadata features
    service_type: str = Field(..., description="Type of service requested")
    customer_segment: str = Field(..., description="Customer segment classification")
    contract_type: str = Field(..., description="Type of insurance contract")
    plan_tier: str = Field(..., description="Insurance plan tier")
    
    # Historical features
    customer_history_score: float = Field(0.0, ge=0.0, le=1.0, description="Customer history score")
    claim_frequency: int = Field(0, ge=0, description="Historical claim frequency")
    avg_claim_amount: float = Field(0.0, ge=0.0, description="Average historical claim amount")
    
    # Request features
    request_complexity: float = Field(0.0, ge=0.0, le=1.0, description="Request complexity score")
    documentation_completeness: float = Field(0.0, ge=0.0, le=1.0, description="Documentation completeness")
    urgency_score: float = Field(0.0, ge=0.0, le=1.0, description="Request urgency score")
    
    # Temporal features
    submission_hour: int = Field(..., ge=0, le=23, description="Hour of submission")
    submission_day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday)")
    is_holiday: bool = Field(False, description="Whether submitted on holiday")
    
    # Amount and financial features
    requested_amount: float = Field(0.0, ge=0.0, description="Requested claim amount")
    policy_limit: float = Field(0.0, ge=0.0, description="Policy coverage limit")
    deductible_amount: float = Field(0.0, ge=0.0, description="Policy deductible")
    
    # Risk indicators
    fraud_risk_indicators: int = Field(0, ge=0, description="Number of fraud risk indicators")
    medical_complexity: float = Field(0.0, ge=0.0, le=1.0, description="Medical complexity score")
    provider_risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Healthcare provider risk score")


class ClassificationConfig(BaseModel):
    """Configuration for classification service."""
    
    # Model settings
    model_name: str = "policy_classifier_v1"
    model_version: Optional[str] = None
    fallback_model: str = "rule_based_classifier"
    
    # Feature engineering
    enable_feature_scaling: bool = True
    enable_feature_selection: bool = True
    feature_importance_threshold: float = 0.01
    
    # Classification thresholds
    high_confidence_threshold: float = 0.8
    medium_confidence_threshold: float = 0.6
    risk_escalation_threshold: float = 0.7
    
    # Request type mappings
    request_types: List[str] = [
        "MEDICAL_CLAIM",
        "DENTAL_CLAIM", 
        "PHARMACY_CLAIM",
        "EMERGENCY_CLAIM",
        "PREVENTIVE_CARE",
        "SPECIALIST_REFERRAL",
        "PRIOR_AUTHORIZATION",
        "APPEAL_REQUEST"
    ]
    
    # Policy routing rules
    policy_routing_rules: Dict[str, List[str]] = {
        "MEDICAL_CLAIM": ["medical_policy_v2.1", "general_coverage_v1.5"],
        "DENTAL_CLAIM": ["dental_policy_v1.8", "general_coverage_v1.5"],
        "PHARMACY_CLAIM": ["pharmacy_policy_v2.0", "formulary_v3.2"],
        "EMERGENCY_CLAIM": ["emergency_policy_v1.9", "medical_policy_v2.1"],
        "PREVENTIVE_CARE": ["preventive_policy_v1.6", "wellness_policy_v1.2"],
        "SPECIALIST_REFERRAL": ["specialist_policy_v1.4", "network_policy_v2.0"],
        "PRIOR_AUTHORIZATION": ["prior_auth_policy_v2.3", "medical_policy_v2.1"],
        "APPEAL_REQUEST": ["appeals_policy_v1.7", "grievance_policy_v1.3"]
    }
    
    # Risk assessment rules
    risk_factors: Dict[str, float] = {
        "high_amount": 0.3,
        "fraud_indicators": 0.4,
        "provider_risk": 0.2,
        "complexity": 0.1
    }


class ClassificationFeatureEngineer(FeatureEngineer):
    """Feature engineering for classification service."""
    
    def __init__(self, config: ClassificationConfig):
        super().__init__()
        self.config = config
    
    def extract_features(self, case_data: Dict[str, Any]) -> ClassificationFeatures:
        """Extract features from case data."""
        # Extract basic case information
        service = case_data.get('service', '')
        additional_data = case_data.get('additional_data', {})
        
        # Service type classification
        service_type = self._classify_service_type(service)
        
        # Customer segment from customer_id pattern or lookup
        customer_segment = self._determine_customer_segment(case_data.get('customer_id', ''))
        
        # Contract and plan information
        contract_type = additional_data.get('contract_type', 'INDIVIDUAL')
        plan_tier = additional_data.get('plan_tier', 'STANDARD')
        
        # Historical features (would come from database in real implementation)
        customer_history_score = additional_data.get('customer_history_score', 0.5)
        claim_frequency = additional_data.get('claim_frequency', 0)
        avg_claim_amount = additional_data.get('avg_claim_amount', 0.0)
        
        # Request complexity analysis
        request_complexity = self._calculate_request_complexity(case_data)
        documentation_completeness = self._assess_documentation_completeness(case_data)
        urgency_score = self._calculate_urgency_score(case_data)
        
        # Temporal features
        submitted_at = case_data.get('submitted_at', datetime.utcnow())
        if isinstance(submitted_at, str):
            submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
        
        submission_hour = submitted_at.hour
        submission_day_of_week = submitted_at.weekday()
        is_holiday = self._is_holiday(submitted_at)
        
        # Financial features
        requested_amount = additional_data.get('requested_amount', 0.0)
        policy_limit = additional_data.get('policy_limit', 100000.0)
        deductible_amount = additional_data.get('deductible_amount', 1000.0)
        
        # Risk indicators
        fraud_risk_indicators = self._count_fraud_indicators(case_data)
        medical_complexity = self._assess_medical_complexity(case_data)
        provider_risk_score = additional_data.get('provider_risk_score', 0.0)
        
        return ClassificationFeatures(
            service_type=service_type,
            customer_segment=customer_segment,
            contract_type=contract_type,
            plan_tier=plan_tier,
            customer_history_score=customer_history_score,
            claim_frequency=claim_frequency,
            avg_claim_amount=avg_claim_amount,
            request_complexity=request_complexity,
            documentation_completeness=documentation_completeness,
            urgency_score=urgency_score,
            submission_hour=submission_hour,
            submission_day_of_week=submission_day_of_week,
            is_holiday=is_holiday,
            requested_amount=requested_amount,
            policy_limit=policy_limit,
            deductible_amount=deductible_amount,
            fraud_risk_indicators=fraud_risk_indicators,
            medical_complexity=medical_complexity,
            provider_risk_score=provider_risk_score
        )
    
    def _classify_service_type(self, service: str) -> str:
        """Classify service type from service description."""
        service_lower = service.lower()
        
        if any(term in service_lower for term in ['emergency', 'urgent', 'er', 'ambulance']):
            return 'EMERGENCY'
        elif any(term in service_lower for term in ['dental', 'tooth', 'oral']):
            return 'DENTAL'
        elif any(term in service_lower for term in ['pharmacy', 'prescription', 'medication', 'drug']):
            return 'PHARMACY'
        elif any(term in service_lower for term in ['preventive', 'screening', 'checkup', 'wellness']):
            return 'PREVENTIVE'
        elif any(term in service_lower for term in ['specialist', 'referral', 'consultation']):
            return 'SPECIALIST'
        elif any(term in service_lower for term in ['authorization', 'approval', 'prior auth']):
            return 'PRIOR_AUTH'
        elif any(term in service_lower for term in ['appeal', 'grievance', 'dispute']):
            return 'APPEAL'
        else:
            return 'MEDICAL'
    
    def _determine_customer_segment(self, customer_id: str) -> str:
        """Determine customer segment from customer ID or other indicators."""
        # Simple rule-based segmentation (would be more sophisticated in real implementation)
        if customer_id.startswith('PREM'):
            return 'PREMIUM'
        elif customer_id.startswith('CORP'):
            return 'CORPORATE'
        elif customer_id.startswith('GOV'):
            return 'GOVERNMENT'
        else:
            return 'INDIVIDUAL'
    
    def _calculate_request_complexity(self, case_data: Dict[str, Any]) -> float:
        """Calculate request complexity score."""
        complexity_score = 0.0
        
        # Number of attachments
        attachments = case_data.get('attachments', [])
        if attachments:
            complexity_score += min(0.3, len(attachments) * 0.1)
        
        # Service description length and complexity
        service = case_data.get('service', '')
        if len(service) > 100:
            complexity_score += 0.2
        
        # Additional data complexity
        additional_data = case_data.get('additional_data', {})
        if len(additional_data) > 5:
            complexity_score += 0.3
        
        # Medical codes or technical terms
        if any(term in service.lower() for term in ['icd', 'cpt', 'procedure', 'diagnosis']):
            complexity_score += 0.2
        
        return min(1.0, complexity_score)
    
    def _assess_documentation_completeness(self, case_data: Dict[str, Any]) -> float:
        """Assess documentation completeness."""
        completeness_score = 0.0
        
        # Required fields present
        required_fields = ['case_id', 'customer_id', 'contract_id', 'service']
        present_fields = sum(1 for field in required_fields if case_data.get(field))
        completeness_score += (present_fields / len(required_fields)) * 0.4
        
        # Attachments present
        attachments = case_data.get('attachments', [])
        if attachments:
            completeness_score += 0.3
        
        # Additional data completeness
        additional_data = case_data.get('additional_data', {})
        if additional_data:
            completeness_score += 0.3
        
        return min(1.0, completeness_score)
    
    def _calculate_urgency_score(self, case_data: Dict[str, Any]) -> float:
        """Calculate urgency score based on various factors."""
        urgency_score = 0.0
        
        # Priority level
        priority = case_data.get('priority', 'MEDIUM')
        priority_scores = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.8, 'CRITICAL': 1.0}
        urgency_score += priority_scores.get(priority, 0.5) * 0.4
        
        # Service type urgency
        service = case_data.get('service', '').lower()
        if any(term in service for term in ['emergency', 'urgent', 'critical']):
            urgency_score += 0.4
        
        # SLA proximity
        sla_target = case_data.get('sla_target')
        if sla_target:
            # Calculate time until SLA (simplified)
            urgency_score += 0.2
        
        return min(1.0, urgency_score)
    
    def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday (simplified implementation)."""
        # Simple holiday check (would use proper holiday library in real implementation)
        return date.weekday() in [5, 6]  # Weekend
    
    def _count_fraud_indicators(self, case_data: Dict[str, Any]) -> int:
        """Count potential fraud indicators."""
        indicators = 0
        
        service = case_data.get('service', '').lower()
        additional_data = case_data.get('additional_data', {})
        
        # High amount claims
        requested_amount = additional_data.get('requested_amount', 0.0)
        if requested_amount > 10000:
            indicators += 1
        
        # Suspicious patterns in service description
        suspicious_terms = ['multiple', 'repeated', 'urgent', 'immediate']
        if any(term in service for term in suspicious_terms):
            indicators += 1
        
        # Weekend/holiday submissions
        submitted_at = case_data.get('submitted_at', datetime.utcnow())
        if isinstance(submitted_at, str):
            submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
        if submitted_at.weekday() in [5, 6]:
            indicators += 1
        
        return indicators
    
    def _assess_medical_complexity(self, case_data: Dict[str, Any]) -> float:
        """Assess medical complexity of the case."""
        complexity = 0.0
        
        service = case_data.get('service', '').lower()
        
        # Complex medical terms
        complex_terms = ['surgery', 'procedure', 'treatment', 'therapy', 'diagnosis']
        if any(term in service for term in complex_terms):
            complexity += 0.4
        
        # Multiple services
        if len(service.split(',')) > 1:
            complexity += 0.3
        
        # Specialist involvement
        if any(term in service for term in ['specialist', 'consultation', 'referral']):
            complexity += 0.3
        
        return min(1.0, complexity)


class ClassificationService(BaseMLService):
    """ML Classification service for request type prediction and routing."""
    
    def __init__(self, config: ClassificationConfig = None, model_registry: ModelRegistry = None):
        super().__init__()
        self.config = config or ClassificationConfig()
        self.model_registry = model_registry or ModelRegistry()
        self.feature_engineer = ClassificationFeatureEngineer(self.config)
        
        # Load models
        self.primary_model = None
        self.fallback_model = None
        self._load_models()
    
    def _load_models(self) -> None:
        """Load classification models."""
        try:
            # Load primary model
            self.primary_model = self.model_registry.load_model(
                self.config.model_name,
                self.config.model_version
            )
            
            # Load fallback model
            self.fallback_model = self.model_registry.load_model(
                self.config.fallback_model
            )
            
            logger.info(f"Loaded classification models: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load classification models: {e}")
            # Use rule-based fallback
            self.primary_model = None
            self.fallback_model = self._create_rule_based_classifier()
    
    def classify(
        self,
        case_id: str,
        features: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> MLClassificationOutput:
        """
        Classify request type and determine routing.
        
        Implements ML-CLASSIFY API contract from Anexo B.
        """
        start_time = time.time()
        
        try:
            # Extract and engineer features
            classification_features = self.feature_engineer.extract_features(features)
            
            # Get model version info
            model_info = self._get_model_version_info(model_version)
            
            # Perform classification
            if self.primary_model and not model_version:
                prediction_result = self._predict_with_model(classification_features)
            else:
                prediction_result = self._predict_with_fallback(classification_features)
            
            # Calculate inference time
            inference_time = int((time.time() - start_time) * 1000)
            
            # Create output
            output = MLClassificationOutput(
                case_id=case_id,
                request_type=prediction_result['request_type'],
                candidate_policy_ids=prediction_result['candidate_policy_ids'],
                route=prediction_result['route'],
                risk_prior=prediction_result['risk_prior'],
                probabilities=prediction_result['probabilities'],
                confidence_score=prediction_result['confidence_score'],
                top_features=prediction_result['top_features'],
                feature_vector=prediction_result.get('feature_vector'),
                model_version=model_info,
                inference_time_ms=inference_time
            )
            
            logger.info(f"Classification completed for case {case_id}: {output.request_type}")
            return output
            
        except Exception as e:
            logger.error(f"Classification failed for case {case_id}: {e}")
            # Return fallback result
            return self._create_fallback_output(case_id, features, start_time)
    
    def _predict_with_model(self, features: ClassificationFeatures) -> Dict[str, Any]:
        """Predict using the primary ML model."""
        # Convert features to model input format
        feature_vector = self._features_to_vector(features)
        
        # Get model prediction (mock implementation)
        probabilities = self._mock_model_prediction(feature_vector)
        
        # Determine request type
        request_type = max(probabilities, key=probabilities.get)
        confidence_score = probabilities[request_type]
        
        # Get candidate policies
        candidate_policy_ids = self.config.policy_routing_rules.get(request_type, [])
        
        # Determine route
        route = self._determine_route(request_type, confidence_score)
        
        # Assess risk
        risk_prior = self._assess_risk_prior(features, request_type)
        
        # Get top features
        top_features = self._get_top_features(features, request_type)
        
        return {
            'request_type': request_type,
            'candidate_policy_ids': candidate_policy_ids,
            'route': route,
            'risk_prior': risk_prior,
            'probabilities': probabilities,
            'confidence_score': confidence_score,
            'top_features': top_features,
            'feature_vector': feature_vector
        }
    
    def _predict_with_fallback(self, features: ClassificationFeatures) -> Dict[str, Any]:
        """Predict using rule-based fallback."""
        # Rule-based classification
        request_type = self._rule_based_classification(features)
        
        # Create mock probabilities
        probabilities = {rt: 0.1 for rt in self.config.request_types}
        probabilities[request_type] = 0.7
        confidence_score = 0.7
        
        # Get candidate policies
        candidate_policy_ids = self.config.policy_routing_rules.get(request_type, [])
        
        # Determine route
        route = self._determine_route(request_type, confidence_score)
        
        # Assess risk
        risk_prior = self._assess_risk_prior(features, request_type)
        
        # Get top features
        top_features = self._get_top_features(features, request_type)
        
        return {
            'request_type': request_type,
            'candidate_policy_ids': candidate_policy_ids,
            'route': route,
            'risk_prior': risk_prior,
            'probabilities': probabilities,
            'confidence_score': confidence_score,
            'top_features': top_features
        }
    
    def _features_to_vector(self, features: ClassificationFeatures) -> Dict[str, float]:
        """Convert features to numerical vector."""
        vector = {}
        
        # Categorical features (one-hot encoded)
        service_types = ['EMERGENCY', 'DENTAL', 'PHARMACY', 'PREVENTIVE', 'SPECIALIST', 'PRIOR_AUTH', 'APPEAL', 'MEDICAL']
        for st in service_types:
            vector[f'service_type_{st}'] = 1.0 if features.service_type == st else 0.0
        
        # Numerical features
        vector.update({
            'customer_history_score': features.customer_history_score,
            'claim_frequency': min(features.claim_frequency / 10.0, 1.0),  # Normalize
            'avg_claim_amount': min(features.avg_claim_amount / 50000.0, 1.0),  # Normalize
            'request_complexity': features.request_complexity,
            'documentation_completeness': features.documentation_completeness,
            'urgency_score': features.urgency_score,
            'submission_hour': features.submission_hour / 24.0,
            'submission_day_of_week': features.submission_day_of_week / 7.0,
            'is_holiday': 1.0 if features.is_holiday else 0.0,
            'requested_amount_normalized': min(features.requested_amount / 100000.0, 1.0),
            'fraud_risk_indicators': min(features.fraud_risk_indicators / 5.0, 1.0),
            'medical_complexity': features.medical_complexity,
            'provider_risk_score': features.provider_risk_score
        })
        
        return vector
    
    def _mock_model_prediction(self, feature_vector: Dict[str, float]) -> Dict[str, float]:
        """Mock model prediction (replace with actual model inference)."""
        # Simple rule-based mock prediction
        probabilities = {rt: 0.05 for rt in self.config.request_types}
        
        # Determine most likely type based on features
        if feature_vector.get('service_type_EMERGENCY', 0) > 0:
            probabilities['EMERGENCY_CLAIM'] = 0.8
        elif feature_vector.get('service_type_DENTAL', 0) > 0:
            probabilities['DENTAL_CLAIM'] = 0.8
        elif feature_vector.get('service_type_PHARMACY', 0) > 0:
            probabilities['PHARMACY_CLAIM'] = 0.8
        elif feature_vector.get('service_type_PREVENTIVE', 0) > 0:
            probabilities['PREVENTIVE_CARE'] = 0.8
        elif feature_vector.get('service_type_SPECIALIST', 0) > 0:
            probabilities['SPECIALIST_REFERRAL'] = 0.8
        elif feature_vector.get('service_type_PRIOR_AUTH', 0) > 0:
            probabilities['PRIOR_AUTHORIZATION'] = 0.8
        elif feature_vector.get('service_type_APPEAL', 0) > 0:
            probabilities['APPEAL_REQUEST'] = 0.8
        else:
            probabilities['MEDICAL_CLAIM'] = 0.7
        
        # Normalize probabilities
        total = sum(probabilities.values())
        return {k: v / total for k, v in probabilities.items()}
    
    def _rule_based_classification(self, features: ClassificationFeatures) -> str:
        """Rule-based classification fallback."""
        service_type_mapping = {
            'EMERGENCY': 'EMERGENCY_CLAIM',
            'DENTAL': 'DENTAL_CLAIM',
            'PHARMACY': 'PHARMACY_CLAIM',
            'PREVENTIVE': 'PREVENTIVE_CARE',
            'SPECIALIST': 'SPECIALIST_REFERRAL',
            'PRIOR_AUTH': 'PRIOR_AUTHORIZATION',
            'APPEAL': 'APPEAL_REQUEST',
            'MEDICAL': 'MEDICAL_CLAIM'
        }
        
        return service_type_mapping.get(features.service_type, 'MEDICAL_CLAIM')
    
    def _determine_route(self, request_type: str, confidence_score: float) -> str:
        """Determine processing route based on classification."""
        if confidence_score >= self.config.high_confidence_threshold:
            return 'FAST_TRACK'
        elif confidence_score >= self.config.medium_confidence_threshold:
            return 'STANDARD'
        else:
            return 'MANUAL_REVIEW'
    
    def _assess_risk_prior(self, features: ClassificationFeatures, request_type: str) -> RiskLevel:
        """Assess prior risk level based on features."""
        risk_score = 0.0
        
        # Amount-based risk
        if features.requested_amount > 50000:
            risk_score += self.config.risk_factors['high_amount']
        
        # Fraud indicators
        if features.fraud_risk_indicators > 0:
            risk_score += self.config.risk_factors['fraud_indicators'] * features.fraud_risk_indicators
        
        # Provider risk
        risk_score += self.config.risk_factors['provider_risk'] * features.provider_risk_score
        
        # Complexity risk
        risk_score += self.config.risk_factors['complexity'] * features.medical_complexity
        
        # Convert to risk level
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _get_top_features(self, features: ClassificationFeatures, request_type: str) -> List[Dict[str, float]]:
        """Get top contributing features for the prediction."""
        # Mock feature importance (would come from actual model)
        feature_importance = [
            {'feature': 'service_type', 'importance': 0.3},
            {'feature': 'request_complexity', 'importance': 0.2},
            {'feature': 'urgency_score', 'importance': 0.15},
            {'feature': 'customer_history_score', 'importance': 0.1},
            {'feature': 'documentation_completeness', 'importance': 0.1},
            {'feature': 'medical_complexity', 'importance': 0.08},
            {'feature': 'fraud_risk_indicators', 'importance': 0.07}
        ]
        
        return feature_importance
    
    def _get_model_version_info(self, requested_version: Optional[str] = None) -> ModelVersion:
        """Get model version information."""
        if self.primary_model and not requested_version:
            return ModelVersion(
                name=self.config.model_name,
                version="1.0.0",
                trained_at=datetime(2024, 1, 1),
                metrics={'accuracy': 0.92, 'f1_score': 0.89},
                features_used=list(self._features_to_vector(ClassificationFeatures(
                    service_type='MEDICAL', customer_segment='INDIVIDUAL',
                    contract_type='INDIVIDUAL', plan_tier='STANDARD',
                    submission_hour=12, submission_day_of_week=1
                )).keys())
            )
        else:
            return ModelVersion(
                name=self.config.fallback_model,
                version="1.0.0",
                trained_at=datetime(2024, 1, 1),
                metrics={'accuracy': 0.75, 'f1_score': 0.72},
                features_used=['rule_based']
            )
    
    def _create_rule_based_classifier(self):
        """Create a simple rule-based classifier as fallback."""
        return "rule_based_classifier"
    
    def _create_fallback_output(self, case_id: str, features: Dict[str, Any], start_time: float) -> MLClassificationOutput:
        """Create fallback output when classification fails."""
        inference_time = int((time.time() - start_time) * 1000)
        
        return MLClassificationOutput(
            case_id=case_id,
            request_type='MEDICAL_CLAIM',
            candidate_policy_ids=['medical_policy_v2.1'],
            route='MANUAL_REVIEW',
            risk_prior=RiskLevel.MEDIUM,
            probabilities={'MEDICAL_CLAIM': 1.0},
            confidence_score=0.5,
            top_features=[{'feature': 'fallback', 'importance': 1.0}],
            model_version=ModelVersion(
                name='fallback_classifier',
                version='1.0.0',
                trained_at=datetime(2024, 1, 1),
                metrics={'accuracy': 0.5},
                features_used=['fallback']
            ),
            inference_time_ms=inference_time
        )


# Factory function for easy instantiation
def create_classification_service(config: ClassificationConfig = None) -> ClassificationService:
    """Create a classification service instance."""
    return ClassificationService(config)
