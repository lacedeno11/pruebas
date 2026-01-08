"""
LangGraph Policy Validation Workflow

This module implements the complete LangGraph workflow for the Policy Validation Copilot system,
orchestrating all nodes and agents with proper state transitions, conditional routing, error handling,
and HITL integration points.

Workflow Structure:
CRM Webhook -> Case Ingest -> Guardrails -> Intelligent Routing -> Policy Retrieval (RAG) -> 
Rules & Checklist Builder -> Decision Orchestrator -> (HITL or Auto-close) -> Audited Closure
"""

from typing import Dict, Any, List, Optional, Literal, TypedDict
from datetime import datetime
import logging
import asyncio
from langgraph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from ..state import PolicyValidationState, DecisionStatus, CaseState
from ..nodes.case_ingest import CaseIngestNode, create_case_ingest_node
from ..nodes.intelligent_routing import IntelligentRoutingNode, create_intelligent_routing_node
from ..nodes.audited_closure import AuditedClosureNode, create_audited_closure_node
from ..agents.policy_retrieval import PolicyRetrievalAgent, create_policy_retrieval_agent
from ..agents.rules_checklist import RulesChecklistAgent, create_rules_checklist_agent
from ..agents.decision_orchestrator import DecisionOrchestratorAgent, create_decision_orchestrator_agent
from ..agents.insurer_connector import InsurerConnectorAgent, create_insurer_connector_agent
from ..guardrails import GuardrailEngine, create_guardrail_engine
from ..database import get_repository_factory

logger = logging.getLogger(__name__)


class WorkflowConfig(TypedDict):
    """Workflow configuration"""
    use_mock: bool
    enable_hitl: bool
    enable_auto_closure: bool
    enable_external_queries: bool
    max_workflow_duration_hours: int
    checkpoint_enabled: bool


class WorkflowMetrics(TypedDict):
    """Workflow execution metrics"""
    total_executions: int
    successful_completions: int
    failed_executions: int
    hitl_escalations: int
    auto_closures: int
    avg_processing_time_ms: int
    node_execution_counts: Dict[str, int]


