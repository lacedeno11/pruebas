"""
Intelligent Routing Node with ML Integration for Policy Validation Copilot

This module implements the routing_node function that integrates with ML services
for enhanced case processing and routing decisions. It implements:

- ML Classification Service integration (UC-OP-11)
- ML Anomaly Detection Service integration (UC-OP-12) 
- ML ETA Prediction Service integration (UC-OP-13)
- Feature vector construction from case data
- Fallback logic for ML service degradation
- Model version tracking and drift monitoring
- State updates with ML outputs and metadata

The node enriches case data with ML insights to enable intelligent routing
and decision-making in downstream workflow nodes.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.schemas.state import (
    PolicyValidationState,
    MLClassificationOutput,
    MLAnomalyOutput,
    MLETAOutput,
    MLOutputs,
    MLModelVersions,
    update_state_audit
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration and Constants
# ============================================================================

# ML Service Endpoints (would be loaded from config in production)
ML_SERVICE_CONFIG = {
    "classification": {
        "endpoint": "http://localhost:8001/classify",
        "timeout": 30,
        "retries": 3,
        "fallback_enabled": True
    },
    "anomaly": {
        "endpoint": "http://localhost:8002/anomaly", 
        "timeout": 30,
        "retries": 3,
        "fallback_enabled": True
    },
    "eta": {
        "endpoint": "http://localhost:8003/eta",
        "timeout": 30,
        "retries": 3,
        "fallback_enabled": True
    }
}

# Feature engineering constants
FEATURE_CATEGORIES = {
    "temporal": ["service_date", "created_at", "sla_target"],
    "categorical": ["insurer_id", "plan_id", "service_code", "provider_id", "priority"],
    "numerical": ["attachment_count", "attachment_total_size"],
    "derived": ["days_since_service", "hours_to_sla", "is_weekend_service"]
}

# Fallback values for ML service failures
FALLBACK_VALUES = {
    "classification": {
        "request_type": "UNKNOWN",
        "candidate_policy_ids": [],
        "route": "standard",
        "risk_prior": 0.5,
        "probabilities": {"standard": 0.5, "specialist": 0.3, "fraud": 0.2},
        "top_features": [],
        "confidence": 0.3
    },
    "anomaly": {
        "anomaly_score": 0.5,
        "anomaly_flags": [],
        "recommended_action": "standard_processing",
        "confidence": 0.3
    },
    "eta": {
        "eta_minutes": 240,  # 4 hours default
        "p50": 240,
        "p90": 480,
        "confidence": 0.3
    }
}


# ============================================================================
# Feature Engineering
# ============================================================================

def extract_case_features(state: PolicyValidationState) -> Dict[str, Any]:
    """
    Extract and engineer features from case data for ML services.
    
    Args:
        state: Current PolicyValidationState
        
    Returns:
        Dict[str, Any]: Feature vector for ML services
    """
    case = state["case"]
    now = datetime.utcnow()
    
    # Basic case features
    features = {
        "case_id": case.case_id,
        "crm_ticket_id": case.crm_ticket_id,
        "customer_id": case.customer_id,
        "contract_id": case.contract_id,
        "insurer_id": case.insurer_id,
        "plan_id": case.plan_id,
        "service_code": case.service_code,
        "provider_id": case.provider_id,
        "priority": case.priority.value,
        "assigned_queue": case.assigned_queue
    }
    
    # Temporal features
    features.update({
        "service_date": case.service_date.isoformat(),
        "created_at": case.created_at.isoformat(),
        "sla_target": case.sla_target.isoformat(),
        "days_since_service": (now.date() - case.service_date.date()).days,
        "hours_to_sla": (case.sla_target - now).total_seconds() / 3600,
        "is_weekend_service": case.service_date.weekday() >= 5,
        "service_hour": case.service_date.hour,
        "created_hour": case.created_at.hour
    })
    
    # Attachment features
    features.update({
        "attachment_count": len(case.attachments),
        "attachment_total_size": sum(att.size_bytes for att in case.attachments),
        "has_pdf_attachments": any(att.content_type == "application/pdf" for att in case.attachments),
        "has_excel_attachments": any("excel" in att.content_type for att in case.attachments),
        "has_image_attachments": any(att.content_type.startswith("image/") for att in case.attachments)
    })
    
    # Derived categorical features
    features.update({
        "is_high_priority": case.priority.value == "HIGH",
        "is_urgent_sla": features["hours_to_sla"] < 2,
        "is_recent_service": features["days_since_service"] <= 1,
        "is_large_case": features["attachment_total_size"] > 10 * 1024 * 1024,  # > 10MB
        "service_code_category": case.service_code[:3],  # First 3 chars
        "provider_type": case.provider_id[:3]  # First 3 chars
    })
    
    return features


def create_aggregated_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create aggregated features for anomaly detection.
    
    Args:
        features: Base feature vector
        
    Returns:
        Dict[str, Any]: Aggregated features
    """
    # Historical aggregates (would be computed from database in production)
    # For now, using mock aggregates based on feature patterns
    
    aggregates = {
        "customer_case_count_30d": hash(features["customer_id"]) % 50 + 1,
        "provider_case_count_30d": hash(features["provider_id"]) % 100 + 10,
        "insurer_case_count_30d": hash(features["insurer_id"]) % 200 + 50,
        "service_code_frequency_30d": hash(features["service_code"]) % 30 + 5,
        "avg_attachment_size_customer": hash(features["customer_id"]) % 5000000 + 1000000,
        "avg_processing_time_provider": hash(features["provider_id"]) % 300 + 60,
        "fraud_rate_provider_30d": (hash(features["provider_id"]) % 100) / 1000,  # 0-0.1
        "rejection_rate_insurer_30d": (hash(features["insurer_id"]) % 200) / 1000  # 0-0.2
    }
    
    # Ratio features
    aggregates.update({
        "attachment_size_vs_avg": features["attachment_total_size"] / max(aggregates["avg_attachment_size_customer"], 1),
        "case_frequency_score": aggregates["customer_case_count_30d"] / 30,  # Cases per day
        "provider_load_score": aggregates["provider_case_count_30d"] / 100  # Normalized load
    })
    
    return aggregates


