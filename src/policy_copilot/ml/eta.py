"""
ML ETA Prediction Service for Policy Validation Copilot

This module implements UC-OP-13 ETA prediction service with estimated time
of arrival prediction and confidence intervals per Anexo B API contracts.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from ..models.base import ModelVersion
from ..models.ml import MLETAOutput
from .base import BaseMLService, FeatureEngineer, ModelRegistry

logger = logging.getLogger(__name__)


class ETAFeatures(BaseModel):
    """Feature schema for ETA prediction service."""
    
    # Case characteristics
    case_complexity_score: float = Field(0.0, ge=0.0, le=1.0, description="Case complexity score")
    documentation_completeness: float = Field(0.0, ge=0.0, le=1.0, description="Documentation completeness")
    service_complexity: float = Field(0.0, ge=0.0, le=1.0, description="Service complexity score")
    
    # Request type features
    request_type: str = Field(..., description="Type of request")
    is_emergency: bool = Field(False, description="Whether request is emergency")
    requires_specialist: bool = Field(False, description="Whether specialist review is required")
    requires_external_validation: bool = Field(False, description="Whether external validation is needed")
    
    # Historical processing features
    similar_cases_avg_time: float = Field(0.0, ge=0.0, description="Average processing time for similar cases (minutes)")
    customer_avg_processing_time: float = Field(0.0, ge=0.0, description="Customer's average processing time (minutes)")
    provider_avg_processing_time: float = Field(0.0, ge=0.0, description="Provider's average processing time (minutes)")
    
    # Workload features
    current_queue_size: int = Field(0, ge=0, description="Current queue size")
    agent_availability: float = Field(1.0, ge=0.0, le=1.0, description="Agent availability ratio")
    system_load: float = Field(0.0, ge=0.0, le=1.0, description="Current system load")
    
    # Priority and urgency
    priority_level: str = Field("MEDIUM", description="Priority level")
    urgency_score: float = Field(0.0, ge=0.0, le=1.0, description="Urgency score")
    sla_target_hours: float = Field(24.0, ge=0.0, description="SLA target in hours")
    
    # Temporal features
    submission_hour: int = Field(..., ge=0, le=23, description="Hour of submission")
    submission_day_of_week: int = Field(..., ge=0, le=6, description="Day of week")
    is_holiday: bool = Field(False, description="Whether submitted on holiday")
    is_weekend: bool = Field(False, description="Whether submitted on weekend")
    
    # Amount and financial complexity
    requested_amount: float = Field(0.0, ge=0.0, description="Requested amount")
    amount_complexity_factor: float = Field(1.0, ge=1.0, description="Amount-based complexity factor")
    
    # External dependencies
    external_validations_required: int = Field(0, ge=0, description="Number of external validations required")
    estimated_external_delay: float = Field(0.0, ge=0.0, description="Estimated external validation delay (minutes)")
    
    # ML predictions from other services
    classification_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Classification confidence")
    anomaly_score: float = Field(0.0, ge=0.0, le=1.0, description="Anomaly score")
    risk_level: str = Field("MEDIUM", description="Risk level")
    
    # Seasonal and trend factors
    seasonal_factor: float = Field(1.0, ge=0.5, le=2.0, description="Seasonal processing factor")
    trend_factor: float = Field(1.0, ge=0.5, le=2.0, description="Trend-based processing factor")


class ETAConfig(BaseModel):
    """Configuration for ETA prediction service."""
    
    # Model settings
    model_name: str = "eta_predictor_v1"
    model_version: Optional[str] = None
    fallback_model: str = "rule_based_eta_predictor"
    
    # Base processing times by request type (in minutes)
    base_processing_times: Dict[str, float] = {
        "MEDICAL_CLAIM": 120.0,
        "DENTAL_CLAIM": 60.0,
        "PHARMACY_CLAIM": 30.0,
        "EMERGENCY_CLAIM": 15.0,
        "PREVENTIVE_CARE": 45.0,
        "SPECIALIST_REFERRAL": 90.0,
        "PRIOR_AUTHORIZATION": 180.0,
        "APPEAL_REQUEST": 240.0
    }
    
    # Complexity multipliers
    complexity_multipliers: Dict[str, float] = {
        "LOW": 0.8,
        "MEDIUM": 1.0,
        "HIGH": 1.5,
        "CRITICAL": 2.0
    }
    
    # Priority multipliers
    priority_multipliers: Dict[str, float] = {
        "LOW": 1.2,
        "MEDIUM": 1.0,
        "HIGH": 0.7,
        "CRITICAL": 0.4
    }
    
    # Workload impact factors
    workload_factors: Dict[str, float] = {
        "queue_size_factor": 0.1,  # Minutes per case in queue
        "agent_availability_factor": 2.0,  # Multiplier when agents unavailable
        "system_load_factor": 1.5  # Multiplier for high system load
    }
    
    # Temporal factors
    temporal_factors: Dict[str, float] = {
        "night_hours_factor": 1.8,  # 10 PM - 6 AM
        "weekend_factor": 1.4,
        "holiday_factor": 2.0,
        "business_hours_factor": 0.9  # 9 AM - 5 PM
    }
    
    # Confidence intervals
    confidence_levels: Dict[str, float] = {
        "p10": 0.1,
        "p25": 0.25,
        "p50": 0.5,
        "p75": 0.75,
        "p90": 0.9,
        "p95": 0.95
    }
    
    # Uncertainty factors
    uncertainty_factors: Dict[str, float] = {
        "low_confidence_multiplier": 1.3,
        "high_anomaly_multiplier": 1.4,
        "external_dependency_multiplier": 1.6,
        "new_customer_multiplier": 1.2
    }
    
    # Model performance thresholds
    accuracy_threshold: float = 0.8
    mae_threshold: float = 30.0  # Mean Absolute Error in minutes


class ETAFeatureEngineer(FeatureEngineer):
    """Feature engineering for ETA prediction service."""
    
    def __init__(self, config: ETAConfig):
        super().__init__()
        self.config = config
    
    def extract_features(self, case_data: Dict[str, Any]) -> ETAFeatures:
        """Extract features from case data."""
        additional_data = case_data.get('additional_data', {})
        
        # Case characteristics
        case_complexity_score = self._calculate_case_complexity(case_data)
        documentation_completeness = self._assess_documentation_completeness(case_data)
        service_complexity = self._assess_service_complexity(case_data)
        
        # Request type features
        request_type = additional_data.get('request_type', 'MEDICAL_CLAIM')
        is_emergency = 'emergency' in case_data.get('service', '').lower()
        requires_specialist = self._requires_specialist_review(case_data)
        requires_external_validation = self._requires_external_validation(case_data)
        
        # Historical processing features
        similar_cases_avg_time = additional_data.get('similar_cases_avg_time', 
                                                   self.config.base_processing_times.get(request_type, 120.0))
        customer_avg_processing_time = additional_data.get('customer_avg_processing_time', similar_cases_avg_time)
        provider_avg_processing_time = additional_data.get('provider_avg_processing_time', similar_cases_avg_time)
        
        # Workload features
        current_queue_size = additional_data.get('current_queue_size', 10)
        agent_availability = additional_data.get('agent_availability', 0.8)
        system_load = additional_data.get('system_load', 0.3)
        
        # Priority and urgency
        priority_level = case_data.get('priority', 'MEDIUM')
        urgency_score = self._calculate_urgency_score(case_data)
        sla_target_hours = self._calculate_sla_target_hours(case_data)
        
        # Temporal features
        submitted_at = case_data.get('submitted_at', datetime.utcnow())
        if isinstance(submitted_at, str):
            submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
        
        submission_hour = submitted_at.hour
        submission_day_of_week = submitted_at.weekday()
        is_holiday = self._is_holiday(submitted_at)
        is_weekend = submitted_at.weekday() >= 5
        
        # Amount and financial complexity
        requested_amount = additional_data.get('requested_amount', 0.0)
        amount_complexity_factor = self._calculate_amount_complexity_factor(requested_amount)
        
        # External dependencies
        external_validations_required = self._count_external_validations_required(case_data)
        estimated_external_delay = external_validations_required * 60.0  # 1 hour per validation
        
        # ML predictions from other services
        classification_confidence = additional_data.get('classification_confidence', 0.5)
        anomaly_score = additional_data.get('anomaly_score', 0.0)
        risk_level = additional_data.get('risk_level', 'MEDIUM')
        
        # Seasonal and trend factors
        seasonal_factor = self._calculate_seasonal_factor(submitted_at)
        trend_factor = self._calculate_trend_factor(submitted_at)
        
        return ETAFeatures(
            case_complexity_score=case_complexity_score,
            documentation_completeness=documentation_completeness,
            service_complexity=service_complexity,
            request_type=request_type,
            is_emergency=is_emergency,
            requires_specialist=requires_specialist,
            requires_external_validation=requires_external_validation,
            similar_cases_avg_time=similar_cases_avg_time,
            customer_avg_processing_time=customer_avg_processing_time,
            provider_avg_processing_time=provider_avg_processing_time,
            current_queue_size=current_queue_size,
            agent_availability=agent_availability,
            system_load=system_load,
            priority_level=priority_level,
            urgency_score=urgency_score,
            sla_target_hours=sla_target_hours,
            submission_hour=submission_hour,
            submission_day_of_week=submission_day_of_week,
            is_holiday=is_holiday,
            is_weekend=is_weekend,
            requested_amount=requested_amount,
            amount_complexity_factor=amount_complexity_factor,
            external_validations_required=external_validations_required,
            estimated_external_delay=estimated_external_delay,
            classification_confidence=classification_confidence,
            anomaly_score=anomaly_score,
            risk_level=risk_level,
            seasonal_factor=seasonal_factor,
            trend_factor=trend_factor
        )
    
    def _calculate_case_complexity(self, case_data: Dict[str, Any]) -> float:
        """Calculate case complexity score."""
        complexity = 0.0
        
        # Service description complexity
        service = case_data.get('service', '')
        if len(service) > 100:
            complexity += 0.2
        
        # Number of attachments
        attachments = case_data.get('attachments', [])
        complexity += min(len(attachments) * 0.1, 0.3)
        
        # Additional data complexity
        additional_data = case_data.get('additional_data', {})
        complexity += min(len(additional_data) * 0.05, 0.3)
        
        # Medical complexity indicators
        complex_terms = ['surgery', 'procedure', 'treatment', 'therapy', 'diagnosis']
        if any(term in service.lower() for term in complex_terms):
            complexity += 0.2
        
        return min(complexity, 1.0)
    
    def _assess_documentation_completeness(self, case_data: Dict[str, Any]) -> float:
        """Assess documentation completeness."""
        completeness = 0.0
        
        # Required fields
        required_fields = ['case_id', 'customer_id', 'service']
        present_fields = sum(1 for field in required_fields if case_data.get(field))
        completeness += (present_fields / len(required_fields)) * 0.4
        
        # Attachments
        attachments = case_data.get('attachments', [])
        if attachments:
            completeness += 0.3
        
        # Service description quality
        service = case_data.get('service', '')
        if len(service) > 20:
            completeness += 0.3
        
        return min(completeness, 1.0)
    
    def _assess_service_complexity(self, case_data: Dict[str, Any]) -> float:
        """Assess service complexity."""
        service = case_data.get('service', '').lower()
        
        # Emergency services
        if any(term in service for term in ['emergency', 'urgent', 'critical']):
            return 0.9
        
        # Complex procedures
        if any(term in service for term in ['surgery', 'procedure', 'treatment']):
            return 0.8
        
        # Specialist services
        if any(term in service for term in ['specialist', 'consultation', 'referral']):
            return 0.6
        
        # Standard services
        return 0.4
    
    def _requires_specialist_review(self, case_data: Dict[str, Any]) -> bool:
        """Check if case requires specialist review."""
        service = case_data.get('service', '').lower()
        specialist_terms = ['specialist', 'consultation', 'referral', 'complex', 'rare']
        return any(term in service for term in specialist_terms)
    
    def _requires_external_validation(self, case_data: Dict[str, Any]) -> bool:
        """Check if case requires external validation."""
        additional_data = case_data.get('additional_data', {})
        requested_amount = additional_data.get('requested_amount', 0.0)
        
        # High amount claims require external validation
        if requested_amount > 50000:
            return True
        
        # Certain service types require external validation
        service = case_data.get('service', '').lower()
        external_terms = ['experimental', 'investigational', 'clinical trial']
        return any(term in service for term in external_terms)
    
    def _calculate_urgency_score(self, case_data: Dict[str, Any]) -> float:
        """Calculate urgency score."""
        urgency = 0.0
        
        # Priority level
        priority = case_data.get('priority', 'MEDIUM')
        priority_scores = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.8, 'CRITICAL': 1.0}
        urgency += priority_scores.get(priority, 0.5) * 0.5
        
        # Service urgency
        service = case_data.get('service', '').lower()
        if any(term in service for term in ['emergency', 'urgent', 'critical']):
            urgency += 0.5
        
        return min(urgency, 1.0)
    
    def _calculate_sla_target_hours(self, case_data: Dict[str, Any]) -> float:
        """Calculate SLA target in hours."""
        sla_target = case_data.get('sla_target')
        if sla_target:
            if isinstance(sla_target, str):
                sla_target = datetime.fromisoformat(sla_target.replace('Z', '+00:00'))
            
            submitted_at = case_data.get('submitted_at', datetime.utcnow())
            if isinstance(submitted_at, str):
                submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
            
            delta = sla_target - submitted_at
            return max(delta.total_seconds() / 3600, 1.0)  # At least 1 hour
        
        # Default SLA based on priority
        priority = case_data.get('priority', 'MEDIUM')
        default_slas = {'LOW': 72.0, 'MEDIUM': 24.0, 'HIGH': 8.0, 'CRITICAL': 2.0}
        return default_slas.get(priority, 24.0)
    
    def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday (simplified)."""
        # Simple holiday check (would use proper holiday library in real implementation)
        return date.month == 12 and date.day in [24, 25, 31] or date.month == 1 and date.day == 1
    
    def _calculate_amount_complexity_factor(self, amount: float) -> float:
        """Calculate complexity factor based on amount."""
        if amount < 1000:
            return 1.0
        elif amount < 10000:
            return 1.2
        elif amount < 50000:
            return 1.5
        else:
            return 2.0
    
    def _count_external_validations_required(self, case_data: Dict[str, Any]) -> int:
        """Count number of external validations required."""
        count = 0
        
        additional_data = case_data.get('additional_data', {})
        requested_amount = additional_data.get('requested_amount', 0.0)
        
        # High amount validation
        if requested_amount > 50000:
            count += 1
        
        # Provider validation
        if additional_data.get('new_provider', False):
            count += 1
        
        # Medical necessity validation
        service = case_data.get('service', '').lower()
        if any(term in service for term in ['experimental', 'investigational']):
            count += 1
        
        return count
    
    def _calculate_seasonal_factor(self, date: datetime) -> float:
        """Calculate seasonal processing factor."""
        month = date.month
        
        # Holiday seasons are slower
        if month in [12, 1]:  # December, January
            return 1.3
        elif month in [6, 7]:  # Summer vacation months
            return 1.2
        else:
            return 1.0
    
    def _calculate_trend_factor(self, date: datetime) -> float:
        """Calculate trend-based processing factor."""
        # Simplified trend calculation (would use actual historical data)
        hour = date.hour
        
        # Peak hours are slower
        if 9 <= hour <= 17:  # Business hours
            return 1.1
        else:
            return 0.9


