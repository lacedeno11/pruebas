"""
Core LangGraph Workflow for Policy Validation Copilot

This module implements the PolicyValidationWorkflow class that orchestrates
the complete policy validation process using LangGraph's StateGraph.

The workflow includes:
- Case ingestion and validation
- Intelligent routing with ML integration
- Policy retrieval using RAG
- Rules-based checklist building
- Decision orchestration with multi-signal fusion
- External insurer connector (conditional)
- Audited closure with compliance tracking

Workflow follows the state machine pattern with conditional routing
based on confidence thresholds, risk levels, and business rules.
"""

from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph

from src.schemas.state import (
    PolicyValidationState,
    CaseState,
    DecisionStatus,
    RiskLevel,
    GuardrailDecision,
    update_state_audit
)


class PolicyValidationWorkflow:
    """
    LangGraph workflow orchestrator for policy validation process.
    
    This class defines the complete workflow graph with all nodes and edges,
    implements conditional routing logic, and provides the compiled graph
    for execution.
    """
    
    def __init__(self):
        """Initialize the workflow with StateGraph configuration."""
        self.graph = StateGraph(PolicyValidationState)
        self._setup_nodes()
        self._setup_edges()
        self._compiled_graph: Optional[CompiledGraph] = None
    
    def _setup_nodes(self) -> None:
        """Add all workflow nodes to the graph."""
        # Import node functions (will be implemented in subsequent tasks)
        from src.nodes.case_ingest import case_ingest_node
        from src.nodes.intelligent_routing import routing_node
        from src.nodes.audited_closure import closure_node
        from src.agents.policy_retrieval import rag_agent
        from src.agents.rules_builder import checklist_agent
        from src.agents.decision_orchestrator import decision_agent
        from src.agents.insurer_connector import external_query_agent
        
        # Add nodes to the graph
        self.graph.add_node("case_ingest", case_ingest_node)
        self.graph.add_node("intelligent_routing", routing_node)
        self.graph.add_node("policy_retrieval", rag_agent)
        self.graph.add_node("rules_builder", checklist_agent)
        self.graph.add_node("decision_orchestrator", decision_agent)
        self.graph.add_node("insurer_connector", external_query_agent)
        self.graph.add_node("audited_closure", closure_node)
    
    def _setup_edges(self) -> None:
        """Define workflow edges and conditional routing logic."""
        # Set entry point
        self.graph.set_entry_point("case_ingest")
        
        # Linear flow: case_ingest -> intelligent_routing
        self.graph.add_edge("case_ingest", "intelligent_routing")
        
        # Linear flow: intelligent_routing -> policy_retrieval
        self.graph.add_edge("intelligent_routing", "policy_retrieval")
        
        # Linear flow: policy_retrieval -> rules_builder
        self.graph.add_edge("policy_retrieval", "rules_builder")
        
        # Linear flow: rules_builder -> decision_orchestrator
        self.graph.add_edge("rules_builder", "decision_orchestrator")
        
        # Conditional routing from decision_orchestrator
        self.graph.add_conditional_edges(
            "decision_orchestrator",
            self._route_after_decision,
            {
                "external_query": "insurer_connector",
                "closure": "audited_closure",
                "hitl": END  # HITL cases exit workflow for human review
            }
        )
        
        # From insurer_connector, always go to audited_closure
        self.graph.add_edge("insurer_connector", "audited_closure")
        
        # audited_closure is a finish point
        self.graph.add_edge("audited_closure", END)
    
    def _route_after_decision(self, state: PolicyValidationState) -> str:
        """
        Conditional routing logic after decision orchestrator.
        
        Determines next step based on:
        - Decision status
        - Confidence thresholds
        - Risk levels
        - Guardrail decisions
        - HITL requirements
        
        Args:
            state: Current workflow state
            
        Returns:
            str: Next node name ("external_query", "closure", or "hitl")
        """
        decision = state["decision"]
        guardrails = state["guardrails"]
        hitl = state["hitl"]
        
        # Check if HITL is explicitly required
        if hitl.required:
            return "hitl"
        
        # Check guardrail decisions that require HITL
        if guardrails.decision in [GuardrailDecision.REQUIRE_HITL, GuardrailDecision.BLOCK]:
            return "hitl"
        
        # Check if external insurer query is needed
        if decision.status == DecisionStatus.REQUIRES_EXTERNAL:
            return "external_query"
        
        # Check confidence and risk thresholds for auto-closure
        if self._should_require_hitl(state):
            return "hitl"
        
        # Default to closure for auto-approved/rejected cases
        return "closure"
    
    def _should_require_hitl(self, state: PolicyValidationState) -> bool:
        """
        Determine if case requires human-in-the-loop review.
        
        HITL is required when:
        - Low or medium confidence
        - High or critical risk
        - Anomaly detected
        - Evidence conflicts present
        - Policy changes detected
        - Critical guardrail flags
        
        Args:
            state: Current workflow state
            
        Returns:
            bool: True if HITL is required
        """
        decision = state["decision"]
        evidence_pack = state["evidence_pack"]
        guardrails = state["guardrails"]
        ml = state["ml"]
        
        # Confidence thresholds (configurable via settings)
        CONFIDENCE_HIGH_THRESHOLD = 0.85
        CONFIDENCE_MEDIUM_THRESHOLD = 0.65
        
        # Risk thresholds
        RISK_HIGH_THRESHOLD = 0.75
        ANOMALY_HIGH_THRESHOLD = 0.80
        
        # Check confidence levels
        if decision.confidence_score < CONFIDENCE_HIGH_THRESHOLD:
            return True
        
        # Check risk levels
        if decision.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return True
        
        # Check anomaly scores
        if decision.anomaly_score > ANOMALY_HIGH_THRESHOLD:
            return True
        
        # Check for evidence conflicts
        if evidence_pack.conflicts:
            # High severity conflicts require HITL
            high_severity_conflicts = [
                c for c in evidence_pack.conflicts 
                if c.severity in ["high", "critical"]
            ]
            if high_severity_conflicts:
                return True
        
        # Check for critical guardrail flags
        critical_flags = [
            flag for flag in guardrails.flags
            if flag.severity in ["error", "critical"]
        ]
        if critical_flags:
            return True
        
        # Check ML anomaly flags
        if ml.anomaly and ml.anomaly.anomaly_flags:
            critical_anomaly_flags = [
                flag for flag in ml.anomaly.anomaly_flags
                if "critical" in flag.lower() or "high_risk" in flag.lower()
            ]
            if critical_anomaly_flags:
                return True
        
        # Check coverage score
        COVERAGE_MIN_THRESHOLD = 0.60
        if evidence_pack.coverage_score < COVERAGE_MIN_THRESHOLD:
            return True
        
        return False
    
    def _route_for_external_query(self, state: PolicyValidationState) -> str:
        """
        Determine if external insurer query is needed.
        
        External queries are triggered when:
        - Missing critical evidence
        - Policy ambiguity detected
        - Exception rules require external validation
        - Specific insurer protocols mandate external check
        
        Args:
            state: Current workflow state
            
        Returns:
            str: "external_query" or "continue"
        """
        checklist = state["checklist"]
        evidence_pack = state["evidence_pack"]
        
        # Check for missing critical fields that require external validation
        critical_missing_fields = [
            field for field in checklist.missing_fields
            if field in ["authorization_code", "pre_approval", "network_status"]
        ]
        
        if critical_missing_fields:
            return "external_query"
        
        # Check for low coverage that might be resolved externally
        if evidence_pack.coverage_score < 0.40:
            return "external_query"
        
        # Check for specific checklist items that failed and require external validation
        failed_external_items = [
            item for item in checklist.items
            if item.outcome.value == "FAIL" and "external" in item.rule_id.lower()
        ]
        
        if failed_external_items:
            return "external_query"
        
        return "continue"
    
    def compile(self) -> CompiledGraph:
        """
        Compile the workflow graph for execution.
        
        Returns:
            CompiledGraph: Compiled LangGraph workflow
        """
        if self._compiled_graph is None:
            self._compiled_graph = self.graph.compile()
        return self._compiled_graph
    
    async def execute(
        self, 
        initial_state: PolicyValidationState,
        config: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationState:
        """
        Execute the complete workflow with the given initial state.
        
        Args:
            initial_state: Starting state for the workflow
            config: Optional configuration for execution
            
        Returns:
            PolicyValidationState: Final state after workflow completion
        """
        compiled_graph = self.compile()
        
        # Update audit trail for workflow start
        initial_state = update_state_audit(
            initial_state,
            node_name="workflow",
            status="started",
            input_hash=str(hash(str(initial_state)))
        )
        
        try:
            # Execute the workflow
            final_state = await compiled_graph.ainvoke(
                initial_state,
                config=config or {}
            )
            
            # Update audit trail for workflow completion
            final_state = update_state_audit(
                final_state,
                node_name="workflow",
                status="completed",
                input_hash=str(hash(str(initial_state))),
                output_hash=str(hash(str(final_state)))
            )
            
            return final_state
            
        except Exception as e:
            # Update audit trail for workflow failure
            initial_state = update_state_audit(
                initial_state,
                node_name="workflow",
                status="failed",
                input_hash=str(hash(str(initial_state))),
                error_message=str(e)
            )
            raise
    
    def get_graph_visualization(self) -> str:
        """
        Get a text representation of the workflow graph.
        
        Returns:
            str: Graph structure description
        """
        return """
Policy Validation Workflow Graph:

┌─────────────────┐
│   case_ingest   │ (Entry Point)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│intelligent_routing│
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ policy_retrieval│
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  rules_builder  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│decision_orchestrator│
└─────────┬───────┘
          │
          ▼ (conditional)
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌───────┐  ┌─────────────────┐
│ HITL  │  │insurer_connector│
│(END)  │  └─────────┬───────┘
└───────┘            │
                     ▼
              ┌─────────────────┐
              │ audited_closure │
              └─────────┬───────┘
                        │
                        ▼
                      (END)

Routing Logic:
- After decision_orchestrator:
  * HITL required → END (human review)
  * External query needed → insurer_connector
  * Auto-decision → audited_closure
- After insurer_connector → audited_closure
- After audited_closure → END
        """
    
    def get_node_info(self) -> Dict[str, str]:
        """
        Get information about each workflow node.
        
        Returns:
            Dict[str, str]: Node descriptions
        """
        return {
            "case_ingest": "Validates payload, normalizes fields, handles deduplication and idempotency",
            "intelligent_routing": "ML-powered classification, anomaly detection, and ETA prediction",
            "policy_retrieval": "RAG-based policy document retrieval with semantic search",
            "rules_builder": "Policy-as-code execution and checklist generation",
            "decision_orchestrator": "Multi-signal fusion and routing decision",
            "insurer_connector": "External insurer API/portal/email queries",
            "audited_closure": "Final decision persistence and audit trail generation"
        }


# ============================================================================
# Workflow Factory and Utilities
# ============================================================================

def create_workflow() -> PolicyValidationWorkflow:
    """
    Factory function to create a new PolicyValidationWorkflow instance.
    
    Returns:
        PolicyValidationWorkflow: Configured workflow instance
    """
    return PolicyValidationWorkflow()


def get_workflow_config(
    confidence_thresholds: Optional[Dict[str, float]] = None,
    risk_thresholds: Optional[Dict[str, float]] = None,
    enable_external_queries: bool = True,
    enable_hitl: bool = True
) -> Dict[str, Any]:
    """
    Create workflow configuration dictionary.
    
    Args:
        confidence_thresholds: Custom confidence threshold values
        risk_thresholds: Custom risk threshold values
        enable_external_queries: Whether to enable external insurer queries
        enable_hitl: Whether to enable human-in-the-loop routing
        
    Returns:
        Dict[str, Any]: Workflow configuration
    """
    default_confidence = {
        "high": 0.85,
        "medium": 0.65,
        "low": 0.45
    }
    
    default_risk = {
        "high": 0.75,
        "medium": 0.50,
        "low": 0.25
    }
    
    return {
        "confidence_thresholds": confidence_thresholds or default_confidence,
        "risk_thresholds": risk_thresholds or default_risk,
        "enable_external_queries": enable_external_queries,
        "enable_hitl": enable_hitl,
        "workflow_version": "1.0.0",
        "created_at": "2024-01-01T00:00:00Z"
    }


# ============================================================================
# Workflow Validation
# ============================================================================

def validate_workflow_state(state: PolicyValidationState) -> List[str]:
    """
    Validate workflow state for consistency and completeness.
    
    Args:
        state: State to validate
        
    Returns:
        List[str]: List of validation errors
    """
    errors = []
    
    # Check required fields are present
    if not state.get("case"):
        errors.append("Missing case data")
    
    if not state.get("audit"):
        errors.append("Missing audit data")
    
    # Check case state consistency
    case = state.get("case")
    if case:
        if case.state == CaseState.PROCESSING and not state.get("ml"):
            errors.append("Case is processing but ML data is missing")
        
        if case.state in [CaseState.APPROVED, CaseState.REJECTED]:
            decision = state.get("decision")
            if not decision or decision.status == DecisionStatus.PENDING:
                errors.append("Case is closed but decision is still pending")
    
    return errors


# ============================================================================
# Workflow Monitoring
# ============================================================================

class WorkflowMetrics:
    """Workflow execution metrics and monitoring."""
    
    def __init__(self):
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.hitl_count = 0
        self.external_query_count = 0
        self.auto_closure_count = 0
    
    def record_execution(self, state: PolicyValidationState, success: bool):
        """Record workflow execution metrics."""
        self.execution_count += 1
        
        if success:
            self.success_count += 1
            
            # Track routing decisions
            if state["hitl"].required:
                self.hitl_count += 1
            elif state["decision"].status == DecisionStatus.REQUIRES_EXTERNAL:
                self.external_query_count += 1
            else:
                self.auto_closure_count += 1
        else:
            self.failure_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        return {
            "total_executions": self.execution_count,
            "success_rate": self.success_count / max(self.execution_count, 1),
            "failure_rate": self.failure_count / max(self.execution_count, 1),
            "hitl_rate": self.hitl_count / max(self.success_count, 1),
            "external_query_rate": self.external_query_count / max(self.success_count, 1),
            "auto_closure_rate": self.auto_closure_count / max(self.success_count, 1)
        }


# Global metrics instance
workflow_metrics = WorkflowMetrics()
