"""
ML Classification Service (UC-OP-11)

This module implements the ML Classification service for intelligent routing
and request type prediction as specified in Anexo B.

API Contract:
Request: {case_id, features, model_version?}
Response: {request_type, candidate_policy_ids, route, risk_prior, probabilities, top_features, model_version}
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import asyncio
import json

from .base import BaseMLService, BaseMLRequest, BaseMLResponse, MockMLService, MLServiceError

logger = logging.getLogger(__name__)


class MLClassificationRequest(BaseMLRequest):
    """
    ML Classification service request model.
    
    Implements the API contract from Anexo B:
    {case_id, features, model_version?}
    """
    features: Dict[str, Any] = Field(..., description="Feature vector for classification")
    
    class Config:
        schema_extra = {
            "example": {
                "case_id": "550e8400-e29b-41d4-a716-446655440000",
                "features": {
                    "insurer_id": "INS001",
                    "plan_id": "PLAN_BASIC",
                    "service_code": "CONSULTATION",
                    "service_amount": 150.0,
                    "provider_type": "CLINIC",
                    "customer_age": 35,
                    "customer_gender": "M",
                    "historical_claims": 2,
                    "service_urgency": "NORMAL",
                    "attachment_count": 1,
                    "text_features": {
                        "service_description": "Consulta médica general",
                        "diagnosis_keywords": ["dolor", "cabeza"]
                    }
                },
                "model_version": "classification-v2.1.0"
            }
        }


class MLClassificationResponse(BaseMLResponse):
    """
    ML Classification service response model.
    
    Implements the API contract from Anexo B:
    {request_type, candidate_policy_ids, route, risk_prior, probabilities, top_features, model_version}
    """
    request_type: str = Field(..., description="Predicted request type")
    candidate_policy_ids: List[str] = Field(..., description="List of candidate policy IDs")
    route: str = Field(..., description="Recommended processing route")
    risk_prior: float = Field(..., ge=0.0, le=1.0, description="Prior risk assessment (0.0 to 1.0)")
    probabilities: Dict[str, float] = Field(..., description="Classification probabilities by class")
    top_features: List[str] = Field(..., description="Most important features for this prediction")
    
    class Config:
        schema_extra = {
            "example": {
                "request_type": "MEDICAL_CONSULTATION",
                "candidate_policy_ids": ["POL_MED_001", "POL_MED_002"],
                "route": "AUTO_PROCESS",
                "risk_prior": 0.15,
                "probabilities": {
                    "MEDICAL_CONSULTATION": 0.85,
                    "EMERGENCY_CARE": 0.10,
                    "SPECIALIST_REFERRAL": 0.05
                },
                "top_features": [
                    "service_code",
                    "provider_type",
                    "service_amount",
                    "diagnosis_keywords"
                ],
                "model_version": "classification-v2.1.0",
                "processed_at": "2024-01-15T10:30:00Z",
                "processing_time_ms": 150
            }
        }


class MLClassificationService(BaseMLService):
    """
    ML Classification service implementation for UC-OP-11.
    
    Provides intelligent routing and request type prediction using
    machine learning models trained on historical case data.
    """
    
    def __init__(self, model_endpoint: Optional[str] = None, default_model_version: str = "classification-v2.1.0"):
        super().__init__("classification", default_model_version)
        self.model_endpoint = model_endpoint
        self.feature_extractors = self._initialize_feature_extractors()
        self.route_mappings = self._initialize_route_mappings()
        
    def _initialize_feature_extractors(self) -> Dict[str, Any]:
        """Initialize feature extraction configurations"""
        return {
            "categorical_features": [
                "insurer_id", "plan_id", "service_code", "provider_type",
                "customer_gender", "service_urgency"
            ],
            "numerical_features": [
                "service_amount", "customer_age", "historical_claims",
                "attachment_count"
            ],
            "text_features": [
                "service_description", "diagnosis_keywords"
            ],
            "derived_features": [
                "amount_percentile", "age_group", "claim_frequency",
                "complexity_score"
            ]
        }
    
    def _initialize_route_mappings(self) -> Dict[str, str]:
        """Initialize route mappings based on request types"""
        return {
            "MEDICAL_CONSULTATION": "AUTO_PROCESS",
            "EMERGENCY_CARE": "PRIORITY_REVIEW",
            "SPECIALIST_REFERRAL": "AUTO_PROCESS",
            "SURGERY": "MANUAL_REVIEW",
            "DIAGNOSTIC_TEST": "AUTO_PROCESS",
            "MEDICATION": "AUTO_PROCESS",
            "THERAPY": "AUTO_PROCESS",
            "DENTAL_CARE": "AUTO_PROCESS",
            "MENTAL_HEALTH": "MANUAL_REVIEW",
            "EXPERIMENTAL_TREATMENT": "EXPERT_REVIEW",
            "HIGH_COST_PROCEDURE": "MANUAL_REVIEW",
            "UNKNOWN": "MANUAL_REVIEW"
        }
    
    async def predict(self, request: MLClassificationRequest) -> MLClassificationResponse:
        """
        Perform classification prediction.
        
        Args:
            request: Classification request with features
            
        Returns:
            Classification response with predictions
            
        Raises:
            MLServiceError: If prediction fails
        """
        start_time = datetime.utcnow()
        
        try:
            await self._validate_request(request)
            
            # Extract and validate features
            processed_features = await self._process_features(request.features)
            
            # Get model version
            model_version = self._get_model_version(request)
            
            # Perform prediction
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
            raise MLServiceError(f"Classification prediction failed: {str(e)}")
    
    async def _process_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate input features.
        
        Args:
            features: Raw input features
            
        Returns:
            Processed features ready for model input
        """
        processed = {}
        
        # Process categorical features
        for feature in self.feature_extractors["categorical_features"]:
            if feature in features:
                processed[feature] = str(features[feature])
        
        # Process numerical features
        for feature in self.feature_extractors["numerical_features"]:
            if feature in features:
                try:
                    processed[feature] = float(features[feature])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid numerical feature {feature}: {features[feature]}")
                    processed[feature] = 0.0
        
        # Process text features
        text_features = features.get("text_features", {})
        for feature in self.feature_extractors["text_features"]:
            if feature in text_features:
                processed[f"text_{feature}"] = str(text_features[feature])
        
        # Calculate derived features
        processed.update(await self._calculate_derived_features(processed))
        
        return processed
    
    async def _calculate_derived_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived features from base features"""
        derived = {}
        
        # Amount percentile (simplified calculation)
        amount = features.get("service_amount", 0.0)
        if amount < 100:
            derived["amount_percentile"] = "LOW"
        elif amount < 500:
            derived["amount_percentile"] = "MEDIUM"
        else:
            derived["amount_percentile"] = "HIGH"
        
        # Age group
        age = features.get("customer_age", 0)
        if age < 18:
            derived["age_group"] = "MINOR"
        elif age < 65:
            derived["age_group"] = "ADULT"
        else:
            derived["age_group"] = "SENIOR"
        
        # Claim frequency
        claims = features.get("historical_claims", 0)
        if claims == 0:
            derived["claim_frequency"] = "NONE"
        elif claims <= 2:
            derived["claim_frequency"] = "LOW"
        elif claims <= 5:
            derived["claim_frequency"] = "MEDIUM"
        else:
            derived["claim_frequency"] = "HIGH"
        
        # Complexity score (simplified)
        complexity = 0
        if features.get("attachment_count", 0) > 3:
            complexity += 1
        if amount > 1000:
            complexity += 1
        if "SURGERY" in features.get("service_code", ""):
            complexity += 2
        
        derived["complexity_score"] = min(complexity, 5)
        
        return derived
    
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
        Call local ML model (fallback implementation).
        
        Args:
            features: Processed features
            model_version: Model version to use
            
        Returns:
            Prediction result
        """
        # Simulate model inference delay
        await asyncio.sleep(0.1)
        
        # Rule-based fallback logic
        service_code = features.get("service_code", "UNKNOWN")
        amount = features.get("service_amount", 0.0)
        complexity = features.get("complexity_score", 0)
        
        # Determine request type based on service code
        if "CONSULTATION" in service_code:
            request_type = "MEDICAL_CONSULTATION"
            risk_prior = 0.1
        elif "EMERGENCY" in service_code:
            request_type = "EMERGENCY_CARE"
            risk_prior = 0.4
        elif "SURGERY" in service_code:
            request_type = "SURGERY"
            risk_prior = 0.6
        elif "DIAGNOSTIC" in service_code:
            request_type = "DIAGNOSTIC_TEST"
            risk_prior = 0.2
        else:
            request_type = "UNKNOWN"
            risk_prior = 0.5
        
        # Adjust risk based on amount and complexity
        if amount > 1000:
            risk_prior = min(risk_prior + 0.2, 1.0)
        if complexity > 3:
            risk_prior = min(risk_prior + 0.1, 1.0)
        
        # Generate probabilities
        probabilities = {
            request_type: 0.8,
            "OTHER": 0.2
        }
        
        # Generate candidate policies
        candidate_policies = [f"POL_{request_type[:3]}_{i:03d}" for i in range(1, 4)]
        
        return {
            "request_type": request_type,
            "candidate_policy_ids": candidate_policies,
            "risk_prior": risk_prior,
            "probabilities": probabilities,
            "top_features": ["service_code", "service_amount", "complexity_score"]
        }
    
    async def _process_prediction_result(
        self, 
        prediction: Dict[str, Any], 
        model_version: str, 
        case_id: str
    ) -> MLClassificationResponse:
        """
        Process raw prediction result into response format.
        
        Args:
            prediction: Raw prediction from model
            model_version: Model version used
            case_id: Case ID for logging
            
        Returns:
            Formatted classification response
        """
        request_type = prediction.get("request_type", "UNKNOWN")
        route = self.route_mappings.get(request_type, "MANUAL_REVIEW")
        
        response = MLClassificationResponse(
            request_type=request_type,
            candidate_policy_ids=prediction.get("candidate_policy_ids", []),
            route=route,
            risk_prior=prediction.get("risk_prior", 0.5),
            probabilities=prediction.get("probabilities", {}),
            top_features=prediction.get("top_features", []),
            model_version=model_version
        )
        
        logger.info(f"Classification completed for case {case_id}: {request_type} -> {route}")
        
        return response
    
    async def health_check(self) -> "MLServiceHealth":
        """Check service health"""
        from .base import MLServiceHealth
        
        start_time = datetime.utcnow()
        
        try:
            # Test with dummy features
            test_features = {
                "service_code": "TEST",
                "service_amount": 100.0,
                "customer_age": 30
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
            "classification-v2.1.0",
            "classification-v2.0.0",
            "classification-v1.9.0"
        ]