class PolicyValidationWorkflow:
    """
    Complete LangGraph workflow for policy validation.
    
    Orchestrates all nodes and agents with proper state transitions,
    conditional routing, error handling, and HITL integration.
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        self.config = config or WorkflowConfig(
            use_mock=False,
            enable_hitl=True,
            enable_auto_closure=True,
            enable_external_queries=True,
            max_workflow_duration_hours=48,
            checkpoint_enabled=True
        )
        
        # Initialize components
        self.case_ingest_node = create_case_ingest_node(self.config["use_mock"])
        self.intelligent_routing_node = create_intelligent_routing_node(self.config["use_mock"])
        self.audited_closure_node = create_audited_closure_node(self.config["use_mock"])
        
        self.policy_retrieval_agent = create_policy_retrieval_agent(self.config["use_mock"])
        self.rules_checklist_agent = create_rules_checklist_agent(self.config["use_mock"])
        self.decision_orchestrator_agent = create_decision_orchestrator_agent(self.config["use_mock"])
        self.insurer_connector_agent = create_insurer_connector_agent(self.config["use_mock"])
        
        self.guardrail_engine = create_guardrail_engine(self.config["use_mock"])
        
        # Repository factory
        self.repo_factory = get_repository_factory()
        
        # Build workflow graph
        self.workflow = self._build_workflow_graph()
        
        # Workflow metrics
        self.metrics = WorkflowMetrics(
            total_executions=0,
            successful_completions=0,
            failed_executions=0,
            hitl_escalations=0,
            auto_closures=0,
            avg_processing_time_ms=0,
            node_execution_counts={}
        )
    
    def _build_workflow_graph(self) -> StateGraph:
        """Build the complete LangGraph workflow"""
        
        # Create state graph
        workflow = StateGraph(PolicyValidationState)
        
        # Add nodes
        workflow.add_node("case_ingest", self._case_ingest_node)
        workflow.add_node("guardrails_validation", self._guardrails_validation_node)
        workflow.add_node("intelligent_routing", self._intelligent_routing_node)
        workflow.add_node("policy_retrieval", self._policy_retrieval_node)
        workflow.add_node("rules_checklist", self._rules_checklist_node)
        workflow.add_node("decision_orchestrator", self._decision_orchestrator_node)
        workflow.add_node("external_query", self._external_query_node)
        workflow.add_node("hitl_review", self._hitl_review_node)
        workflow.add_node("audited_closure", self._audited_closure_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Set entry point
        workflow.set_entry_point("case_ingest")
        
        # Add edges with conditional routing
        workflow.add_edge("case_ingest", "guardrails_validation")
        
        # Guardrails routing
        workflow.add_conditional_edges(
            "guardrails_validation",
            self._route_after_guardrails,
            {
                "continue": "intelligent_routing",
                "block": "error_handler",
                "manual_review": "hitl_review"
            }
        )
        
        # Intelligent routing
        workflow.add_conditional_edges(
            "intelligent_routing",
            self._route_after_intelligent_routing,
            {
                "policy_retrieval": "policy_retrieval",
                "manual_review": "hitl_review",
                "fraud_investigation": "hitl_review",
                "emergency": "policy_retrieval"
            }
        )
        
        # Policy retrieval routing
        workflow.add_conditional_edges(
            "policy_retrieval",
            self._route_after_policy_retrieval,
            {
                "rules_checklist": "rules_checklist",
                "external_query": "external_query",
                "insufficient_coverage": "hitl_review"
            }
        )
        
        # External query routing
        workflow.add_conditional_edges(
            "external_query",
            self._route_after_external_query,
            {
                "policy_retrieval": "policy_retrieval",
                "rules_checklist": "rules_checklist",
                "timeout": "hitl_review"
            }
        )
        
        # Rules checklist routing
        workflow.add_conditional_edges(
            "rules_checklist",
            self._route_after_rules_checklist,
            {
                "decision_orchestrator": "decision_orchestrator",
                "external_query": "external_query",
                "missing_fields": "hitl_review"
            }
        )
        
        # Decision orchestrator routing
        workflow.add_conditional_edges(
            "decision_orchestrator",
            self._route_after_decision_orchestrator,
            {
                "auto_closure": "audited_closure",
                "hitl_review": "hitl_review",
                "external_query": "external_query"
            }
        )
        
        # HITL review routing
        workflow.add_conditional_edges(
            "hitl_review",
            self._route_after_hitl_review,
            {
                "audited_closure": "audited_closure",
                "policy_retrieval": "policy_retrieval",
                "rules_checklist": "rules_checklist",
                "external_query": "external_query"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("audited_closure", END)
        workflow.add_edge("error_handler", END)
        
        return workflow
    
    async def _case_ingest_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Case ingestion node wrapper"""
        try:
            logger.info(f"Executing case_ingest for case {state.get('case', {}).get('case_id', 'unknown')}")
            
            # Update node execution log
            await self._log_node_execution(state, "case_ingest", "STARTED")
            
            # Execute case ingestion
            updated_state = await self.case_ingest_node.ingest_case(state)
            
            # Update case state
            updated_state["case"]["state"] = CaseState.INGESTED
            
            await self._log_node_execution(updated_state, "case_ingest", "COMPLETED")
            self._update_node_metrics("case_ingest")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Case ingest failed: {e}")
            await self._log_node_execution(state, "case_ingest", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _guardrails_validation_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Guardrails validation node wrapper"""
        try:
            logger.info(f"Executing guardrails_validation for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "guardrails_validation", "STARTED")
            
            # Execute guardrails validation
            updated_state = await self.guardrail_engine.evaluate_case(state)
            
            # Update case state based on guardrails result
            guardrails_decision = updated_state.get("guardrails", {}).get("decision", "ALLOW")
            if guardrails_decision == "BLOCK":
                updated_state["case"]["state"] = CaseState.BLOCKED
            elif guardrails_decision == "REQUIRE_HITL":
                updated_state["case"]["state"] = CaseState.REQUIRES_REVIEW
            else:
                updated_state["case"]["state"] = CaseState.VALIDATED
            
            await self._log_node_execution(updated_state, "guardrails_validation", "COMPLETED")
            self._update_node_metrics("guardrails_validation")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Guardrails validation failed: {e}")
            await self._log_node_execution(state, "guardrails_validation", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _intelligent_routing_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Intelligent routing node wrapper"""
        try:
            logger.info(f"Executing intelligent_routing for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "intelligent_routing", "STARTED")
            
            # Execute intelligent routing
            updated_state = await self.intelligent_routing_node.route_case(state)
            
            # Update case state
            updated_state["case"]["state"] = CaseState.ROUTED
            
            await self._log_node_execution(updated_state, "intelligent_routing", "COMPLETED")
            self._update_node_metrics("intelligent_routing")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Intelligent routing failed: {e}")
            await self._log_node_execution(state, "intelligent_routing", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _policy_retrieval_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Policy retrieval node wrapper"""
        try:
            logger.info(f"Executing policy_retrieval for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "policy_retrieval", "STARTED")
            
            # Execute policy retrieval
            updated_state = await self.policy_retrieval_agent.retrieve_policies(state)
            
            # Update case state
            updated_state["case"]["state"] = CaseState.EVIDENCE_GATHERED
            
            await self._log_node_execution(updated_state, "policy_retrieval", "COMPLETED")
            self._update_node_metrics("policy_retrieval")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Policy retrieval failed: {e}")
            await self._log_node_execution(state, "policy_retrieval", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _rules_checklist_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Rules checklist node wrapper"""
        try:
            logger.info(f"Executing rules_checklist for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "rules_checklist", "STARTED")
            
            # Execute rules and checklist evaluation
            updated_state = await self.rules_checklist_agent.evaluate_checklist(state)
            
            # Update case state
            updated_state["case"]["state"] = CaseState.EVALUATED
            
            await self._log_node_execution(updated_state, "rules_checklist", "COMPLETED")
            self._update_node_metrics("rules_checklist")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Rules checklist failed: {e}")
            await self._log_node_execution(state, "rules_checklist", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _decision_orchestrator_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Decision orchestrator node wrapper"""
        try:
            logger.info(f"Executing decision_orchestrator for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "decision_orchestrator", "STARTED")
            
            # Execute decision orchestration
            updated_state = await self.decision_orchestrator_agent.make_decision(state)
            
            # Update case state based on decision
            decision_status = updated_state.get("decision", {}).get("status")
            if decision_status in [DecisionStatus.APROBADO, DecisionStatus.RECHAZADO]:
                updated_state["case"]["state"] = CaseState.DECIDED
            else:
                updated_state["case"]["state"] = CaseState.REQUIRES_REVIEW
            
            await self._log_node_execution(updated_state, "decision_orchestrator", "COMPLETED")
            self._update_node_metrics("decision_orchestrator")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Decision orchestrator failed: {e}")
            await self._log_node_execution(state, "decision_orchestrator", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _external_query_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """External query node wrapper"""
        try:
            logger.info(f"Executing external_query for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "external_query", "STARTED")
            
            # Execute external query
            updated_state = await self.insurer_connector_agent.query_external_systems(state)
            
            # Update case state
            updated_state["case"]["state"] = CaseState.EXTERNAL_QUERY_COMPLETED
            
            await self._log_node_execution(updated_state, "external_query", "COMPLETED")
            self._update_node_metrics("external_query")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"External query failed: {e}")
            await self._log_node_execution(state, "external_query", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _hitl_review_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """HITL review node wrapper"""
        try:
            logger.info(f"Executing hitl_review for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "hitl_review", "STARTED")
            
            # Initialize HITL if not present
            if "hitl" not in state:
                state["hitl"] = {
                    "required": True,
                    "status": "PENDING",
                    "assigned_to": None,
                    "assigned_at": datetime.utcnow(),
                    "questions": [],
                    "responses": [],
                    "approvals": []
                }
            
            # Update case state
            state["case"]["state"] = CaseState.REQUIRES_REVIEW
            
            # In a real implementation, this would wait for human input
            # For now, we'll simulate HITL completion
            if self.config["enable_hitl"]:
                # Simulate HITL processing
                await self._simulate_hitl_processing(state)
            else:
                # Skip HITL and proceed with default decision
                state["hitl"]["status"] = "SKIPPED"
                state["hitl"]["completed_at"] = datetime.utcnow()
            
            await self._log_node_execution(state, "hitl_review", "COMPLETED")
            self._update_node_metrics("hitl_review")
            self.metrics["hitl_escalations"] += 1
            
            return state
            
        except Exception as e:
            logger.error(f"HITL review failed: {e}")
            await self._log_node_execution(state, "hitl_review", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _audited_closure_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Audited closure node wrapper"""
        try:
            logger.info(f"Executing audited_closure for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "audited_closure", "STARTED")
            
            # Execute audited closure
            updated_state = await self.audited_closure_node.close_case(
                state, 
                user_id="SYSTEM",
                closure_reason="Workflow completion"
            )
            
            # Update case state
            updated_state["case"]["state"] = CaseState.CLOSED
            
            await self._log_node_execution(updated_state, "audited_closure", "COMPLETED")
            self._update_node_metrics("audited_closure")
            
            # Check if this was auto-closure
            decision_status = updated_state.get("decision", {}).get("status")
            if decision_status in [DecisionStatus.APROBADO, DecisionStatus.RECHAZADO]:
                self.metrics["auto_closures"] += 1
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Audited closure failed: {e}")
            await self._log_node_execution(state, "audited_closure", "FAILED", str(e))
            state["case"]["state"] = CaseState.ERROR
            raise
    
    async def _error_handler_node(self, state: PolicyValidationState) -> PolicyValidationState:
        """Error handler node wrapper"""
        try:
            logger.info(f"Executing error_handler for case {state['case']['case_id']}")
            
            await self._log_node_execution(state, "error_handler", "STARTED")
            
            # Update case state
            state["case"]["state"] = CaseState.ERROR
            
            # Create error decision
            state["decision"] = {
                "status": DecisionStatus.RECHAZADO,
                "confidence": 0.0,
                "risk_score": 1.0,
                "explanation": "Case rejected due to workflow error or security violation",
                "next_actions": ["MANUAL_INVESTIGATION"],
                "is_final": True,
                "decided_at": datetime.utcnow(),
                "decided_by": "SYSTEM"
            }
            
            await self._log_node_execution(state, "error_handler", "COMPLETED")
            self._update_node_metrics("error_handler")
            
            return state
            
        except Exception as e:
            logger.error(f"Error handler failed: {e}")
            await self._log_node_execution(state, "error_handler", "FAILED", str(e))
            raise
    
    # Conditional routing functions
    
    def _route_after_guardrails(self, state: PolicyValidationState) -> Literal["continue", "block", "manual_review"]:
        """Route after guardrails validation"""
        guardrails = state.get("guardrails", {})
        decision = guardrails.get("decision", "ALLOW")
        
        if decision == "BLOCK":
            return "block"
        elif decision == "REQUIRE_HITL":
            return "manual_review"
        else:
            return "continue"
    
    def _route_after_intelligent_routing(self, state: PolicyValidationState) -> Literal["policy_retrieval", "manual_review", "fraud_investigation", "emergency"]:
        """Route after intelligent routing"""
        case = state.get("case", {})
        routing_decision = case.get("routing_decision", "AUTO_PROCESS")
        
        if routing_decision == "FRAUD_INVESTIGATION":
            return "fraud_investigation"
        elif routing_decision == "MANUAL_REVIEW":
            return "manual_review"
        elif routing_decision == "EMERGENCY_FAST_TRACK":
            return "emergency"
        else:
            return "policy_retrieval"
    
    def _route_after_policy_retrieval(self, state: PolicyValidationState) -> Literal["rules_checklist", "external_query", "insufficient_coverage"]:
        """Route after policy retrieval"""
        evidence_pack = state.get("evidence_pack", {})
        coverage_score = evidence_pack.get("coverage_score", 0.0)
        
        # Check if external query is needed
        if evidence_pack.get("requires_external_query", False) and self.config["enable_external_queries"]:
            return "external_query"
        
        # Check coverage threshold
        if coverage_score < 0.6:  # Configurable threshold
            return "insufficient_coverage"
        
        return "rules_checklist"
    
    def _route_after_external_query(self, state: PolicyValidationState) -> Literal["policy_retrieval", "rules_checklist", "timeout"]:
        """Route after external query"""
        external_query_result = state.get("external_query_result", {})
        
        if external_query_result.get("timeout", False):
            return "timeout"
        
        # If new evidence was found, go back to policy retrieval
        if external_query_result.get("new_evidence_found", False):
            return "policy_retrieval"
        
        return "rules_checklist"
    
    def _route_after_rules_checklist(self, state: PolicyValidationState) -> Literal["decision_orchestrator", "external_query", "missing_fields"]:
        """Route after rules checklist"""
        checklist = state.get("checklist", {})
        missing_fields = checklist.get("missing_fields", [])
        
        # Check if external query can resolve missing fields
        if missing_fields and self.config["enable_external_queries"]:
            return "external_query"
        
        # Check if too many missing fields for automatic processing
        if len(missing_fields) > 3:  # Configurable threshold
            return "missing_fields"
        
        return "decision_orchestrator"
    
    def _route_after_decision_orchestrator(self, state: PolicyValidationState) -> Literal["auto_closure", "hitl_review", "external_query"]:
        """Route after decision orchestrator"""
        decision = state.get("decision", {})
        
        # Check if external query is recommended
        if decision.get("requires_external_query", False) and self.config["enable_external_queries"]:
            return "external_query"
        
        # Check if HITL is required
        if decision.get("requires_hitl", False):
            return "hitl_review"
        
        # Check auto-closure conditions
        if self.config["enable_auto_closure"] and decision.get("auto_closure_eligible", False):
            return "auto_closure"
        
        return "hitl_review"
    
    def _route_after_hitl_review(self, state: PolicyValidationState) -> Literal["audited_closure", "policy_retrieval", "rules_checklist", "external_query"]:
        """Route after HITL review"""
        hitl = state.get("hitl", {})
        hitl_decision = hitl.get("decision", "PROCEED")
        
        if hitl_decision == "PROCEED":
            return "audited_closure"
        elif hitl_decision == "RETRY_POLICY_RETRIEVAL":
            return "policy_retrieval"
        elif hitl_decision == "RETRY_RULES_CHECKLIST":
            return "rules_checklist"
        elif hitl_decision == "EXTERNAL_QUERY":
            return "external_query"
        else:
            return "audited_closure"
    
    # Helper methods
    
    async def _log_node_execution(
        self, 
        state: PolicyValidationState, 
        node_name: str, 
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Log node execution for audit trail"""
        
        if "audit" not in state:
            state["audit"] = {
                "node_execution_log": [],
                "export_logs": [],
                "access_logs": []
            }
        
        execution_log = {
            "node_name": node_name,
            "status": status,
            "timestamp": datetime.utcnow(),
            "processing_time_ms": 0,  # Would be calculated in real implementation
            "error_message": error_message
        }
        
        state["audit"]["node_execution_log"].append(execution_log)
    
    def _update_node_metrics(self, node_name: str) -> None:
        """Update node execution metrics"""
        if node_name not in self.metrics["node_execution_counts"]:
            self.metrics["node_execution_counts"][node_name] = 0
        
        self.metrics["node_execution_counts"][node_name] += 1
    
    async def _simulate_hitl_processing(self, state: PolicyValidationState) -> None:
        """Simulate HITL processing for testing"""
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        hitl = state["hitl"]
        hitl["status"] = "COMPLETED"
        hitl["completed_at"] = datetime.utcnow()
        hitl["decision"] = "PROCEED"
        hitl["reviewer_id"] = "SIMULATED_REVIEWER"
        hitl["review_notes"] = "Simulated HITL review completed"
    
    # Public interface
    
    async def execute_workflow(self, initial_state: PolicyValidationState) -> PolicyValidationState:
        """
        Execute the complete policy validation workflow.
        
        Args:
            initial_state: Initial state with case information
            
        Returns:
            Final state after workflow completion
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting policy validation workflow for case {initial_state.get('case', {}).get('case_id', 'unknown')}")
            
            # Update metrics
            self.metrics["total_executions"] += 1
            
            # Compile and execute workflow
            app = self.workflow.compile(
                checkpointer=MemorySaver() if self.config["checkpoint_enabled"] else None
            )
            
            # Execute workflow
            final_state = await app.ainvoke(initial_state)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update metrics
            self.metrics["successful_completions"] += 1
            self._update_avg_processing_time(processing_time)
            
            logger.info(
                f"Policy validation workflow completed for case {final_state.get('case', {}).get('case_id', 'unknown')}: "
                f"status={final_state.get('case', {}).get('state', 'unknown')}, "
                f"processing_time={processing_time}ms"
            )
            
            return final_state
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"Policy validation workflow failed: {e}")
            
            # Update error metrics
            self.metrics["failed_executions"] += 1
            self._update_avg_processing_time(processing_time)
            
            # Return error state
            error_state = initial_state.copy()
            error_state["case"]["state"] = CaseState.ERROR
            error_state["workflow_error"] = {
                "error_message": str(e),
                "processing_time_ms": int(processing_time),
                "failed_at": datetime.utcnow()
            }
            
            return error_state
    
    def _update_avg_processing_time(self, processing_time_ms: float) -> None:
        """Update average processing time"""
        total_executions = self.metrics["total_executions"]
        current_avg = self.metrics["avg_processing_time_ms"]
        
        # Calculate new average
        new_avg = ((current_avg * (total_executions - 1)) + processing_time_ms) / total_executions
        self.metrics["avg_processing_time_ms"] = int(new_avg)
    
    def get_workflow_metrics(self) -> WorkflowMetrics:
        """Get workflow execution metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset workflow metrics"""
        self.metrics = WorkflowMetrics(
            total_executions=0,
            successful_completions=0,
            failed_executions=0,
            hitl_escalations=0,
            auto_closures=0,
            avg_processing_time_ms=0,
            node_execution_counts={}
        )
    
    def update_config(self, new_config: WorkflowConfig) -> None:
        """Update workflow configuration"""
        self.config.update(new_config)
        logger.info("Workflow configuration updated")


# Factory functions

def create_policy_validation_workflow(config: Optional[WorkflowConfig] = None) -> PolicyValidationWorkflow:
    """
    Factory function to create policy validation workflow.
    
    Args:
        config: Workflow configuration
        
    Returns:
        Configured policy validation workflow
    """
    return PolicyValidationWorkflow(config)


def create_default_workflow() -> PolicyValidationWorkflow:
    """Create workflow with default configuration"""
    return create_policy_validation_workflow()


def create_mock_workflow() -> PolicyValidationWorkflow:
    """Create workflow with mock services for testing"""
    config = WorkflowConfig(
        use_mock=True,
        enable_hitl=True,
        enable_auto_closure=True,
        enable_external_queries=False,  # Disable for faster testing
        max_workflow_duration_hours=1,
        checkpoint_enabled=False
    )
    return create_policy_validation_workflow(config)


# Workflow execution helper

async def execute_policy_validation(
    crm_payload: Dict[str, Any],
    config: Optional[WorkflowConfig] = None
) -> PolicyValidationState:
    """
    Execute complete policy validation workflow from CRM payload.
    
    Args:
        crm_payload: CRM webhook payload
        config: Workflow configuration
        
    Returns:
        Final workflow state
    """
    from ..state import create_case_from_crm_payload, create_initial_state
    
    # Create initial state from CRM payload
    case = create_case_from_crm_payload(crm_payload)
    initial_state = create_initial_state(case)
    
    # Create and execute workflow
    workflow = create_policy_validation_workflow(config)
    final_state = await workflow.execute_workflow(initial_state)
    
    return final_state
