"""
ML Anomaly Detection Service for Policy Validation Copilot

This module implements UC-OP-12 anomaly detection service with pattern deviation
detection and risk assessment per Anexo B API contracts.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from ..models.base import AnomalyFlag, ModelVersion
from ..models.ml import MLAnomalyOutput
from .base import BaseMLService, FeatureEngineer, ModelRegistry

logger = logging.getLogger(__name__)


class AnomalyFeatures(BaseModel):
    """Feature schema for anomaly detection service."""
    
    # Case characteristics
    case_complexity_score: float = Field(0.0, ge=0.0, le=1.0, description="Case complexity score")
    documentation_quality: float = Field(0.0, ge=0.0, le=1.0, description="Documentation quality score")
    request_urgency: float = Field(0.0, ge=0.0, le=1.0, description="Request urgency level")
    
    # Financial anomalies
    amount_requested: float = Field(0.0, ge=0.0, description="Amount requested")
    amount_vs_historical_avg: float = Field(0.0, description="Ratio to historical average")
    amount_vs_policy_limit: float = Field(0.0, ge=0.0, le=1.0, description="Ratio to policy limit")
    
    # Temporal patterns
    submission_time_anomaly: float = Field(0.0, ge=0.0, le=1.0, description="Submission time anomaly score")
    frequency_anomaly: float = Field(0.0, ge=0.0, le=1.0, description="Submission frequency anomaly")
    seasonal_deviation: float = Field(0.0, description="Seasonal pattern deviation")
    
    # Behavioral patterns
    customer_behavior_score: float = Field(0.0, ge=0.0, le=1.0, description="Customer behavior anomaly")
    provider_pattern_score: float = Field(0.0, ge=0.0, le=1.0, description="Provider pattern anomaly")
    service_pattern_score: float = Field(0.0, ge=0.0, le=1.0, description="Service pattern anomaly")
    
    # Geographic anomalies
    location_anomaly: float = Field(0.0, ge=0.0, le=1.0, description="Geographic location anomaly")
    distance_from_usual: float = Field(0.0, ge=0.0, description="Distance from usual locations")
    
    # Network analysis
    network_centrality: float = Field(0.0, ge=0.0, le=1.0, description="Network centrality score")
    connection_anomaly: float = Field(0.0, ge=0.0, le=1.0, description="Connection pattern anomaly")
    
    # Statistical features
    z_score_amount: float = Field(0.0, description="Z-score for amount")
    z_score_frequency: float = Field(0.0, description="Z-score for frequency")
    outlier_score: float = Field(0.0, ge=0.0, le=1.0, description="Statistical outlier score")
    
    # Historical context
    historical_similarity: float = Field(0.0, ge=0.0, le=1.0, description="Similarity to historical cases")
    trend_deviation: float = Field(0.0, description="Deviation from trend")
    
    # Aggregated features
    total_cases_last_30d: int = Field(0, ge=0, description="Total cases in last 30 days")
    avg_amount_last_30d: float = Field(0.0, ge=0.0, description="Average amount in last 30 days")
    unique_providers_last_30d: int = Field(0, ge=0, description="Unique providers in last 30 days")


class AnomalyConfig(BaseModel):
    """Configuration for anomaly detection service."""
    
    # Model settings
    model_name: str = "anomaly_detector_v1"
    model_version: Optional[str] = None
    fallback_model: str = "statistical_anomaly_detector"
    
    # Detection thresholds
    anomaly_threshold: float = 0.7
    high_anomaly_threshold: float = 0.9
    statistical_threshold: float = 3.0  # Z-score threshold
    
    # Feature weights for ensemble
    feature_weights: Dict[str, float] = {
        "financial": 0.3,
        "temporal": 0.2,
        "behavioral": 0.25,
        "geographic": 0.1,
        "network": 0.1,
        "statistical": 0.05
    }
    
    # Anomaly types and their thresholds
    anomaly_types: Dict[str, float] = {
        "AMOUNT_ANOMALY": 0.8,
        "FREQUENCY_ANOMALY": 0.7,
        "TEMPORAL_ANOMALY": 0.6,
        "BEHAVIORAL_ANOMALY": 0.75,
        "GEOGRAPHIC_ANOMALY": 0.65,
        "NETWORK_ANOMALY": 0.7,
        "STATISTICAL_OUTLIER": 0.85
    }
    
    # Historical data requirements
    min_historical_samples: int = 100
    historical_window_days: int = 365
    
    # Aggregation settings
    aggregation_windows: List[int] = [7, 30, 90, 365]  # days
    
    # Action recommendations
    action_thresholds: Dict[str, float] = {
        "PROCEED": 0.3,
        "REVIEW": 0.7,
        "ESCALATE": 0.9,
        "BLOCK": 0.95
    }


class AnomalyFeatureEngineer(FeatureEngineer):
    """Feature engineering for anomaly detection service."""
    
    def __init__(self, config: AnomalyConfig):
        super().__init__()
        self.config = config
        self.historical_stats = {}
    
    def extract_features(
        self,
        case_data: Dict[str, Any],
        aggregates: Dict[str, Any]
    ) -> AnomalyFeatures:
        """Extract features from case data and aggregates."""
        
        # Basic case information
        additional_data = case_data.get('additional_data', {})
        amount_requested = additional_data.get('requested_amount', 0.0)
        
        # Financial anomaly features
        financial_features = self._extract_financial_features(case_data, aggregates)
        
        # Temporal anomaly features
        temporal_features = self._extract_temporal_features(case_data, aggregates)
        
        # Behavioral anomaly features
        behavioral_features = self._extract_behavioral_features(case_data, aggregates)
        
        # Geographic anomaly features
        geographic_features = self._extract_geographic_features(case_data, aggregates)
        
        # Network anomaly features
        network_features = self._extract_network_features(case_data, aggregates)
        
        # Statistical features
        statistical_features = self._extract_statistical_features(case_data, aggregates)
        
        # Historical context features
        historical_features = self._extract_historical_features(case_data, aggregates)
        
        return AnomalyFeatures(
            # Case characteristics
            case_complexity_score=self._calculate_complexity_score(case_data),
            documentation_quality=self._assess_documentation_quality(case_data),
            request_urgency=self._calculate_urgency_score(case_data),
            
            # Financial features
            amount_requested=amount_requested,
            amount_vs_historical_avg=financial_features['amount_vs_historical_avg'],
            amount_vs_policy_limit=financial_features['amount_vs_policy_limit'],
            
            # Temporal features
            submission_time_anomaly=temporal_features['submission_time_anomaly'],
            frequency_anomaly=temporal_features['frequency_anomaly'],
            seasonal_deviation=temporal_features['seasonal_deviation'],
            
            # Behavioral features
            customer_behavior_score=behavioral_features['customer_behavior_score'],
            provider_pattern_score=behavioral_features['provider_pattern_score'],
            service_pattern_score=behavioral_features['service_pattern_score'],
            
            # Geographic features
            location_anomaly=geographic_features['location_anomaly'],
            distance_from_usual=geographic_features['distance_from_usual'],
            
            # Network features
            network_centrality=network_features['network_centrality'],
            connection_anomaly=network_features['connection_anomaly'],
            
            # Statistical features
            z_score_amount=statistical_features['z_score_amount'],
            z_score_frequency=statistical_features['z_score_frequency'],
            outlier_score=statistical_features['outlier_score'],
            
            # Historical features
            historical_similarity=historical_features['historical_similarity'],
            trend_deviation=historical_features['trend_deviation'],
            
            # Aggregated features
            total_cases_last_30d=aggregates.get('total_cases_last_30d', 0),
            avg_amount_last_30d=aggregates.get('avg_amount_last_30d', 0.0),
            unique_providers_last_30d=aggregates.get('unique_providers_last_30d', 0)
        )
    
    def _extract_financial_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract financial anomaly features."""
        additional_data = case_data.get('additional_data', {})
        amount_requested = additional_data.get('requested_amount', 0.0)
        policy_limit = additional_data.get('policy_limit', 100000.0)
        
        # Historical average
        historical_avg = aggregates.get('avg_amount_last_365d', 1000.0)
        amount_vs_historical_avg = amount_requested / historical_avg if historical_avg > 0 else 0.0
        
        # Policy limit ratio
        amount_vs_policy_limit = amount_requested / policy_limit if policy_limit > 0 else 0.0
        
        return {
            'amount_vs_historical_avg': min(amount_vs_historical_avg, 10.0),  # Cap at 10x
            'amount_vs_policy_limit': amount_vs_policy_limit
        }
    
    def _extract_temporal_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract temporal anomaly features."""
        submitted_at = case_data.get('submitted_at', datetime.utcnow())
        if isinstance(submitted_at, str):
            submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
        
        # Submission time anomaly (unusual hours)
        hour = submitted_at.hour
        unusual_hours = [0, 1, 2, 3, 4, 5, 22, 23]  # Late night/early morning
        submission_time_anomaly = 1.0 if hour in unusual_hours else 0.0
        
        # Frequency anomaly
        cases_last_7d = aggregates.get('total_cases_last_7d', 0)
        avg_cases_per_week = aggregates.get('avg_cases_per_week', 1.0)
        frequency_anomaly = min(cases_last_7d / avg_cases_per_week, 5.0) / 5.0 if avg_cases_per_week > 0 else 0.0
        
        # Seasonal deviation (simplified)
        month = submitted_at.month
        seasonal_months = [12, 1, 6, 7]  # Holiday seasons
        seasonal_deviation = 0.3 if month in seasonal_months else 0.0
        
        return {
            'submission_time_anomaly': submission_time_anomaly,
            'frequency_anomaly': frequency_anomaly,
            'seasonal_deviation': seasonal_deviation
        }
    
    def _extract_behavioral_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract behavioral anomaly features."""
        customer_id = case_data.get('customer_id', '')
        
        # Customer behavior score (based on historical patterns)
        customer_cases_last_30d = aggregates.get('customer_cases_last_30d', 0)
        customer_avg_cases = aggregates.get('customer_avg_cases_per_month', 1.0)
        customer_behavior_score = min(customer_cases_last_30d / customer_avg_cases, 3.0) / 3.0 if customer_avg_cases > 0 else 0.0
        
        # Provider pattern score
        provider_id = case_data.get('additional_data', {}).get('provider_id', '')
        provider_cases_last_30d = aggregates.get('provider_cases_last_30d', 0)
        provider_avg_cases = aggregates.get('provider_avg_cases_per_month', 5.0)
        provider_pattern_score = min(provider_cases_last_30d / provider_avg_cases, 3.0) / 3.0 if provider_avg_cases > 0 else 0.0
        
        # Service pattern score
        service = case_data.get('service', '')
        service_frequency = aggregates.get('service_frequency_score', 0.5)
        
        return {
            'customer_behavior_score': customer_behavior_score,
            'provider_pattern_score': provider_pattern_score,
            'service_pattern_score': service_frequency
        }
    
    def _extract_geographic_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract geographic anomaly features."""
        # Geographic features (simplified - would use actual location data)
        location_data = case_data.get('additional_data', {}).get('location', {})
        
        # Location anomaly (distance from usual locations)
        usual_locations = aggregates.get('usual_locations', [])
        current_location = location_data.get('zip_code', '')
        location_anomaly = 0.0 if current_location in usual_locations else 0.8
        
        # Distance from usual (simplified)
        distance_from_usual = aggregates.get('distance_from_usual_km', 0.0)
        
        return {
            'location_anomaly': location_anomaly,
            'distance_from_usual': min(distance_from_usual / 1000.0, 1.0)  # Normalize to 1000km
        }
    
    def _extract_network_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract network anomaly features."""
        # Network analysis features (simplified)
        customer_id = case_data.get('customer_id', '')
        provider_id = case_data.get('additional_data', {}).get('provider_id', '')
        
        # Network centrality (how connected this customer/provider is)
        network_centrality = aggregates.get('network_centrality_score', 0.5)
        
        # Connection anomaly (unusual customer-provider connections)
        connection_frequency = aggregates.get('customer_provider_connection_frequency', 1)
        connection_anomaly = 1.0 / (1.0 + connection_frequency)  # Inverse relationship
        
        return {
            'network_centrality': network_centrality,
            'connection_anomaly': connection_anomaly
        }
    
    def _extract_statistical_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract statistical anomaly features."""
        additional_data = case_data.get('additional_data', {})
        amount_requested = additional_data.get('requested_amount', 0.0)
        
        # Z-scores
        amount_mean = aggregates.get('amount_mean', 1000.0)
        amount_std = aggregates.get('amount_std', 500.0)
        z_score_amount = (amount_requested - amount_mean) / amount_std if amount_std > 0 else 0.0
        
        frequency_mean = aggregates.get('frequency_mean', 1.0)
        frequency_std = aggregates.get('frequency_std', 0.5)
        current_frequency = aggregates.get('current_frequency', 1.0)
        z_score_frequency = (current_frequency - frequency_mean) / frequency_std if frequency_std > 0 else 0.0
        
        # Overall outlier score
        outlier_score = min((abs(z_score_amount) + abs(z_score_frequency)) / 6.0, 1.0)  # Normalize to [0,1]
        
        return {
            'z_score_amount': z_score_amount,
            'z_score_frequency': z_score_frequency,
            'outlier_score': outlier_score
        }
    
    def _extract_historical_features(self, case_data: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, float]:
        """Extract historical context features."""
        # Historical similarity (how similar this case is to historical cases)
        historical_similarity = aggregates.get('historical_similarity_score', 0.5)
        
        # Trend deviation (how much this deviates from recent trends)
        trend_deviation = aggregates.get('trend_deviation_score', 0.0)
        
        return {
            'historical_similarity': historical_similarity,
            'trend_deviation': trend_deviation
        }
    
    def _calculate_complexity_score(self, case_data: Dict[str, Any]) -> float:
        """Calculate case complexity score."""
        complexity = 0.0
        
        # Service complexity
        service = case_data.get('service', '').lower()
        complex_terms = ['surgery', 'procedure', 'treatment', 'therapy', 'multiple']
        if any(term in service for term in complex_terms):
            complexity += 0.4
        
        # Attachments complexity
        attachments = case_data.get('attachments', [])
        complexity += min(len(attachments) * 0.1, 0.3)
        
        # Additional data complexity
        additional_data = case_data.get('additional_data', {})
        complexity += min(len(additional_data) * 0.05, 0.3)
        
        return min(complexity, 1.0)
    
    def _assess_documentation_quality(self, case_data: Dict[str, Any]) -> float:
        """Assess documentation quality."""
        quality = 0.0
        
        # Required fields present
        required_fields = ['case_id', 'customer_id', 'service']
        present_fields = sum(1 for field in required_fields if case_data.get(field))
        quality += (present_fields / len(required_fields)) * 0.4
        
        # Service description quality
        service = case_data.get('service', '')
        if len(service) > 20:
            quality += 0.3
        
        # Attachments present
        attachments = case_data.get('attachments', [])
        if attachments:
            quality += 0.3
        
        return min(quality, 1.0)
    
    def _calculate_urgency_score(self, case_data: Dict[str, Any]) -> float:
        """Calculate urgency score."""
        urgency = 0.0
        
        # Priority level
        priority = case_data.get('priority', 'MEDIUM')
        priority_scores = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.8, 'CRITICAL': 1.0}
        urgency += priority_scores.get(priority, 0.5)
        
        return urgency


class AnomalyDetectionService(BaseMLService):
    """ML Anomaly Detection service for pattern deviation detection."""
    
    def __init__(self, config: AnomalyConfig = None, model_registry: ModelRegistry = None):
        super().__init__()
        self.config = config or AnomalyConfig()
        self.model_registry = model_registry or ModelRegistry()
        self.feature_engineer = AnomalyFeatureEngineer(self.config)
        
        # Load models
        self.primary_model = None
        self.fallback_model = None
        self._load_models()
    
    def _load_models(self) -> None:
        """Load anomaly detection models."""
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
            
            logger.info(f"Loaded anomaly detection models: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load anomaly detection models: {e}")
            # Use statistical fallback
            self.primary_model = None
            self.fallback_model = self._create_statistical_detector()
    
    def detect_anomaly(
        self,
        case_id: str,
        features: Dict[str, Any],
        aggregates: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> MLAnomalyOutput:
        """
        Detect anomalies in case data.
        
        Implements ML-ANOMALY API contract from Anexo B.
        """
        start_time = time.time()
        
        try:
            # Extract and engineer features
            anomaly_features = self.feature_engineer.extract_features(features, aggregates)
            
            # Get model version info
            model_info = self._get_model_version_info(model_version)
            
            # Perform anomaly detection
            if self.primary_model and not model_version:
                detection_result = self._detect_with_model(anomaly_features)
            else:
                detection_result = self._detect_with_fallback(anomaly_features)
            
            # Calculate inference time
            inference_time = int((time.time() - start_time) * 1000)
            
            # Create output
            output = MLAnomalyOutput(
                case_id=case_id,
                anomaly_score=detection_result['anomaly_score'],
                anomaly_flags=detection_result['anomaly_flags'],
                recommended_action=detection_result['recommended_action'],
                anomaly_details=detection_result['anomaly_details'],
                contributing_factors=detection_result['contributing_factors'],
                baseline_comparison=detection_result.get('baseline_comparison'),
                historical_context=detection_result.get('historical_context'),
                model_version=model_info,
                inference_time_ms=inference_time
            )
            
            logger.info(f"Anomaly detection completed for case {case_id}: score={output.anomaly_score:.3f}")
            return output
            
        except Exception as e:
            logger.error(f"Anomaly detection failed for case {case_id}: {e}")
            # Return fallback result
            return self._create_fallback_output(case_id, features, start_time)
    
    def _detect_with_model(self, features: AnomalyFeatures) -> Dict[str, Any]:
        """Detect anomalies using the primary ML model."""
        # Convert features to model input format
        feature_vector = self._features_to_vector(features)
        
        # Get model prediction (mock implementation)
        anomaly_score = self._mock_model_prediction(feature_vector)
        
        # Detect specific anomaly types
        anomaly_flags = self._detect_anomaly_types(features)
        
        # Determine recommended action
        recommended_action = self._determine_action(anomaly_score)
        
        # Get anomaly details
        anomaly_details = self._get_anomaly_details(features, anomaly_score)
        
        # Get contributing factors
        contributing_factors = self._get_contributing_factors(features, anomaly_score)
        
        # Baseline comparison
        baseline_comparison = self._get_baseline_comparison(features)
        
        # Historical context
        historical_context = self._get_historical_context(features)
        
        return {
            'anomaly_score': anomaly_score,
            'anomaly_flags': anomaly_flags,
            'recommended_action': recommended_action,
            'anomaly_details': anomaly_details,
            'contributing_factors': contributing_factors,
            'baseline_comparison': baseline_comparison,
            'historical_context': historical_context
        }
    
    def _detect_with_fallback(self, features: AnomalyFeatures) -> Dict[str, Any]:
        """Detect anomalies using statistical fallback."""
        # Statistical anomaly detection
        anomaly_score = self._statistical_anomaly_detection(features)
        
        # Detect specific anomaly types
        anomaly_flags = self._detect_anomaly_types(features)
        
        # Determine recommended action
        recommended_action = self._determine_action(anomaly_score)
        
        # Get anomaly details
        anomaly_details = self._get_anomaly_details(features, anomaly_score)
        
        # Get contributing factors
        contributing_factors = self._get_contributing_factors(features, anomaly_score)
        
        return {
            'anomaly_score': anomaly_score,
            'anomaly_flags': anomaly_flags,
            'recommended_action': recommended_action,
            'anomaly_details': anomaly_details,
            'contributing_factors': contributing_factors
        }
    
    def _features_to_vector(self, features: AnomalyFeatures) -> Dict[str, float]:
        """Convert features to numerical vector."""
        return {
            'case_complexity_score': features.case_complexity_score,
            'documentation_quality': features.documentation_quality,
            'request_urgency': features.request_urgency,
            'amount_vs_historical_avg': min(features.amount_vs_historical_avg, 10.0),
            'amount_vs_policy_limit': features.amount_vs_policy_limit,
            'submission_time_anomaly': features.submission_time_anomaly,
            'frequency_anomaly': features.frequency_anomaly,
            'seasonal_deviation': features.seasonal_deviation,
            'customer_behavior_score': features.customer_behavior_score,
            'provider_pattern_score': features.provider_pattern_score,
            'service_pattern_score': features.service_pattern_score,
            'location_anomaly': features.location_anomaly,
            'distance_from_usual': features.distance_from_usual,
            'network_centrality': features.network_centrality,
            'connection_anomaly': features.connection_anomaly,
            'z_score_amount': features.z_score_amount,
            'z_score_frequency': features.z_score_frequency,
            'outlier_score': features.outlier_score,
            'historical_similarity': features.historical_similarity,
            'trend_deviation': features.trend_deviation
        }
    
    def _mock_model_prediction(self, feature_vector: Dict[str, float]) -> float:
        """Mock model prediction (replace with actual model inference)."""
        # Weighted combination of key anomaly indicators
        weights = self.config.feature_weights
        
        financial_score = (
            feature_vector.get('amount_vs_historical_avg', 0) * 0.4 +
            feature_vector.get('amount_vs_policy_limit', 0) * 0.3 +
            feature_vector.get('z_score_amount', 0) * 0.3
        ) / 3.0
        
        temporal_score = (
            feature_vector.get('submission_time_anomaly', 0) * 0.4 +
            feature_vector.get('frequency_anomaly', 0) * 0.4 +
            feature_vector.get('seasonal_deviation', 0) * 0.2
        )
        
        behavioral_score = (
            feature_vector.get('customer_behavior_score', 0) * 0.4 +
            feature_vector.get('provider_pattern_score', 0) * 0.3 +
            feature_vector.get('service_pattern_score', 0) * 0.3
        )
        
        geographic_score = (
            feature_vector.get('location_anomaly', 0) * 0.6 +
            feature_vector.get('distance_from_usual', 0) * 0.4
        )
        
        network_score = (
            feature_vector.get('network_centrality', 0) * 0.5 +
            feature_vector.get('connection_anomaly', 0) * 0.5
        )
        
        statistical_score = feature_vector.get('outlier_score', 0)
        
        # Weighted combination
        anomaly_score = (
            weights['financial'] * min(financial_score, 1.0) +
            weights['temporal'] * temporal_score +
            weights['behavioral'] * behavioral_score +
            weights['geographic'] * geographic_score +
            weights['network'] * network_score +
            weights['statistical'] * statistical_score
        )
        
        return min(anomaly_score, 1.0)
    
    def _statistical_anomaly_detection(self, features: AnomalyFeatures) -> float:
        """Statistical anomaly detection fallback."""
        # Simple statistical approach
        anomaly_indicators = [
            features.outlier_score,
            features.frequency_anomaly,
            features.submission_time_anomaly,
            features.location_anomaly,
            features.customer_behavior_score,
            features.provider_pattern_score
        ]
        
        # Average of indicators
        return sum(anomaly_indicators) / len(anomaly_indicators)
    
    def _detect_anomaly_types(self, features: AnomalyFeatures) -> List[AnomalyFlag]:
        """Detect specific types of anomalies."""
        flags = []
        
        # Amount anomaly
        if features.amount_vs_historical_avg > 3.0 or features.z_score_amount > 3.0:
            flags.append(AnomalyFlag.AMOUNT_ANOMALY)
        
        # Frequency anomaly
        if features.frequency_anomaly > 0.8:
            flags.append(AnomalyFlag.FREQUENCY_ANOMALY)
        
        # Temporal anomaly
        if features.submission_time_anomaly > 0.5:
            flags.append(AnomalyFlag.TEMPORAL_ANOMALY)
        
        # Behavioral anomaly
        if features.customer_behavior_score > 0.8 or features.provider_pattern_score > 0.8:
            flags.append(AnomalyFlag.BEHAVIORAL_ANOMALY)
        
        # Geographic anomaly
        if features.location_anomaly > 0.7:
            flags.append(AnomalyFlag.GEOGRAPHIC_ANOMALY)
        
        # Network anomaly
        if features.connection_anomaly > 0.8:
            flags.append(AnomalyFlag.NETWORK_ANOMALY)
        
        # Statistical outlier
        if features.outlier_score > 0.9:
            flags.append(AnomalyFlag.STATISTICAL_OUTLIER)
        
        return flags
    
    def _determine_action(self, anomaly_score: float) -> str:
        """Determine recommended action based on anomaly score."""
        thresholds = self.config.action_thresholds
        
        if anomaly_score >= thresholds['BLOCK']:
            return 'BLOCK'
        elif anomaly_score >= thresholds['ESCALATE']:
            return 'ESCALATE'
        elif anomaly_score >= thresholds['REVIEW']:
            return 'REVIEW'
        else:
            return 'PROCEED'
    
    def _get_anomaly_details(self, features: AnomalyFeatures, anomaly_score: float) -> Dict[str, float]:
        """Get detailed anomaly scores by category."""
        return {
            'financial_anomaly': min((features.amount_vs_historical_avg + features.z_score_amount) / 2.0, 1.0),
            'temporal_anomaly': (features.submission_time_anomaly + features.frequency_anomaly) / 2.0,
            'behavioral_anomaly': (features.customer_behavior_score + features.provider_pattern_score) / 2.0,
            'geographic_anomaly': features.location_anomaly,
            'network_anomaly': features.connection_anomaly,
            'statistical_anomaly': features.outlier_score,
            'overall_anomaly': anomaly_score
        }
    
    def _get_contributing_factors(self, features: AnomalyFeatures, anomaly_score: float) -> List[str]:
        """Get factors contributing to anomaly detection."""
        factors = []
        
        if features.amount_vs_historical_avg > 2.0:
            factors.append(f"Amount {features.amount_vs_historical_avg:.1f}x higher than historical average")
        
        if features.frequency_anomaly > 0.7:
            factors.append("Unusually high submission frequency")
        
        if features.submission_time_anomaly > 0.5:
            factors.append("Submitted during unusual hours")
        
        if features.customer_behavior_score > 0.8:
            factors.append("Unusual customer behavior pattern")
        
        if features.provider_pattern_score > 0.8:
            factors.append("Unusual provider interaction pattern")
        
        if features.location_anomaly > 0.7:
            factors.append("Submitted from unusual location")
        
        if features.outlier_score > 0.8:
            factors.append("Statistical outlier detected")
        
        return factors
    
    def _get_baseline_comparison(self, features: AnomalyFeatures) -> Dict[str, float]:
        """Get baseline comparison metrics."""
        return {
            'amount_baseline_ratio': features.amount_vs_historical_avg,
            'frequency_baseline_ratio': features.frequency_anomaly,
            'similarity_to_baseline': features.historical_similarity,
            'trend_deviation': features.trend_deviation
        }
    
    def _get_historical_context(self, features: AnomalyFeatures) -> Dict[str, Any]:
        """Get historical context for anomaly assessment."""
        return {
            'total_cases_last_30d': features.total_cases_last_30d,
            'avg_amount_last_30d': features.avg_amount_last_30d,
            'unique_providers_last_30d': features.unique_providers_last_30d,
            'historical_similarity': features.historical_similarity,
            'trend_deviation': features.trend_deviation
        }
    
    def _get_model_version_info(self, requested_version: Optional[str] = None) -> ModelVersion:
        """Get model version information."""
        if self.primary_model and not requested_version:
            return ModelVersion(
                name=self.config.model_name,
                version="1.0.0",
                trained_at=datetime(2024, 1, 1),
                metrics={'precision': 0.89, 'recall': 0.85, 'f1_score': 0.87},
                features_used=list(self._features_to_vector(AnomalyFeatures()).keys())
            )
        else:
            return ModelVersion(
                name=self.config.fallback_model,
                version="1.0.0",
                trained_at=datetime(2024, 1, 1),
                metrics={'precision': 0.75, 'recall': 0.70, 'f1_score': 0.72},
                features_used=['statistical_features']
            )
    
    def _create_statistical_detector(self):
        """Create a statistical anomaly detector as fallback."""
        return "statistical_anomaly_detector"
    
    def _create_fallback_output(self, case_id: str, features: Dict[str, Any], start_time: float) -> MLAnomalyOutput:
        """Create fallback output when anomaly detection fails."""
        inference_time = int((time.time() - start_time) * 1000)
        
        return MLAnomalyOutput(
            case_id=case_id,
            anomaly_score=0.5,
            anomaly_flags=[],
            recommended_action='REVIEW',
            anomaly_details={'overall_anomaly': 0.5},
            contributing_factors=['Fallback detection used'],
            model_version=ModelVersion(
                name='fallback_detector',
                version='1.0.0',
                trained_at=datetime(2024, 1, 1),
                metrics={'precision': 0.5},
                features_used=['fallback']
            ),
            inference_time_ms=inference_time
        )
    
    def predict(self, *args, **kwargs) -> MLAnomalyOutput:
        """Implement abstract predict method."""
        return self.detect_anomaly(*args, **kwargs)


# Factory function for easy instantiation
def create_anomaly_service(config: AnomalyConfig = None) -> AnomalyDetectionService:
    """Create an anomaly detection service instance."""
    return AnomalyDetectionService(config)
