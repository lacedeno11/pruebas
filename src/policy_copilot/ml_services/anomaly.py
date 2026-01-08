"""
ML Anomaly Detection Service (UC-OP-12)

This module implements the ML Anomaly Detection service for risk assessment
and pattern detection as specified in Anexo B.

API Contract:
Request: {case_id, features, aggregates, model_version?}
Response: {anomaly_score, anomaly_flags, recommended_action, model_version}
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
import asyncio
import json

from .base import BaseMLService, BaseMLRequest, BaseMLResponse, MockMLService, MLServiceError

logger = logging.getLogger(__name__)


class MLAnomalyRequest(BaseMLRequest):
    """
    ML Anomaly Detection service request model.
    
    Implements the API contract from Anexo B:
    {case_id, features, aggregates, model_version?}
    """
    features: Dict[str, Any] = Field(..., description="Feature vector for anomaly detection")
    aggregates: Dict[str, Any] = Field(..., description="Aggregated historical data for comparison")
    
    class Config:
        schema_extra = {
            "example": {
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "features": {
                    "service_amount": 2500.0,
                    "service_code": "SURGERY_CARDIAC",
                    "provider_id": "PROV_001",
                    "customer_id": "CUST_12345",
                    "service_date": "2024-01-15",
                    "diagnosis_codes": ["I25.9", "Z95.1"],
                    "procedure_codes": ["33533", "33534"],
                    "provider_specialty": "CARDIOLOGY",
                    "service_location": "HOSPITAL",
                    "urgency_level": "URGENT",
                    "attachment_types": ["MEDICAL_REPORT", "LAB_RESULTS"],
                    "previous_related_claims": 0,
                    "time_since_last_claim": 365
                },
                "aggregates": {
                    "customer_30d": {
                        "claim_count": 1,
                        "total_amount": 150.0,
                        "avg_amount": 150.0,
                        "service_types": ["CONSULTATION"]
                    },
                    "customer_12m": {
                        "claim_count": 3,
                        "total_amount": 800.0,
                        "avg_amount": 266.67,
                        "service_types": ["CONSULTATION", "DIAGNOSTIC"]
                    },
                    "provider_30d": {
                        "claim_count": 45,
                        "total_amount": 67500.0,
                        "avg_amount": 1500.0,
                        "unique_customers": 42
                    },
                    "service_code_30d": {
                        "claim_count": 8,
                        "total_amount": 20000.0,
                        "avg_amount": 2500.0,
                        "unique_providers": 3
                    }
                },
                "model_version": "anomaly-v1.5.0"
            }
        }


class MLAnomalyResponse(BaseMLResponse):
    """
    ML Anomaly Detection service response model.
    
    Implements the API contract from Anexo B:
    {anomaly_score, anomaly_flags, recommended_action, model_version}
    """
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Anomaly score (0.0 = normal, 1.0 = highly anomalous)")
    anomaly_flags: List[str] = Field(..., description="List of specific anomaly flags detected")
    recommended_action: str = Field(..., description="Recommended action based on anomaly level")
    
    class Config:
        schema_extra = {
            "example": {
                "anomaly_score": 0.75,
                "anomaly_flags": [
                    "AMOUNT_OUTLIER",
                    "UNUSUAL_PROVIDER_PATTERN",
                    "RAPID_CLAIM_SEQUENCE"
                ],
                "recommended_action": "MANUAL_REVIEW",
                "model_version": "anomaly-v1.5.0",
                "processed_at": "2024-01-15T10:30:00Z",
                "processing_time_ms": 200
            }
        }


class MLAnomalyService(BaseMLService):
    """
    ML Anomaly Detection service implementation for UC-OP-12.
    
    Detects unusual patterns and potential fraud indicators using
    statistical analysis and machine learning models.
    """
    
    def __init__(self, model_endpoint: Optional[str] = None, default_model_version: str = "anomaly-v1.5.0"):
        super().__init__("anomaly", default_model_version)
        self.model_endpoint = model_endpoint
        self.anomaly_thresholds = self._initialize_thresholds()
        self.anomaly_rules = self._initialize_anomaly_rules()
        
    def _initialize_thresholds(self) -> Dict[str, float]:
        """Initialize anomaly detection thresholds"""
        return {
            "amount_outlier_threshold": 3.0,  # Standard deviations
            "frequency_outlier_threshold": 2.5,
            "provider_pattern_threshold": 0.8,
            "temporal_pattern_threshold": 0.7,
            "customer_behavior_threshold": 0.6,
            "service_combination_threshold": 0.75
        }
    
    def _initialize_anomaly_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize rule-based anomaly detection patterns"""
        return {
            "amount_rules": {
                "high_amount_threshold": 5000.0,
                "amount_increase_factor": 5.0,
                "amount_percentile_threshold": 95
            },
            "frequency_rules": {
                "max_claims_per_day": 3,
                "max_claims_per_week": 10,
                "min_time_between_claims_hours": 2
            },
            "provider_rules": {
                "new_provider_high_amount": 1000.0,
                "provider_specialty_mismatch": True,
                "provider_location_distance_km": 100
            },
            "temporal_rules": {
                "weekend_high_amount": 2000.0,
                "after_hours_threshold": 1500.0,
                "holiday_pattern_check": True
            },
            "customer_rules": {
                "new_customer_high_amount": 3000.0,
                "customer_age_service_mismatch": True,
                "rapid_escalation_factor": 3.0
            }
        }
    
    async def predict(self, request: MLAnomalyRequest) -> MLAnomalyResponse:
        """
        Perform anomaly detection.
        
        Args:
            request: Anomaly detection request with features and aggregates
            
        Returns:
            Anomaly detection response with score and flags
            
        Raises:
            MLServiceError: If detection fails
        """
        start_time = datetime.utcnow()
        
        try:
            await self._validate_request(request)
            
            # Process features and aggregates
            processed_features = await self._process_features(request.features, request.aggregates)
            
            # Get model version
            model_version = self._get_model_version(request)
            
            # Perform anomaly detection
            if self.model_endpoint:
                detection_result = await self._call_external_model(processed_features, model_version)
            else:
                detection_result = await self._call_local_model(processed_features, model_version)
            
            # Process detection results
            response = await self._process_detection_result(
                detection_result, model_version, request.case_id
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            response.processing_time_ms = int(processing_time)
            
            await self._reset_error_count()
            return response
            
        except Exception as e:
            await self._handle_error(e)
            raise MLServiceError(f"Anomaly detection failed: {str(e)}")
    
    async def _process_features(self, features: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate input features and aggregates.
        
        Args:
            features: Raw input features
            aggregates: Historical aggregate data
            
        Returns:
            Processed features ready for model input
        """
        processed = {
            "features": features.copy(),
            "aggregates": aggregates.copy()
        }
        
        # Calculate derived anomaly indicators
        processed["anomaly_indicators"] = await self._calculate_anomaly_indicators(features, aggregates)
        
        # Add temporal features
        processed["temporal_features"] = await self._extract_temporal_features(features)
        
        # Add comparative features
        processed["comparative_features"] = await self._calculate_comparative_features(features, aggregates)
        
        return processed
    
    async def _calculate_anomaly_indicators(self, features: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate specific anomaly indicators"""
        indicators = {}
        
        current_amount = features.get("service_amount", 0.0)
        
        # Amount-based indicators
        customer_12m = aggregates.get("customer_12m", {})
        if customer_12m.get("avg_amount", 0) > 0:
            indicators["amount_vs_customer_avg"] = current_amount / customer_12m["avg_amount"]
        else:
            indicators["amount_vs_customer_avg"] = 1.0
        
        provider_30d = aggregates.get("provider_30d", {})
        if provider_30d.get("avg_amount", 0) > 0:
            indicators["amount_vs_provider_avg"] = current_amount / provider_30d["avg_amount"]
        else:
            indicators["amount_vs_provider_avg"] = 1.0
        
        service_30d = aggregates.get("service_code_30d", {})
        if service_30d.get("avg_amount", 0) > 0:
            indicators["amount_vs_service_avg"] = current_amount / service_30d["avg_amount"]
        else:
            indicators["amount_vs_service_avg"] = 1.0
        
        # Frequency-based indicators
        customer_30d = aggregates.get("customer_30d", {})
        indicators["customer_claim_frequency_30d"] = customer_30d.get("claim_count", 0)
        indicators["customer_amount_velocity_30d"] = customer_30d.get("total_amount", 0.0)
        
        # Provider pattern indicators
        indicators["provider_customer_ratio"] = (
            provider_30d.get("claim_count", 1) / max(provider_30d.get("unique_customers", 1), 1)
        )
        
        # Service pattern indicators
        indicators["service_provider_diversity"] = service_30d.get("unique_providers", 1)
        
        return indicators
    
    async def _extract_temporal_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract temporal pattern features"""
        temporal = {}
        
        # Parse service date
        service_date_str = features.get("service_date")
        if service_date_str:
            try:
                service_date = datetime.fromisoformat(service_date_str.replace('Z', '+00:00'))
                
                temporal["day_of_week"] = service_date.weekday()
                temporal["hour_of_day"] = service_date.hour
                temporal["is_weekend"] = service_date.weekday() >= 5
                temporal["is_after_hours"] = service_date.hour < 8 or service_date.hour > 18
                temporal["is_holiday"] = await self._is_holiday(service_date)
                
            except (ValueError, AttributeError):
                temporal["day_of_week"] = 0
                temporal["hour_of_day"] = 12
                temporal["is_weekend"] = False
                temporal["is_after_hours"] = False
                temporal["is_holiday"] = False
        
        # Time since last claim
        time_since_last = features.get("time_since_last_claim", 365)
        temporal["time_since_last_claim_days"] = time_since_last
        temporal["is_rapid_sequence"] = time_since_last < 7
        
        return temporal
    
    async def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday (simplified implementation)"""
        # Simplified holiday check - in production, use a proper holiday library
        holidays = [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day
            (12, 25), # Christmas
        ]
        
        return (date.month, date.day) in holidays
    
    async def _calculate_comparative_features(self, features: Dict[str, Any], aggregates: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comparative features against historical patterns"""
        comparative = {}
        
        # Service code analysis
        service_code = features.get("service_code", "")
        customer_12m = aggregates.get("customer_12m", {})
        customer_services = customer_12m.get("service_types", [])
        
        comparative["is_new_service_for_customer"] = service_code not in customer_services
        comparative["customer_service_diversity"] = len(set(customer_services))
        
        # Provider analysis
        provider_id = features.get("provider_id", "")
        comparative["is_new_provider_for_customer"] = True  # Simplified - would need historical data
        
        # Diagnosis/procedure analysis
        diagnosis_codes = features.get("diagnosis_codes", [])
        procedure_codes = features.get("procedure_codes", [])
        
        comparative["diagnosis_count"] = len(diagnosis_codes)
        comparative["procedure_count"] = len(procedure_codes)
        comparative["is_complex_case"] = len(diagnosis_codes) > 2 or len(procedure_codes) > 2
        
        return comparative
    
    async def _call_external_model(self, features: Dict[str, Any], model_version: str) -> Dict[str, Any]:
        """
        Call external ML model endpoint.
        
        Args:
            features: Processed features
            model_version: Model version to use
            
        Returns:
            Raw detection result
        """
        import aiohttp
        
        payload = {
            "features": features,
            "model_version": model_version
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.model_endpoint}/detect",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise MLServiceError(f"External model returned status {response.status}")
                
                return await response.json()
    
    async def _call_local_model(self, features: Dict[str, Any], model_version: str) -> Dict[str, Any]:
        """
        Call local anomaly detection model (rule-based fallback).
        
        Args:
            features: Processed features
            model_version: Model version to use
            
        Returns:
            Detection result
        """
        # Simulate model inference delay
        await asyncio.sleep(0.15)
        
        anomaly_flags = []
        anomaly_score = 0.0
        
        # Extract features
        base_features = features.get("features", {})
        indicators = features.get("anomaly_indicators", {})
        temporal = features.get("temporal_features", {})
        comparative = features.get("comparative_features", {})
        
        current_amount = base_features.get("service_amount", 0.0)
        
        # Amount-based anomaly detection
        amount_vs_customer = indicators.get("amount_vs_customer_avg", 1.0)
        if amount_vs_customer > self.anomaly_thresholds["amount_outlier_threshold"]:
            anomaly_flags.append("AMOUNT_OUTLIER")
            anomaly_score += 0.3
        
        if current_amount > self.anomaly_rules["amount_rules"]["high_amount_threshold"]:
            anomaly_flags.append("HIGH_AMOUNT")
            anomaly_score += 0.2
        
        # Frequency-based anomaly detection
        claim_frequency = indicators.get("customer_claim_frequency_30d", 0)
        if claim_frequency > self.anomaly_rules["frequency_rules"]["max_claims_per_week"]:
            anomaly_flags.append("HIGH_FREQUENCY")
            anomaly_score += 0.25
        
        if temporal.get("is_rapid_sequence", False):
            anomaly_flags.append("RAPID_CLAIM_SEQUENCE")
            anomaly_score += 0.2
        
        # Provider pattern anomaly detection
        provider_ratio = indicators.get("provider_customer_ratio", 1.0)
        if provider_ratio > self.anomaly_thresholds["provider_pattern_threshold"]:
            anomaly_flags.append("UNUSUAL_PROVIDER_PATTERN")
            anomaly_score += 0.15
        
        # Temporal pattern anomaly detection
        if temporal.get("is_after_hours", False) and current_amount > self.anomaly_rules["temporal_rules"]["after_hours_threshold"]:
            anomaly_flags.append("AFTER_HOURS_HIGH_AMOUNT")
            anomaly_score += 0.1
        
        if temporal.get("is_weekend", False) and current_amount > self.anomaly_rules["temporal_rules"]["weekend_high_amount"]:
            anomaly_flags.append("WEEKEND_HIGH_AMOUNT")
            anomaly_score += 0.1
        
        # Service pattern anomaly detection
        if comparative.get("is_new_service_for_customer", False) and current_amount > 1000:
            anomaly_flags.append("NEW_SERVICE_HIGH_AMOUNT")
            anomaly_score += 0.15
        
        if comparative.get("is_complex_case", False):
            anomaly_flags.append("COMPLEX_CASE")
            anomaly_score += 0.05
        
        # Normalize anomaly score
        anomaly_score = min(anomaly_score, 1.0)
        
        # Determine recommended action
        if anomaly_score >= 0.8:
            recommended_action = "BLOCK"
        elif anomaly_score >= 0.6:
            recommended_action = "MANUAL_REVIEW"
        elif anomaly_score >= 0.4:
            recommended_action = "PRIORITY_REVIEW"
        elif anomaly_score >= 0.2:
            recommended_action = "AUTOMATED_REVIEW"
        else:
            recommended_action = "APPROVE"
        
        return {
            "anomaly_score": anomaly_score,
            "anomaly_flags": anomaly_flags,
            "recommended_action": recommended_action
        }
    
    async def _process_detection_result(
        self, 
        detection: Dict[str, Any], 
        model_version: str, 
        case_id: str
    ) -> MLAnomalyResponse:
        """
        Process raw detection result into response format.
        
        Args:
            detection: Raw detection from model
            model_version: Model version used
            case_id: Case ID for logging
            
        Returns:
            Formatted anomaly response
        """
        anomaly_score = detection.get("anomaly_score", 0.0)
        anomaly_flags = detection.get("anomaly_flags", [])
        recommended_action = detection.get("recommended_action", "APPROVE")
        
        response = MLAnomalyResponse(
            anomaly_score=anomaly_score,
            anomaly_flags=anomaly_flags,
            recommended_action=recommended_action,
            model_version=model_version
        )
        
        logger.info(f"Anomaly detection completed for case {case_id}: score={anomaly_score:.3f}, action={recommended_action}")
        
        return response
    
    async def health_check(self) -> "MLServiceHealth":
        """Check service health"""
        from .base import MLServiceHealth
        
        start_time = datetime.utcnow()
        
        try:
            # Test with dummy features
            test_features = {
                "service_amount": 100.0,
                "service_code": "TEST",
                "provider_id": "TEST_PROVIDER"
            }
            test_aggregates = {
                "customer_30d": {"claim_count": 1, "avg_amount": 100.0},
                "provider_30d": {"claim_count": 10, "avg_amount": 150.0}
            }
            
            if self.model_endpoint:
                # Test external endpoint
                await self._call_external_model(
                    {"features": test_features, "aggregates": test_aggregates}, 
                    self.default_model_version
                )
            else:
                # Test local model
                await self._call_local_model(
                    {"features": test_features, "aggregates": test_aggregates}, 
                    self.default_model_version
                )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return MLServiceHealth(
                service_name=self.service_name,
                status="healthy",
                model_version=self.default_model_version,
                last_check=datetime.utcnow(),
                response_time_ms=int(response_time)
            )
            
        except Exception as e:
            return MLServiceHealth(
                service_name=self.service_name,
                status="unhealthy",
                model_version=self.default_model_version,
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def get_available_models(self) -> List[str]:
        """Get available model versions"""
        if self.model_endpoint:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.model_endpoint}/models") as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("models", [self.default_model_version])
            except Exception:
                pass
        
        # Fallback to default models
        return [
            "anomaly-v1.5.0",
            "anomaly-v1.4.0",
            "anomaly-v1.3.0"
        ]


class MockMLAnomalyService(MockMLService):
    """
    Mock implementation of ML Anomaly Detection service for development and testing.
    
    Provides deterministic responses based on input patterns.
    """
    
    def __init__(self):
        super().__init__("anomaly", "mock-anomaly-1.0.0")
        self._setup_mock_responses()
    
    def _setup_mock_responses(self):
        """Setup predefined mock responses"""
        self.mock_patterns = {
            "normal": {
                "anomaly_score": 0.1,
                "anomaly_flags": [],
                "recommended_action": "APPROVE"
            },
            "suspicious": {
                "anomaly_score": 0.6,
                "anomaly_flags": ["AMOUNT_OUTLIER", "HIGH_FREQUENCY"],
                "recommended_action": "MANUAL_REVIEW"
            },
            "high_risk": {
                "anomaly_score": 0.9,
                "anomaly_flags": ["AMOUNT_OUTLIER", "UNUSUAL_PROVIDER_PATTERN", "RAPID_CLAIM_SEQUENCE"],
                "recommended_action": "BLOCK"
            }
        }
    
    async def predict(self, request: MLAnomalyRequest) -> MLAnomalyResponse:
        """Mock prediction implementation"""
        await self._validate_request(request)
        
        # Simulate processing delay
        await asyncio.sleep(self.mock_delay_ms / 1000)
        
        # Check for specific mock response
        if hasattr(request, 'case_id') and request.case_id in self.mock_responses:
            return self.mock_responses[request.case_id]
        
        # Pattern-based response
        amount = request.features.get("service_amount", 0.0)
        
        if amount > 5000:
            pattern = "high_risk"
        elif amount > 1000:
            pattern = "suspicious"
        else:
            pattern = "normal"
        
        response_data = self.mock_patterns[pattern]
        
        return MLAnomalyResponse(
            **response_data,
            model_version=self.default_model_version,
            processing_time_ms=self.mock_delay_ms
        )
