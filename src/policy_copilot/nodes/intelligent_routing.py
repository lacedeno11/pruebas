"""
Intelligent Routing Node

This module implements the Intelligent Routing Node for the Policy Validation Copilot system,
integrating all ML services for classification, anomaly detection, and ETA prediction with
routing decision logic and fallback mechanisms.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass
from enum import Enum

from ..state import PolicyValidationState
from ..ml_services import (
    MLClassificationService, MLAnomalyService, MLETAService,
    MLClassificationRequest, MLAnomalyRequest, MLETARequest,
    get_classification_service, get_anomaly_service, get_eta_service
)
from ..database import (
    MLPredictionRepository, AuditLogRepository, get_repository_factory
)
from ..guardrails import create_security_context

logger = logging.getLogger(__name__)


class RoutingDecision(str, Enum):
    """Routing decision outcomes"""
    AUTO_PROCESS = "AUTO_PROCESS"
    PRIORITY_REVIEW = "PRIORITY_REVIEW"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    FRAUD_INVESTIGATION = "FRAUD_INVESTIGATION"
    EMERGENCY_FAST_TRACK = "EMERGENCY_FAST_TRACK"


class ProcessingQueue(str, Enum):
    """Processing queue assignments"""
    EMERGENCY = "EMERGENCY"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    STANDARD = "STANDARD"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FRAUD_INVESTIGATION = "FRAUD_INVESTIGATION"
    EXPERT_REVIEW = "EXPERT_REVIEW"


@dataclass
class MLPredictions:
    """Container for all ML service predictions"""
    classification: Optional[Dict[str, Any]] = None
    anomaly: Optional[Dict[str, Any]] = None
    eta: Optional[Dict[str, Any]] = None
    processing_time_ms: int = 0
    errors: List[str] = None


@dataclass
class RoutingResult:
    """Result of intelligent routing analysis"""
    decision: RoutingDecision
    queue: ProcessingQueue
    priority: str
    confidence: float
    reasoning: str
    next_actions: List[str]
    estimated_processing_time: int
    ml_predictions: MLPredictions
    fallback_used: bool = False


class IntelligentRoutingNode:
    """
    Intelligent Routing Node integrating all ML services.
    
    Orchestrates classification, anomaly detection, and ETA prediction
    to make intelligent routing decisions for case processing.
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.repo_factory = get_repository_factory()
        
        # Initialize ML services
        self.classification_service = get_classification_service(use_mock)
        self.anomaly_service = get_anomaly_service(use_mock)
        self.eta_service = get_eta_service(use_mock)
        
        # Routing configuration
        self.routing_config = self._initialize_routing_config()
        
        # Fallback mechanisms
        self.fallback_enabled = True
        self.max_ml_timeout = 30  # seconds
        self.max_concurrent_ml_calls = 3
        
        # Statistics
        self.routing_stats = {
            "total_routed": 0,
            "ml_service_calls": 0,
            "fallback_used": 0,
            "routing_decisions": {decision.value: 0 for decision in RoutingDecision},
            "queue_assignments": {queue.value: 0 for queue in ProcessingQueue}
        }
    
    def _initialize_routing_config(self) -> Dict[str, Any]:
        """Initialize routing configuration and thresholds"""
        return {
            # Classification-based routing
            "request_type_routing": {
                "EMERGENCY_CARE": {
                    "decision": RoutingDecision.EMERGENCY_FAST_TRACK,
                    "queue": ProcessingQueue.EMERGENCY,
                    "priority": "CRITICAL"
                },
                "SURGERY": {
                    "decision": RoutingDecision.MANUAL_REVIEW,
                    "queue": ProcessingQueue.MANUAL_REVIEW,
                    "priority": "HIGH"
                },
                "HIGH_COST_PROCEDURE": {
                    "decision": RoutingDecision.EXPERT_REVIEW,
                    "queue": ProcessingQueue.EXPERT_REVIEW,
                    "priority": "HIGH"
                },
                "EXPERIMENTAL_TREATMENT": {
                    "decision": RoutingDecision.EXPERT_REVIEW,
                    "queue": ProcessingQueue.EXPERT_REVIEW,
                    "priority": "HIGH"
                },
                "MEDICAL_CONSULTATION": {
                    "decision": RoutingDecision.AUTO_PROCESS,
                    "queue": ProcessingQueue.STANDARD,
                    "priority": "MEDIUM"
                },
                "DIAGNOSTIC_TEST": {
                    "decision": RoutingDecision.AUTO_PROCESS,
                    "queue": ProcessingQueue.STANDARD,
                    "priority": "MEDIUM"
                }
            },
            
            # Anomaly-based routing thresholds
            "anomaly_thresholds": {
                "fraud_investigation": 0.8,
                "manual_review": 0.6,
                "priority_review": 0.4,
                "auto_process": 0.2
            },
            
            # Risk-based routing
            "risk_thresholds": {
                "high_risk": 0.7,
                "medium_risk": 0.4,
                "low_risk": 0.2
            },
            
            # Amount-based routing
            "amount_thresholds": {
                "expert_review": 50000.0,
                "manual_review": 10000.0,
                "priority_review": 5000.0
            },
            
            # ETA-based priority adjustment
            "eta_priority_adjustment": {
                "critical_threshold_hours": 2,
                "high_threshold_hours": 8,
                "medium_threshold_hours": 24
            }
        }
    
    async def route_case(self, state: PolicyValidationState) -> PolicyValidationState:
        """
        Main entry point for intelligent routing.
        
        Args:
            state: Current policy validation state
            
        Returns:
            Updated state with ML predictions and routing decisions
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract case information
            case = state["case"]
            case_id = case["case_id"]
            
            logger.info(f"Starting intelligent routing for case {case_id}")
            
            # Execute all ML services concurrently
            ml_predictions = await self._execute_ml_services(case)
            
            # Make routing decision based on ML predictions
            routing_result = await self._make_routing_decision(case, ml_predictions)
            
            # Update case with routing information
            await self._update_case_routing(state, routing_result)
            
            # Update state with ML predictions
            state["ml"] = {
                "classification": ml_predictions.classification,
                "anomaly": ml_predictions.anomaly,
                "eta": ml_predictions.eta,
                "processing_time_ms": ml_predictions.processing_time_ms,
                "errors": ml_predictions.errors or [],
                "model_versions": self._extract_model_versions(ml_predictions)
            }
            
            # Persist ML predictions
            await self._persist_ml_predictions(case_id, ml_predictions)
            
            # Log routing audit
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._log_routing_audit(case_id, routing_result, processing_time)
            
            # Update statistics
            await self._update_routing_statistics(routing_result)
            
            logger.info(
                f"Intelligent routing completed for case {case_id}: "
                f"decision={routing_result.decision.value}, "
                f"queue={routing_result.queue.value}, "
                f"confidence={routing_result.confidence:.3f}, "
                f"eta={routing_result.estimated_processing_time}min"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Intelligent routing failed for case {case.get('case_id', 'unknown')}: {e}")
            
            # Apply fallback routing
            fallback_result = await self._apply_fallback_routing(case)
            await self._update_case_routing(state, fallback_result)
            
            # Update state with error information
            state["ml"] = {
                "classification": None,
                "anomaly": None,
                "eta": None,
                "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "errors": [str(e)],
                "model_versions": {},
                "fallback_used": True
            }
            
            raise
    
    async def _execute_ml_services(self, case: Dict[str, Any]) -> MLPredictions:
        """Execute all ML services concurrently"""
        
        start_time = datetime.utcnow()
        errors = []
        
        # Prepare feature vectors for ML services
        features = await self._extract_features(case)
        aggregates = await self._extract_aggregates(case)
        
        # Create ML service requests
        classification_request = MLClassificationRequest(
            case_id=case["case_id"],
            features=features
        )
        
        anomaly_request = MLAnomalyRequest(
            case_id=case["case_id"],
            features=features,
            aggregates=aggregates
        )
        
        eta_request = MLETARequest(
            case_id=case["case_id"],
            features=features
        )
        
        # Execute ML services concurrently with timeout
        tasks = [
            asyncio.create_task(self._call_classification_service(classification_request)),
            asyncio.create_task(self._call_anomaly_service(anomaly_request)),
            asyncio.create_task(self._call_eta_service(eta_request))
        ]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.max_ml_timeout
            )
            
            classification_result, anomaly_result, eta_result = results
            
            # Process results and handle exceptions
            classification_data = None
            if isinstance(classification_result, Exception):
                errors.append(f"Classification service error: {classification_result}")
            else:
                classification_data = {
                    "request_type": classification_result.request_type,
                    "candidate_policy_ids": classification_result.candidate_policy_ids,
                    "route": classification_result.route,
                    "risk_prior": classification_result.risk_prior,
                    "probabilities": classification_result.probabilities,
                    "top_features": classification_result.top_features,
                    "model_version": classification_result.model_version
                }
            
            anomaly_data = None
            if isinstance(anomaly_result, Exception):
                errors.append(f"Anomaly service error: {anomaly_result}")
            else:
                anomaly_data = {
                    "anomaly_score": anomaly_result.anomaly_score,
                    "anomaly_flags": anomaly_result.anomaly_flags,
                    "recommended_action": anomaly_result.recommended_action,
                    "model_version": anomaly_result.model_version
                }
            
            eta_data = None
            if isinstance(eta_result, Exception):
                errors.append(f"ETA service error: {eta_result}")
            else:
                eta_data = {
                    "eta_minutes": eta_result.eta_minutes,
                    "p50": eta_result.p50,
                    "p90": eta_result.p90,
                    "model_version": eta_result.model_version
                }
            
        except asyncio.TimeoutError:
            errors.append(f"ML services timeout after {self.max_ml_timeout} seconds")
            classification_data = anomaly_data = eta_data = None
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return MLPredictions(
            classification=classification_data,
            anomaly=anomaly_data,
            eta=eta_data,
            processing_time_ms=int(processing_time),
            errors=errors if errors else None
        )
    
    async def _extract_features(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for ML services"""
        
        features = {
            # Basic case information
            "insurer_id": case.get("insurer_id"),
            "plan_id": case.get("plan_id"),
            "service_code": case.get("service_code"),
            "service_amount": case.get("service_amount", 0.0),
            "provider_id": case.get("provider_id"),
            
            # Service details
            "service_urgency": case.get("service_urgency", "NORMAL"),
            "diagnosis_codes": case.get("diagnosis_codes", []),
            "procedure_codes": case.get("procedure_codes", []),
            
            # Customer information
            "customer_id": case.get("customer_id"),
            "priority": case.get("priority", "MEDIUM"),
            
            # Temporal features
            "service_date": case.get("service_date"),
            "hour_of_day": case.get("service_date").hour if case.get("service_date") else 12,
            "day_of_week": case.get("service_date").weekday() if case.get("service_date") else 1,
            
            # Case metadata
            "attachment_count": len(case.get("attachments", [])),
            "queue": case.get("queue", "STANDARD"),
            
            # Derived features
            "is_emergency": "EMERGENCY" in case.get("service_code", "").upper(),
            "is_high_value": case.get("service_amount", 0.0) > 10000,
            "is_surgery": "SURGERY" in case.get("service_code", "").upper(),
            "has_multiple_diagnoses": len(case.get("diagnosis_codes", [])) > 1,
            "has_multiple_procedures": len(case.get("procedure_codes", [])) > 1
        }
        
        return features
    
    async def _extract_aggregates(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Extract aggregates for anomaly detection"""
        
        # In production, would query database for historical data
        # For now, provide mock aggregates
        
        customer_id = case.get("customer_id")
        provider_id = case.get("provider_id")
        service_code = case.get("service_code")
        
        aggregates = {
            "customer_30d": {
                "claim_count": 2,
                "total_amount": 500.0,
                "avg_amount": 250.0,
                "service_types": ["CONSULTATION", "DIAGNOSTIC"]
            },
            "customer_12m": {
                "claim_count": 8,
                "total_amount": 3200.0,
                "avg_amount": 400.0,
                "service_types": ["CONSULTATION", "DIAGNOSTIC", "THERAPY"]
            },
            "provider_30d": {
                "claim_count": 150,
                "total_amount": 75000.0,
                "avg_amount": 500.0,
                "unique_customers": 120
            },
            "service_code_30d": {
                "claim_count": 25,
                "total_amount": 12500.0,
                "avg_amount": 500.0,
                "unique_providers": 8
            }
        }
        
        return aggregates
    
    async def _call_classification_service(self, request: MLClassificationRequest):
        """Call classification service with error handling"""
        try:
            return await self.classification_service.predict(request)
        except Exception as e:
            logger.error(f"Classification service call failed: {e}")
            raise
    
    async def _call_anomaly_service(self, request: MLAnomalyRequest):
        """Call anomaly service with error handling"""
        try:
            return await self.anomaly_service.predict(request)
        except Exception as e:
            logger.error(f"Anomaly service call failed: {e}")
            raise
    
    async def _call_eta_service(self, request: MLETARequest):
        """Call ETA service with error handling"""
        try:
            return await self.eta_service.predict(request)
        except Exception as e:
            logger.error(f"ETA service call failed: {e}")
            raise
    
    async def _make_routing_decision(
        self, 
        case: Dict[str, Any], 
        ml_predictions: MLPredictions
    ) -> RoutingResult:
        """Make routing decision based on ML predictions and business rules"""
        
        # Initialize with default routing
        decision = RoutingDecision.AUTO_PROCESS
        queue = ProcessingQueue.STANDARD
        priority = case.get("priority", "MEDIUM")
        confidence = 0.5
        reasoning = "Default routing"
        next_actions = ["PROCEED_TO_POLICY_RETRIEVAL"]
        estimated_time = 720  # 12 hours default
        
        # Apply classification-based routing
        if ml_predictions.classification:
            classification = ml_predictions.classification
            request_type = classification.get("request_type", "UNKNOWN")
            
            if request_type in self.routing_config["request_type_routing"]:
                routing_rule = self.routing_config["request_type_routing"][request_type]
                decision = RoutingDecision(routing_rule["decision"])
                queue = ProcessingQueue(routing_rule["queue"])
                priority = routing_rule["priority"]
                confidence = max(classification.get("probabilities", {}).values()) if classification.get("probabilities") else 0.5
                reasoning = f"Classification-based routing: {request_type}"
        
        # Apply anomaly-based routing overrides
        if ml_predictions.anomaly:
            anomaly = ml_predictions.anomaly
            anomaly_score = anomaly.get("anomaly_score", 0.0)
            
            if anomaly_score >= self.routing_config["anomaly_thresholds"]["fraud_investigation"]:
                decision = RoutingDecision.FRAUD_INVESTIGATION
                queue = ProcessingQueue.FRAUD_INVESTIGATION
                priority = "CRITICAL"
                reasoning = f"High anomaly score detected: {anomaly_score:.3f}"
                next_actions = ["FRAUD_INVESTIGATION", "MANUAL_REVIEW"]
                
            elif anomaly_score >= self.routing_config["anomaly_thresholds"]["manual_review"]:
                if decision == RoutingDecision.AUTO_PROCESS:  # Don't override emergency routing
                    decision = RoutingDecision.MANUAL_REVIEW
                    queue = ProcessingQueue.MANUAL_REVIEW
                    priority = "HIGH"
                    reasoning = f"Medium anomaly score detected: {anomaly_score:.3f}"
                    next_actions = ["MANUAL_REVIEW"]
        
        # Apply amount-based routing overrides
        service_amount = case.get("service_amount", 0.0)
        if service_amount >= self.routing_config["amount_thresholds"]["expert_review"]:
            if decision not in [RoutingDecision.FRAUD_INVESTIGATION, RoutingDecision.EMERGENCY_FAST_TRACK]:
                decision = RoutingDecision.EXPERT_REVIEW
                queue = ProcessingQueue.EXPERT_REVIEW
                priority = "HIGH"
                reasoning = f"High-value case: ${service_amount:,.2f}"
                next_actions = ["EXPERT_REVIEW"]
                
        elif service_amount >= self.routing_config["amount_thresholds"]["manual_review"]:
            if decision == RoutingDecision.AUTO_PROCESS:
                decision = RoutingDecision.MANUAL_REVIEW
                queue = ProcessingQueue.MANUAL_REVIEW
                reasoning = f"Medium-value case: ${service_amount:,.2f}"
        
        # Apply ETA-based priority adjustments
        if ml_predictions.eta:
            eta_data = ml_predictions.eta
            estimated_time = eta_data.get("eta_minutes", 720)
            
            eta_hours = estimated_time / 60
            if eta_hours <= self.routing_config["eta_priority_adjustment"]["critical_threshold_hours"]:
                if priority not in ["CRITICAL"]:
                    priority = "HIGH"
            elif eta_hours <= self.routing_config["eta_priority_adjustment"]["high_threshold_hours"]:
                if priority == "LOW":
                    priority = "MEDIUM"
        
        # Apply emergency overrides
        if case.get("priority") == "CRITICAL" or "EMERGENCY" in case.get("service_code", "").upper():
            decision = RoutingDecision.EMERGENCY_FAST_TRACK
            queue = ProcessingQueue.EMERGENCY
            priority = "CRITICAL"
            reasoning = "Emergency case override"
            next_actions = ["EMERGENCY_PROCESSING"]
            estimated_time = min(estimated_time, 240)  # Max 4 hours for emergency
        
        return RoutingResult(
            decision=decision,
            queue=queue,
            priority=priority,
            confidence=confidence,
            reasoning=reasoning,
            next_actions=next_actions,
            estimated_processing_time=estimated_time,
            ml_predictions=ml_predictions,
            fallback_used=False
        )
    
    async def _apply_fallback_routing(self, case: Dict[str, Any]) -> RoutingResult:
        """Apply fallback routing when ML services fail"""
        
        # Rule-based fallback routing
        service_code = case.get("service_code", "").upper()
        service_amount = case.get("service_amount", 0.0)
        priority = case.get("priority", "MEDIUM")
        
        # Emergency fallback
        if priority == "CRITICAL" or "EMERGENCY" in service_code:
            decision = RoutingDecision.EMERGENCY_FAST_TRACK
            queue = ProcessingQueue.EMERGENCY
            priority = "CRITICAL"
            reasoning = "Emergency fallback routing"
            estimated_time = 240
            
        # High-value fallback
        elif service_amount > 50000:
            decision = RoutingDecision.EXPERT_REVIEW
            queue = ProcessingQueue.EXPERT_REVIEW
            priority = "HIGH"
            reasoning = "High-value fallback routing"
            estimated_time = 480
            
        # Surgery fallback
        elif "SURGERY" in service_code:
            decision = RoutingDecision.MANUAL_REVIEW
            queue = ProcessingQueue.MANUAL_REVIEW
            priority = "HIGH"
            reasoning = "Surgery fallback routing"
            estimated_time = 720
            
        # Default fallback
        else:
            decision = RoutingDecision.MANUAL_REVIEW
            queue = ProcessingQueue.MANUAL_REVIEW
            priority = "MEDIUM"
            reasoning = "Default fallback routing due to ML service failure"
            estimated_time = 1440
        
        return RoutingResult(
            decision=decision,
            queue=queue,
            priority=priority,
            confidence=0.3,  # Low confidence for fallback
            reasoning=reasoning,
            next_actions=["MANUAL_REVIEW"],
            estimated_processing_time=estimated_time,
            ml_predictions=MLPredictions(),
            fallback_used=True
        )
    
    async def _update_case_routing(
        self, 
        state: PolicyValidationState, 
        routing_result: RoutingResult
    ) -> None:
        """Update case with routing information"""
        
        case = state["case"]
        
        # Update case routing information
        case["queue"] = routing_result.queue.value
        case["priority"] = routing_result.priority
        case["routing_decision"] = routing_result.decision.value
        case["estimated_processing_time"] = routing_result.estimated_processing_time
        case["routing_confidence"] = routing_result.confidence
        case["routing_reasoning"] = routing_result.reasoning
        case["next_actions"] = routing_result.next_actions
        
        # Update metadata
        if "metadata" not in case:
            case["metadata"] = {}
        
        case["metadata"]["routing"] = {
            "decision": routing_result.decision.value,
            "queue": routing_result.queue.value,
            "confidence": routing_result.confidence,
            "reasoning": routing_result.reasoning,
            "fallback_used": routing_result.fallback_used,
            "routed_at": datetime.utcnow()
        }
    
    def _extract_model_versions(self, ml_predictions: MLPredictions) -> Dict[str, str]:
        """Extract model versions from ML predictions"""
        
        versions = {}
        
        if ml_predictions.classification:
            versions["classification"] = ml_predictions.classification.get("model_version", "unknown")
        
        if ml_predictions.anomaly:
            versions["anomaly"] = ml_predictions.anomaly.get("model_version", "unknown")
        
        if ml_predictions.eta:
            versions["eta"] = ml_predictions.eta.get("model_version", "unknown")
        
        return versions
    
    async def _persist_ml_predictions(
        self, 
        case_id: str, 
        ml_predictions: MLPredictions
    ) -> None:
        """Persist ML predictions to database"""
        
        ml_repo = self.repo_factory.ml_prediction_repository()
        
        # Persist classification prediction
        if ml_predictions.classification:
            classification_data = {
                "case_id": case_id,
                "service_name": "classification",
                "model_version": ml_predictions.classification.get("model_version", "unknown"),
                "prediction_type": "CLASSIFICATION",
                "input_features": {},  # Would include input features
                "prediction_result": ml_predictions.classification,
                "processing_time_ms": ml_predictions.processing_time_ms // 3,
                "confidence_score": max(ml_predictions.classification.get("probabilities", {}).values()) if ml_predictions.classification.get("probabilities") else None
            }
            
            try:
                ml_repo.create(**classification_data)
            except Exception as e:
                logger.error(f"Failed to persist classification prediction: {e}")
        
        # Persist anomaly prediction
        if ml_predictions.anomaly:
            anomaly_data = {
                "case_id": case_id,
                "service_name": "anomaly",
                "model_version": ml_predictions.anomaly.get("model_version", "unknown"),
                "prediction_type": "ANOMALY",
                "input_features": {},  # Would include input features
                "prediction_result": ml_predictions.anomaly,
                "processing_time_ms": ml_predictions.processing_time_ms // 3,
                "confidence_score": 1.0 - ml_predictions.anomaly.get("anomaly_score", 0.0)
            }
            
            try:
                ml_repo.create(**anomaly_data)
            except Exception as e:
                logger.error(f"Failed to persist anomaly prediction: {e}")
        
        # Persist ETA prediction
        if ml_predictions.eta:
            eta_data = {
                "case_id": case_id,
                "service_name": "eta",
                "model_version": ml_predictions.eta.get("model_version", "unknown"),
                "prediction_type": "ETA",
                "input_features": {},  # Would include input features
                "prediction_result": ml_predictions.eta,
                "processing_time_ms": ml_predictions.processing_time_ms // 3,
                "confidence_score": 0.8  # Default confidence for ETA
            }
            
            try:
                ml_repo.create(**eta_data)
            except Exception as e:
                logger.error(f"Failed to persist ETA prediction: {e}")
    
    async def _log_routing_audit(
        self,
        case_id: str,
        routing_result: RoutingResult,
        processing_time_ms: int
    ) -> None:
        """Log routing audit trail"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        audit_data = {
            "case_id": case_id,
            "event_type": "INTELLIGENT_ROUTING",
            "event_category": "SYSTEM",
            "event_description": f"Intelligent routing completed: {routing_result.decision.value}",
            "user_id": "SYSTEM",
            "event_data": {
                "routing_decision": routing_result.decision.value,
                "queue_assignment": routing_result.queue.value,
                "priority": routing_result.priority,
                "confidence": routing_result.confidence,
                "reasoning": routing_result.reasoning,
                "estimated_time_minutes": routing_result.estimated_processing_time,
                "fallback_used": routing_result.fallback_used,
                "ml_services_used": {
                    "classification": routing_result.ml_predictions.classification is not None,
                    "anomaly": routing_result.ml_predictions.anomaly is not None,
                    "eta": routing_result.ml_predictions.eta is not None
                },
                "ml_errors": routing_result.ml_predictions.errors
            },
            "processing_time_ms": processing_time_ms
        }
        
        try:
            audit_repo.create(**audit_data)
        except Exception as e:
            logger.error(f"Failed to log routing audit: {e}")
    
    async def _update_routing_statistics(self, routing_result: RoutingResult) -> None:
        """Update routing statistics"""
        
        self.routing_stats["total_routed"] += 1
        self.routing_stats["ml_service_calls"] += 3  # Always attempt all 3 services
        
        if routing_result.fallback_used:
            self.routing_stats["fallback_used"] += 1
        
        self.routing_stats["routing_decisions"][routing_result.decision.value] += 1
        self.routing_stats["queue_assignments"][routing_result.queue.value] += 1
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics"""
        stats = self.routing_stats.copy()
        
        if stats["total_routed"] > 0:
            stats["fallback_rate"] = stats["fallback_used"] / stats["total_routed"]
            stats["ml_success_rate"] = 1 - stats["fallback_rate"]
        
        return stats
    
    def update_routing_config(self, new_config: Dict[str, Any]) -> None:
        """Update routing configuration"""
        self.routing_config.update(new_config)
        logger.info("Routing configuration updated")


# Factory function for creating intelligent routing node
def create_intelligent_routing_node(use_mock: bool = False) -> IntelligentRoutingNode:
    """
    Factory function to create intelligent routing node.
    
    Args:
        use_mock: Whether to use mock ML services
        
    Returns:
        Configured intelligent routing node
    """
    return IntelligentRoutingNode(use_mock=use_mock)
