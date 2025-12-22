"""
ML Classification Service Client.

This module implements the classification service client based on Anexo B API contracts:

ML-CLASSIFY API Contract:
Request: {case_id, features, model_version?}
Response: {request_type, candidate_policy_ids, route, risk_prior, probabilities, top_features, model_version}

Features:
- Case type classification and routing decisions
- Policy candidate identification
- Risk assessment and scoring
- Feature importance analysis
- Model versioning and drift monitoring
- Fallback rules for service degradation
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseMLServiceClient, MLServiceConfig, MLServiceError
from ...models.ml import (
    ClassificationRequest, ClassificationResponse, ClassificationFeatures,
    MLServiceType, RequestType, RouteDecision, MLScoreRecord
)

logger = logging.getLogger(__name__)


class ClassificationServiceClient(BaseMLServiceClient[ClassificationResponse]):
    """
    ML Classification Service Client.
    
    Implements the ML-CLASSIFY service based on Anexo B specifications
    for case classification, routing decisions, and policy candidate identification.
    """
    
    def __init__(self, config: MLServiceConfig):
        """
        Initialize classification service client.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.service_type = MLServiceType.CLASSIFICATION
        
        # Classification-specific configuration
        self.default_confidence_threshold = 0.7
        self.max_policy_candidates = 10
        self.feature_importance_threshold = 0.1
        
        logger.info("Initialized Classification Service Client")

    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        return MLServiceType.CLASSIFICATION

    async def predict(
        self, 
        request: ClassificationRequest, 
        **kwargs
    ) -> ClassificationResponse:
        """
        Make classification prediction request.
        
        Args:
            request: Classification request
            **kwargs: Additional arguments
            
        Returns:
            Classification response
            
        Raises:
            MLServiceError: If classification fails
        """
        try:
            # Prepare request data according to Anexo B
            request_data = {
                "case_id": str(request.case_id),
                "features": request.features.dict(),
                "model_version": request.model_version
            }
            
            # Remove None values
            request_data = {k: v for k, v in request_data.items() if v is not None}
            
            # Make API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/classify",
                data=request_data,
                model_version=request.model_version
            )
            
            # Parse response according to Anexo B contract
            classification_response = ClassificationResponse(
                case_id=request.case_id,
                request_type=RequestType(response_data["request_type"]),
                candidate_policy_ids=response_data["candidate_policy_ids"],
                route=RouteDecision(response_data["route"]),
                risk_prior=response_data["risk_prior"],
                probabilities=response_data["probabilities"],
                top_features=response_data["top_features"],
                model_version=response_data["model_version"],
                confidence_score=response_data.get("confidence_score", 0.0),
                processing_time_ms=response_data.get("processing_time_ms", 0.0),
                timestamp=datetime.utcnow()
            )
            
            # Check for drift if enabled
            if self.config.drift_check_interval > 0:
                await self._check_drift_if_needed(request.features.dict())
            
            logger.debug(
                f"Classification completed for case {request.case_id}: "
                f"type={classification_response.request_type}, "
                f"route={classification_response.route}, "
                f"confidence={classification_response.confidence_score:.3f}"
            )
            
            return classification_response
            
        except Exception as e:
            logger.error(f"Classification failed for case {request.case_id}: {e}")
            
            # Return fallback classification if service is degraded
            if self.is_degraded():
                return await self._fallback_classification(request)
            
            raise MLServiceError(f"Classification failed: {e}")

    async def classify_batch(
        self, 
        requests: List[ClassificationRequest],
        **kwargs
    ) -> List[ClassificationResponse]:
        """
        Perform batch classification.
        
        Args:
            requests: List of classification requests
            **kwargs: Additional arguments
            
        Returns:
            List of classification responses
        """
        try:
            # Prepare batch request data
            batch_data = {
                "requests": [
                    {
                        "case_id": str(req.case_id),
                        "features": req.features.dict(),
                        "model_version": req.model_version
                    }
                    for req in requests
                ]
            }
            
            # Make batch API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/classify/batch",
                data=batch_data
            )
            
            # Parse batch response
            responses = []
            for i, result in enumerate(response_data["results"]):
                if result.get("error"):
                    # Handle individual request errors
                    logger.error(f"Batch classification error for request {i}: {result['error']}")
                    if self.is_degraded():
                        responses.append(await self._fallback_classification(requests[i]))
                    else:
                        responses.append(None)
                else:
                    responses.append(ClassificationResponse(
                        case_id=requests[i].case_id,
                        request_type=RequestType(result["request_type"]),
                        candidate_policy_ids=result["candidate_policy_ids"],
                        route=RouteDecision(result["route"]),
                        risk_prior=result["risk_prior"],
                        probabilities=result["probabilities"],
                        top_features=result["top_features"],
                        model_version=result["model_version"],
                        confidence_score=result.get("confidence_score", 0.0),
                        processing_time_ms=result.get("processing_time_ms", 0.0),
                        timestamp=datetime.utcnow()
                    ))
            
            logger.info(f"Batch classification completed for {len(requests)} requests")
            return responses
            
        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            
            # Fallback to individual requests
            if self.is_degraded():
                return [await self._fallback_classification(req) for req in requests]
            
            raise MLServiceError(f"Batch classification failed: {e}")

    async def get_feature_importance(
        self, 
        case_id: UUID,
        features: ClassificationFeatures,
        model_version: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get feature importance for classification decision.
        
        Args:
            case_id: Case identifier
            features: Feature vector
            model_version: Specific model version
            
        Returns:
            Feature importance scores
        """
        try:
            request_data = {
                "case_id": str(case_id),
                "features": features.dict(),
                "model_version": model_version
            }
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/classify/feature_importance",
                data=request_data,
                model_version=model_version
            )
            
            return response_data["feature_importance"]
            
        except Exception as e:
            logger.error(f"Feature importance request failed for case {case_id}: {e}")
            return {}

    async def explain_classification(
        self,
        case_id: UUID,
        classification_response: ClassificationResponse
    ) -> Dict[str, Any]:
        """
        Get detailed explanation for classification decision.
        
        Args:
            case_id: Case identifier
            classification_response: Classification result to explain
            
        Returns:
            Detailed explanation
        """
        try:
            request_data = {
                "case_id": str(case_id),
                "classification": classification_response.dict()
            }
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/classify/explain",
                data=request_data
            )
            
            return {
                "decision_path": response_data.get("decision_path", []),
                "rule_activations": response_data.get("rule_activations", {}),
                "confidence_factors": response_data.get("confidence_factors", {}),
                "alternative_routes": response_data.get("alternative_routes", []),
                "risk_factors": response_data.get("risk_factors", []),
                "policy_matching_scores": response_data.get("policy_matching_scores", {})
            }
            
        except Exception as e:
            logger.error(f"Classification explanation failed for case {case_id}: {e}")
            return {"error": str(e)}

    async def validate_features(
        self, 
        features: ClassificationFeatures
    ) -> Dict[str, Any]:
        """
        Validate feature vector for classification.
        
        Args:
            features: Feature vector to validate
            
        Returns:
            Validation results
        """
        try:
            request_data = {"features": features.dict()}
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/classify/validate_features",
                data=request_data
            )
            
            return {
                "valid": response_data["valid"],
                "missing_features": response_data.get("missing_features", []),
                "invalid_features": response_data.get("invalid_features", []),
                "feature_ranges": response_data.get("feature_ranges", {}),
                "recommendations": response_data.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Feature validation failed: {e}")
            return {"valid": False, "error": str(e)}

    async def get_model_performance(
        self, 
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get model performance metrics.
        
        Args:
            model_version: Specific model version
            
        Returns:
            Performance metrics
        """
        try:
            params = {}
            if model_version:
                params["version"] = model_version
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/classify/performance",
                params=params
            )
            
            return {
                "accuracy": response_data.get("accuracy", 0.0),
                "precision": response_data.get("precision", {}),
                "recall": response_data.get("recall", {}),
                "f1_score": response_data.get("f1_score", {}),
                "confusion_matrix": response_data.get("confusion_matrix", {}),
                "roc_auc": response_data.get("roc_auc", {}),
                "feature_importance": response_data.get("feature_importance", {}),
                "model_version": response_data.get("model_version", "unknown"),
                "evaluation_date": response_data.get("evaluation_date")
            }
            
        except Exception as e:
            logger.error(f"Model performance request failed: {e}")
            return {"error": str(e)}

    async def _fallback_classification(
        self, 
        request: ClassificationRequest
    ) -> ClassificationResponse:
        """
        Provide fallback classification when service is degraded.
        
        Args:
            request: Original classification request
            
        Returns:
            Fallback classification response
        """
        logger.warning(f"Using fallback classification for case {request.case_id}")
        
        # Simple rule-based fallback logic
        features = request.features
        
        # Determine request type based on simple rules
        request_type = RequestType.STANDARD
        if hasattr(features, 'urgency') and features.urgency == "HIGH":
            request_type = RequestType.URGENT
        elif hasattr(features, 'amount') and getattr(features, 'amount', 0) > 100000:
            request_type = RequestType.HIGH_VALUE
        
        # Determine route based on request type
        route = RouteDecision.MANUAL_REVIEW
        if request_type == RequestType.STANDARD:
            route = RouteDecision.AUTO_PROCESS
        elif request_type == RequestType.URGENT:
            route = RouteDecision.PRIORITY_QUEUE
        
        # Default risk assessment
        risk_prior = 0.5  # Medium risk
        if request_type == RequestType.HIGH_VALUE:
            risk_prior = 0.8  # High risk
        
        return ClassificationResponse(
            case_id=request.case_id,
            request_type=request_type,
            candidate_policy_ids=["FALLBACK_POLICY"],
            route=route,
            risk_prior=risk_prior,
            probabilities={request_type.value: 0.6},
            top_features={"fallback": 1.0},
            model_version="fallback-v1.0",
            confidence_score=0.3,  # Low confidence for fallback
            processing_time_ms=1.0,
            timestamp=datetime.utcnow(),
            fallback_used=True
        )

    async def _check_drift_if_needed(self, features: Dict[str, Any]) -> None:
        """Check for model drift if interval has passed."""
        if not hasattr(self, '_last_drift_check'):
            self._last_drift_check = datetime.utcnow()
        
        time_since_check = (datetime.utcnow() - self._last_drift_check).total_seconds()
        
        if time_since_check >= self.config.drift_check_interval:
            try:
                drift_metrics = await self.check_drift(features)
                self._last_drift_check = datetime.utcnow()
                
                if drift_metrics.drift_detected:
                    logger.warning(
                        f"Model drift detected in classification service: "
                        f"score={drift_metrics.drift_score:.3f}"
                    )
            except Exception as e:
                logger.error(f"Drift check failed: {e}")


