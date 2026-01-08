"""
ML Anomaly Detection Service Client (UC-OP-12).

This module implements the anomaly detection service client following the ML-ANOMALY
contract from Anexo B. It provides anomaly detection, fraud scoring, and risk
assessment capabilities.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .base import BaseMLServiceClient, MLServiceConfig, MockMLServiceClient
from ..models.ml import AnomalyRecord, FeatureVector

logger = logging.getLogger(__name__)


class AnomalyRequest(BaseModel):
    """Request model for ML-ANOMALY service (Anexo B)."""
    
    case_id: str = Field(..., description="Unique case identifier")
    features: FeatureVector = Field(..., description="Feature vector for anomaly detection")
    aggregates: Dict[str, float] = Field(..., description="Aggregate statistics for comparison")
    model_version: Optional[str] = Field(None, description="Specific model version to use")
    
    @validator('case_id')
    def validate_case_id(cls, v):
        if not v or not v.strip():
            raise ValueError("case_id cannot be empty")
        return v.strip()
    
    @validator('aggregates')
    def validate_aggregates(cls, v):
        if not v:
            raise ValueError("aggregates cannot be empty")
        
        # Validate that all aggregate values are numeric
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Aggregate {key} must be numeric, got {type(value)}")
        
        return v


class AnomalyResponse(BaseModel):
    """Response model for ML-ANOMALY service (Anexo B)."""
    
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Anomaly score (0=normal, 1=highly anomalous)")
    anomaly_flags: List[str] = Field(..., description="Specific anomaly flags detected")
    recommended_action: str = Field(..., description="Recommended action based on anomaly level")
    model_version: str = Field(..., description="Model version used")
    processing_time_ms: float = Field(..., ge=0.0, description="Processing time in milliseconds")
    feature_contributions: Dict[str, float] = Field(..., description="Feature contributions to anomaly score")
    risk_factors: List[str] = Field(..., description="Identified risk factors")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in anomaly detection")
    
    @validator('recommended_action')
    def validate_recommended_action(cls, v):
        valid_actions = [
            "PROCEED", "MANUAL_REVIEW", "EXPERT_REVIEW", 
            "ESCALATE", "BLOCK", "ADDITIONAL_VERIFICATION"
        ]
        if v not in valid_actions:
            raise ValueError(f"recommended_action must be one of {valid_actions}")
        return v
    
    @validator('feature_contributions')
    def validate_feature_contributions(cls, v):
        # Validate that all contributions are between -1 and 1
        for feature, contribution in v.items():
            if not -1.0 <= contribution <= 1.0:
                raise ValueError(f"Feature contribution for {feature} must be between -1 and 1")
        return v


class AnomalyServiceClient(BaseMLServiceClient):
    """Client for ML Anomaly Detection Service (UC-OP-12)."""
    
    def __init__(self, config: MLServiceConfig):
        super().__init__(config)
        self.service_endpoint = "/detect_anomaly"
        self.health_endpoint = "/health"
        self.model_info_endpoint = "/model/info"
    
    async def detect_anomaly(
        self,
        case_id: str,
        features: FeatureVector,
        aggregates: Dict[str, float],
        model_version: Optional[str] = None
    ) -> AnomalyRecord:
        """
        Detect anomalies in a case and return anomaly record.
        
        Args:
            case_id: Unique case identifier
            features: Feature vector for anomaly detection
            aggregates: Aggregate statistics for comparison
            model_version: Specific model version to use
            
        Returns:
            AnomalyRecord with detection results
            
        Raises:
            MLServiceError: If anomaly detection fails
            MLServiceValidationError: If input validation fails
            MLModelVersionError: If model version is incompatible
        """
        logger.info(f"Detecting anomalies for case {case_id} with {len(features)} features")
        
        # Prepare request
        request = AnomalyRequest(
            case_id=case_id,
            features=features,
            aggregates=aggregates,
            model_version=model_version or self.config.model_version
        )
        
        # Make request
        response = await self._make_request_with_retry(
            method="POST",
            endpoint=self.service_endpoint,
            request_data=request.dict(),
            response_model=AnomalyResponse
        )
        
        # Convert to AnomalyRecord
        anomaly_record = AnomalyRecord(
            case_id=case_id,
            model_type="ANOMALY_DETECTION",
            model_version=response.model_version,
            anomaly_score=response.anomaly_score,
            anomaly_flags=response.anomaly_flags,
            recommended_action=response.recommended_action,
            processing_time_ms=response.processing_time_ms,
            feature_contributions=response.feature_contributions,
            risk_factors=response.risk_factors,
            confidence_score=response.confidence_score,
            features_used=features,
            aggregates_used=aggregates,
        )
        
        logger.info(
            f"Anomaly detection completed for case {case_id}: "
            f"score={response.anomaly_score:.3f}, action={response.recommended_action}, "
            f"flags={len(response.anomaly_flags)}"
        )
        
        return anomaly_record
    
    async def batch_detect_anomalies(
        self,
        cases: List[Dict[str, Any]],
        model_version: Optional[str] = None
    ) -> List[AnomalyRecord]:
        """
        Detect anomalies in multiple cases in batch.
        
        Args:
            cases: List of case data with case_id, features, and aggregates
            model_version: Specific model version to use
            
        Returns:
            List of AnomalyRecord results
        """
        logger.info(f"Batch detecting anomalies for {len(cases)} cases")
        
        results = []
        for case_data in cases:
            try:
                result = await self.detect_anomaly(
                    case_id=case_data["case_id"],
                    features=case_data["features"],
                    aggregates=case_data["aggregates"],
                    model_version=model_version
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error detecting anomalies for case {case_data.get('case_id')}: {e}")
                # Continue with other cases
                continue
        
        logger.info(f"Batch anomaly detection completed: {len(results)}/{len(cases)} successful")
        return results
    
    async def get_anomaly_thresholds(
        self,
        model_version: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get anomaly detection thresholds from the model.
        
        Args:
            model_version: Specific model version
            
        Returns:
            Dictionary of threshold names to values
        """
        logger.info("Getting anomaly detection thresholds")
        
        params = {}
        if model_version:
            params["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="GET",
                endpoint="/model/thresholds",
                request_data=params,
                response_model=dict
            )
            
            return response.get("thresholds", {})
            
        except Exception as e:
            logger.warning(f"Could not get anomaly thresholds: {e}")
            return {
                "low_anomaly": 0.3,
                "medium_anomaly": 0.6,
                "high_anomaly": 0.8,
                "critical_anomaly": 0.9
            }
    
    async def explain_anomaly(
        self,
        case_id: str,
        features: FeatureVector,
        aggregates: Dict[str, float],
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed explanation for anomaly detection result.
        
        Args:
            case_id: Case identifier
            features: Feature vector
            aggregates: Aggregate statistics
            model_version: Specific model version
            
        Returns:
            Detailed explanation of anomaly detection
        """
        logger.info(f"Getting anomaly explanation for case {case_id}")
        
        request_data = {
            "case_id": case_id,
            "features": features,
            "aggregates": aggregates
        }
        if model_version:
            request_data["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="POST",
                endpoint="/explain",
                request_data=request_data,
                response_model=dict
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"Could not get anomaly explanation: {e}")
            return {
                "explanation": "Explanation not available",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check anomaly detection service health."""
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
        """Get anomaly detection model information."""
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
    
    async def update_model_thresholds(
        self,
        thresholds: Dict[str, float],
        model_version: Optional[str] = None
    ) -> bool:
        """
        Update anomaly detection thresholds.
        
        Args:
            thresholds: New threshold values
            model_version: Specific model version
            
        Returns:
            True if update successful
        """
        logger.info("Updating anomaly detection thresholds")
        
        request_data = {"thresholds": thresholds}
        if model_version:
            request_data["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="POST",
                endpoint="/model/update_thresholds",
                request_data=request_data,
                response_model=dict
            )
            
            return response.get("success", False)
            
        except Exception as e:
            logger.error(f"Could not update thresholds: {e}")
            return False


class MockAnomalyServiceClient(MockMLServiceClient):
    """Mock anomaly detection service client for testing."""
    
    def __init__(self, config: MLServiceConfig):
        # Default mock responses
        mock_responses = {
            "/detect_anomaly": {
                "anomaly_score": 0.25,
                "anomaly_flags": ["UNUSUAL_AMOUNT", "OFF_HOURS_SUBMISSION"],
                "recommended_action": "MANUAL_REVIEW",
                "model_version": "anomaly-v1.3.0",
                "processing_time_ms": 78.5,
                "feature_contributions": {
                    "amount_requested": 0.45,
                    "submission_time": 0.32,
                    "provider_history": -0.15,
                    "customer_profile": 0.08,
                    "geographic_location": 0.12
                },
                "risk_factors": [
                    "Amount significantly higher than historical average",
                    "Submission outside normal business hours",
                    "New provider with limited history"
                ],
                "confidence_score": 0.78
            },
            "/health": {
                "status": "healthy",
                "service": "anomaly_detection",
                "version": "1.3.0",
                "model_loaded": True,
                "last_detection": datetime.utcnow().isoformat(),
                "detection_rate": 0.15
            },
            "/model/info": {
                "model_name": "isolation_forest_v1",
                "model_version": "anomaly-v1.3.0",
                "model_type": "isolation_forest",
                "training_date": "2024-01-20T14:30:00Z",
                "feature_count": 35,
                "contamination_rate": 0.1,
                "performance_metrics": {
                    "precision": 0.87,
                    "recall": 0.82,
                    "f1_score": 0.84,
                    "auc_roc": 0.91
                },
                "supported_actions": [
                    "PROCEED", "MANUAL_REVIEW", "EXPERT_REVIEW",
                    "ESCALATE", "BLOCK", "ADDITIONAL_VERIFICATION"
                ]
            },
            "/model/thresholds": {
                "thresholds": {
                    "low_anomaly": 0.3,
                    "medium_anomaly": 0.6,
                    "high_anomaly": 0.8,
                    "critical_anomaly": 0.9
                }
            },
            "/explain": {
                "explanation": "Case shows unusual patterns in amount and timing",
                "top_anomalous_features": [
                    "amount_requested",
                    "submission_time",
                    "provider_history"
                ],
                "normal_ranges": {
                    "amount_requested": {"min": 100, "max": 5000, "current": 15000},
                    "submission_time": {"normal_hours": "08:00-18:00", "current": "23:45"}
                },
                "similar_cases": {
                    "count": 3,
                    "outcomes": ["DENIED", "MANUAL_APPROVED", "DENIED"]
                }
            },
            "/model/update_thresholds": {
                "success": True,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        super().__init__(config, mock_responses)
    
    async def detect_anomaly(
        self,
        case_id: str,
        features: FeatureVector,
        aggregates: Dict[str, float],
        model_version: Optional[str] = None
    ) -> AnomalyRecord:
        """Mock anomaly detection with realistic variations."""
        import random
        
        base_response = self.mock_responses["/detect_anomaly"].copy()
        
        # Vary anomaly score based on features
        if "amount_requested" in features:
            amount = features.get("amount_requested", 1000)
            if amount > 10000:
                base_response["anomaly_score"] = min(0.9, base_response["anomaly_score"] + 0.3)
                base_response["recommended_action"] = "EXPERT_REVIEW"
                base_response["anomaly_flags"].append("HIGH_VALUE_CLAIM")
        
        if "submission_hour" in features:
            hour = features.get("submission_hour", 12)
            if hour < 6 or hour > 22:
                base_response["anomaly_score"] = min(0.9, base_response["anomaly_score"] + 0.2)
                if "OFF_HOURS_SUBMISSION" not in base_response["anomaly_flags"]:
                    base_response["anomaly_flags"].append("OFF_HOURS_SUBMISSION")
        
        # Add some randomness
        base_response["anomaly_score"] += random.uniform(-0.1, 0.1)
        base_response["anomaly_score"] = max(0.0, min(1.0, base_response["anomaly_score"]))
        
        # Adjust confidence based on anomaly score
        if base_response["anomaly_score"] > 0.7:
            base_response["confidence_score"] = min(0.95, base_response["confidence_score"] + 0.1)
        
        # Simulate processing time variation
        base_response["processing_time_ms"] = random.uniform(50, 150)
        
        # Create response object
        response = AnomalyResponse(**base_response)
        
        # Convert to AnomalyRecord
        return AnomalyRecord(
            case_id=case_id,
            model_type="ANOMALY_DETECTION",
            model_version=response.model_version,
            anomaly_score=response.anomaly_score,
            anomaly_flags=response.anomaly_flags,
            recommended_action=response.recommended_action,
            processing_time_ms=response.processing_time_ms,
            feature_contributions=response.feature_contributions,
            risk_factors=response.risk_factors,
            confidence_score=response.confidence_score,
            features_used=features,
            aggregates_used=aggregates,
        )


def create_anomaly_client(
    base_url: str,
    api_key: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout: float = 30.0,
    use_mock: bool = False
) -> BaseMLServiceClient:
    """
    Create an anomaly detection service client.
    
    Args:
        base_url: Base URL of the anomaly detection service
        api_key: API key for authentication
        model_version: Specific model version to use
        timeout: Request timeout in seconds
        use_mock: Whether to use mock client for testing
        
    Returns:
        Anomaly detection service client instance
    """
    config = MLServiceConfig(
        service_name="anomaly_detection",
        base_url=base_url,
        api_key=api_key,
        model_version=model_version,
        timeout=timeout
    )
    
    if use_mock:
        return MockAnomalyServiceClient(config)
    else:
        return AnomalyServiceClient(config)