# ============================================================================
# ML Service Client
# ============================================================================

class MLServiceClient:
    """HTTP client for ML service interactions with retry logic and fallbacks."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.service_health = {
            "classification": True,
            "anomaly": True,
            "eta": True
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_classification_service(
        self,
        features: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Call ML Classification Service (UC-OP-11).
        
        Args:
            features: Feature vector
            model_version: Optional model version
            
        Returns:
            Tuple[Dict[str, Any], bool]: (Response data, Success flag)
        """
        try:
            config = ML_SERVICE_CONFIG["classification"]
            
            payload = {
                "case_id": features["case_id"],
                "features": features,
                "model_version": model_version
            }
            
            response = await self.client.post(
                config["endpoint"],
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                self.service_health["classification"] = True
                return response.json(), True
            else:
                logger.warning(f"Classification service returned {response.status_code}: {response.text}")
                self.service_health["classification"] = False
                return FALLBACK_VALUES["classification"], False
                
        except Exception as e:
            logger.error(f"Classification service error: {str(e)}")
            self.service_health["classification"] = False
            return FALLBACK_VALUES["classification"], False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_anomaly_service(
        self,
        features: Dict[str, Any],
        aggregates: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Call ML Anomaly Detection Service (UC-OP-12).
        
        Args:
            features: Feature vector
            aggregates: Aggregated features
            model_version: Optional model version
            
        Returns:
            Tuple[Dict[str, Any], bool]: (Response data, Success flag)
        """
        try:
            config = ML_SERVICE_CONFIG["anomaly"]
            
            payload = {
                "case_id": features["case_id"],
                "features": features,
                "aggregates": aggregates,
                "model_version": model_version
            }
            
            response = await self.client.post(
                config["endpoint"],
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                self.service_health["anomaly"] = True
                return response.json(), True
            else:
                logger.warning(f"Anomaly service returned {response.status_code}: {response.text}")
                self.service_health["anomaly"] = False
                return FALLBACK_VALUES["anomaly"], False
                
        except Exception as e:
            logger.error(f"Anomaly service error: {str(e)}")
            self.service_health["anomaly"] = False
            return FALLBACK_VALUES["anomaly"], False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_eta_service(
        self,
        features: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Call ML ETA Prediction Service (UC-OP-13).
        
        Args:
            features: Feature vector
            model_version: Optional model version
            
        Returns:
            Tuple[Dict[str, Any], bool]: (Response data, Success flag)
        """
        try:
            config = ML_SERVICE_CONFIG["eta"]
            
            payload = {
                "case_id": features["case_id"],
                "features": features,
                "model_version": model_version
            }
            
            response = await self.client.post(
                config["endpoint"],
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                self.service_health["eta"] = True
                return response.json(), True
            else:
                logger.warning(f"ETA service returned {response.status_code}: {response.text}")
                self.service_health["eta"] = False
                return FALLBACK_VALUES["eta"], False
                
        except Exception as e:
            logger.error(f"ETA service error: {str(e)}")
            self.service_health["eta"] = False
            return FALLBACK_VALUES["eta"], False
    
    def get_service_health(self) -> Dict[str, bool]:
        """Get current service health status."""
        return self.service_health.copy()


# ============================================================================
# ML Output Processing
# ============================================================================

def process_classification_output(
    response_data: Dict[str, Any],
    success: bool
) -> MLClassificationOutput:
    """
    Process classification service response into structured output.
    
    Args:
        response_data: Raw response from classification service
        success: Whether the service call was successful
        
    Returns:
        MLClassificationOutput: Structured classification output
    """
    return MLClassificationOutput(
        request_type=response_data.get("request_type", "UNKNOWN"),
        candidate_policy_ids=response_data.get("candidate_policy_ids", []),
        route=response_data.get("route", "standard"),
        risk_prior=response_data.get("risk_prior", 0.5),
        probabilities=response_data.get("probabilities", {}),
        top_features=response_data.get("top_features", []),
        confidence=response_data.get("confidence", 0.3 if not success else 0.8)
    )


def process_anomaly_output(
    response_data: Dict[str, Any],
    success: bool
) -> MLAnomalyOutput:
    """
    Process anomaly detection service response into structured output.
    
    Args:
        response_data: Raw response from anomaly service
        success: Whether the service call was successful
        
    Returns:
        MLAnomalyOutput: Structured anomaly output
    """
    return MLAnomalyOutput(
        anomaly_score=response_data.get("anomaly_score", 0.5),
        anomaly_flags=response_data.get("anomaly_flags", []),
        recommended_action=response_data.get("recommended_action", "standard_processing"),
        confidence=response_data.get("confidence", 0.3 if not success else 0.8)
    )


def process_eta_output(
    response_data: Dict[str, Any],
    success: bool
) -> MLETAOutput:
    """
    Process ETA prediction service response into structured output.
    
    Args:
        response_data: Raw response from ETA service
        success: Whether the service call was successful
        
    Returns:
        MLETAOutput: Structured ETA output
    """
    return MLETAOutput(
        eta_minutes=response_data.get("eta_minutes", 240),
        p50=response_data.get("p50", 240),
        p90=response_data.get("p90"),
        confidence=response_data.get("confidence", 0.3 if not success else 0.8)
    )


def extract_model_versions(
    classification_response: Dict[str, Any],
    anomaly_response: Dict[str, Any],
    eta_response: Dict[str, Any]
) -> MLModelVersions:
    """
    Extract model versions from ML service responses.
    
    Args:
        classification_response: Classification service response
        anomaly_response: Anomaly service response
        eta_response: ETA service response
        
    Returns:
        MLModelVersions: Model version information
    """
    return MLModelVersions(
        classify_version=classification_response.get("model_version"),
        anomaly_version=anomaly_response.get("model_version"),
        eta_version=eta_response.get("model_version")
    )


# ============================================================================
# Drift Monitoring and Quality Checks
# ============================================================================

def detect_feature_drift(features: Dict[str, Any]) -> List[str]:
    """
    Detect potential feature drift or data quality issues.
    
    Args:
        features: Feature vector
        
    Returns:
        List[str]: List of drift warnings
    """
    warnings = []
    
    # Check for extreme values
    if features.get("days_since_service", 0) > 365:
        warnings.append("Service date is more than 1 year old")
    
    if features.get("hours_to_sla", 0) < 0:
        warnings.append("SLA target is in the past")
    
    if features.get("attachment_total_size", 0) > 100 * 1024 * 1024:  # 100MB
        warnings.append("Unusually large attachment size")
    
    if features.get("attachment_count", 0) > 20:
        warnings.append("Unusually high attachment count")
    
    # Check for missing critical features
    critical_features = ["insurer_id", "service_code", "provider_id"]
    for feature in critical_features:
        if not features.get(feature):
            warnings.append(f"Missing critical feature: {feature}")
    
    return warnings


def validate_ml_outputs(
    classification: MLClassificationOutput,
    anomaly: MLAnomalyOutput,
    eta: MLETAOutput
) -> List[str]:
    """
    Validate ML outputs for consistency and reasonableness.
    
    Args:
        classification: Classification output
        anomaly: Anomaly output
        eta: ETA output
        
    Returns:
        List[str]: List of validation warnings
    """
    warnings = []
    
    # Check classification consistency
    if classification.confidence < 0.5 and classification.route == "fraud":
        warnings.append("Low confidence fraud classification")
    
    # Check anomaly consistency
    if anomaly.anomaly_score > 0.8 and not anomaly.anomaly_flags:
        warnings.append("High anomaly score without specific flags")
    
    # Check ETA reasonableness
    if eta.eta_minutes < 5:
        warnings.append("Unreasonably short ETA prediction")
    
    if eta.eta_minutes > 2880:  # 48 hours
        warnings.append("Unreasonably long ETA prediction")
    
    # Check cross-model consistency
    if (classification.route == "fraud" and 
        anomaly.anomaly_score < 0.3):
        warnings.append("Fraud classification inconsistent with low anomaly score")
    
    return warnings


# ============================================================================
# Main Routing Node Function
# ============================================================================

async def routing_node(state: PolicyValidationState) -> PolicyValidationState:
    """
    Intelligent Routing Node with ML Integration.
    
    Integrates with ML services for:
    - Classification (UC-OP-11): Request type, policy candidates, routing
    - Anomaly Detection (UC-OP-12): Anomaly scoring and flag detection
    - ETA Prediction (UC-OP-13): Processing time estimation
    
    Implements feature engineering, fallback logic, and model version tracking.
    
    Args:
        state: Current PolicyValidationState
        
    Returns:
        PolicyValidationState: Updated state with ML outputs
    """
    start_time = datetime.utcnow()
    node_name = "intelligent_routing"
    
    # Update audit trail - node started
    state = update_state_audit(
        state,
        node_name=node_name,
        status="started",
        input_hash=str(hash(str(state["case"])))
    )
    
    try:
        # Step 1: Extract and engineer features
        logger.info(f"Extracting features for case {state['case'].case_id}")
        features = extract_case_features(state)
        aggregates = create_aggregated_features(features)
        
        # Step 2: Check for feature drift
        drift_warnings = detect_feature_drift(features)
        if drift_warnings:
            logger.warning(f"Feature drift detected: {drift_warnings}")
        
        # Step 3: Call ML services concurrently
        logger.info("Calling ML services")
        async with MLServiceClient() as ml_client:
            # Execute all ML service calls concurrently
            classification_task = ml_client.call_classification_service(features)
            anomaly_task = ml_client.call_anomaly_service(features, aggregates)
            eta_task = ml_client.call_eta_service(features)
            
            # Wait for all services to complete
            (classification_response, classification_success), \
            (anomaly_response, anomaly_success), \
            (eta_response, eta_success) = await asyncio.gather(
                classification_task,
                anomaly_task,
                eta_task,
                return_exceptions=True
            )
            
            # Handle any exceptions from service calls
            if isinstance(classification_response, Exception):
                logger.error(f"Classification service exception: {classification_response}")
                classification_response, classification_success = FALLBACK_VALUES["classification"], False
            
            if isinstance(anomaly_response, Exception):
                logger.error(f"Anomaly service exception: {anomaly_response}")
                anomaly_response, anomaly_success = FALLBACK_VALUES["anomaly"], False
            
            if isinstance(eta_response, Exception):
                logger.error(f"ETA service exception: {eta_response}")
                eta_response, eta_success = FALLBACK_VALUES["eta"], False
            
            # Get service health status
            service_health = ml_client.get_service_health()
        
        # Step 4: Process ML outputs
        classification_output = process_classification_output(classification_response, classification_success)
        anomaly_output = process_anomaly_output(anomaly_response, anomaly_success)
        eta_output = process_eta_output(eta_response, eta_success)
        
        # Step 5: Extract model versions
        model_versions = extract_model_versions(
            classification_response,
            anomaly_response,
            eta_response
        )
        
        # Step 6: Validate ML outputs
        validation_warnings = validate_ml_outputs(
            classification_output,
            anomaly_output,
            eta_output
        )
        
        if validation_warnings:
            logger.warning(f"ML output validation warnings: {validation_warnings}")
        
        # Step 7: Create ML outputs container
        ml_outputs = MLOutputs(
            classification=classification_output,
            anomaly=anomaly_output,
            eta=eta_output,
            model_versions=model_versions,
            last_updated=datetime.utcnow()
        )
        
        # Step 8: Update state with ML outputs
        state["ml"] = ml_outputs
        
        # Step 9: Log ML insights for audit trail
        ml_summary = {
            "classification_route": classification_output.route,
            "classification_confidence": classification_output.confidence,
            "anomaly_score": anomaly_output.anomaly_score,
            "anomaly_flags": anomaly_output.anomaly_flags,
            "eta_minutes": eta_output.eta_minutes,
            "service_health": service_health,
            "drift_warnings": drift_warnings,
            "validation_warnings": validation_warnings
        }
        
        # Step 10: Update audit trail with execution details
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        state = update_state_audit(
            state,
            node_name=node_name,
            status="completed",
            input_hash=str(hash(str(features))),
            output_hash=str(hash(str(ml_outputs.dict()))),
            execution_time_ms=execution_time_ms
        )
        
        # Add detailed execution log
        state["audit"].data_lineage[node_name] = {
            "features_extracted": len(features),
            "aggregates_computed": len(aggregates),
            "ml_services_called": 3,
            "successful_calls": sum([classification_success, anomaly_success, eta_success]),
            "model_versions": model_versions.dict(),
            "execution_summary": ml_summary
        }
        
        logger.info(f"Intelligent routing completed for case {state['case'].case_id}")
        logger.info(f"Route: {classification_output.route}, Anomaly: {anomaly_output.anomaly_score:.3f}, ETA: {eta_output.eta_minutes}min")
        
        return state
        
    except Exception as e:
        # Update audit trail - node failed
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        state = update_state_audit(
            state,
            node_name=node_name,
            status="failed",
            input_hash=str(hash(str(state["case"]))),
            error_message=str(e),
            execution_time_ms=execution_time_ms
        )
        
        logger.error(f"Intelligent routing failed for case {state['case'].case_id}: {str(e)}")
        
        # Create fallback ML outputs to allow workflow to continue
        fallback_ml_outputs = MLOutputs(
            classification=MLClassificationOutput(**FALLBACK_VALUES["classification"]),
            anomaly=MLAnomalyOutput(**FALLBACK_VALUES["anomaly"]),
            eta=MLETAOutput(**FALLBACK_VALUES["eta"]),
            model_versions=MLModelVersions(),
            last_updated=datetime.utcnow()
        )
        
        state["ml"] = fallback_ml_outputs
        
        # Log fallback usage
        state["audit"].compliance_flags.append(f"ML_FALLBACK_USED_{node_name}")
        
        raise


# ============================================================================
# Utility Functions for Testing and Monitoring
# ============================================================================

def get_ml_service_status() -> Dict[str, Any]:
    """
    Get current ML service status and health metrics.
    
    Returns:
        Dict[str, Any]: Service status information
    """
    return {
        "services": list(ML_SERVICE_CONFIG.keys()),
        "endpoints": {k: v["endpoint"] for k, v in ML_SERVICE_CONFIG.items()},
        "timeouts": {k: v["timeout"] for k, v in ML_SERVICE_CONFIG.items()},
        "fallback_enabled": {k: v["fallback_enabled"] for k, v in ML_SERVICE_CONFIG.items()}
    }


def create_mock_ml_responses(case_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Create mock ML service responses for testing.
    
    Args:
        case_id: Case identifier
        
    Returns:
        Tuple[Dict, Dict, Dict]: (Classification, Anomaly, ETA) responses
    """
    # Deterministic mock responses based on case_id hash
    case_hash = hash(case_id)
    
    classification_response = {
        "request_type": "STANDARD" if case_hash % 3 == 0 else "SPECIALIST",
        "candidate_policy_ids": [f"POL_{(case_hash % 100):03d}", f"POL_{((case_hash + 1) % 100):03d}"],
        "route": "standard" if case_hash % 4 != 0 else "specialist",
        "risk_prior": (case_hash % 100) / 100,
        "probabilities": {
            "standard": 0.6 + (case_hash % 20) / 100,
            "specialist": 0.3 + (case_hash % 15) / 100,
            "fraud": 0.1 + (case_hash % 10) / 100
        },
        "top_features": ["service_code", "provider_id", "attachment_count"],
        "confidence": 0.7 + (case_hash % 30) / 100,
        "model_version": "v1.2.3"
    }
    
    anomaly_response = {
        "anomaly_score": (case_hash % 80) / 100,
        "anomaly_flags": ["unusual_timing"] if case_hash % 5 == 0 else [],
        "recommended_action": "investigate" if case_hash % 7 == 0 else "standard_processing",
        "confidence": 0.8 + (case_hash % 20) / 100,
        "model_version": "v2.1.0"
    }
    
    eta_response = {
        "eta_minutes": 60 + (case_hash % 300),
        "p50": 120 + (case_hash % 200),
        "p90": 240 + (case_hash % 400),
        "confidence": 0.75 + (case_hash % 25) / 100,
        "model_version": "v1.5.2"
    }
    
    return classification_response, anomaly_response, eta_response


async def test_ml_service_connectivity() -> Dict[str, bool]:
    """
    Test connectivity to all ML services.
    
    Returns:
        Dict[str, bool]: Service connectivity status
    """
    results = {}
    
    async with MLServiceClient() as client:
        for service_name in ML_SERVICE_CONFIG.keys():
            try:
                # Simple health check (would be actual health endpoint in production)
                config = ML_SERVICE_CONFIG[service_name]
                response = await client.client.get(
                    f"{config['endpoint']}/health",
                    timeout=5.0
                )
                results[service_name] = response.status_code == 200
            except Exception:
                results[service_name] = False
    
    return results
