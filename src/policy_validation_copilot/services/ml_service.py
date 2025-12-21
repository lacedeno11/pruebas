"""
ML Service client.

Handles communication with ML services for classification, anomaly detection, and ETA.
Based on UC-OP-11, UC-OP-12, UC-OP-13 and Anexo B contracts.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

import httpx

from policy_validation_copilot.models.ml import (
    MLClassifyOutput,
    MLAnomalyOutput,
    MLETAOutput,
)
from policy_validation_copilot.models.case import Case

logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """Error from ML service."""

    pass


class MLService:
    """
    Client for ML services.

    Provides classification, anomaly detection, and ETA prediction
    with fallback to rule-based defaults on degradation.
    """

    def __init__(
        self,
        classify_endpoint: str = "http://ml-service:8001/classify",
        anomaly_endpoint: str = "http://ml-service:8001/anomaly",
        eta_endpoint: str = "http://ml-service:8001/eta",
        timeout: float = 30.0,
        fallback_enabled: bool = True,
    ):
        self.classify_endpoint = classify_endpoint
        self.anomaly_endpoint = anomaly_endpoint
        self.eta_endpoint = eta_endpoint
        self.timeout = timeout
        self.fallback_enabled = fallback_enabled
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_features(self, case: Case) -> dict:
        """Build feature vector from case data."""
        return {
            "case_id": case.case_id,
            "insurer_id": case.insurer_id,
            "plan_id": case.plan_id,
            "service_code": case.service_code,
            "service_description": case.service_description,
            "priority": case.priority,
            "has_attachments": len(case.attachments) > 0,
            "attachment_count": len(case.attachments),
            "channel": case.channel,
        }

    async def classify(
        self,
        case: Case,
        model_version: Optional[str] = None,
    ) -> MLClassifyOutput:
        """
        Classify case and determine routing.

        UC-OP-11: Predicts request type, candidate policies, route, and risk.
        """
        features = self._build_features(case)
        start_time = datetime.utcnow()

        try:
            client = await self._get_client()
            response = await client.post(
                self.classify_endpoint,
                json={
                    "case_id": case.case_id,
                    "features": features,
                    "model_version": model_version,
                },
            )
            response.raise_for_status()
            data = response.json()

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return MLClassifyOutput(
                request_type=data.get("request_type", "VALIDATION"),
                request_type_confidence=data.get("request_type_confidence", 0.8),
                candidate_policy_ids=data.get("candidate_policy_ids", []),
                route=data.get("route", "HITL_AGENT"),
                route_confidence=data.get("route_confidence", 0.7),
                risk_prior=data.get("risk_prior", 0.5),
                probabilities=data.get("probabilities", {}),
                top_features=data.get("top_features", []),
                model_version=data.get("model_version", "unknown"),
                inference_duration_ms=duration,
                ml_degraded=False,
            )

        except Exception as e:
            logger.warning(f"ML classify failed, using fallback: {e}")
            if not self.fallback_enabled:
                raise MLServiceError(f"ML classify failed: {e}") from e

            # Fallback to rule-based classification
            return self._fallback_classify(case)

    def _fallback_classify(self, case: Case) -> MLClassifyOutput:
        """Rule-based fallback for classification."""
        # Simple heuristics based on case attributes
        risk_prior = 0.5
        route = "HITL_AGENT"

        if case.priority.value in ("HIGH", "URGENT"):
            risk_prior = 0.7
            route = "HITL_SUPERVISOR"
        elif len(case.attachments) > 0 and case.service_code:
            risk_prior = 0.3
            route = "AUTO"

        return MLClassifyOutput(
            request_type="VALIDATION",
            request_type_confidence=0.6,
            candidate_policy_ids=[],
            route=route,
            route_confidence=0.5,
            risk_prior=risk_prior,
            probabilities={},
            top_features=[],
            model_version="fallback-rules-v1",
            ml_degraded=True,
        )

    async def detect_anomaly(
        self,
        case: Case,
        aggregates: Optional[dict] = None,
        model_version: Optional[str] = None,
    ) -> MLAnomalyOutput:
        """
        Detect anomalies in case.

        UC-OP-12: Detects atypical patterns requiring special attention.
        """
        features = self._build_features(case)
        start_time = datetime.utcnow()

        try:
            client = await self._get_client()
            response = await client.post(
                self.anomaly_endpoint,
                json={
                    "case_id": case.case_id,
                    "features": features,
                    "aggregates": aggregates or {},
                    "model_version": model_version,
                },
            )
            response.raise_for_status()
            data = response.json()

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return MLAnomalyOutput(
                anomaly_score=data.get("anomaly_score", 0.0),
                is_anomalous=data.get("is_anomalous", False),
                anomaly_flags=data.get("anomaly_flags", []),
                recommended_action=data.get("recommended_action", "CONTINUE"),
                baseline_deviation=data.get("baseline_deviation"),
                similar_cases_count=data.get("similar_cases_count"),
                model_version=data.get("model_version", "unknown"),
                inference_duration_ms=duration,
                ml_degraded=False,
            )

        except Exception as e:
            logger.warning(f"ML anomaly detection failed, using fallback: {e}")
            if not self.fallback_enabled:
                raise MLServiceError(f"ML anomaly failed: {e}") from e

            return self._fallback_anomaly(case)

    def _fallback_anomaly(self, case: Case) -> MLAnomalyOutput:
        """Rule-based fallback for anomaly detection."""
        # Simple heuristics - flag unknown as potentially anomalous
        return MLAnomalyOutput(
            anomaly_score=0.3,  # Slightly elevated due to unknown
            is_anomalous=False,
            anomaly_flags=[],
            recommended_action="CONTINUE",
            model_version="fallback-rules-v1",
            ml_degraded=True,
        )

    async def predict_eta(
        self,
        case: Case,
        model_version: Optional[str] = None,
    ) -> MLETAOutput:
        """
        Predict case resolution time.

        UC-OP-13: Estimates time for SLA management.
        """
        features = self._build_features(case)
        start_time = datetime.utcnow()

        try:
            client = await self._get_client()
            response = await client.post(
                self.eta_endpoint,
                json={
                    "case_id": case.case_id,
                    "features": features,
                    "model_version": model_version,
                },
            )
            response.raise_for_status()
            data = response.json()

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return MLETAOutput(
                eta_minutes=data.get("eta_minutes", 60),
                p50_minutes=data.get("p50_minutes"),
                p90_minutes=data.get("p90_minutes"),
                sla_risk=data.get("sla_risk", "MEDIUM"),
                sla_breach_probability=data.get("sla_breach_probability"),
                eta_factors=data.get("eta_factors", []),
                model_version=data.get("model_version", "unknown"),
                inference_duration_ms=duration,
                ml_degraded=False,
            )

        except Exception as e:
            logger.warning(f"ML ETA prediction failed, using fallback: {e}")
            if not self.fallback_enabled:
                raise MLServiceError(f"ML ETA failed: {e}") from e

            return self._fallback_eta(case)

    def _fallback_eta(self, case: Case) -> MLETAOutput:
        """Rule-based fallback for ETA prediction."""
        # Simple heuristics based on priority
        eta_map = {
            "URGENT": 30,
            "HIGH": 60,
            "NORMAL": 120,
            "LOW": 240,
        }
        eta = eta_map.get(case.priority.value, 120)

        return MLETAOutput(
            eta_minutes=eta,
            p50_minutes=eta,
            p90_minutes=int(eta * 1.5),
            sla_risk="MEDIUM",
            model_version="fallback-rules-v1",
            ml_degraded=True,
        )
