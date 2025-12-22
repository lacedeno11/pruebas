"""
ML ETA Prediction Service (UC-OP-13)

This module implements the ML ETA (Estimated Time to Arrival) prediction service
for SLA management and expectation setting as specified in Anexo B.

API Contract:
Request: {case_id, features, model_version?}
Response: {eta_minutes, p50, p90?, model_version}
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
import asyncio
import json

from .base import BaseMLService, BaseMLRequest, BaseMLResponse, MockMLService, MLServiceError

logger = logging.getLogger(__name__)


class MLETARequest(BaseMLRequest):
    """
    ML ETA Prediction service request model.
    
    Implements the API contract from Anexo B:
    {case_id, features, model_version?}
    """
    features: Dict[str, Any] = Field(..., description="Feature vector for ETA prediction")
    
    class Config:
        schema_extra = {
            "example": {
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "features": {
                    "request_type": "MEDICAL_CONSULTATION",
                    "service_code": "CONSULTATION_GENERAL",
                    "insurer_id": "INS001",
                    "plan_id": "PLAN_BASIC",
                    "priority": "MEDIUM",
                    "service_amount": 150.0,
                    "complexity_score": 2,
                    "requires_external_query": False,
                    "requires_manual_review": False,
                    "evidence_completeness": 0.8,
                    "policy_coverage_score": 0.9,
                    "anomaly_score": 0.1,
                    "attachment_count": 1,
                    "attachment_types": ["MEDICAL_REPORT"],
                    "provider_type": "CLINIC",
                    "service_urgency": "NORMAL",
                    "customer_history": {
                        "total_claims": 5,
                        "avg_processing_time": 1440,
                        "approval_rate": 0.9
                    },
                    "provider_history": {
                        "total_claims": 150,
                        "avg_processing_time": 720,
                        "approval_rate": 0.95
                    },
                    "insurer_sla": {
                        "standard_sla_hours": 24,
                        "priority_sla_hours": 12,
                        "complex_sla_hours": 48
                    },
                    "current_queue_load": 25,
                    "available_reviewers": 3,
                    "time_of_day": 14,
                    "day_of_week": 2,
                    "is_holiday": False
                },
                "model_version": "eta-v1.2.0"
            }
        }


class MLETAResponse(BaseMLResponse):
    """
    ML ETA Prediction service response model.
    
    Implements the API contract from Anexo B:
    {eta_minutes, p50, p90?, model_version}
    """
    eta_minutes: int = Field(..., ge=0, description="Estimated time to completion in minutes")
    p50: Optional[int] = Field(None, ge=0, description="50th percentile estimate (median)")
    p90: Optional[int] = Field(None, ge=0, description="90th percentile estimate")
    
    class Config:
        schema_extra = {
            "example": {
                "eta_minutes": 720,  # 12 hours
                "p50": 600,          # 10 hours
                "p90": 1200,         # 20 hours
                "model_version": "eta-v1.2.0",
                "processed_at": "2024-01-15T10:30:00Z",
                "processing_time_ms": 100
            }
        }


class MLETAService(BaseMLService):
    """
    ML ETA Prediction service implementation for UC-OP-13.
    
    Predicts processing time for cases to support SLA management,
    resource planning, and customer expectation setting.
    """
    
    def __init__(self, model_endpoint: Optional[str] = None, default_model_version: str = "eta-v1.2.0"):
        super().__init__("eta", default_model_version)
        self.model_endpoint = model_endpoint
        self.base_processing_times = self._initialize_base_times()
        self.complexity_factors = self._initialize_complexity_factors()
        self.queue_factors = self._initialize_queue_factors()
        
    def _initialize_base_times(self) -> Dict[str, int]:
        """Initialize base processing times by request type (in minutes)"""
        return {
            "MEDICAL_CONSULTATION": 480,      # 8 hours
            "EMERGENCY_CARE": 120,            # 2 hours
            "SPECIALIST_REFERRAL": 720,       # 12 hours
            "SURGERY": 1440,                  # 24 hours
            "DIAGNOSTIC_TEST": 360,           # 6 hours
            "MEDICATION": 240,                # 4 hours
            "THERAPY": 480,                   # 8 hours
            "DENTAL_CARE": 360,               # 6 hours
            "MENTAL_HEALTH": 960,             # 16 hours
            "EXPERIMENTAL_TREATMENT": 2880,   # 48 hours
            "HIGH_COST_PROCEDURE": 1440,      # 24 hours
            "UNKNOWN": 720                    # 12 hours (default)
        }
    
    def _initialize_complexity_factors(self) -> Dict[str, float]:
        """Initialize complexity adjustment factors"""
        return {
            "low_complexity": 0.7,      # 30% faster
            "medium_complexity": 1.0,   # baseline
            "high_complexity": 1.5,     # 50% slower
            "very_high_complexity": 2.0, # 100% slower
            "external_query_required": 1.3,  # 30% slower
            "manual_review_required": 1.4,   # 40% slower
            "expert_review_required": 2.5,   # 150% slower
            "incomplete_evidence": 1.2,      # 20% slower
            "policy_conflict": 1.6,          # 60% slower
            "anomaly_detected": 1.8          # 80% slower
        }
    
    def _initialize_queue_factors(self) -> Dict[str, Any]:
        """Initialize queue and resource factors"""
        return {
            "queue_load_thresholds": {
                "low": 10,      # < 10 cases
                "medium": 25,   # 10-25 cases
                "high": 50,     # 25-50 cases
                "very_high": 100 # > 50 cases
            },
            "queue_load_factors": {
                "low": 0.8,      # 20% faster
                "medium": 1.0,   # baseline
                "high": 1.3,     # 30% slower
                "very_high": 1.8 # 80% slower
            },
            "time_of_day_factors": {
                "business_hours": 1.0,    # 9-17
                "extended_hours": 1.2,    # 7-9, 17-19
                "after_hours": 1.5        # 19-7
            },
            "day_of_week_factors": {
                "weekday": 1.0,
                "weekend": 1.4
            },
            "holiday_factor": 1.6
        }
    
    async def predict(self, request: MLETARequest) -> MLETAResponse:
        """
        Perform ETA prediction.
        
        Args:
            request: ETA prediction request with features
            
        Returns:
            ETA prediction response with estimates
            
        Raises:
            MLServiceError: If prediction fails
        """
        start_time = datetime.utcnow()
        
        try:
            await self._validate_request(request)
            
            # Process features
            processed_features = await self._process_features(request.features)
            
            # Get model version
            model_version = self._get_model_version(request)
            
            # Perform ETA prediction
            if self.model_endpoint:
                prediction_result = await self._call_external_model(processed_features, model_version)
            else:
                prediction_result = await self._call_local_model(processed_features, model_version)
            
            # Process prediction results
            response = await self._process_prediction_result(
                prediction_result, model_version, request.case_id
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            response.processing_time_ms = int(processing_time)
            
            await self._reset_error_count()
            return response
            
        except Exception as e:
            await self._handle_error(e)
            raise MLServiceError(f"ETA prediction failed: {str(e)}")
    
    async def _process_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate input features.
        
        Args:
            features: Raw input features
            
        Returns:
            Processed features ready for model input
        """
        processed = features.copy()
        
        # Add derived features
        processed["derived_features"] = await self._calculate_derived_features(features)
        
        # Add temporal context
        processed["temporal_context"] = await self._extract_temporal_context(features)
        
        # Add resource context
        processed["resource_context"] = await self._extract_resource_context(features)
        
        return processed
    
    async def _calculate_derived_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived features for ETA prediction"""
        derived = {}
        
        # Complexity assessment
        complexity_score = features.get("complexity_score", 1)
        if complexity_score <= 1:
            derived["complexity_level"] = "low_complexity"
        elif complexity_score <= 3:
            derived["complexity_level"] = "medium_complexity"
        elif complexity_score <= 5:
            derived["complexity_level"] = "high_complexity"
        else:
            derived["complexity_level"] = "very_high_complexity"
        
        # Evidence completeness assessment
        evidence_completeness = features.get("evidence_completeness", 1.0)
        derived["evidence_complete"] = evidence_completeness >= 0.8
        derived["evidence_factor"] = "complete" if evidence_completeness >= 0.8 else "incomplete_evidence"
        
        # Policy coverage assessment
        policy_coverage = features.get("policy_coverage_score", 1.0)
        derived["policy_clear"] = policy_coverage >= 0.9
        derived["policy_factor"] = "clear" if policy_coverage >= 0.9 else "policy_conflict"
        
        # Anomaly assessment
        anomaly_score = features.get("anomaly_score", 0.0)
        derived["anomaly_detected"] = anomaly_score >= 0.6
        derived["anomaly_factor"] = "anomaly_detected" if anomaly_score >= 0.6 else "normal"
        
        # Review requirements
        derived["requires_external"] = features.get("requires_external_query", False)
        derived["requires_manual"] = features.get("requires_manual_review", False)
        
        # Historical performance
        customer_history = features.get("customer_history", {})
        derived["customer_avg_time"] = customer_history.get("avg_processing_time", 720)
        derived["customer_approval_rate"] = customer_history.get("approval_rate", 0.9)
        
        provider_history = features.get("provider_history", {})
        derived["provider_avg_time"] = provider_history.get("avg_processing_time", 720)
        derived["provider_approval_rate"] = provider_history.get("approval_rate", 0.9)
        
        return derived
    
    async def _extract_temporal_context(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract temporal context factors"""
        temporal = {}
        
        # Time of day
        time_of_day = features.get("time_of_day", 12)
        if 9 <= time_of_day <= 17:
            temporal["time_period"] = "business_hours"
        elif 7 <= time_of_day < 9 or 17 < time_of_day <= 19:
            temporal["time_period"] = "extended_hours"
        else:
            temporal["time_period"] = "after_hours"
        
        # Day of week
        day_of_week = features.get("day_of_week", 2)  # 0=Monday, 6=Sunday
        temporal["is_weekend"] = day_of_week >= 5
        temporal["day_type"] = "weekend" if day_of_week >= 5 else "weekday"
        
        # Holiday
        temporal["is_holiday"] = features.get("is_holiday", False)
        
        return temporal
    
    async def _extract_resource_context(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract resource and queue context"""
        resource = {}
        
        # Queue load assessment
        queue_load = features.get("current_queue_load", 25)
        thresholds = self.queue_factors["queue_load_thresholds"]
        
        if queue_load < thresholds["low"]:
            resource["queue_load_level"] = "low"
        elif queue_load < thresholds["medium"]:
            resource["queue_load_level"] = "medium"
        elif queue_load < thresholds["high"]:
            resource["queue_load_level"] = "high"
        else:
            resource["queue_load_level"] = "very_high"
        
        # Available reviewers
        available_reviewers = features.get("available_reviewers", 1)
        resource["reviewer_availability"] = "high" if available_reviewers >= 3 else "low"
        
        # Priority assessment
        priority = features.get("priority", "MEDIUM")
        resource["priority_level"] = priority.lower()
        
        return resource
    
    async def _call_external_model(self, features: Dict[str, Any], model_version: str) -> Dict[str, Any]:
        """
        Call external ML model endpoint.
        
        Args:
            features: Processed features
            model_version: Model version to use
            
        Returns:
            Raw prediction result
        """
        import aiohttp
        
        payload = {
            "features": features,
            "model_version": model_version
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.model_endpoint}/predict",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise MLServiceError(f"External model returned status {response.status}")
                
                return await response.json()
    
    async def _call_local_model(self, features: Dict[str, Any], model_version: str) -> Dict[str, Any]:
        """
        Call local ETA prediction model (rule-based fallback).
        
        Args:
            features: Processed features
            model_version: Model version to use
            
        Returns:
            Prediction result
        """
        # Simulate model inference delay
        await asyncio.sleep(0.08)
        
        # Get base processing time
        request_type = features.get("request_type", "UNKNOWN")
        base_time = self.base_processing_times.get(request_type, 720)
        
        # Extract derived features
        derived = features.get("derived_features", {})
        temporal = features.get("temporal_context", {})
        resource = features.get("resource_context", {})
        
        # Apply complexity factors
        complexity_factor = self.complexity_factors.get(derived.get("complexity_level", "medium_complexity"), 1.0)
        eta_minutes = base_time * complexity_factor
        
        # Apply evidence and policy factors
        if not derived.get("evidence_complete", True):
            eta_minutes *= self.complexity_factors["incomplete_evidence"]
        
        if not derived.get("policy_clear", True):
            eta_minutes *= self.complexity_factors["policy_conflict"]
        
        if derived.get("anomaly_detected", False):
            eta_minutes *= self.complexity_factors["anomaly_detected"]
        
        # Apply review requirement factors
        if derived.get("requires_external", False):
            eta_minutes *= self.complexity_factors["external_query_required"]
        
        if derived.get("requires_manual", False):
            eta_minutes *= self.complexity_factors["manual_review_required"]
        
        # Apply queue and resource factors
        queue_load_level = resource.get("queue_load_level", "medium")
        queue_factor = self.queue_factors["queue_load_factors"].get(queue_load_level, 1.0)
        eta_minutes *= queue_factor
        
        # Apply temporal factors
        time_period = temporal.get("time_period", "business_hours")
        time_factor = self.queue_factors["time_of_day_factors"].get(time_period, 1.0)
        eta_minutes *= time_factor
        
        day_type = temporal.get("day_type", "weekday")
        day_factor = self.queue_factors["day_of_week_factors"].get(day_type, 1.0)
        eta_minutes *= day_factor
        
        if temporal.get("is_holiday", False):
            eta_minutes *= self.queue_factors["holiday_factor"]
        
        # Apply historical performance adjustments
        customer_avg = derived.get("customer_avg_time", 720)
        provider_avg = derived.get("provider_avg_time", 720)
        
        # Weight historical performance (30% customer, 20% provider, 50% model)
        historical_avg = (customer_avg * 0.3 + provider_avg * 0.2 + eta_minutes * 0.5)
        eta_minutes = historical_avg
        
        # Apply priority adjustments
        priority = resource.get("priority_level", "medium")
        if priority == "high" or priority == "critical":
            eta_minutes *= 0.7  # 30% faster for high priority
        elif priority == "low":
            eta_minutes *= 1.2  # 20% slower for low priority
        
        # Calculate percentiles (simplified statistical model)
        eta_minutes = int(eta_minutes)
        p50 = int(eta_minutes * 0.8)  # Median is typically faster
        p90 = int(eta_minutes * 1.5)  # 90th percentile accounts for delays
        
        # Ensure minimum times
        eta_minutes = max(eta_minutes, 30)  # Minimum 30 minutes
        p50 = max(p50, 15)                  # Minimum 15 minutes
        p90 = max(p90, eta_minutes)         # P90 >= ETA
        
        return {
            "eta_minutes": eta_minutes,
            "p50": p50,
            "p90": p90
        }
    
    async def _process_prediction_result(
        self, 
        prediction: Dict[str, Any], 
        model_version: str, 
        case_id: str
    ) -> MLETAResponse:
        """
        Process raw prediction result into response format.
        
        Args:
            prediction: Raw prediction from model
            model_version: Model version used
            case_id: Case ID for logging
            
        Returns:
            Formatted ETA response
        """
        eta_minutes = prediction.get("eta_minutes", 720)
        p50 = prediction.get("p50")
        p90 = prediction.get("p90")
        
        response = MLETAResponse(
            eta_minutes=eta_minutes,
            p50=p50,
            p90=p90,
            model_version=model_version
        )
        
        # Convert to hours for logging
        eta_hours = eta_minutes / 60
        logger.info(f"ETA prediction completed for case {case_id}: {eta_hours:.1f} hours ({eta_minutes} minutes)")
        
        return response
    
    async def health_check(self) -> "MLServiceHealth":
        """Check service health"""
        from .base import MLServiceHealth
        
        start_time = datetime.utcnow()
        
        try:
            # Test with dummy features
            test_features = {
                "request_type": "MEDICAL_CONSULTATION",
                "priority": "MEDIUM",
                "complexity_score": 2,
                "evidence_completeness": 0.8
            }
            
            if self.model_endpoint:
                # Test external endpoint
                await self._call_external_model(test_features, self.default_model_version)
            else:
                # Test local model
                await self._call_local_model(test_features, self.default_model_version)
            
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
            "eta-v1.2.0",
            "eta-v1.1.0",
            "eta-v1.0.0"
        ]


class MockMLETAService(MockMLService):
    """
    Mock implementation of ML ETA Prediction service for development and testing.
    
    Provides deterministic responses based on input patterns.
    """
    
    def __init__(self):
        super().__init__("eta", "mock-eta-1.0.0")
        self._setup_mock_responses()
    
    def _setup_mock_responses(self):
        """Setup predefined mock responses"""
        self.mock_patterns = {
            "EMERGENCY_CARE": {
                "eta_minutes": 120,  # 2 hours
                "p50": 90,
                "p90": 180
            },
            "MEDICAL_CONSULTATION": {
                "eta_minutes": 480,  # 8 hours
                "p50": 360,
                "p90": 720
            },
            "SURGERY": {
                "eta_minutes": 1440,  # 24 hours
                "p50": 1200,
                "p90": 2160
            },
            "HIGH_COMPLEXITY": {
                "eta_minutes": 2880,  # 48 hours
                "p50": 2400,
                "p90": 4320
            }
        }
    
    async def predict(self, request: MLETARequest) -> MLETAResponse:
        """Mock prediction implementation"""
        await self._validate_request(request)
        
        # Simulate processing delay
        await asyncio.sleep(self.mock_delay_ms / 1000)
        
        # Check for specific mock response
        if hasattr(request, 'case_id') and request.case_id in self.mock_responses:
            return self.mock_responses[request.case_id]
        
        # Pattern-based response
        request_type = request.features.get("request_type", "MEDICAL_CONSULTATION")
        complexity = request.features.get("complexity_score", 1)
        
        if complexity > 5:
            pattern = "HIGH_COMPLEXITY"
        elif request_type in self.mock_patterns:
            pattern = request_type
        else:
            pattern = "MEDICAL_CONSULTATION"
        
        response_data = self.mock_patterns[pattern]
        
        return MLETAResponse(
            **response_data,
            model_version=self.default_model_version,
            processing_time_ms=self.mock_delay_ms
        )
