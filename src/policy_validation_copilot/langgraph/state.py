"""
LangGraph state management for the Policy Validation Copilot system.

This module provides LangGraph-specific state management utilities, including
state transitions, validation methods, serialization utilities, and audit logging
functionality for the PolicyValidationState.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import uuid4

from langgraph.graph import StateGraph
from pydantic import BaseModel, ValidationError

from ..models.state import (
    PolicyValidationState,
    StateTransition,
    StateValidationResult,
)
from ..models.case import Case
from ..models.decision import AuditTrail
from ..models.evidence import EvidencePack
from ..models.checklist import Checklist
from ..models.decision import Decision, HITLRequest
from ..models.ml import MLScoreRecord, AnomalyRecord, ETARecord
from ..models.guardrails import GuardrailLog, SecurityEvent

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class StateManager:
    """
    LangGraph state manager for PolicyValidationState.
    
    Provides utilities for state transitions, validation, serialization,
    and audit logging within the LangGraph workflow context.
    """
    
    def __init__(self, enable_audit_logging: bool = True):
        """Initialize the state manager."""
        self.enable_audit_logging = enable_audit_logging
        self.transitions: List[StateTransition] = []
        
    def create_initial_state(self, case: Case) -> PolicyValidationState:
        """
        Create initial PolicyValidationState from a case.
        
        Args:
            case: The case to create state for
            
        Returns:
            Initial PolicyValidationState
        """
        logger.info(f"Creating initial state for case {case.case_id}")
        
        # Create audit trail
        audit = AuditTrail(
            case_id=case.case_id,
            processing_started_at=datetime.utcnow(),
            system_version="1.0.0",  # TODO: Get from config
            langgraph_version="0.2.0",  # TODO: Get from langgraph
        )
        
        # Create initial state
        state = PolicyValidationState(
            case=case,
            audit=audit,
            workflow_status="INITIALIZED",
        )
        
        state.start_processing()
        
        if self.enable_audit_logging:
            audit.add_node_execution("state_initialization", {
                "action": "create_initial_state",
                "case_id": case.case_id,
                "state_id": state.state_id,
            })
        
        logger.info(f"Initial state created with ID {state.state_id}")
        return state
    
    def transition_to_node(
        self,
        state: PolicyValidationState,
        node_name: str,
        transition_reason: str = "workflow_progression",
        metadata: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Transition state to a new node.
        
        Args:
            state: Current state
            node_name: Target node name
            transition_reason: Reason for transition
            metadata: Additional transition metadata
            
        Returns:
            Updated state
        """
        logger.info(f"Transitioning state {state.state_id} to node {node_name}")
        
        previous_node = state.current_node
        state_before = state.to_summary() if self.enable_audit_logging else {}
        
        # Update state
        state.enter_node(node_name)
        
        # Record transition
        if self.enable_audit_logging:
            transition = StateTransition(
                state_id=state.state_id,
                from_node=previous_node,
                to_node=node_name,
                transition_reason=transition_reason,
                state_before=state_before,
                state_after=state.to_summary(),
                triggered_by="state_manager",
                execution_time_ms=0.0,  # Will be updated by caller if needed
            )
            self.transitions.append(transition)
            
            # Add to audit trail
            if state.audit:
                state.audit.add_node_execution(f"transition_to_{node_name}", {
                    "action": "node_transition",
                    "from_node": previous_node,
                    "to_node": node_name,
                    "reason": transition_reason,
                    "metadata": metadata or {},
                })
        
        logger.info(f"State transitioned from {previous_node} to {node_name}")
        return state
    
    def complete_node(
        self,
        state: PolicyValidationState,
        node_name: str,
        execution_result: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Mark a node as completed in the state.
        
        Args:
            state: Current state
            node_name: Node that was completed
            execution_result: Result of node execution
            
        Returns:
            Updated state
        """
        logger.info(f"Completing node {node_name} for state {state.state_id}")
        
        state.complete_node(node_name)
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution(f"complete_{node_name}", {
                "action": "node_completion",
                "node_name": node_name,
                "execution_result": execution_result or {},
                "completed_at": datetime.utcnow().isoformat(),
            })
        
        logger.info(f"Node {node_name} marked as completed")
        return state
    
    def add_evidence_pack(
        self,
        state: PolicyValidationState,
        evidence_pack: EvidencePack
    ) -> PolicyValidationState:
        """
        Add evidence pack to state.
        
        Args:
            state: Current state
            evidence_pack: Evidence pack to add
            
        Returns:
            Updated state
        """
        logger.info(f"Adding evidence pack {evidence_pack.pack_id} to state {state.state_id}")
        
        state.evidence_pack = evidence_pack
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("evidence_pack_added", {
                "action": "add_evidence_pack",
                "pack_id": evidence_pack.pack_id,
                "coverage_score": evidence_pack.coverage_score,
                "item_count": len(evidence_pack.items),
                "conflicts": len(evidence_pack.conflicts),
            })
        
        return state
    
    def add_checklist(
        self,
        state: PolicyValidationState,
        checklist: Checklist
    ) -> PolicyValidationState:
        """
        Add checklist to state.
        
        Args:
            state: Current state
            checklist: Checklist to add
            
        Returns:
            Updated state
        """
        logger.info(f"Adding checklist {checklist.checklist_id} to state {state.state_id}")
        
        state.checklist = checklist
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("checklist_added", {
                "action": "add_checklist",
                "checklist_id": checklist.checklist_id,
                "total_items": checklist.total_items,
                "passed_items": checklist.passed_items,
                "failed_items": checklist.failed_items,
                "missing_items": checklist.missing_items,
                "overall_outcome": checklist.overall_outcome.value if checklist.overall_outcome else None,
            })
        
        return state
    
    def add_ml_results(
        self,
        state: PolicyValidationState,
        classification: Optional[MLScoreRecord] = None,
        anomaly: Optional[AnomalyRecord] = None,
        eta: Optional[ETARecord] = None
    ) -> PolicyValidationState:
        """
        Add ML service results to state.
        
        Args:
            state: Current state
            classification: Classification results
            anomaly: Anomaly detection results
            eta: ETA prediction results
            
        Returns:
            Updated state
        """
        logger.info(f"Adding ML results to state {state.state_id}")
        
        if classification:
            state.ml.add_classification_result(classification)
        
        if anomaly:
            state.ml.add_anomaly_result(anomaly)
        
        if eta:
            state.ml.add_eta_result(eta)
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("ml_results_added", {
                "action": "add_ml_results",
                "classification_added": classification is not None,
                "anomaly_added": anomaly is not None,
                "eta_added": eta is not None,
                "ml_processing_completed": state.ml.ml_processing_completed,
                "model_versions": state.ml.model_versions,
            })
        
        return state
    
    def add_decision(
        self,
        state: PolicyValidationState,
        decision: Decision
    ) -> PolicyValidationState:
        """
        Add decision to state.
        
        Args:
            state: Current state
            decision: Decision to add
            
        Returns:
            Updated state
        """
        logger.info(f"Adding decision {decision.decision_id} to state {state.state_id}")
        
        state.decision = decision
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("decision_added", {
                "action": "add_decision",
                "decision_id": decision.decision_id,
                "status": decision.status.value,
                "confidence_score": decision.confidence_score,
                "risk_level": decision.risk_level.value,
                "decision_type": decision.decision_type,
                "next_actions_count": len(decision.next_actions),
            })
        
        return state
    
    def add_guardrail_log(
        self,
        state: PolicyValidationState,
        guardrail_log: GuardrailLog
    ) -> PolicyValidationState:
        """
        Add guardrail log to state.
        
        Args:
            state: Current state
            guardrail_log: Guardrail log to add
            
        Returns:
            Updated state
        """
        logger.info(f"Adding guardrail log {guardrail_log.log_id} to state {state.state_id}")
        
        state.guardrails.add_log(guardrail_log)
        
        # Update guardrails decision based on log
        if guardrail_log.action_taken:
            state.guardrails.decision = guardrail_log.action_taken.value
        
        # Add flags from log
        for flag in guardrail_log.flags_raised:
            state.guardrails.add_flag(flag)
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("guardrail_log_added", {
                "action": "add_guardrail_log",
                "log_id": guardrail_log.log_id,
                "guardrail_type": guardrail_log.guardrail_type,
                "action_taken": guardrail_log.action_taken.value,
                "flags_raised": guardrail_log.flags_raised,
                "processing_time_ms": guardrail_log.processing_time_ms,
            })
        
        return state
    
    def add_security_event(
        self,
        state: PolicyValidationState,
        security_event: SecurityEvent
    ) -> PolicyValidationState:
        """
        Add security event to state.
        
        Args:
            state: Current state
            security_event: Security event to add
            
        Returns:
            Updated state
        """
        logger.info(f"Adding security event {security_event.event_id} to state {state.state_id}")
        
        # Add security flag to guardrails
        state.guardrails.add_flag(f"SECURITY_EVENT_{security_event.event_type.value}")
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("security_event_added", {
                "action": "add_security_event",
                "event_id": security_event.event_id,
                "event_type": security_event.event_type.value,
                "severity": security_event.severity,
                "confidence_score": security_event.confidence_score,
                "potential_impact": security_event.potential_impact,
            })
        
        return state
    
    def require_hitl(
        self,
        state: PolicyValidationState,
        reason: str,
        questions: Optional[List[str]] = None,
        priority: str = "MEDIUM"
    ) -> PolicyValidationState:
        """
        Mark state as requiring HITL intervention.
        
        Args:
            state: Current state
            reason: Reason for HITL requirement
            questions: Specific questions for human reviewer
            priority: Priority level
            
        Returns:
            Updated state
        """
        logger.info(f"Requiring HITL for state {state.state_id}: {reason}")
        
        state.hitl.require_hitl(reason)
        
        if questions:
            for question in questions:
                state.hitl.add_question(question)
        
        # Create HITL request
        hitl_request = HITLRequest(
            case_id=state.case.case_id,
            decision_id=state.decision.decision_id if state.decision else None,
            request_type="POLICY_VALIDATION_REVIEW",
            priority=priority,
            reason=reason,
            context_summary=self._create_context_summary(state),
            specific_questions=questions or [],
        )
        
        state.hitl.requests.append(hitl_request)
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("hitl_required", {
                "action": "require_hitl",
                "reason": reason,
                "priority": priority,
                "questions_count": len(questions) if questions else 0,
                "request_id": hitl_request.request_id,
            })
        
        return state
    
    def validate_state(self, state: PolicyValidationState) -> StateValidationResult:
        """
        Validate state integrity and completeness.
        
        Args:
            state: State to validate
            
        Returns:
            Validation result
        """
        logger.info(f"Validating state {state.state_id}")
        
        result = StateValidationResult(is_valid=True)
        
        try:
            # Validate case data
            if not state.case:
                result.add_error("Case data is missing")
                result.case_valid = False
            elif not state.case.case_id:
                result.add_error("Case ID is missing")
                result.case_valid = False
            
            # Validate evidence pack if present
            if state.evidence_pack:
                if not state.evidence_pack.items:
                    result.add_warning("Evidence pack has no items")
                elif state.evidence_pack.coverage_score < 0.5:
                    result.add_warning(f"Low evidence coverage: {state.evidence_pack.coverage_score}")
                
                if state.evidence_pack.has_critical_conflicts():
                    result.add_error("Evidence pack has critical conflicts")
                    result.evidence_valid = False
            
            # Validate checklist if present
            if state.checklist:
                if not state.checklist.is_complete:
                    result.add_warning("Checklist is not complete")
                
                if state.checklist.has_blocking_issues():
                    result.add_error("Checklist has blocking issues")
                    result.checklist_valid = False
            
            # Validate decision if present
            if state.decision:
                if not state.decision.rationale:
                    result.add_error("Decision lacks rationale")
                    result.decision_valid = False
                
                if state.decision.confidence_score < 0.3:
                    result.add_warning(f"Low decision confidence: {state.decision.confidence_score}")
            
            # Validate workflow consistency
            if state.workflow_status == "COMPLETED" and not state.decision:
                result.add_error("Workflow marked complete but no decision present")
            
            if state.requires_hitl_intervention() and not state.hitl.required:
                result.add_error("State requires HITL but HITL not marked as required")
            
        except Exception as e:
            logger.error(f"Error during state validation: {e}")
            result.add_error(f"Validation error: {str(e)}")
        
        logger.info(f"State validation completed: {'VALID' if result.is_valid else 'INVALID'}")
        return result
    
    def serialize_state(self, state: PolicyValidationState) -> Dict[str, Any]:
        """
        Serialize state to dictionary for storage or transmission.
        
        Args:
            state: State to serialize
            
        Returns:
            Serialized state dictionary
        """
        logger.debug(f"Serializing state {state.state_id}")
        
        try:
            # Use Pydantic's built-in serialization
            serialized = state.dict()
            
            # Add metadata
            serialized["_metadata"] = {
                "serialized_at": datetime.utcnow().isoformat(),
                "serializer_version": "1.0.0",
                "state_manager_version": "1.0.0",
            }
            
            return serialized
            
        except Exception as e:
            logger.error(f"Error serializing state: {e}")
            raise
    
    def deserialize_state(self, data: Dict[str, Any]) -> PolicyValidationState:
        """
        Deserialize state from dictionary.
        
        Args:
            data: Serialized state data
            
        Returns:
            Deserialized PolicyValidationState
        """
        logger.debug("Deserializing state from data")
        
        try:
            # Remove metadata if present
            state_data = {k: v for k, v in data.items() if not k.startswith("_")}
            
            # Create state from data
            state = PolicyValidationState(**state_data)
            
            logger.debug(f"State deserialized with ID {state.state_id}")
            return state
            
        except ValidationError as e:
            logger.error(f"Validation error during deserialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deserializing state: {e}")
            raise
    
    def export_state_json(self, state: PolicyValidationState, pretty: bool = True) -> str:
        """
        Export state as JSON string.
        
        Args:
            state: State to export
            pretty: Whether to format JSON prettily
            
        Returns:
            JSON string representation
        """
        serialized = self.serialize_state(state)
        
        if pretty:
            return json.dumps(serialized, indent=2, default=str)
        else:
            return json.dumps(serialized, default=str)
    
    def import_state_json(self, json_str: str) -> PolicyValidationState:
        """
        Import state from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            Imported PolicyValidationState
        """
        try:
            data = json.loads(json_str)
            return self.deserialize_state(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise
    
    def finalize_processing(
        self,
        state: PolicyValidationState,
        final_status: str = "COMPLETED"
    ) -> PolicyValidationState:
        """
        Finalize state processing.
        
        Args:
            state: State to finalize
            final_status: Final workflow status
            
        Returns:
            Finalized state
        """
        logger.info(f"Finalizing processing for state {state.state_id} with status {final_status}")
        
        state.complete_processing(final_status)
        
        if state.audit:
            state.audit.finalize_processing()
        
        if self.enable_audit_logging and state.audit:
            state.audit.add_node_execution("processing_finalized", {
                "action": "finalize_processing",
                "final_status": final_status,
                "processing_duration": state.get_processing_duration(),
                "completed_nodes": state.completed_nodes,
                "total_transitions": len(self.transitions),
            })
        
        logger.info(f"Processing finalized for state {state.state_id}")
        return state
    
    def get_state_summary(self, state: PolicyValidationState) -> Dict[str, Any]:
        """
        Get a summary of the current state.
        
        Args:
            state: State to summarize
            
        Returns:
            State summary dictionary
        """
        return state.to_summary()
    
    def _create_context_summary(self, state: PolicyValidationState) -> str:
        """
        Create a context summary for HITL requests.
        
        Args:
            state: Current state
            
        Returns:
            Context summary string
        """
        summary_parts = [
            f"Case ID: {state.case.case_id}",
            f"Service: {state.case.service_description or state.case.service_code or 'Unknown'}",
            f"Customer: {state.case.customer_id}",
            f"Insurer: {state.case.insurer_id}",
        ]
        
        if state.evidence_pack:
            summary_parts.append(f"Evidence Coverage: {state.evidence_pack.coverage_score:.2f}")
        
        if state.decision:
            summary_parts.append(f"Confidence: {state.decision.confidence_score:.2f}")
            summary_parts.append(f"Risk: {state.decision.risk_level.value}")
        
        if state.ml.ml_processing_completed:
            if state.ml.anomaly:
                summary_parts.append(f"Anomaly Score: {state.ml.anomaly.anomaly_score:.2f}")
        
        return " | ".join(summary_parts)


# Utility functions for LangGraph integration

def create_state_reducer(state_manager: StateManager):
    """
    Create a state reducer function for LangGraph.
    
    Args:
        state_manager: State manager instance
        
    Returns:
        State reducer function
    """
    def reducer(left: PolicyValidationState, right: PolicyValidationState) -> PolicyValidationState:
        """Reduce two states by merging the right state into the left."""
        # For now, simply return the right state (latest)
        # In a more sophisticated implementation, we could merge specific fields
        return right
    
    return reducer


def create_state_schema() -> Type[PolicyValidationState]:
    """
    Create the state schema for LangGraph.
    
    Returns:
        PolicyValidationState class for use as LangGraph state schema
    """
    return PolicyValidationState


# Global state manager instance
default_state_manager = StateManager(enable_audit_logging=True)
