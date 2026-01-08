"""
ML ETA Prediction Service Client (UC-OP-13).

This module implements the ETA prediction service client following the ML-ETA
contract from Anexo B. It provides processing time estimation and SLA
management capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .base import BaseMLServiceClient, MLServiceConfig, MockMLServiceClient
from ..models.ml import ETARecord, FeatureVector

logger = logging.getLogger(__name__)


class ETARequest(BaseModel):
    """Request model for ML-ETA service (Anexo B)."""
    
    case_id: str = Field(..., description="Unique case identifier")
    features: FeatureVector = Field(..., description="Feature vector for ETA prediction")
    model_version: Optional[str] = Field(None, description="Specific model version to use")
    
    @validator('case_id')
    def validate_case_id(cls, v):
        if not v or not v.strip():
            raise ValueError("case_id cannot be empty")
        return v.strip()


class ETAResponse(BaseModel):
    """Response model for ML-ETA service (Anexo B)."""
    
    eta_minutes: float = Field(..., ge=0.0, description="Estimated time to completion in minutes")
    p50: float = Field(..., ge=0.0, description="50th percentile estimate (median)")
    p90: Optional[float] = Field(None, ge=0.0, description="90th percentile estimate")
    model_version: str = Field(..., description="Model version used")
    processing_time_ms: float = Field(..., ge=0.0, description="Processing time in milliseconds")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in ETA prediction")
    feature_importance: Dict[str, float] = Field(..., description="Feature importance for this prediction")
    similar_cases_count: int = Field(..., ge=0, description="Number of similar cases used for prediction")
    
    @validator('p90')
    def validate_p90_greater_than_p50(cls, v, values):
        if v is not None and 'p50' in values and v < values['p50']:
            raise ValueError("p90 must be greater than or equal to p50")
        return v


class ETAServiceClient(BaseMLServiceClient):
    """Client for ML ETA Prediction Service (UC-OP-13)."""
    
    def __init__(self, config: MLServiceConfig):
        super().__init__(config)
        self.service_endpoint = "/predict_eta"
        self.health_endpoint = "/health"
        self.model_info_endpoint = "/model/info"
    
    async def predict_eta(
        self,
        case_id: str,
        features: FeatureVector,
        model_version: Optional[str] = None
    ) -> ETARecord:
        """
        Predict ETA for a case and return ETA record.
        
        Args:
            case_id: Unique case identifier
            features: Feature vector for ETA prediction
            model_version: Specific model version to use
            
        Returns:
            ETARecord with prediction results
            
        Raises:
            MLServiceError: If ETA prediction fails
            MLServiceValidationError: If input validation fails
            MLModelVersionError: If model version is incompatible
        """
        logger.info(f"Predicting ETA for case {case_id} with {len(features)} features")
        
        # Prepare request
        request = ETARequest(
            case_id=case_id,
            features=features,
            model_version=model_version or self.config.model_version
        )
        
        # Make request
        response = await self._make_request_with_retry(
            method="POST",
            endpoint=self.service_endpoint,
            request_data=request.dict(),
            response_model=ETAResponse
        )
        
        # Convert to ETARecord
        eta_record = ETARecord(
            case_id=case_id,
            model_type="ETA_PREDICTION",
            model_version=response.model_version,
            eta_minutes=response.eta_minutes,
            p50=response.p50,
            p90=response.p90,
            processing_time_ms=response.processing_time_ms,
            confidence_score=response.confidence_score,
            feature_importance=response.feature_importance,
            similar_cases_count=response.similar_cases_count,
            features_used=features,
        )
        
        logger.info(
            f"ETA prediction completed for case {case_id}: "
            f"eta={response.eta_minutes:.1f}min, p50={response.p50:.1f}min, "
            f"confidence={response.confidence_score:.3f}"
        )
        
        return eta_record
    
    async def batch_predict_eta(
        self,
        cases: List[Dict[str, Any]],
        model_version: Optional[str] = None
    ) -> List[ETARecord]:
        """
        Predict ETA for multiple cases in batch.
        
        Args:
            cases: List of case data with case_id and features
            model_version: Specific model version to use
            
        Returns:
            List of ETARecord results
        """
        logger.info(f"Batch predicting ETA for {len(cases)} cases")
        
        results = []
        for case_data in cases:
            try:
                result = await self.predict_eta(
                    case_id=case_data["case_id"],
                    features=case_data["features"],
                    model_version=model_version
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error predicting ETA for case {case_data.get('case_id')}: {e}")
                # Continue with other cases
                continue
        
        logger.info(f"Batch ETA prediction completed: {len(results)}/{len(cases)} successful")
        return results
    
    async def get_sla_compliance_prediction(
        self,
        case_id: str,
        features: FeatureVector,
        sla_target_minutes: float,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict SLA compliance probability for a case.
        
        Args:
            case_id: Case identifier
            features: Feature vector
            sla_target_minutes: SLA target in minutes
            model_version: Specific model version
            
        Returns:
            SLA compliance prediction with probability
        """
        logger.info(f"Predicting SLA compliance for case {case_id} (target: {sla_target_minutes}min)")
        
        request_data = {
            "case_id": case_id,
            "features": features,
            "sla_target_minutes": sla_target_minutes
        }
        if model_version:
            request_data["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="POST",
                endpoint="/predict_sla_compliance",
                request_data=request_data,
                response_model=dict
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"Could not get SLA compliance prediction: {e}")
            
            # Fallback: use basic ETA prediction
            eta_record = await self.predict_eta(case_id, features, model_version)
            compliance_probability = 1.0 if eta_record.eta_minutes <= sla_target_minutes else 0.0
            
            return {
                "case_id": case_id,
                "sla_target_minutes": sla_target_minutes,
                "predicted_eta_minutes": eta_record.eta_minutes,
                "compliance_probability": compliance_probability,
                "risk_level": "LOW" if compliance_probability > 0.8 else "HIGH",
                "fallback_prediction": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_processing_bottlenecks(
        self,
        features: Optional[FeatureVector] = None,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get information about processing bottlenecks.
        
        Args:
            features: Optional feature vector for context
            model_version: Specific model version
            
        Returns:
            Information about current processing bottlenecks
        """
        logger.info("Getting processing bottleneck information")
        
        params = {}
        if features:
            params["features"] = features
        if model_version:
            params["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="GET",
                endpoint="/bottlenecks",
                request_data=params,
                response_model=dict
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"Could not get bottleneck information: {e}")
            return {
                "bottlenecks": [],
                "current_load": "unknown",
                "estimated_delay": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def update_actual_processing_time(
        self,
        case_id: str,
        actual_minutes: float,
        model_version: Optional[str] = None
    ) -> bool:
        """
        Update the model with actual processing time for feedback learning.
        
        Args:
            case_id: Case identifier
            actual_minutes: Actual processing time in minutes
            model_version: Specific model version
            
        Returns:
            True if update successful
        """
        logger.info(f"Updating actual processing time for case {case_id}: {actual_minutes}min")
        
        request_data = {
            "case_id": case_id,
            "actual_minutes": actual_minutes
        }
        if model_version:
            request_data["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="POST",
                endpoint="/feedback/actual_time",
                request_data=request_data,
                response_model=dict
            )
            
            return response.get("success", False)
            
        except Exception as e:
            logger.error(f"Could not update actual processing time: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ETA prediction service health."""
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
        """Get ETA prediction model information."""
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
    
    async def get_historical_performance(
        self,
        days_back: int = 30,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get historical performance metrics for ETA predictions.
        
        Args:
            days_back: Number of days to look back
            model_version: Specific model version
            
        Returns:
            Historical performance metrics
        """
        logger.info(f"Getting historical performance for last {days_back} days")
        
        params = {"days_back": days_back}
        if model_version:
            params["model_version"] = model_version
        
        try:
            response = await self._make_request_with_retry(
                method="GET",
                endpoint="/performance/historical",
                request_data=params,
                response_model=dict
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"Could not get historical performance: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class MockETAServiceClient(MockMLServiceClient):
    """Mock ETA prediction service client for testing."""
    
    def __init__(self, config: MLServiceConfig):
        # Default mock responses
        mock_responses = {
            "/predict_eta": {
                "eta_minutes": 45.5,
                "p50": 42.0,
                "p90": 78.0,
                "model_version": "eta-v2.0.0",
                "processing_time_ms": 32.1,
                "confidence_score": 0.82,
                "feature_importance": {
                    "case_complexity": 0.35,
                    "current_queue_size": 0.28,
                    "case_type": 0.18,
                    "time_of_day": 0.12,
                    "reviewer_availability": 0.07
                },
                "similar_cases_count": 127
            },
            "/health": {
                "status": "healthy",
                "service": "eta_prediction",
                "version": "2.0.0",
                "model_loaded": True,
                "last_prediction": datetime.utcnow().isoformat(),
                "queue_size": 23,
                "average_processing_time": 38.5
            },
            "/model/info": {
                "model_name": "gradient_boosting_eta_v2",
                "model_version": "eta-v2.0.0",
                "model_type": "gradient_boosting_regressor",
                "training_date": "2024-01-25T09:15:00Z",
                "feature_count": 28,
                "training_samples": 50000,
                "performance_metrics": {
                    "mae": 8.5,  # Mean Absolute Error in minutes
                    "rmse": 12.3,  # Root Mean Square Error in minutes
                    "mape": 0.18,  # Mean Absolute Percentage Error
                    "r2_score": 0.87
                },
                "prediction_ranges": {
                    "min_eta": 5.0,
                    "max_eta": 480.0,
                    "typical_range": [15.0, 120.0]
                }
            },
            "/predict_sla_compliance": {
                "case_id": "test-case",
                "sla_target_minutes": 60.0,
                "predicted_eta_minutes": 45.5,
                "compliance_probability": 0.85,
                "risk_level": "LOW",
                "confidence_score": 0.82,
                "factors_affecting_compliance": [
                    "Current queue size is normal",
                    "Case complexity is moderate",
                    "Sufficient reviewer capacity"
                ]
            },
            "/bottlenecks": {
                "bottlenecks": [
                    {
                        "type": "REVIEWER_CAPACITY",
                        "severity": "MEDIUM",
                        "estimated_delay": 15.0,
                        "description": "Limited expert reviewers available"
                    }
                ],
                "current_load": "MEDIUM",
                "estimated_delay": 15.0,
                "queue_statistics": {
                    "total_cases": 23,
                    "high_priority": 3,
                    "medium_priority": 12,
                    "low_priority": 8
                }
            },
            "/feedback/actual_time": {
                "success": True,
                "updated_at": datetime.utcnow().isoformat(),
                "prediction_error": 5.2
            },
            "/performance/historical": {
                "period_days": 30,
                "total_predictions": 1250,
                "accuracy_metrics": {
                    "mae": 8.7,
                    "rmse": 12.8,
                    "mape": 0.19,
                    "within_10_percent": 0.78,
                    "within_20_percent": 0.92
                },
                "sla_compliance_accuracy": 0.89,
                "trend": "IMPROVING"
            }
        }
        
        super().__init__(config, mock_responses)
    
    async def predict_eta(
        self,
        case_id: str,
        features: FeatureVector,
        model_version: Optional[str] = None
    ) -> ETARecord:
        """Mock ETA prediction with realistic variations."""
        import random
        
        base_response = self.mock_responses["/predict_eta"].copy()
        
        # Vary ETA based on features
        base_eta = base_response["eta_minutes"]
        
        if "case_complexity" in features:
            complexity = features.get("case_complexity", 0.5)
            if complexity > 0.8:
                base_eta *= 1.5  # Complex cases take longer
            elif complexity < 0.3:
                base_eta *= 0.7  # Simple cases are faster
        
        if "queue_size" in features:
            queue_size = features.get("queue_size", 10)
            if queue_size > 50:
                base_eta *= 1.3  # Large queue increases time
            elif queue_size < 5:
                base_eta *= 0.8  # Small queue decreases time
        
        if "priority" in features:
            priority = features.get("priority", "MEDIUM")
            if priority == "HIGH":
                base_eta *= 0.6  # High priority cases are expedited
            elif priority == "LOW":
                base_eta *= 1.2  # Low priority cases may wait longer
        
        # Add some randomness
        base_eta *= random.uniform(0.8, 1.2)
        
        # Update response
        base_response["eta_minutes"] = round(base_eta, 1)
        base_response["p50"] = round(base_eta * 0.9, 1)
        base_response["p90"] = round(base_eta * 1.7, 1)
        
        # Adjust confidence based on feature completeness
        feature_completeness = len(features) / 28  # Assuming 28 total features
        base_response["confidence_score"] = min(0.95, 0.5 + feature_completeness * 0.4)
        
        # Simulate processing time variation
        base_response["processing_time_ms"] = random.uniform(20, 60)
        
        # Create response object
        response = ETAResponse(**base_response)
        
        # Convert to ETARecord
        return ETARecord(
            case_id=case_id,
            model_type="ETA_PREDICTION",
            model_version=response.model_version,
            eta_minutes=response.eta_minutes,
            p50=response.p50,
            p90=response.p90,
            processing_time_ms=response.processing_time_ms,
            confidence_score=response.confidence_score,
            feature_importance=response.feature_importance,
            similar_cases_count=response.similar_cases_count,
            features_used=features,
        )


def create_eta_client(
    base_url: str,
    api_key: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout: float = 30.0,
    use_mock: bool = False
) -> BaseMLServiceClient:
    """
    Create an ETA prediction service client.
    
    Args:
        base_url: Base URL of the ETA prediction service
        api_key: API key for authentication
        model_version: Specific model version to use
        timeout: Request timeout in seconds
        use_mock: Whether to use mock client for testing
        
    Returns:
        ETA prediction service client instance
    """
    config = MLServiceConfig(
        service_name="eta_prediction",
        base_url=base_url,
        api_key=api_key,
        model_version=model_version,
        timeout=timeout
    )
    
    if use_mock:
        return MockETAServiceClient(config)
    else:
        return ETAServiceClient(config)
