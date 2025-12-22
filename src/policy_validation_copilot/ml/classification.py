"""
ML Classification Service Client (UC-OP-11).

This module implements the classification service client following the ML-CLASSIFY
contract from Anexo B. It provides case classification, policy routing, and risk
assessment capabilities.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .base import BaseMLServiceClient, MLServiceConfig, MockMLServiceClient
from ..models.ml import MLScoreRecord, FeatureVector

logger = logging.getLogger(__name__)


class ClassificationRequest(BaseModel):
    """Request model for ML-CLASSIFY service (Anexo B)."""
    
    case_id: str = Field(..., description="Unique case identifier")
    features: FeatureVector = Field(..., description="Feature vector for classification")
    model_version: Optional[str] = Field(None, description="Specific model version to use")
    
    @validator('case_id')
    def validate_case_id(cls, v):
        if not v or not v.strip():
            raise ValueError("case_id cannot be empty")
        return v.strip()


class ClassificationResponse(BaseModel):
    """Response model for ML-CLASSIFY service (Anexo B)."""
    
    request_type: str = Field(..., description="Classified request type")
    candidate_policy_ids: List[str] = Field(..., description="Candidate policy document IDs")
    route: str = Field(..., description="Recommended processing route")
    risk_prior: float = Field(..., ge=0.0, le=1.0, description="Prior risk assessment")
    probabilities: Dict[str, float] = Field(..., description="Class probabilities")
    top_features: List[str] = Field(..., description="Most important features")
    model_version: str = Field(..., description="Model version used")
    processing_time_ms: float = Field(..., ge=0.0, description="Processing time in milliseconds")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    
    @validator('probabilities')
    def validate_probabilities(cls, v):
        if not v:
            raise ValueError("probabilities cannot be empty")
        
        # Check that all probabilities are between 0 and 1
        for class_name, prob in v.items():
            if not 0.0 <= prob <= 1.0:
                raise ValueError(f"Probability for {class_name} must be between 0 and 1")
        
        # Check that probabilities sum to approximately 1
        total_prob = sum(v.values())
        if not 0.95 <= total_prob <= 1.05:  # Allow small floating point errors
            raise ValueError(f"Probabilities must sum to 1, got {total_prob}")
        
        return v
    
    @validator('route')
    def validate_route(cls, v):
        valid_routes = [
            "AUTO_APPROVE", "AUTO_DENY", "MANUAL_REVIEW", 
            "EXPERT_REVIEW", "ESCALATE", "ADDITIONAL_INFO"
        ]
        if v not in valid_routes:
            raise ValueError(f"route must be one of {valid_routes}")
        return v


class ClassificationServiceClient(BaseMLServiceClient):
    """Client for ML Classification Service (UC-OP-11)."""
    
    def __init__(self, config: MLServiceConfig):
        super().__init__(config)
        self.service_endpoint = "/classify"
        self.health_endpoint = "/health"
        self.model_info_endpoint = "/model/info"
    
    async def classify_case(
        self,
        case_id: str,
        features: FeatureVector,
        model_version: Optional[str] = None
    ) -> MLScoreRecord:
        """
        Classify a case and return ML score record.
        
        Args:
            case_id: Unique case identifier
            features: Feature vector for classification
            model_version: Specific model version to use
            
        Returns:
            MLScoreRecord with classification results
            
        Raises:
            MLServiceError: If classification fails
            MLServiceValidationError: If input validation fails
            MLModelVersionError: If model version is incompatible
        """
        logger.info(f"Classifying case {case_id} with {len(features)} features")
        
        # Prepare request
        request = ClassificationRequest(
            case_id=case_id,
            features=features,
            model_version=model_version or self.config.model_version
        )
        
        # Make request
        response = await self._make_request_with_retry(
            method="POST",
            endpoint=self.service_endpoint,
            request_data=request.dict(),
            response_model=ClassificationResponse
        )
        
        # Convert to MLScoreRecord
        ml_record = MLScoreRecord(
            case_id=case_id,
            model_type="CLASSIFICATION",
            model_version=response.model_version,
            request_type=response.request_type,
            candidate_policy_ids=response.candidate_policy_ids,
            route=response.route,
            risk_prior=response.risk_prior,
            probabilities=response.probabilities,
            top_features=response.top_features,
            processing_time_ms=response.processing_time_ms,
            confidence_score=response.confidence_score,
            features_used=features,
        )
        
        logger.info(
            f"Classification completed for case {case_id}: "
            f"type={response.request_type}, route={response.route}, "
            f"confidence={response.confidence_score:.3f}"
        )
        
        return ml_record
    
    async def batch_classify_cases(
        self,
        cases: List[Dict[str, Any]],
        model_version: Optional[str] = None
    ) -> List[MLScoreRecord]:
        """
        Classify multiple cases in batch.
        
        Args:
            cases: List of case data with case_id and features
            model_version: Specific model version to use
            
        Returns:
            List of MLScoreRecord results
        """
        logger.info(f"Batch classifying {len(cases)} cases")
        
        results = []
        for case_data in cases:
            try:
                result = await self.classify_case(
                    case_id=case_data["case_id"],
                    features=case_data["features"],
                    model_version=model_version
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error classifying case {case_data.get('case_id')}: {e}")
                # Continue with other cases
                continue
        
        logger.info(f"Batch classification completed: {len(results)}/{len(cases)} successful")
        return results
    
    async def get_feature_importance(
        self,
        request_type: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get feature importance scores from the model.
        
        Args:
            request_type: Specific request type to get importance for
            model_version: Specific model version
            
        Returns:
            Dictionary of feature names to importance scores
        """
        logger.info(f"Getting feature importance for request_type={request_type}")
        
        params = {}
        if request_type:
            params["request_type"] = request_type
        if model_version:
            params["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="GET",
                endpoint="/model/feature_importance",
                request_data=params,
                response_model=dict  # Simple dict response
            )
            
            return response.get("feature_importance", {})
            
        except Exception as e:
            logger.warning(f"Could not get feature importance: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check classification service health."""
        try:
            response = await self._make_request_with_retry(
                method="GET",
                endpoint=self.health_endpoint,
                request_data={},
                response_model=dict
            )
            return response
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get classification model information."""
        try:
            response = await self._make_request_with_retry(
                method="GET",
                endpoint=self.model_info_endpoint,
                request_data={},
                response_model=dict
            )
            return response
        except Exception as e:
            logger.error(f"Could not get model info: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def validate_features(self, features: FeatureVector) -> Dict[str, Any]:
        """
        Validate feature vector against model requirements.
        
        Args:
            features: Feature vector to validate
            
        Returns:
            Validation result with any issues found
        """
        try:
            response = await self._make_request_with_retry(
                method="POST",
                endpoint="/validate_features",
                request_data={"features": features},
                response_model=dict
            )
            return response
        except Exception as e:
            logger.warning(f"Feature validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "timestamp": datetime.utcnow().isoformat()
            }


class MockClassificationServiceClient(MockMLServiceClient):
    """Mock classification service client for testing."""
    
    def __init__(self, config: MLServiceConfig):
        # Default mock responses
        mock_responses = {
            "/classify": {
                "request_type": "REEMBOLSO_MEDICAMENTOS",
                "candidate_policy_ids": ["POL-001", "POL-002", "POL-003"],
                "route": "AUTO_APPROVE",
                "risk_prior": 0.15,
                "probabilities": {
                    "REEMBOLSO_MEDICAMENTOS": 0.85,
                    "REEMBOLSO_CONSULTAS": 0.10,
                    "AUTORIZACION_PROCEDIMIENTOS": 0.05
                },
                "top_features": [
                    "service_code",
                    "provider_type",
                    "amount_requested",
                    "customer_tier",
                    "historical_claims"
                ],
                "model_version": "classification-v2.1.0",
                "processing_time_ms": 45.2,
                "confidence_score": 0.85
            },
            "/health": {
                "status": "healthy",
                "service": "classification",
                "version": "2.1.0",
                "model_loaded": True,
                "last_prediction": datetime.utcnow().isoformat()
            },
            "/model/info": {
                "model_name": "policy_classification_v2",
                "model_version": "classification-v2.1.0",
                "model_type": "gradient_boosting",
                "training_date": "2024-01-15T10:30:00Z",
                "feature_count": 47,
                "class_count": 12,
                "performance_metrics": {
                    "accuracy": 0.94,
                    "precision": 0.92,
                    "recall": 0.95,
                    "f1_score": 0.93
                },
                "supported_routes": [
                    "AUTO_APPROVE", "AUTO_DENY", "MANUAL_REVIEW",
                    "EXPERT_REVIEW", "ESCALATE", "ADDITIONAL_INFO"
                ]
            },
            "/model/feature_importance": {
                "feature_importance": {
                    "service_code": 0.25,
                    "provider_type": 0.18,
                    "amount_requested": 0.15,
                    "customer_tier": 0.12,
                    "historical_claims": 0.10,
                    "diagnosis_code": 0.08,
                    "provider_network": 0.07,
                    "claim_frequency": 0.05
                }
            },
            "/validate_features": {
                "valid": True,
                "feature_count": 47,
                "missing_features": [],
                "invalid_features": [],
                "warnings": []
            }
        }
        
        super().__init__(config, mock_responses)
    
    async def classify_case(
        self,
        case_id: str,
        features: FeatureVector,
        model_version: Optional[str] = None
    ) -> MLScoreRecord:
        """Mock classification with realistic variations."""
        # Add some realistic variation to mock responses
        import random
        
        base_response = self.mock_responses["/classify"].copy()
        
        # Vary confidence and risk based on case characteristics
        if "amount_requested" in features:
            amount = features.get("amount_requested", 1000)
            if amount > 10000:
                base_response["confidence_score"] = max(0.3, base_response["confidence_score"] - 0.2)
                base_response["risk_prior"] = min(0.8, base_response["risk_prior"] + 0.3)
                base_response["route"] = "MANUAL_REVIEW"
        
        # Add some randomness
        base_response["confidence_score"] += random.uniform(-0.05, 0.05)
        base_response["confidence_score"] = max(0.0, min(1.0, base_response["confidence_score"]))
        
        # Simulate processing time variation
        base_response["processing_time_ms"] = random.uniform(30, 100)
        
        # Create response object
        response = ClassificationResponse(**base_response)
        
        # Convert to MLScoreRecord
        return MLScoreRecord(
            case_id=case_id,
            model_type="CLASSIFICATION",
            model_version=response.model_version,
            request_type=response.request_type,
            candidate_policy_ids=response.candidate_policy_ids,
            route=response.route,
            risk_prior=response.risk_prior,
            probabilities=response.probabilities,
            top_features=response.top_features,
            processing_time_ms=response.processing_time_ms,
            confidence_score=response.confidence_score,
            features_used=features,
        )


def create_classification_client(
    base_url: str,
    api_key: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout: float = 30.0,
    use_mock: bool = False
) -> BaseMLServiceClient:
    """
    Create a classification service client.
    
    Args:
        base_url: Base URL of the classification service
        api_key: API key for authentication
        model_version: Specific model version to use
        timeout: Request timeout in seconds
        use_mock: Whether to use mock client for testing
        
    Returns:
        Classification service client instance
    """
    config = MLServiceConfig(
        service_name="classification",
        base_url=base_url,
        api_key=api_key,
        model_version=model_version,
        timeout=timeout
    )
    
    if use_mock:
        return MockClassificationServiceClient(config)
    else:
        return ClassificationServiceClient(config)
