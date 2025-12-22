"""
Decision Orchestrator Agent (UC-OP-08)

This module implements the Decision Orchestrator Agent for the Policy Validation Copilot system,
providing confidence/risk calculation, threshold-based decision making, HITL escalation logic,
auto-closure conditions, and decision audit logging.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
import json
from dataclasses import dataclass
from enum import Enum

from ..state import PolicyValidationState, Decision, DecisionStatus, ChecklistOutcome
from ..database import (
    DecisionRepository, AuditLogRepository, SystemConfigurationRepository,
    get_repository_factory
)
from ..guardrails import create_security_context, evaluate_payload_security

logger = logging.getLogger(__name__)


class DecisionConfidence(str, Enum):
    """Decision confidence levels"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class DecisionRisk(str, Enum):
    """Decision risk levels"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class HITLReason(str, Enum):
    """Reasons for HITL escalation"""
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    HIGH_RISK = "HIGH_RISK"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    GUARDRAIL_VIOLATION = "GUARDRAIL_VIOLATION"
    COMPLEX_CASE = "COMPLEX_CASE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    REGULATORY_COMPLIANCE = "REGULATORY_COMPLIANCE"


@dataclass
class DecisionThresholds:
    """Decision-making thresholds configuration"""
    # Confidence thresholds
    min_confidence_auto_approve: float = 0.8
    min_confidence_auto_reject: float = 0.7
    min_confidence_observe: float = 0.6
    
    # Risk thresholds
    max_risk_auto_approve: float = 0.3
    max_risk_auto_reject: float = 0.8
    max_risk_observe: float = 0.6
    
    # Coverage thresholds
    min_coverage_auto_approve: float = 0.8
    min_coverage_auto_reject: float = 0.6
    
    # Anomaly thresholds
    max_anomaly_auto_approve: float = 0.4
    max_anomaly_escalate: float = 0.7
    
    # Checklist thresholds
    min_checklist_completion: float = 0.8
    max_failed_critical_rules: int = 0
    
    # Amount thresholds
    high_value_threshold: float = 10000.0
    critical_value_threshold: float = 50000.0


@dataclass
class DecisionFactors:
    """Factors contributing to decision calculation"""
    confidence_score: float
    risk_score: float
    coverage_score: float
    anomaly_score: float
    checklist_completion: float
    failed_critical_rules: int
    evidence_quality: float
    policy_clarity: float
    service_amount: float
    guardrail_flags: List[str]
    ml_predictions: Dict[str, Any]


@dataclass
class DecisionResult:
    """Result of decision orchestration"""
    status: DecisionStatus
    confidence_score: float
    risk_score: float
    explanation: str
    next_actions: List[str]
    requires_hitl: bool
    hitl_reason: Optional[HITLReason]
    supporting_evidence: List[str]
    decision_factors: DecisionFactors
    thresholds_version: str
    processing_time_ms: int


class DecisionOrchestrator:
    """
    Decision Orchestrator Agent implementing UC-OP-08.
    
    Orchestrates the final decision-making process by analyzing all available
    information, calculating confidence and risk scores, applying business rules,
    and determining whether to auto-approve, reject, escalate to HITL, or observe.
    """
    
    def __init__(self, use_mock: bool = False):
        self.repo_factory = get_repository_factory()
        self.use_mock = use_mock
        
        # Load configuration
        self.thresholds = self._load_decision_thresholds()
        self.business_rules = self._load_business_rules()
        
        # Decision statistics
        self.decision_stats = {
            "total_decisions": 0,
            "auto_approved": 0,
            "auto_rejected": 0,
            "observed": 0,
            "escalated": 0,
            "hitl_required": 0
        }
    
    def _load_decision_thresholds(self) -> DecisionThresholds:
        """Load decision thresholds from configuration"""
        
        config_repo = self.repo_factory.system_configuration_repository()
        
        # Load thresholds from database or use defaults
        thresholds = DecisionThresholds()
        
        try:
            # Confidence thresholds
            confidence_config = config_repo.get_by_key("decision.confidence_threshold")
            if confidence_config:
                thresholds.min_confidence_auto_approve = confidence_config.config_value
            
            # Risk thresholds
            risk_config = config_repo.get_by_key("decision.risk_threshold")
            if risk_config:
                thresholds.max_risk_auto_approve = risk_config.config_value
            
            # Coverage thresholds
            coverage_config = config_repo.get_by_key("evidence.minimum_coverage_score")
            if coverage_config:
                thresholds.min_coverage_auto_approve = coverage_config.config_value
            
        except Exception as e:
            logger.warning(f"Failed to load decision thresholds from config: {e}")
        
        return thresholds
    
    def _load_business_rules(self) -> Dict[str, Any]:
        """Load business rules configuration"""
        
        return {
            # RB-01: No APROBADO without verifiable evidence
            "require_evidence_for_approval": True,
            "min_evidence_items": 1,
            
            # RB-04: Auto-closure conditions
            "auto_closure_enabled": True,
            "auto_closure_conditions": {
                "confidence_high": True,
                "risk_low": True,
                "coverage_ok": True,
                "no_critical_guardrails": True
            },
            
            # High-value case rules
            "high_value_manual_review": True,
            "critical_value_expert_review": True,
            
            # Emergency case rules
            "emergency_fast_track": True,
            "emergency_reduced_thresholds": True
        }
    
    async def orchestrate_decision(
        self, 
        state: PolicyValidationState
    ) -> PolicyValidationState:
        """
        Main entry point for decision orchestration.
        
        Args:
            state: Current policy validation state
            
        Returns:
            Updated state with decision
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract components from state
            case = state["case"]
            evidence_pack = state.get("evidence_pack", {})
            checklist = state.get("checklist", {})
            ml_results = state.get("ml", {})
            guardrails = state.get("guardrails", {})
            
            case_id = case["case_id"]
            
            logger.info(f"Starting decision orchestration for case {case_id}")
            
            # Calculate decision factors
            decision_factors = await self._calculate_decision_factors(
                case, evidence_pack, checklist, ml_results, guardrails
            )
            
            # Apply business rules and thresholds
            decision_result = await self._apply_decision_logic(
                decision_factors, case, state
            )
            
            # Check auto-closure conditions (RB-04)
            if decision_result.status == DecisionStatus.APROBADO:
                auto_closure_eligible = await self._check_auto_closure_conditions(
                    decision_result, decision_factors
                )
                if not auto_closure_eligible:
                    decision_result.requires_hitl = True
                    decision_result.hitl_reason = HITLReason.MANUAL_REVIEW_REQUIRED
            
            # Create decision record
            decision = await self._create_decision_record(
                case_id, decision_result, decision_factors
            )
            
            # Update state
            state["decision"] = decision
            
            # Log decision audit trail
            await self._log_decision_audit(case_id, decision_result, decision_factors)
            
            # Update statistics
            await self._update_decision_statistics(decision_result)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            decision["processing_time_ms"] = int(processing_time)
            
            logger.info(
                f"Decision orchestration completed for case {case_id}: "
                f"status={decision_result.status.value}, "
                f"confidence={decision_result.confidence_score:.3f}, "
                f"risk={decision_result.risk_score:.3f}, "
                f"hitl={decision_result.requires_hitl}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Decision orchestration failed for case {case.get('case_id', 'unknown')}: {e}")
            
            # Create error decision
            state["decision"] = {
                "status": DecisionStatus.ESCALAR,
                "confidence_score": 0.0,
                "risk_score": 1.0,
                "explanation": f"Decision orchestration failed: {str(e)}",
                "next_actions": ["MANUAL_REVIEW"],
                "requires_hitl": True,
                "hitl_reason": "SYSTEM_ERROR",
                "supporting_evidence": [],
                "thresholds_version": "ERROR",
                "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }
            
            raise
    
    async def _calculate_decision_factors(
        self,
        case: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        checklist: Dict[str, Any],
        ml_results: Dict[str, Any],
        guardrails: Dict[str, Any]
    ) -> DecisionFactors:
        """Calculate all factors that contribute to the decision"""
        
        # Extract basic scores
        confidence_score = await self._calculate_confidence_score(
            evidence_pack, checklist, ml_results
        )
        
        risk_score = await self._calculate_risk_score(
            case, ml_results, guardrails, checklist
        )
        
        coverage_score = evidence_pack.get("coverage_score", 0.0)
        anomaly_score = ml_results.get("anomaly", {}).get("anomaly_score", 0.0)
        
        # Calculate checklist metrics
        checklist_completion = checklist.get("completion_percentage", 0.0) / 100.0
        failed_critical_rules = await self._count_failed_critical_rules(checklist)
        
        # Calculate evidence quality
        evidence_quality = await self._calculate_evidence_quality(evidence_pack)
        
        # Calculate policy clarity
        policy_clarity = await self._calculate_policy_clarity(evidence_pack)
        
        # Extract other factors
        service_amount = case.get("service_amount", 0.0)
        guardrail_flags = [flag.get("flag_type", "") for flag in guardrails.get("flags", [])]
        
        return DecisionFactors(
            confidence_score=confidence_score,
            risk_score=risk_score,
            coverage_score=coverage_score,
            anomaly_score=anomaly_score,
            checklist_completion=checklist_completion,
            failed_critical_rules=failed_critical_rules,
            evidence_quality=evidence_quality,
            policy_clarity=policy_clarity,
            service_amount=service_amount,
            guardrail_flags=guardrail_flags,
            ml_predictions=ml_results
        )
    
    async def _calculate_confidence_score(
        self,
        evidence_pack: Dict[str, Any],
        checklist: Dict[str, Any],
        ml_results: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score"""
        
        # Factors for confidence calculation
        evidence_factor = 0.4
        checklist_factor = 0.3
        ml_factor = 0.2
        consistency_factor = 0.1
        
        # Evidence confidence
        evidence_items = evidence_pack.get("items", [])
        if evidence_items:
            evidence_confidence = sum(
                item.get("confidence_score", 0.0) for item in evidence_items
            ) / len(evidence_items)
        else:
            evidence_confidence = 0.0
        
        # Checklist confidence
        checklist_items = checklist.get("items", [])
        if checklist_items:
            passed_items = sum(
                1 for item in checklist_items 
                if item.get("outcome") == ChecklistOutcome.PASS
            )
            checklist_confidence = passed_items / len(checklist_items)
        else:
            checklist_confidence = 0.0
        
        # ML confidence
        classification = ml_results.get("classification", {})
        ml_confidence = max(classification.get("probabilities", {}).values()) if classification.get("probabilities") else 0.0
        
        # Consistency check
        consistency_score = await self._calculate_consistency_score(
            evidence_pack, checklist, ml_results
        )
        
        # Calculate weighted confidence
        confidence = (
            evidence_confidence * evidence_factor +
            checklist_confidence * checklist_factor +
            ml_confidence * ml_factor +
            consistency_score * consistency_factor
        )
        
        return min(confidence, 1.0)
    
    async def _calculate_risk_score(
        self,
        case: Dict[str, Any],
        ml_results: Dict[str, Any],
        guardrails: Dict[str, Any],
        checklist: Dict[str, Any]
    ) -> float:
        """Calculate overall risk score"""
        
        # Base risk factors
        base_risk = 0.1
        
        # ML risk factors
        anomaly_score = ml_results.get("anomaly", {}).get("anomaly_score", 0.0)
        classification_risk = ml_results.get("classification", {}).get("risk_prior", 0.0)
        
        # Guardrail risk factors
        guardrail_decision = guardrails.get("decision", "ALLOW")
        guardrail_risk = 0.0
        if guardrail_decision == "BLOCK":
            guardrail_risk = 0.9
        elif guardrail_decision == "REQUIRE_HITL":
            guardrail_risk = 0.6
        elif guardrail_decision == "REDACT":
            guardrail_risk = 0.3
        
        # Checklist risk factors
        failed_rules = sum(
            1 for item in checklist.get("items", [])
            if item.get("outcome") == ChecklistOutcome.FAIL
        )
        checklist_risk = min(failed_rules * 0.2, 0.8)
        
        # Amount-based risk
        service_amount = case.get("service_amount", 0.0)
        amount_risk = 0.0
        if service_amount > self.thresholds.critical_value_threshold:
            amount_risk = 0.4
        elif service_amount > self.thresholds.high_value_threshold:
            amount_risk = 0.2
        
        # Calculate composite risk
        risk_score = max(
            base_risk,
            anomaly_score,
            classification_risk,
            guardrail_risk,
            checklist_risk,
            amount_risk
        )
        
        return min(risk_score, 1.0)
    
    async def _calculate_consistency_score(
        self,
        evidence_pack: Dict[str, Any],
        checklist: Dict[str, Any],
        ml_results: Dict[str, Any]
    ) -> float:
        """Calculate consistency score across different components"""
        
        # Check for conflicts in evidence pack
        conflicts_detected = evidence_pack.get("conflicts_detected", False)
        if conflicts_detected:
            return 0.3
        
        # Check for inconsistencies between checklist and ML results
        classification = ml_results.get("classification", {})
        request_type = classification.get("request_type", "")
        
        # Simple consistency check - in production would be more sophisticated
        checklist_items = checklist.get("items", [])
        failed_items = [item for item in checklist_items if item.get("outcome") == ChecklistOutcome.FAIL]
        
        if failed_items and request_type in ["MEDICAL_CONSULTATION", "EMERGENCY_CARE"]:
            # Inconsistency between ML classification and failed rules
            return 0.6
        
        return 0.9  # Default high consistency
    
    async def _count_failed_critical_rules(self, checklist: Dict[str, Any]) -> int:
        """Count failed critical rules in checklist"""
        
        critical_rule_types = ["ELIGIBILITY", "EXCLUSION", "AUTHORIZATION"]
        failed_critical = 0
        
        for item in checklist.get("items", []):
            if item.get("outcome") == ChecklistOutcome.FAIL:
                # Check if this is a critical rule (simplified check)
                rule_id = item.get("rule_id", "")
                if any(rule_type in rule_id for rule_type in critical_rule_types):
                    failed_critical += 1
        
        return failed_critical
    
    async def _calculate_evidence_quality(self, evidence_pack: Dict[str, Any]) -> float:
        """Calculate evidence quality score"""
        
        evidence_items = evidence_pack.get("items", [])
        if not evidence_items:
            return 0.0
        
        # Calculate average relevance and confidence
        total_relevance = sum(item.get("relevance_score", 0.0) for item in evidence_items)
        total_confidence = sum(item.get("confidence_score", 0.0) for item in evidence_items)
        
        avg_relevance = total_relevance / len(evidence_items)
        avg_confidence = total_confidence / len(evidence_items)
        
        # Weight relevance and confidence equally
        quality_score = (avg_relevance + avg_confidence) / 2
        
        return quality_score
    
    async def _calculate_policy_clarity(self, evidence_pack: Dict[str, Any]) -> float:
        """Calculate policy clarity score"""
        
        # Check for conflicts
        if evidence_pack.get("conflicts_detected", False):
            return 0.4
        
        # Check coverage score
        coverage_score = evidence_pack.get("coverage_score", 0.0)
        
        # High coverage indicates clear policy guidance
        if coverage_score >= 0.9:
            return 0.9
        elif coverage_score >= 0.7:
            return 0.7
        elif coverage_score >= 0.5:
            return 0.5
        else:
            return 0.3
    
    async def _apply_decision_logic(
        self,
        factors: DecisionFactors,
        case: Dict[str, Any],
        state: PolicyValidationState
    ) -> DecisionResult:
        """Apply decision logic based on factors and thresholds"""
        
        # Check for immediate escalation conditions
        escalation_result = await self._check_escalation_conditions(factors, case)
        if escalation_result:
            return escalation_result
        
        # Apply threshold-based decision logic
        decision_status = DecisionStatus.PENDIENTE
        explanation = ""
        next_actions = []
        requires_hitl = False
        hitl_reason = None
        
        # Check for auto-approval conditions
        if await self._check_auto_approval_conditions(factors):
            decision_status = DecisionStatus.APROBADO
            explanation = "Case meets all criteria for automatic approval"
            next_actions = ["AUTO_CLOSE"]
            
        # Check for auto-rejection conditions
        elif await self._check_auto_rejection_conditions(factors):
            decision_status = DecisionStatus.RECHAZADO
            explanation = "Case fails critical criteria for automatic rejection"
            next_actions = ["AUTO_CLOSE", "NOTIFY_CUSTOMER"]
            
        # Check for observation conditions
        elif await self._check_observation_conditions(factors):
            decision_status = DecisionStatus.OBSERVADO
            explanation = "Case requires additional information or clarification"
            next_actions = ["REQUEST_ADDITIONAL_INFO"]
            requires_hitl = True
            hitl_reason = HITLReason.MISSING_EVIDENCE
            
        # Default to escalation
        else:
            decision_status = DecisionStatus.ESCALAR
            explanation = "Case requires manual review due to unclear conditions"
            next_actions = ["MANUAL_REVIEW"]
            requires_hitl = True
            hitl_reason = HITLReason.COMPLEX_CASE
        
        # Generate supporting evidence
        supporting_evidence = await self._generate_supporting_evidence(factors, state)
        
        return DecisionResult(
            status=decision_status,
            confidence_score=factors.confidence_score,
            risk_score=factors.risk_score,
            explanation=explanation,
            next_actions=next_actions,
            requires_hitl=requires_hitl,
            hitl_reason=hitl_reason,
            supporting_evidence=supporting_evidence,
            decision_factors=factors,
            thresholds_version="v1.0.0",
            processing_time_ms=0  # Will be set by caller
        )
    
    async def _check_escalation_conditions(
        self, 
        factors: DecisionFactors, 
        case: Dict[str, Any]
    ) -> Optional[DecisionResult]:
        """Check for immediate escalation conditions"""
        
        # Critical guardrail violations
        if "INJECTION_DETECTED" in factors.guardrail_flags:
            return DecisionResult(
                status=DecisionStatus.ESCALAR,
                confidence_score=0.0,
                risk_score=1.0,
                explanation="Security violation detected - immediate escalation required",
                next_actions=["SECURITY_REVIEW"],
                requires_hitl=True,
                hitl_reason=HITLReason.GUARDRAIL_VIOLATION,
                supporting_evidence=[],
                decision_factors=factors,
                thresholds_version="v1.0.0",
                processing_time_ms=0
            )
        
        # Critical value threshold
        if factors.service_amount > self.thresholds.critical_value_threshold:
            return DecisionResult(
                status=DecisionStatus.ESCALAR,
                confidence_score=factors.confidence_score,
                risk_score=max(factors.risk_score, 0.8),
                explanation=f"High-value case (${factors.service_amount:,.2f}) requires expert review",
                next_actions=["EXPERT_REVIEW"],
                requires_hitl=True,
                hitl_reason=HITLReason.COMPLEX_CASE,
                supporting_evidence=[],
                decision_factors=factors,
                thresholds_version="v1.0.0",
                processing_time_ms=0
            )
        
        # High anomaly score
        if factors.anomaly_score > self.thresholds.max_anomaly_escalate:
            return DecisionResult(
                status=DecisionStatus.ESCALAR,
                confidence_score=factors.confidence_score,
                risk_score=max(factors.risk_score, 0.7),
                explanation=f"High anomaly score ({factors.anomaly_score:.3f}) detected",
                next_actions=["FRAUD_INVESTIGATION"],
                requires_hitl=True,
                hitl_reason=HITLReason.ANOMALY_DETECTED,
                supporting_evidence=[],
                decision_factors=factors,
                thresholds_version="v1.0.0",
                processing_time_ms=0
            )
        
        return None
    
    async def _check_auto_approval_conditions(self, factors: DecisionFactors) -> bool:
        """Check if case meets auto-approval conditions"""
        
        # RB-01: Must have evidence for approval
        if not factors.ml_predictions.get("evidence_pack", {}).get("items"):
            return False
        
        # All threshold conditions must be met
        conditions = [
            factors.confidence_score >= self.thresholds.min_confidence_auto_approve,
            factors.risk_score <= self.thresholds.max_risk_auto_approve,
            factors.coverage_score >= self.thresholds.min_coverage_auto_approve,
            factors.anomaly_score <= self.thresholds.max_anomaly_auto_approve,
            factors.checklist_completion >= self.thresholds.min_checklist_completion,
            factors.failed_critical_rules <= self.thresholds.max_failed_critical_rules,
            "BLOCK" not in factors.guardrail_flags,
            "HIGH_RISK_PII" not in factors.guardrail_flags
        ]
        
        return all(conditions)
    
    async def _check_auto_rejection_conditions(self, factors: DecisionFactors) -> bool:
        """Check if case meets auto-rejection conditions"""
        
        # Clear rejection indicators
        rejection_conditions = [
            factors.failed_critical_rules > 0,
            factors.confidence_score >= self.thresholds.min_confidence_auto_reject and factors.risk_score > self.thresholds.max_risk_auto_reject,
            "BLOCK" in factors.guardrail_flags
        ]
        
        return any(rejection_conditions)
    
    async def _check_observation_conditions(self, factors: DecisionFactors) -> bool:
        """Check if case meets observation conditions"""
        
        # Observation indicators
        observation_conditions = [
            self.thresholds.min_confidence_observe <= factors.confidence_score < self.thresholds.min_confidence_auto_approve,
            factors.coverage_score < self.thresholds.min_coverage_auto_approve,
            factors.checklist_completion < self.thresholds.min_checklist_completion,
            "MISSING_EVIDENCE" in factors.guardrail_flags
        ]
        
        return any(observation_conditions)
    
    async def _check_auto_closure_conditions(
        self, 
        decision_result: DecisionResult, 
        factors: DecisionFactors
    ) -> bool:
        """Check RB-04 auto-closure conditions"""
        
        if not self.business_rules["auto_closure_enabled"]:
            return False
        
        conditions = self.business_rules["auto_closure_conditions"]
        
        # Check each condition
        checks = []
        
        if conditions["confidence_high"]:
            checks.append(factors.confidence_score >= 0.8)
        
        if conditions["risk_low"]:
            checks.append(factors.risk_score <= 0.3)
        
        if conditions["coverage_ok"]:
            checks.append(factors.coverage_score >= 0.8)
        
        if conditions["no_critical_guardrails"]:
            critical_flags = ["BLOCK", "HIGH_RISK_PII", "INJECTION_DETECTED"]
            checks.append(not any(flag in factors.guardrail_flags for flag in critical_flags))
        
        return all(checks)
    
    async def _generate_supporting_evidence(
        self, 
        factors: DecisionFactors, 
        state: PolicyValidationState
    ) -> List[str]:
        """Generate supporting evidence references for the decision"""
        
        evidence_refs = []
        
        # Add evidence pack references
        evidence_pack = state.get("evidence_pack", {})
        for item in evidence_pack.get("items", []):
            if item.get("confidence_score", 0.0) >= 0.7:
                ref = f"{item.get('doc_id')}#{item.get('pointer')}"
                evidence_refs.append(ref)
        
        # Add checklist references
        checklist = state.get("checklist", {})
        for item in checklist.get("items", []):
            if item.get("outcome") == ChecklistOutcome.PASS and item.get("evidence_ref"):
                evidence_refs.append(item["evidence_ref"])
        
        return evidence_refs[:5]  # Limit to top 5 references
    
    async def _create_decision_record(
        self,
        case_id: str,
        decision_result: DecisionResult,
        factors: DecisionFactors
    ) -> Decision:
        """Create decision record for state"""
        
        decision = {
            "status": decision_result.status,
            "confidence_score": decision_result.confidence_score,
            "risk_score": decision_result.risk_score,
            "explanation": decision_result.explanation,
            "next_actions": decision_result.next_actions,
            "supporting_evidence": decision_result.supporting_evidence,
            "thresholds_version": decision_result.thresholds_version,
            "rules_applied": [],  # Would be populated from checklist
            "requires_hitl": decision_result.requires_hitl,
            "hitl_reason": decision_result.hitl_reason.value if decision_result.hitl_reason else None,
            "hitl_assigned_to": None,
            "hitl_completed_at": None,
            "is_final": not decision_result.requires_hitl,
            "finalized_at": datetime.utcnow() if not decision_result.requires_hitl else None,
            "finalized_by": "SYSTEM" if not decision_result.requires_hitl else None
        }
        
        return decision
    
    async def _log_decision_audit(
        self,
        case_id: str,
        decision_result: DecisionResult,
        factors: DecisionFactors
    ) -> None:
        """Log decision audit trail"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        audit_data = {
            "case_id": case_id,
            "event_type": "DECISION_ORCHESTRATED",
            "event_category": "DECISION",
            "event_description": f"Decision orchestrated: {decision_result.status.value}",
            "user_id": "SYSTEM",
            "event_data": {
                "decision_status": decision_result.status.value,
                "confidence_score": decision_result.confidence_score,
                "risk_score": decision_result.risk_score,
                "requires_hitl": decision_result.requires_hitl,
                "hitl_reason": decision_result.hitl_reason.value if decision_result.hitl_reason else None,
                "decision_factors": {
                    "coverage_score": factors.coverage_score,
                    "anomaly_score": factors.anomaly_score,
                    "checklist_completion": factors.checklist_completion,
                    "failed_critical_rules": factors.failed_critical_rules,
                    "service_amount": factors.service_amount,
                    "guardrail_flags": factors.guardrail_flags
                },
                "thresholds_version": decision_result.thresholds_version
            },
            "processing_time_ms": decision_result.processing_time_ms
        }
        
        try:
            audit_repo.create(**audit_data)
        except Exception as e:
            logger.error(f"Failed to log decision audit: {e}")
    
    async def _update_decision_statistics(self, decision_result: DecisionResult) -> None:
        """Update decision statistics"""
        
        self.decision_stats["total_decisions"] += 1
        
        if decision_result.status == DecisionStatus.APROBADO:
            self.decision_stats["auto_approved"] += 1
        elif decision_result.status == DecisionStatus.RECHAZADO:
            self.decision_stats["auto_rejected"] += 1
        elif decision_result.status == DecisionStatus.OBSERVADO:
            self.decision_stats["observed"] += 1
        elif decision_result.status == DecisionStatus.ESCALAR:
            self.decision_stats["escalated"] += 1
        
        if decision_result.requires_hitl:
            self.decision_stats["hitl_required"] += 1
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get decision statistics"""
        stats = self.decision_stats.copy()
        
        if stats["total_decisions"] > 0:
            stats["auto_approval_rate"] = stats["auto_approved"] / stats["total_decisions"]
            stats["auto_rejection_rate"] = stats["auto_rejected"] / stats["total_decisions"]
            stats["escalation_rate"] = stats["escalated"] / stats["total_decisions"]
            stats["hitl_rate"] = stats["hitl_required"] / stats["total_decisions"]
        
        return stats
    
    def update_thresholds(self, new_thresholds: DecisionThresholds) -> None:
        """Update decision thresholds"""
        self.thresholds = new_thresholds
        logger.info("Decision thresholds updated")


# Factory function for creating decision orchestrator
def create_decision_orchestrator(use_mock: bool = False) -> DecisionOrchestrator:
    """
    Factory function to create decision orchestrator.
    
    Args:
        use_mock: Whether to use mock implementations
        
    Returns:
        Configured decision orchestrator
    """
    return DecisionOrchestrator(use_mock=use_mock)
