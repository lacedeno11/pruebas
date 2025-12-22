"""
ML Anomaly Detection Service Client.

This module implements the anomaly detection service client based on Anexo B API contracts:

ML-ANOMALY API Contract:
Request: {case_id, features, aggregates, model_version?}
Response: {anomaly_score, anomaly_flags, recommended_action, model_version}

Features:
- Anomaly detection and scoring
- Multi-dimensional anomaly analysis
- Recommended action generation
- Threshold-based alerting
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
    AnomalyRequest, AnomalyResponse, AnomalyFeatures,
    MLServiceType, AnomalyFlag, RecommendedAction, MLScoreRecord
)

logger = logging.getLogger(__name__)


class AnomalyServiceClient(BaseMLServiceClient[AnomalyResponse]):
    """
    ML Anomaly Detection Service Client.
    
    Implements the ML-ANOMALY service based on Anexo B specifications
    for anomaly detection, scoring, and recommended action generation.
    """
    
    def __init__(self, config: MLServiceConfig):
        """
        Initialize anomaly detection service client.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.service_type = MLServiceType.ANOMALY_DETECTION
        
        # Anomaly-specific configuration
        self.default_anomaly_threshold = 0.7
        self.high_anomaly_threshold = 0.9
        self.critical_anomaly_threshold = 0.95
        self.max_anomaly_flags = 20
        
        logger.info("Initialized Anomaly Detection Service Client")

    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        return MLServiceType.ANOMALY_DETECTION

    async def predict(
        self, 
        request: AnomalyRequest, 
        **kwargs
    ) -> AnomalyResponse:
        """
        Make anomaly detection prediction request.
        
        Args:
            request: Anomaly detection request
            **kwargs: Additional arguments
            
        Returns:
            Anomaly detection response
            
        Raises:
            MLServiceError: If anomaly detection fails
        """
        try:
            # Prepare request data according to Anexo B
            request_data = {
                "case_id": str(request.case_id),
                "features": request.features.dict(),
                "aggregates": request.aggregates,
                "model_version": request.model_version
            }
            
            # Remove None values
            request_data = {k: v for k, v in request_data.items() if v is not None}
            
            # Make API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/anomaly",
                data=request_data,
                model_version=request.model_version
            )
            
            # Parse response according to Anexo B contract
            anomaly_response = AnomalyResponse(
                case_id=request.case_id,
                anomaly_score=response_data["anomaly_score"],
                anomaly_flags=[AnomalyFlag(flag) for flag in response_data["anomaly_flags"]],
                recommended_action=RecommendedAction(response_data["recommended_action"]),
                model_version=response_data["model_version"],
                confidence_score=response_data.get("confidence_score", 0.0),
                processing_time_ms=response_data.get("processing_time_ms", 0.0),
                timestamp=datetime.utcnow(),
                anomaly_details=response_data.get("anomaly_details", {}),
                feature_contributions=response_data.get("feature_contributions", {}),
                threshold_used=response_data.get("threshold_used", self.default_anomaly_threshold)
            )
            
            # Check for drift if enabled
            if self.config.drift_check_interval > 0:
                await self._check_drift_if_needed(request.features.dict())
            
            # Log anomaly detection results
            if anomaly_response.anomaly_score > self.high_anomaly_threshold:
                logger.warning(
                    f"High anomaly detected for case {request.case_id}: "
                    f"score={anomaly_response.anomaly_score:.3f}, "
                    f"flags={[flag.value for flag in anomaly_response.anomaly_flags]}, "
                    f"action={anomaly_response.recommended_action.value}"
                )
            else:
                logger.debug(
                    f"Anomaly detection completed for case {request.case_id}: "
                    f"score={anomaly_response.anomaly_score:.3f}, "
                    f"action={anomaly_response.recommended_action.value}"
                )
            
            return anomaly_response
            
        except Exception as e:
            logger.error(f"Anomaly detection failed for case {request.case_id}: {e}")
            
            # Return fallback anomaly detection if service is degraded
            if self.is_degraded():
                return await self._fallback_anomaly_detection(request)
            
            raise MLServiceError(f"Anomaly detection failed: {e}")

    async def detect_batch_anomalies(
        self, 
        requests: List[AnomalyRequest],
        **kwargs
    ) -> List[AnomalyResponse]:
        """
        Perform batch anomaly detection.
        
        Args:
            requests: List of anomaly detection requests
            **kwargs: Additional arguments
            
        Returns:
            List of anomaly detection responses
        """
        try:
            # Prepare batch request data
            batch_data = {
                "requests": [
                    {
                        "case_id": str(req.case_id),
                        "features": req.features.dict(),
                        "aggregates": req.aggregates,
                        "model_version": req.model_version
                    }
                    for req in requests
                ]
            }
            
            # Make batch API request
            response_data = await self._make_request(
                method="POST",
                endpoint="/anomaly/batch",
                data=batch_data
            )
            
            # Parse batch response
            responses = []
            for i, result in enumerate(response_data["results"]):
                if result.get("error"):
                    # Handle individual request errors
                    logger.error(f"Batch anomaly detection error for request {i}: {result['error']}")
                    if self.is_degraded():
                        responses.append(await self._fallback_anomaly_detection(requests[i]))
                    else:
                        responses.append(None)
                else:
                    responses.append(AnomalyResponse(
                        case_id=requests[i].case_id,
                        anomaly_score=result["anomaly_score"],
                        anomaly_flags=[AnomalyFlag(flag) for flag in result["anomaly_flags"]],
                        recommended_action=RecommendedAction(result["recommended_action"]),
                        model_version=result["model_version"],
                        confidence_score=result.get("confidence_score", 0.0),
                        processing_time_ms=result.get("processing_time_ms", 0.0),
                        timestamp=datetime.utcnow(),
                        anomaly_details=result.get("anomaly_details", {}),
                        feature_contributions=result.get("feature_contributions", {}),
                        threshold_used=result.get("threshold_used", self.default_anomaly_threshold)
                    ))
            
            logger.info(f"Batch anomaly detection completed for {len(requests)} requests")
            return responses
            
        except Exception as e:
            logger.error(f"Batch anomaly detection failed: {e}")
            
            # Fallback to individual requests
            if self.is_degraded():
                return [await self._fallback_anomaly_detection(req) for req in requests]
            
            raise MLServiceError(f"Batch anomaly detection failed: {e}")

    async def get_anomaly_explanation(
        self,
        case_id: UUID,
        anomaly_response: AnomalyResponse
    ) -> Dict[str, Any]:
        """
        Get detailed explanation for anomaly detection.
        
        Args:
            case_id: Case identifier
            anomaly_response: Anomaly detection result to explain
            
        Returns:
            Detailed explanation
        """
        try:
            request_data = {
                "case_id": str(case_id),
                "anomaly_result": anomaly_response.dict()
            }
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/anomaly/explain",
                data=request_data
            )
            
            return {
                "anomaly_type": response_data.get("anomaly_type", "unknown"),
                "contributing_features": response_data.get("contributing_features", {}),
                "normal_ranges": response_data.get("normal_ranges", {}),
                "deviation_analysis": response_data.get("deviation_analysis", {}),
                "similar_cases": response_data.get("similar_cases", []),
                "historical_context": response_data.get("historical_context", {}),
                "remediation_suggestions": response_data.get("remediation_suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"Anomaly explanation failed for case {case_id}: {e}")
            return {"error": str(e)}

    async def get_anomaly_thresholds(
        self, 
        model_version: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get current anomaly detection thresholds.
        
        Args:
            model_version: Specific model version
            
        Returns:
            Anomaly thresholds
        """
        try:
            params = {}
            if model_version:
                params["version"] = model_version
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/anomaly/thresholds",
                params=params
            )
            
            return {
                "low_anomaly": response_data.get("low_anomaly", 0.3),
                "medium_anomaly": response_data.get("medium_anomaly", 0.6),
                "high_anomaly": response_data.get("high_anomaly", 0.8),
                "critical_anomaly": response_data.get("critical_anomaly", 0.95),
                "model_version": response_data.get("model_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Anomaly thresholds request failed: {e}")
            return {
                "low_anomaly": 0.3,
                "medium_anomaly": 0.6,
                "high_anomaly": 0.8,
                "critical_anomaly": 0.95,
                "error": str(e)
            }

    async def update_anomaly_thresholds(
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
        try:
            request_data = {
                "thresholds": thresholds,
                "model_version": model_version
            }
            
            response_data = await self._make_request(
                method="PUT",
                endpoint="/anomaly/thresholds",
                data=request_data
            )
            
            success = response_data.get("success", False)
            if success:
                logger.info(f"Updated anomaly thresholds: {thresholds}")
            else:
                logger.error(f"Failed to update anomaly thresholds: {response_data.get('error')}")
            
            return success
            
        except Exception as e:
            logger.error(f"Anomaly threshold update failed: {e}")
            return False

    async def get_anomaly_statistics(
        self,
        time_range_hours: int = 24,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get anomaly detection statistics.
        
        Args:
            time_range_hours: Time range for statistics
            model_version: Specific model version
            
        Returns:
            Anomaly statistics
        """
        try:
            params = {
                "time_range_hours": time_range_hours
            }
            if model_version:
                params["version"] = model_version
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/anomaly/statistics",
                params=params
            )
            
            return {
                "total_cases": response_data.get("total_cases", 0),
                "anomalous_cases": response_data.get("anomalous_cases", 0),
                "anomaly_rate": response_data.get("anomaly_rate", 0.0),
                "avg_anomaly_score": response_data.get("avg_anomaly_score", 0.0),
                "max_anomaly_score": response_data.get("max_anomaly_score", 0.0),
                "flag_distribution": response_data.get("flag_distribution", {}),
                "action_distribution": response_data.get("action_distribution", {}),
                "time_range_hours": time_range_hours,
                "model_version": response_data.get("model_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Anomaly statistics request failed: {e}")
            return {"error": str(e)}

    async def validate_features(
        self, 
        features: AnomalyFeatures
    ) -> Dict[str, Any]:
        """
        Validate feature vector for anomaly detection.
        
        Args:
            features: Feature vector to validate
            
        Returns:
            Validation results
        """
        try:
            request_data = {"features": features.dict()}
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/anomaly/validate_features",
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

    async def _fallback_anomaly_detection(
        self, 
        request: AnomalyRequest
    ) -> AnomalyResponse:
        """
        Provide fallback anomaly detection when service is degraded.
        
        Args:
            request: Original anomaly detection request
            
        Returns:
            Fallback anomaly detection response
        """
        logger.warning(f"Using fallback anomaly detection for case {request.case_id}")
        
        # Simple rule-based fallback logic
        features = request.features
        aggregates = request.aggregates or {}
        
        # Calculate simple anomaly score based on basic rules
        anomaly_score = 0.0
        anomaly_flags = []
        
        # Check for extreme values in aggregates
        if aggregates:
            for key, value in aggregates.items():
                if isinstance(value, (int, float)):
                    if value > 1000000:  # Very high value
                        anomaly_score += 0.3
                        anomaly_flags.append(AnomalyFlag.HIGH_VALUE)
                    elif value < 0:  # Negative value where not expected
                        anomaly_score += 0.2
                        anomaly_flags.append(AnomalyFlag.INVALID_VALUE)
        
        # Check feature patterns
        if hasattr(features, 'transaction_count') and getattr(features, 'transaction_count', 0) > 100:
            anomaly_score += 0.4
            anomaly_flags.append(AnomalyFlag.HIGH_FREQUENCY)
        
        if hasattr(features, 'time_of_day') and getattr(features, 'time_of_day', 12) < 6:
            anomaly_score += 0.2
            anomaly_flags.append(AnomalyFlag.UNUSUAL_TIME)
        
        # Determine recommended action
        if anomaly_score > 0.8:
            recommended_action = RecommendedAction.BLOCK
        elif anomaly_score > 0.5:
            recommended_action = RecommendedAction.MANUAL_REVIEW
        elif anomaly_score > 0.3:
            recommended_action = RecommendedAction.FLAG
        else:
            recommended_action = RecommendedAction.ALLOW
        
        # Ensure we don't exceed maximum score
        anomaly_score = min(anomaly_score, 1.0)
        
        return AnomalyResponse(
            case_id=request.case_id,
            anomaly_score=anomaly_score,
            anomaly_flags=anomaly_flags[:self.max_anomaly_flags],
            recommended_action=recommended_action,
            model_version="fallback-v1.0",
            confidence_score=0.4,  # Low confidence for fallback
            processing_time_ms=2.0,
            timestamp=datetime.utcnow(),
            anomaly_details={"fallback": True, "rule_based": True},
            feature_contributions={"fallback_score": anomaly_score},
            threshold_used=self.default_anomaly_threshold,
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
                        f"Model drift detected in anomaly detection service: "
                        f"score={drift_metrics.drift_score:.3f}"
                    )
            except Exception as e:
                logger.error(f"Drift check failed: {e}")


class MockAnomalyServiceClient(BaseMLServiceClient[AnomalyResponse]):
    """
    Mock Anomaly Detection Service Client for testing.
    
    Provides deterministic responses for testing without requiring
    actual ML service infrastructure.
    """
    
    def __init__(self, config: Optional[MLServiceConfig] = None):
        """Initialize mock anomaly detection service client."""
        if config is None:
            config = MLServiceConfig(
                service_name="mock-anomaly",
                base_url="http://localhost:8001",
                request_timeout=1.0,
                max_retries=0
            )
        
        super().__init__(config)
        self.service_type = MLServiceType.ANOMALY_DETECTION
        
        # Mock data
        self.mock_responses = {
            "normal": AnomalyResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000001"),
                anomaly_score=0.2,
                anomaly_flags=[],
                recommended_action=RecommendedAction.ALLOW,
                model_version="mock-v1.0",
                confidence_score=0.9,
                processing_time_ms=30.0,
                timestamp=datetime.utcnow(),
                anomaly_details={"type": "normal"},
                feature_contributions={"amount": 0.1, "frequency": 0.1},
                threshold_used=0.7
            ),
            "suspicious": AnomalyResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000002"),
                anomaly_score=0.6,
                anomaly_flags=[AnomalyFlag.UNUSUAL_PATTERN],
                recommended_action=RecommendedAction.FLAG,
                model_version="mock-v1.0",
                confidence_score=0.8,
                processing_time_ms=35.0,
                timestamp=datetime.utcnow(),
                anomaly_details={"type": "suspicious", "pattern": "unusual_timing"},
                feature_contributions={"timing": 0.4, "amount": 0.2},
                threshold_used=0.7
            ),
            "anomalous": AnomalyResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000003"),
                anomaly_score=0.9,
                anomaly_flags=[AnomalyFlag.HIGH_VALUE, AnomalyFlag.HIGH_FREQUENCY],
                recommended_action=RecommendedAction.MANUAL_REVIEW,
                model_version="mock-v1.0",
                confidence_score=0.95,
                processing_time_ms=40.0,
                timestamp=datetime.utcnow(),
                anomaly_details={"type": "anomalous", "severity": "high"},
                feature_contributions={"amount": 0.6, "frequency": 0.3},
                threshold_used=0.7
            )
        }

    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        return MLServiceType.ANOMALY_DETECTION

    async def start(self):
        """Start mock service (no-op)."""
        logger.info("Started mock anomaly detection service")

    async def stop(self):
        """Stop mock service (no-op)."""
        logger.info("Stopped mock anomaly detection service")

    async def predict(
        self, 
        request: AnomalyRequest, 
        **kwargs
    ) -> AnomalyResponse:
        """
        Mock anomaly detection prediction.
        
        Args:
            request: Anomaly detection request
            **kwargs: Additional arguments
            
        Returns:
            Mock anomaly detection response
        """
        # Simulate processing delay
        import asyncio
        await asyncio.sleep(0.03)
        
        # Determine mock response based on features and aggregates
        features = request.features
        aggregates = request.aggregates or {}
        
        # Simple logic to determine response type
        if aggregates.get('amount', 0) > 100000 or aggregates.get('frequency', 0) > 50:
            response = self.mock_responses["anomalous"].copy()
        elif (hasattr(features, 'time_of_day') and getattr(features, 'time_of_day', 12) < 6) or \
             aggregates.get('amount', 0) > 50000:
            response = self.mock_responses["suspicious"].copy()
        else:
            response = self.mock_responses["normal"].copy()
        
        # Update with actual case ID
        response.case_id = request.case_id
        response.timestamp = datetime.utcnow()
        
        logger.debug(f"Mock anomaly detection for case {request.case_id}: score={response.anomaly_score}")
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
            models_available=["anomaly-mock-v1.0"],
            error_message=None
        )

    async def get_model_info(self, model_version: Optional[str] = None):
        """Mock model info."""
        from ...models.ml import MLModelInfo, ModelStatus
        
        return MLModelInfo(
            model_id="anomaly-mock",
            model_version="mock-v1.0",
            model_type=MLServiceType.ANOMALY_DETECTION,
            training_date=datetime(2024, 1, 1),
            deployment_date=datetime(2024, 1, 15),
            performance_metrics={"precision": 0.92, "recall": 0.88, "f1_score": 0.90},
            feature_schema={"amount": "float", "frequency": "int", "time_of_day": "int"},
            status=ModelStatus.HEALTHY
        )


__all__ = [
    "AnomalyServiceClient",
    "MockAnomalyServiceClient"
]