class MockClassificationServiceClient(BaseMLServiceClient[ClassificationResponse]):
    """
    Mock Classification Service Client for testing.
    
    Provides deterministic responses for testing without requiring
    actual ML service infrastructure.
    """
    
    def __init__(self, config: Optional[MLServiceConfig] = None):
        """Initialize mock classification service client."""
        if config is None:
            config = MLServiceConfig(
                service_name="mock-classification",
                base_url="http://localhost:8000",
                request_timeout=1.0,
                max_retries=0
            )
        
        super().__init__(config)
        self.service_type = MLServiceType.CLASSIFICATION
        
        # Mock data
        self.mock_responses = {
            "standard": ClassificationResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000001"),
                request_type=RequestType.STANDARD,
                candidate_policy_ids=["POL-001", "POL-002"],
                route=RouteDecision.AUTO_PROCESS,
                risk_prior=0.3,
                probabilities={"STANDARD": 0.8, "URGENT": 0.2},
                top_features={"amount": 0.6, "customer_tier": 0.4},
                model_version="mock-v1.0",
                confidence_score=0.85,
                processing_time_ms=50.0,
                timestamp=datetime.utcnow()
            ),
            "urgent": ClassificationResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000002"),
                request_type=RequestType.URGENT,
                candidate_policy_ids=["POL-003", "POL-004"],
                route=RouteDecision.PRIORITY_QUEUE,
                risk_prior=0.7,
                probabilities={"URGENT": 0.9, "STANDARD": 0.1},
                top_features={"urgency": 0.9, "complexity": 0.5},
                model_version="mock-v1.0",
                confidence_score=0.92,
                processing_time_ms=45.0,
                timestamp=datetime.utcnow()
            ),
            "high_value": ClassificationResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000003"),
                request_type=RequestType.HIGH_VALUE,
                candidate_policy_ids=["POL-005"],
                route=RouteDecision.MANUAL_REVIEW,
                risk_prior=0.8,
                probabilities={"HIGH_VALUE": 0.95, "STANDARD": 0.05},
                top_features={"amount": 0.95, "risk_score": 0.8},
                model_version="mock-v1.0",
                confidence_score=0.96,
                processing_time_ms=60.0,
                timestamp=datetime.utcnow()
            )
        }

    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        return MLServiceType.CLASSIFICATION

    async def start(self):
        """Start mock service (no-op)."""
        logger.info("Started mock classification service")

    async def stop(self):
        """Stop mock service (no-op)."""
        logger.info("Stopped mock classification service")

    async def predict(
        self, 
        request: ClassificationRequest, 
        **kwargs
    ) -> ClassificationResponse:
        """
        Mock classification prediction.
        
        Args:
            request: Classification request
            **kwargs: Additional arguments
            
        Returns:
            Mock classification response
        """
        # Simulate processing delay
        import asyncio
        await asyncio.sleep(0.05)
        
        # Determine mock response based on features
        features = request.features
        
        if hasattr(features, 'urgency') and getattr(features, 'urgency') == "HIGH":
            response = self.mock_responses["urgent"].copy()
        elif hasattr(features, 'amount') and getattr(features, 'amount', 0) > 100000:
            response = self.mock_responses["high_value"].copy()
        else:
            response = self.mock_responses["standard"].copy()
        
        # Update with actual case ID
        response.case_id = request.case_id
        response.timestamp = datetime.utcnow()
        
        logger.debug(f"Mock classification for case {request.case_id}: {response.request_type}")
        return response

    async def health_check(self):
        """Mock health check."""
        from ...models.ml import MLServiceHealth, ModelStatus
        
        return MLServiceHealth(
            service_name=self.config.service_name,
            status=ModelStatus.HEALTHY,
            response_time_ms=1.0,
            last_check=datetime.utcnow(),
            version="mock-v1.0",
            models_available=["classification-mock-v1.0"],
            error_message=None
        )

    async def get_model_info(self, model_version: Optional[str] = None):
        """Mock model info."""
        from ...models.ml import MLModelInfo, ModelStatus
        
        return MLModelInfo(
            model_id="classification-mock",
            model_version="mock-v1.0",
            model_type=MLServiceType.CLASSIFICATION,
            training_date=datetime(2024, 1, 1),
            deployment_date=datetime(2024, 1, 15),
            performance_metrics={"accuracy": 0.95, "f1_score": 0.93},
            feature_schema={"amount": "float", "urgency": "string"},
            status=ModelStatus.HEALTHY
        )


__all__ = [
    "ClassificationServiceClient",
    "MockClassificationServiceClient"
]
