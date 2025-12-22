"""
ML ETA Prediction Service Client.

This module implements the ETA prediction service client based on Anexo B API contracts:

ML-ETA API Contract:
Request: {case_id, features, model_version?}
Response: {eta_minutes, p50, p90?, model_version}

Features:
- Processing time estimation
- Confidence intervals (p50, p90)
- SLA compliance prediction
- Workload-based adjustments
- Model versioning and drift monitoring
- Fallback rules for service degradation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseMLServiceClient, MLServiceConfig, MLServiceError
from ...models.ml import (
    ETARequest, ETAResponse, ETAFeatures,
    MLServiceType, MLScoreRecord
)

logger = logging.getLogger(__name__)


class ETAServiceClient(BaseMLServiceClient[ETAResponse]):
    """
    ML ETA Prediction Service Client.
    
    Implements the ML-ETA service based on Anexo B specifications
    for processing time estimation and SLA compliance prediction.
    """
    
    def __init__(self, config: MLServiceConfig):
        """
        Initialize ETA prediction service client.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.service_type = MLServiceType.ETA_PREDICTION
        
        # ETA-specific configuration
        self.default_eta_minutes = 60  # 1 hour default
        self.max_eta_minutes = 2880  # 48 hours max
        self.min_eta_minutes = 5  # 5 minutes minimum
        self.confidence_levels = [0.5, 0.9, 0.95, 0.99]  # p50, p90, p95, p99
        
        logger.info("Initialized ETA Prediction Service Client")

    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        return MLServiceType.ETA_PREDICTION

    async def predict(
        self, 
        request: ETARequest, 
        **kwargs
    ) -> ETAResponse:
        """
        Make ETA prediction request.
        
        Args:
            request: ETA prediction request
            **kwargs: Additional arguments
            
        Returns:
            ETA prediction response
            
        Raises:
            MLServiceError: If ETA prediction fails
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
                endpoint="/eta",
                data=request_data,
                model_version=request.model_version
            )
            
            # Parse response according to Anexo B contract
            eta_response = ETAResponse(
                case_id=request.case_id,
                eta_minutes=response_data["eta_minutes"],
                p50=response_data["p50"],
                p90=response_data.get("p90"),
                model_version=response_data["model_version"],
                confidence_score=response_data.get("confidence_score", 0.0),
                processing_time_ms=response_data.get("processing_time_ms", 0.0),
                timestamp=datetime.utcnow(),
                confidence_intervals=response_data.get("confidence_intervals", {}),
                sla_compliance_probability=response_data.get("sla_compliance_probability", 0.0),
                workload_factors=response_data.get("workload_factors", {}),
                estimated_completion_time=self._calculate_completion_time(response_data["eta_minutes"])
            )
            
            # Validate ETA bounds
            eta_response.eta_minutes = max(
                self.min_eta_minutes, 
                min(self.max_eta_minutes, eta_response.eta_minutes)
            )
            
            # Check for drift if enabled
            if self.config.drift_check_interval > 0:
                await self._check_drift_if_needed(request.features.dict())
            
            logger.debug(
                f"ETA prediction completed for case {request.case_id}: "
                f"eta={eta_response.eta_minutes}min, "
                f"p50={eta_response.p50}min, "
                f"confidence={eta_response.confidence_score:.3f}"
            )
            
            return eta_response
            
        except Exception as e:
            logger.error(f"ETA prediction failed for case {request.case_id}: {e}")
            
            # Return fallback ETA if service is degraded
            if self.is_degraded():
                return await self._fallback_eta_prediction(request)
            
            raise MLServiceError(f"ETA prediction failed: {e}")

    async def predict_batch_eta(
        self, 
        requests: List[ETARequest],
        **kwargs
    ) -> List[ETAResponse]:
        """
        Perform batch ETA prediction.
        
        Args:
            requests: List of ETA prediction requests
            **kwargs: Additional arguments
            
        Returns:
            List of ETA prediction responses
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
                endpoint="/eta/batch",
                data=batch_data
            )
            
            # Parse batch response
            responses = []
            for i, result in enumerate(response_data["results"]):
                if result.get("error"):
                    # Handle individual request errors
                    logger.error(f"Batch ETA prediction error for request {i}: {result['error']}")
                    if self.is_degraded():
                        responses.append(await self._fallback_eta_prediction(requests[i]))
                    else:
                        responses.append(None)
                else:
                    eta_minutes = max(
                        self.min_eta_minutes, 
                        min(self.max_eta_minutes, result["eta_minutes"])
                    )
                    
                    responses.append(ETAResponse(
                        case_id=requests[i].case_id,
                        eta_minutes=eta_minutes,
                        p50=result["p50"],
                        p90=result.get("p90"),
                        model_version=result["model_version"],
                        confidence_score=result.get("confidence_score", 0.0),
                        processing_time_ms=result.get("processing_time_ms", 0.0),
                        timestamp=datetime.utcnow(),
                        confidence_intervals=result.get("confidence_intervals", {}),
                        sla_compliance_probability=result.get("sla_compliance_probability", 0.0),
                        workload_factors=result.get("workload_factors", {}),
                        estimated_completion_time=self._calculate_completion_time(eta_minutes)
                    ))
            
            logger.info(f"Batch ETA prediction completed for {len(requests)} requests")
            return responses
            
        except Exception as e:
            logger.error(f"Batch ETA prediction failed: {e}")
            
            # Fallback to individual requests
            if self.is_degraded():
                return [await self._fallback_eta_prediction(req) for req in requests]
            
            raise MLServiceError(f"Batch ETA prediction failed: {e}")

    async def get_workload_status(self) -> Dict[str, Any]:
        """
        Get current workload status affecting ETA predictions.
        
        Returns:
            Workload status information
        """
        try:
            response_data = await self._make_request(
                method="GET",
                endpoint="/eta/workload"
            )
            
            return {
                "current_queue_size": response_data.get("current_queue_size", 0),
                "average_processing_time": response_data.get("average_processing_time", 0.0),
                "system_load": response_data.get("system_load", 0.0),
                "available_capacity": response_data.get("available_capacity", 1.0),
                "peak_hours": response_data.get("peak_hours", []),
                "estimated_delay_factor": response_data.get("estimated_delay_factor", 1.0),
                "last_updated": response_data.get("last_updated", datetime.utcnow().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Workload status request failed: {e}")
            return {
                "current_queue_size": 0,
                "average_processing_time": self.default_eta_minutes,
                "system_load": 0.5,
                "available_capacity": 1.0,
                "estimated_delay_factor": 1.0,
                "error": str(e)
            }

    async def get_sla_compliance_prediction(
        self,
        case_id: UUID,
        sla_target_minutes: int,
        features: ETAFeatures,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get SLA compliance prediction for a case.
        
        Args:
            case_id: Case identifier
            sla_target_minutes: SLA target in minutes
            features: Feature vector
            model_version: Specific model version
            
        Returns:
            SLA compliance prediction
        """
        try:
            request_data = {
                "case_id": str(case_id),
                "sla_target_minutes": sla_target_minutes,
                "features": features.dict(),
                "model_version": model_version
            }
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/eta/sla_compliance",
                data=request_data,
                model_version=model_version
            )
            
            return {
                "compliance_probability": response_data.get("compliance_probability", 0.0),
                "risk_level": response_data.get("risk_level", "MEDIUM"),
                "estimated_eta": response_data.get("estimated_eta", 0),
                "sla_buffer_minutes": response_data.get("sla_buffer_minutes", 0),
                "breach_probability": response_data.get("breach_probability", 0.0),
                "recommended_actions": response_data.get("recommended_actions", []),
                "confidence_score": response_data.get("confidence_score", 0.0)
            }
            
        except Exception as e:
            logger.error(f"SLA compliance prediction failed for case {case_id}: {e}")
            return {"error": str(e)}

    async def get_eta_explanation(
        self,
        case_id: UUID,
        eta_response: ETAResponse
    ) -> Dict[str, Any]:
        """
        Get detailed explanation for ETA prediction.
        
        Args:
            case_id: Case identifier
            eta_response: ETA prediction result to explain
            
        Returns:
            Detailed explanation
        """
        try:
            request_data = {
                "case_id": str(case_id),
                "eta_result": eta_response.dict()
            }
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/eta/explain",
                data=request_data
            )
            
            return {
                "contributing_factors": response_data.get("contributing_factors", {}),
                "processing_stages": response_data.get("processing_stages", []),
                "bottleneck_analysis": response_data.get("bottleneck_analysis", {}),
                "historical_comparisons": response_data.get("historical_comparisons", []),
                "workload_impact": response_data.get("workload_impact", {}),
                "optimization_suggestions": response_data.get("optimization_suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"ETA explanation failed for case {case_id}: {e}")
            return {"error": str(e)}

    async def get_eta_statistics(
        self,
        time_range_hours: int = 24,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get ETA prediction statistics.
        
        Args:
            time_range_hours: Time range for statistics
            model_version: Specific model version
            
        Returns:
            ETA statistics
        """
        try:
            params = {
                "time_range_hours": time_range_hours
            }
            if model_version:
                params["version"] = model_version
            
            response_data = await self._make_request(
                method="GET",
                endpoint="/eta/statistics",
                params=params
            )
            
            return {
                "total_predictions": response_data.get("total_predictions", 0),
                "avg_eta_minutes": response_data.get("avg_eta_minutes", 0.0),
                "median_eta_minutes": response_data.get("median_eta_minutes", 0.0),
                "eta_accuracy": response_data.get("eta_accuracy", 0.0),
                "sla_compliance_rate": response_data.get("sla_compliance_rate", 0.0),
                "prediction_error_distribution": response_data.get("prediction_error_distribution", {}),
                "confidence_distribution": response_data.get("confidence_distribution", {}),
                "time_range_hours": time_range_hours,
                "model_version": response_data.get("model_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"ETA statistics request failed: {e}")
            return {"error": str(e)}

    async def update_eta_model(
        self,
        actual_processing_times: List[Dict[str, Any]],
        model_version: Optional[str] = None
    ) -> bool:
        """
        Update ETA model with actual processing times for learning.
        
        Args:
            actual_processing_times: List of actual processing time records
            model_version: Specific model version
            
        Returns:
            True if update successful
        """
        try:
            request_data = {
                "actual_times": actual_processing_times,
                "model_version": model_version
            }
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/eta/update_model",
                data=request_data
            )
            
            success = response_data.get("success", False)
            if success:
                logger.info(f"Updated ETA model with {len(actual_processing_times)} records")
            else:
                logger.error(f"Failed to update ETA model: {response_data.get('error')}")
            
            return success
            
        except Exception as e:
            logger.error(f"ETA model update failed: {e}")
            return False

    async def validate_features(
        self, 
        features: ETAFeatures
    ) -> Dict[str, Any]:
        """
        Validate feature vector for ETA prediction.
        
        Args:
            features: Feature vector to validate
            
        Returns:
            Validation results
        """
        try:
            request_data = {"features": features.dict()}
            
            response_data = await self._make_request(
                method="POST",
                endpoint="/eta/validate_features",
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

    def _calculate_completion_time(self, eta_minutes: float) -> datetime:
        """Calculate estimated completion time."""
        return datetime.utcnow() + timedelta(minutes=eta_minutes)

    async def _fallback_eta_prediction(
        self, 
        request: ETARequest
    ) -> ETAResponse:
        """
        Provide fallback ETA prediction when service is degraded.
        
        Args:
            request: Original ETA prediction request
            
        Returns:
            Fallback ETA prediction response
        """
        logger.warning(f"Using fallback ETA prediction for case {request.case_id}")
        
        # Simple rule-based fallback logic
        features = request.features
        
        # Base ETA calculation
        base_eta = self.default_eta_minutes
        
        # Adjust based on complexity
        if hasattr(features, 'complexity') and getattr(features, 'complexity', 'MEDIUM') == 'HIGH':
            base_eta *= 2
        elif hasattr(features, 'complexity') and getattr(features, 'complexity', 'MEDIUM') == 'LOW':
            base_eta *= 0.5
        
        # Adjust based on priority
        if hasattr(features, 'priority') and getattr(features, 'priority', 'MEDIUM') == 'HIGH':
            base_eta *= 0.7  # High priority gets faster processing
        elif hasattr(features, 'priority') and getattr(features, 'priority', 'MEDIUM') == 'LOW':
            base_eta *= 1.5  # Low priority takes longer
        
        # Adjust based on workload (simple simulation)
        import random
        workload_factor = random.uniform(0.8, 1.5)  # Simulate variable workload
        base_eta *= workload_factor
        
        # Ensure bounds
        eta_minutes = max(self.min_eta_minutes, min(self.max_eta_minutes, base_eta))
        
        # Calculate confidence intervals
        p50 = eta_minutes * 0.8  # 50% chance to complete earlier
        p90 = eta_minutes * 1.5  # 90% chance to complete by this time
        
        return ETAResponse(
            case_id=request.case_id,
            eta_minutes=eta_minutes,
            p50=p50,
            p90=p90,
            model_version="fallback-v1.0",
            confidence_score=0.5,  # Medium confidence for fallback
            processing_time_ms=3.0,
            timestamp=datetime.utcnow(),
            confidence_intervals={"p50": p50, "p90": p90, "p95": p90 * 1.2},
            sla_compliance_probability=0.7,  # Default moderate compliance
            workload_factors={"fallback": True, "workload_factor": workload_factor},
            estimated_completion_time=self._calculate_completion_time(eta_minutes),
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
                        f"Model drift detected in ETA prediction service: "
                        f"score={drift_metrics.drift_score:.3f}"
                    )
            except Exception as e:
                logger.error(f"Drift check failed: {e}")


class MockETAServiceClient(BaseMLServiceClient[ETAResponse]):
    """
    Mock ETA Prediction Service Client for testing.
    
    Provides deterministic responses for testing without requiring
    actual ML service infrastructure.
    """
    
    def __init__(self, config: Optional[MLServiceConfig] = None):
        """Initialize mock ETA prediction service client."""
        if config is None:
            config = MLServiceConfig(
                service_name="mock-eta",
                base_url="http://localhost:8002",
                request_timeout=1.0,
                max_retries=0
            )
        
        super().__init__(config)
        self.service_type = MLServiceType.ETA_PREDICTION
        
        # Mock data
        self.mock_responses = {
            "fast": ETAResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000001"),
                eta_minutes=15.0,
                p50=12.0,
                p90=20.0,
                model_version="mock-v1.0",
                confidence_score=0.9,
                processing_time_ms=25.0,
                timestamp=datetime.utcnow(),
                confidence_intervals={"p50": 12.0, "p90": 20.0, "p95": 25.0},
                sla_compliance_probability=0.95,
                workload_factors={"complexity": "LOW", "priority": "HIGH"},
                estimated_completion_time=datetime.utcnow() + timedelta(minutes=15)
            ),
            "standard": ETAResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000002"),
                eta_minutes=60.0,
                p50=45.0,
                p90=80.0,
                model_version="mock-v1.0",
                confidence_score=0.85,
                processing_time_ms=30.0,
                timestamp=datetime.utcnow(),
                confidence_intervals={"p50": 45.0, "p90": 80.0, "p95": 90.0},
                sla_compliance_probability=0.8,
                workload_factors={"complexity": "MEDIUM", "priority": "MEDIUM"},
                estimated_completion_time=datetime.utcnow() + timedelta(minutes=60)
            ),
            "slow": ETAResponse(
                case_id=UUID("00000000-0000-0000-0000-000000000003"),
                eta_minutes=180.0,
                p50=150.0,
                p90=240.0,
                model_version="mock-v1.0",
                confidence_score=0.75,
                processing_time_ms=35.0,
                timestamp=datetime.utcnow(),
                confidence_intervals={"p50": 150.0, "p90": 240.0, "p95": 300.0},
                sla_compliance_probability=0.6,
                workload_factors={"complexity": "HIGH", "priority": "LOW"},
                estimated_completion_time=datetime.utcnow() + timedelta(minutes=180)
            )
        }

    def get_service_type(self) -> MLServiceType:
        """Get the service type."""
        return MLServiceType.ETA_PREDICTION

    async def start(self):
        """Start mock service (no-op)."""
        logger.info("Started mock ETA prediction service")

    async def stop(self):
        """Stop mock service (no-op)."""
        logger.info("Stopped mock ETA prediction service")

    async def predict(
        self, 
        request: ETARequest, 
        **kwargs
    ) -> ETAResponse:
        """
        Mock ETA prediction.
        
        Args:
            request: ETA prediction request
            **kwargs: Additional arguments
            
        Returns:
            Mock ETA prediction response
        """
        # Simulate processing delay
        import asyncio
        await asyncio.sleep(0.025)
        
        # Determine mock response based on features
        features = request.features
        
        # Simple logic to determine response type
        if hasattr(features, 'priority') and getattr(features, 'priority') == "HIGH":
            response = self.mock_responses["fast"].copy()
        elif hasattr(features, 'complexity') and getattr(features, 'complexity') == "HIGH":
            response = self.mock_responses["slow"].copy()
        else:
            response = self.mock_responses["standard"].copy()
        
        # Update with actual case ID and recalculate completion time
        response.case_id = request.case_id
        response.timestamp = datetime.utcnow()
        response.estimated_completion_time = datetime.utcnow() + timedelta(minutes=response.eta_minutes)
        
        logger.debug(f"Mock ETA prediction for case {request.case_id}: {response.eta_minutes} minutes")
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
            models_available=["eta-mock-v1.0"],
            error_message=None
        )

    async def get_model_info(self, model_version: Optional[str] = None):
        """Mock model info."""
        from ...models.ml import MLModelInfo, ModelStatus
        
        return MLModelInfo(
            model_id="eta-mock",
            model_version="mock-v1.0",
            model_type=MLServiceType.ETA_PREDICTION,
            training_date=datetime(2024, 1, 1),
            deployment_date=datetime(2024, 1, 15),
            performance_metrics={"mae": 5.2, "rmse": 8.1, "r2_score": 0.87},
            feature_schema={"complexity": "string", "priority": "string", "workload": "float"},
            status=ModelStatus.HEALTHY
        )


__all__ = [
    "ETAServiceClient",
    "MockETAServiceClient"
]