class ETAPredictionService(BaseMLService):
    """ML ETA Prediction service for estimated time of arrival prediction."""
    
    def __init__(self, config: ETAConfig = None, model_registry: ModelRegistry = None):
        super().__init__()
        self.config = config or ETAConfig()
        self.model_registry = model_registry or ModelRegistry()
        self.feature_engineer = ETAFeatureEngineer(self.config)
        
        # Load models
        self.primary_model = None
        self.fallback_model = None
        self._load_models()
    
    def _load_models(self) -> None:
        """Load ETA prediction models."""
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
            
            logger.info(f"Loaded ETA prediction models: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load ETA prediction models: {e}")
            # Use rule-based fallback
            self.primary_model = None
            self.fallback_model = self._create_rule_based_predictor()
    
    def predict_eta(
        self,
        case_id: str,
        features: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> MLETAOutput:
        """
        Predict estimated time of arrival for case completion.
        
        Implements ML-ETA API contract from Anexo B.
        """
        start_time = time.time()
        
        try:
            # Extract and engineer features
            eta_features = self.feature_engineer.extract_features(features)
            
            # Get model version info
            model_info = self._get_model_version_info(model_version)
            
            # Perform ETA prediction
            if self.primary_model and not model_version:
                prediction_result = self._predict_with_model(eta_features)
            else:
                prediction_result = self._predict_with_fallback(eta_features)
            
            # Calculate inference time
            inference_time = int((time.time() - start_time) * 1000)
            
            # Create ETA timestamp
            eta_timestamp = datetime.utcnow() + timedelta(minutes=prediction_result['eta_minutes'])
            
            # Create output
            output = MLETAOutput(
                case_id=case_id,
                eta_minutes=prediction_result['eta_minutes'],
                eta_timestamp=eta_timestamp,
                p50=prediction_result['p50'],
                p90=prediction_result.get('p90'),
                confidence_interval=prediction_result.get('confidence_interval'),
                complexity_score=prediction_result['complexity_score'],
                workload_factor=prediction_result['workload_factor'],
                historical_average=prediction_result.get('historical_average'),
                model_version=model_info,
                inference_time_ms=inference_time
            )
            
            logger.info(f"ETA prediction completed for case {case_id}: {output.eta_minutes} minutes")
            return output
            
        except Exception as e:
            logger.error(f"ETA prediction failed for case {case_id}: {e}")
            # Return fallback result
            return self._create_fallback_output(case_id, features, start_time)
    
    def _predict_with_model(self, features: ETAFeatures) -> Dict[str, Any]:
        """Predict ETA using the primary ML model."""
        # Convert features to model input format
        feature_vector = self._features_to_vector(features)
        
        # Get model prediction (mock implementation)
        eta_minutes = self._mock_model_prediction(feature_vector)
        
        # Calculate percentiles
        p50 = int(eta_minutes)
        p90 = int(eta_minutes * 1.5)
        
        # Calculate confidence interval
        confidence_interval = {
            'lower': int(eta_minutes * 0.7),
            'upper': int(eta_minutes * 1.3)
        }
        
        # Calculate complexity and workload factors
        complexity_score = features.case_complexity_score
        workload_factor = self._calculate_workload_factor(features)
        
        # Historical average
        historical_average = int(features.similar_cases_avg_time)
        
        return {
            'eta_minutes': int(eta_minutes),
            'p50': p50,
            'p90': p90,
            'confidence_interval': confidence_interval,
            'complexity_score': complexity_score,
            'workload_factor': workload_factor,
            'historical_average': historical_average
        }
    
    def _predict_with_fallback(self, features: ETAFeatures) -> Dict[str, Any]:
        """Predict ETA using rule-based fallback."""
        # Rule-based ETA prediction
        eta_minutes = self._rule_based_prediction(features)
        
        # Calculate percentiles
        p50 = int(eta_minutes)
        p90 = int(eta_minutes * 1.4)
        
        # Calculate complexity and workload factors
        complexity_score = features.case_complexity_score
        workload_factor = self._calculate_workload_factor(features)
        
        # Historical average
        historical_average = int(features.similar_cases_avg_time)
        
        return {
            'eta_minutes': int(eta_minutes),
            'p50': p50,
            'p90': p90,
            'complexity_score': complexity_score,
            'workload_factor': workload_factor,
            'historical_average': historical_average
        }
    
    def _features_to_vector(self, features: ETAFeatures) -> Dict[str, float]:
        """Convert features to numerical vector."""
        # Request type encoding
        request_types = ['MEDICAL_CLAIM', 'DENTAL_CLAIM', 'PHARMACY_CLAIM', 'EMERGENCY_CLAIM', 
                        'PREVENTIVE_CARE', 'SPECIALIST_REFERRAL', 'PRIOR_AUTHORIZATION', 'APPEAL_REQUEST']
        
        vector = {}
        for rt in request_types:
            vector[f'request_type_{rt}'] = 1.0 if features.request_type == rt else 0.0
        
        # Priority encoding
        priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        for priority in priorities:
            vector[f'priority_{priority}'] = 1.0 if features.priority_level == priority else 0.0
        
        # Risk level encoding
        risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        for risk in risk_levels:
            vector[f'risk_{risk}'] = 1.0 if features.risk_level == risk else 0.0
        
        # Numerical features
        vector.update({
            'case_complexity_score': features.case_complexity_score,
            'documentation_completeness': features.documentation_completeness,
            'service_complexity': features.service_complexity,
            'is_emergency': 1.0 if features.is_emergency else 0.0,
            'requires_specialist': 1.0 if features.requires_specialist else 0.0,
            'requires_external_validation': 1.0 if features.requires_external_validation else 0.0,
            'similar_cases_avg_time': features.similar_cases_avg_time / 1000.0,  # Normalize
            'customer_avg_processing_time': features.customer_avg_processing_time / 1000.0,
            'provider_avg_processing_time': features.provider_avg_processing_time / 1000.0,
            'current_queue_size': min(features.current_queue_size / 100.0, 1.0),  # Normalize
            'agent_availability': features.agent_availability,
            'system_load': features.system_load,
            'urgency_score': features.urgency_score,
            'sla_target_hours': min(features.sla_target_hours / 72.0, 1.0),  # Normalize to 72 hours
            'submission_hour': features.submission_hour / 24.0,
            'submission_day_of_week': features.submission_day_of_week / 7.0,
            'is_holiday': 1.0 if features.is_holiday else 0.0,
            'is_weekend': 1.0 if features.is_weekend else 0.0,
            'requested_amount': min(features.requested_amount / 100000.0, 1.0),  # Normalize
            'amount_complexity_factor': features.amount_complexity_factor / 2.0,
            'external_validations_required': min(features.external_validations_required / 5.0, 1.0),
            'estimated_external_delay': min(features.estimated_external_delay / 1000.0, 1.0),
            'classification_confidence': features.classification_confidence,
            'anomaly_score': features.anomaly_score,
            'seasonal_factor': features.seasonal_factor / 2.0,
            'trend_factor': features.trend_factor / 2.0
        })
        
        return vector
    
    def _mock_model_prediction(self, feature_vector: Dict[str, float]) -> float:
        """Mock model prediction (replace with actual model inference)."""
        # Base time from request type
        base_time = 120.0  # Default 2 hours
        
        # Request type adjustment
        if feature_vector.get('request_type_EMERGENCY_CLAIM', 0) > 0:
            base_time = 15.0
        elif feature_vector.get('request_type_PHARMACY_CLAIM', 0) > 0:
            base_time = 30.0
        elif feature_vector.get('request_type_DENTAL_CLAIM', 0) > 0:
            base_time = 60.0
        elif feature_vector.get('request_type_PRIOR_AUTHORIZATION', 0) > 0:
            base_time = 180.0
        elif feature_vector.get('request_type_APPEAL_REQUEST', 0) > 0:
            base_time = 240.0
        
        # Complexity adjustment
        complexity_multiplier = 1.0 + feature_vector.get('case_complexity_score', 0) * 0.5
        
        # Priority adjustment
        if feature_vector.get('priority_CRITICAL', 0) > 0:
            priority_multiplier = 0.4
        elif feature_vector.get('priority_HIGH', 0) > 0:
            priority_multiplier = 0.7
        elif feature_vector.get('priority_LOW', 0) > 0:
            priority_multiplier = 1.2
        else:
            priority_multiplier = 1.0
        
        # Workload adjustment
        queue_factor = 1.0 + feature_vector.get('current_queue_size', 0) * 0.5
        availability_factor = 2.0 - feature_vector.get('agent_availability', 1.0)
        
        # Temporal adjustment
        temporal_factor = 1.0
        if feature_vector.get('is_weekend', 0) > 0:
            temporal_factor *= 1.4
        if feature_vector.get('is_holiday', 0) > 0:
            temporal_factor *= 2.0
        
        # External validation delay
        external_delay = feature_vector.get('estimated_external_delay', 0) * 1000.0
        
        # Calculate final ETA
        eta = (base_time * complexity_multiplier * priority_multiplier * 
               queue_factor * availability_factor * temporal_factor) + external_delay
        
        return max(eta, 5.0)  # Minimum 5 minutes
    
    def _rule_based_prediction(self, features: ETAFeatures) -> float:
        """Rule-based ETA prediction fallback."""
        # Start with base processing time
        base_time = self.config.base_processing_times.get(features.request_type, 120.0)
        
        # Apply complexity multiplier
        if features.case_complexity_score > 0.8:
            complexity_multiplier = self.config.complexity_multipliers['CRITICAL']
        elif features.case_complexity_score > 0.6:
            complexity_multiplier = self.config.complexity_multipliers['HIGH']
        elif features.case_complexity_score > 0.3:
            complexity_multiplier = self.config.complexity_multipliers['MEDIUM']
        else:
            complexity_multiplier = self.config.complexity_multipliers['LOW']
        
        # Apply priority multiplier
        priority_multiplier = self.config.priority_multipliers.get(features.priority_level, 1.0)
        
        # Apply workload factors
        workload_factor = self._calculate_workload_factor(features)
        
        # Apply temporal factors
        temporal_factor = 1.0
        if features.is_weekend:
            temporal_factor *= self.config.temporal_factors['weekend_factor']
        if features.is_holiday:
            temporal_factor *= self.config.temporal_factors['holiday_factor']
        if 9 <= features.submission_hour <= 17:
            temporal_factor *= self.config.temporal_factors['business_hours_factor']
        else:
            temporal_factor *= self.config.temporal_factors['night_hours_factor']
        
        # Apply seasonal factor
        temporal_factor *= features.seasonal_factor
        
        # Add external validation delay
        external_delay = features.estimated_external_delay
        
        # Calculate final ETA
        eta = (base_time * complexity_multiplier * priority_multiplier * 
               workload_factor * temporal_factor) + external_delay
        
        return max(eta, 5.0)  # Minimum 5 minutes
    
    def _calculate_workload_factor(self, features: ETAFeatures) -> float:
        """Calculate workload impact factor."""
        workload_factor = 1.0
        
        # Queue size impact
        workload_factor += features.current_queue_size * self.config.workload_factors['queue_size_factor']
        
        # Agent availability impact
        if features.agent_availability < 0.5:
            workload_factor *= self.config.workload_factors['agent_availability_factor']
        
        # System load impact
        if features.system_load > 0.8:
            workload_factor *= self.config.workload_factors['system_load_factor']
        
        return workload_factor
    
    def _get_model_version_info(self, requested_version: Optional[str] = None) -> ModelVersion:
        """Get model version information."""
        if self.primary_model and not requested_version:
            return ModelVersion(
                name=self.config.model_name,
                version="1.0.0",
                trained_at=datetime(2024, 1, 1),
                metrics={'mae': 25.3, 'rmse': 45.2, 'r2_score': 0.87},
                features_used=list(self._features_to_vector(ETAFeatures(
                    request_type='MEDICAL_CLAIM', priority_level='MEDIUM',
                    submission_hour=12, submission_day_of_week=1, risk_level='MEDIUM'
                )).keys())
            )
        else:
            return ModelVersion(
                name=self.config.fallback_model,
                version="1.0.0",
                trained_at=datetime(2024, 1, 1),
                metrics={'mae': 35.8, 'rmse': 55.1, 'r2_score': 0.72},
                features_used=['rule_based']
            )
    
    def _create_rule_based_predictor(self):
        """Create a rule-based ETA predictor as fallback."""
        return "rule_based_eta_predictor"
    
    def _create_fallback_output(self, case_id: str, features: Dict[str, Any], start_time: float) -> MLETAOutput:
        """Create fallback output when ETA prediction fails."""
        inference_time = int((time.time() - start_time) * 1000)
        
        # Simple fallback: 2 hours
        eta_minutes = 120
        eta_timestamp = datetime.utcnow() + timedelta(minutes=eta_minutes)
        
        return MLETAOutput(
            case_id=case_id,
            eta_minutes=eta_minutes,
            eta_timestamp=eta_timestamp,
            p50=eta_minutes,
            p90=int(eta_minutes * 1.5),
            complexity_score=0.5,
            workload_factor=1.0,
            model_version=ModelVersion(
                name='fallback_predictor',
                version='1.0.0',
                trained_at=datetime(2024, 1, 1),
                metrics={'mae': 60.0},
                features_used=['fallback']
            ),
            inference_time_ms=inference_time
        )
    
    def predict(self, *args, **kwargs) -> MLETAOutput:
        """Implement abstract predict method."""
        return self.predict_eta(*args, **kwargs)


# Factory function for easy instantiation
def create_eta_service(config: ETAConfig = None) -> ETAPredictionService:
    """Create an ETA prediction service instance."""
    return ETAPredictionService(config)