class MockMLClassificationService(MockMLService):
    """
    Mock implementation of ML Classification service for development and testing.
    
    Provides deterministic responses based on input patterns.
    """
    
    def __init__(self):
        super().__init__("classification", "mock-classification-1.0.0")
        self._setup_mock_responses()
    
    def _setup_mock_responses(self):
        """Setup predefined mock responses"""
        self.mock_patterns = {
            "CONSULTATION": {
                "request_type": "MEDICAL_CONSULTATION",
                "candidate_policy_ids": ["POL_MED_001", "POL_MED_002"],
                "route": "AUTO_PROCESS",
                "risk_prior": 0.15,
                "probabilities": {
                    "MEDICAL_CONSULTATION": 0.85,
                    "EMERGENCY_CARE": 0.10,
                    "SPECIALIST_REFERRAL": 0.05
                },
                "top_features": ["service_code", "provider_type", "service_amount"]
            },
            "EMERGENCY": {
                "request_type": "EMERGENCY_CARE",
                "candidate_policy_ids": ["POL_EMG_001"],
                "route": "PRIORITY_REVIEW",
                "risk_prior": 0.45,
                "probabilities": {
                    "EMERGENCY_CARE": 0.90,
                    "MEDICAL_CONSULTATION": 0.10
                },
                "top_features": ["service_code", "service_urgency", "service_amount"]
            },
            "SURGERY": {
                "request_type": "SURGERY",
                "candidate_policy_ids": ["POL_SUR_001", "POL_SUR_002"],
                "route": "MANUAL_REVIEW",
                "risk_prior": 0.65,
                "probabilities": {
                    "SURGERY": 0.95,
                    "SPECIALIST_REFERRAL": 0.05
                },
                "top_features": ["service_code", "service_amount", "complexity_score"]
            }
        }
    
    async def predict(self, request: MLClassificationRequest) -> MLClassificationResponse:
        """Mock prediction implementation"""
        await self._validate_request(request)
        
        # Simulate processing delay
        await asyncio.sleep(self.mock_delay_ms / 1000)
        
        # Check for specific mock response
        if hasattr(request, 'case_id') and request.case_id in self.mock_responses:
            return self.mock_responses[request.case_id]
        
        # Pattern-based response
        service_code = request.features.get("service_code", "UNKNOWN")
        
        for pattern, response_data in self.mock_patterns.items():
            if pattern in service_code.upper():
                return MLClassificationResponse(
                    **response_data,
                    model_version=self.default_model_version,
                    processing_time_ms=self.mock_delay_ms
                )
        
        # Default response
        return MLClassificationResponse(
            request_type="UNKNOWN",
            candidate_policy_ids=["POL_DEF_001"],
            route="MANUAL_REVIEW",
            risk_prior=0.5,
            probabilities={"UNKNOWN": 1.0},
            top_features=["service_code"],
            model_version=self.default_model_version,
            processing_time_ms=self.mock_delay_ms
        )
