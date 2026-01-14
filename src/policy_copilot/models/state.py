"""
LangGraph State Schema for Policy Validation Copilot

This module contains the complete state schema for the LangGraph workflow
as specified in Anexo A, integrating all component models.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .audit import AuditTrail
from .case import Case
from .checklist import Checklist
from .decision import Decision
from .evidence import EvidencePack
from .guardrails import GuardrailsResult
from .hitl import HITLState
from .ml import MLOutputs


class PolicyValidationState(BaseModel):
    """
    Complete LangGraph state schema for Policy Validation Copilot.
    
    Implements the state schema defined in Anexo A with all required
    components: case, evidence_pack, checklist, ml, decision, 
    guardrails, hitl, and audit.
    """
    
    # Core case information
    case: Case = Field(..., description="Case data with identifiers, service details, and metadata")
    
    # Evidence and policy retrieval
    evidence_pack: Optional[EvidencePack] = Field(None, description="Evidence pack with document references and coverage metrics")
    
    # Rule evaluation and compliance
    checklist: Optional[Checklist] = Field(None, description="Checklist with rule evaluation outcomes and missing fields")
    
    # Machine learning outputs
    ml: Optional[MLOutputs] = Field(None, description="ML service outputs with model versions")
    
    # Decision orchestration
    decision: Optional[Decision] = Field(None, description="Decision with confidence, risk, and next actions")
    
    # Security and governance
    guardrails: Optional[GuardrailsResult] = Field(None, description="Guardrails result with security flags and redactions")
    
    # Human-in-the-loop workflow
    hitl: Optional[HITLState] = Field(None, description="HITL state with questions, answers, and approvals")
    
    # Audit and traceability
    audit: AuditTrail = Field(..., description="Complete audit trail with node execution log and timestamps")
    
    # Workflow metadata
    workflow_id: str = Field(..., description="Unique workflow execution identifier")
    workflow_version: str = Field(..., description="LangGraph workflow version")
    state_version: str = Field("1.0.0", description="State schema version")
    
    # Execution status
    current_node: Optional[str] = Field(None, description="Currently executing node")
    completed_nodes: List[str] = Field(default_factory=list, description="List of completed node names")
    failed_nodes: List[str] = Field(default_factory=list, description="List of failed node names")
    
    # Workflow control
    should_continue: bool = Field(True, description="Whether workflow should continue execution")
    exit_reason: Optional[str] = Field(None, description="Reason for workflow exit if applicable")
    
    # Timing information
    workflow_started_at: datetime = Field(default_factory=datetime.utcnow, description="Workflow start timestamp")
    last_updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last state update timestamp")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Errors encountered during workflow")
    warnings: List[str] = Field(default_factory=list, description="Warnings generated during workflow")
    
    # Configuration references
    config_version: str = Field(..., description="Configuration version used")
    threshold_config_version: Optional[str] = Field(None, description="Threshold configuration version")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    
    @validator('workflow_id')
    def validate_workflow_id(cls, v):
        """Validate workflow ID format."""
        if not v or len(v) < 5:
            raise ValueError('Workflow ID must be at least 5 characters long')
        return v
    
    @validator('case')
    def validate_case_consistency(cls, v, values):
        """Validate case ID consistency across state components."""
        case_id = v.case_id
        
        # Check evidence pack consistency
        if 'evidence_pack' in values and values['evidence_pack']:
            if values['evidence_pack'].case_id != case_id:
                raise ValueError('Evidence pack case_id must match case case_id')
        
        # Check checklist consistency
        if 'checklist' in values and values['checklist']:
            if values['checklist'].case_id != case_id:
                raise ValueError('Checklist case_id must match case case_id')
        
        return v
    
    def update_node_status(self, node_name: str, status: str) -> None:
        """Update the status of a workflow node."""
        self.current_node = node_name if status == 'RUNNING' else None
        
        if status == 'COMPLETED' and node_name not in self.completed_nodes:
            self.completed_nodes.append(node_name)
        elif status == 'FAILED' and node_name not in self.failed_nodes:
            self.failed_nodes.append(node_name)
        
        self.last_updated_at = datetime.utcnow()
    
    def add_error(self, error_message: str, node_name: Optional[str] = None) -> None:
        """Add an error to the workflow state."""
        error_entry = f"{node_name}: {error_message}" if node_name else error_message
        self.errors.append(error_entry)
        self.last_updated_at = datetime.utcnow()
    
    def add_warning(self, warning_message: str, node_name: Optional[str] = None) -> None:
        """Add a warning to the workflow state."""
        warning_entry = f"{node_name}: {warning_message}" if node_name else warning_message
        self.warnings.append(warning_entry)
        self.last_updated_at = datetime.utcnow()
    
    def stop_workflow(self, reason: str) -> None:
        """Stop the workflow execution with a reason."""
        self.should_continue = False
        self.exit_reason = reason
        self.current_node = None
        self.last_updated_at = datetime.utcnow()
    
    def is_complete(self) -> bool:
        """Check if the workflow is complete."""
        return (
            not self.should_continue or
            self.decision is not None or
            len(self.failed_nodes) > 0
        )
    
    def requires_hitl(self) -> bool:
        """Check if the workflow requires human-in-the-loop intervention."""
        return (
            (self.hitl and self.hitl.required) or
            (self.decision and self.decision.requires_hitl()) or
            (self.guardrails and self.guardrails.requires_hitl()) or
            (self.ml and self.ml.requires_human_review())
        )
    
    def can_auto_close(self) -> bool:
        """Check if the case can be automatically closed."""
        return (
            self.decision is not None and
            self.decision.should_auto_close() and
            not self.requires_hitl() and
            len(self.errors) == 0
        )
    
    def get_workflow_summary(self) -> Dict[str, any]:
        """Get a summary of the current workflow state."""
        return {
            'workflow_id': self.workflow_id,
            'case_id': self.case.case_id,
            'current_node': self.current_node,
            'completed_nodes_count': len(self.completed_nodes),
            'failed_nodes_count': len(self.failed_nodes),
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings),
            'should_continue': self.should_continue,
            'exit_reason': self.exit_reason,
            'requires_hitl': self.requires_hitl(),
            'can_auto_close': self.can_auto_close(),
            'is_complete': self.is_complete(),
            'workflow_started_at': self.workflow_started_at,
            'last_updated_at': self.last_updated_at,
            'case_status': self.case.state,
            'decision_status': self.decision.status if self.decision else None,
            'ml_confidence': self.ml.overall_confidence if self.ml else None,
            'guardrails_decision': self.guardrails.decision if self.guardrails else None,
            'evidence_coverage': self.evidence_pack.coverage_score if self.evidence_pack else None,
            'checklist_compliance': self.checklist.compliance_score if self.checklist else None
        }
    
    def get_next_actions(self) -> List[str]:
        """Get recommended next actions based on current state."""
        actions = []
        
        # Check for required HITL actions
        if self.requires_hitl():
            if self.hitl and self.hitl.get_pending_questions():
                actions.append("ANSWER_HITL_QUESTIONS")
            if self.decision and self.decision.escalation_required:
                actions.append("ESCALATE_CASE")
            if self.guardrails and self.guardrails.requires_hitl():
                actions.append("SECURITY_REVIEW")
        
        # Check for auto-closure eligibility
        elif self.can_auto_close():
            actions.append("AUTO_CLOSE")
        
        # Check for missing components
        else:
            if not self.evidence_pack:
                actions.append("RETRIEVE_EVIDENCE")
            if not self.checklist:
                actions.append("BUILD_CHECKLIST")
            if not self.ml:
                actions.append("RUN_ML_SERVICES")
            if not self.decision:
                actions.append("MAKE_DECISION")
        
        # Check for error recovery
        if self.failed_nodes:
            actions.append("RETRY_FAILED_NODES")
        
        return actions
    
    def validate_state_consistency(self) -> List[str]:
        """Validate consistency across all state components."""
        issues = []
        
        # Check case ID consistency
        case_id = self.case.case_id
        
        if self.evidence_pack and self.evidence_pack.case_id != case_id:
            issues.append("Evidence pack case_id mismatch")
        
        if self.checklist and self.checklist.case_id != case_id:
            issues.append("Checklist case_id mismatch")
        
        if self.ml and self.ml.case_id != case_id:
            issues.append("ML outputs case_id mismatch")
        
        if self.decision and self.decision.case_id != case_id:
            issues.append("Decision case_id mismatch")
        
        if self.guardrails and self.guardrails.case_id != case_id:
            issues.append("Guardrails case_id mismatch")
        
        if self.hitl and self.hitl.case_id != case_id:
            issues.append("HITL state case_id mismatch")
        
        if self.audit.case_id != case_id:
            issues.append("Audit trail case_id mismatch")
        
        # Check workflow ID consistency
        if self.audit.workflow_id != self.workflow_id:
            issues.append("Audit trail workflow_id mismatch")
        
        # Check decision consistency with other components
        if self.decision and self.ml:
            if abs(self.decision.ml_confidence - self.ml.overall_confidence) > 0.1:
                issues.append("Decision ML confidence mismatch")
        
        if self.decision and self.checklist:
            if abs(self.decision.checklist_score - self.checklist.compliance_score) > 0.1:
                issues.append("Decision checklist score mismatch")
        
        if self.decision and self.evidence_pack:
            if abs(self.decision.coverage_score - self.evidence_pack.coverage_score) > 0.1:
                issues.append("Decision coverage score mismatch")
        
        return issues
    
    def to_checkpoint(self) -> Dict[str, any]:
        """Convert state to checkpoint format for persistence."""
        return {
            'workflow_id': self.workflow_id,
            'case_id': self.case.case_id,
            'state_version': self.state_version,
            'checkpoint_timestamp': datetime.utcnow().isoformat(),
            'current_node': self.current_node,
            'completed_nodes': self.completed_nodes,
            'failed_nodes': self.failed_nodes,
            'should_continue': self.should_continue,
            'exit_reason': self.exit_reason,
            'errors': self.errors,
            'warnings': self.warnings,
            'case': self.case.dict(),
            'evidence_pack': self.evidence_pack.dict() if self.evidence_pack else None,
            'checklist': self.checklist.dict() if self.checklist else None,
            'ml': self.ml.dict() if self.ml else None,
            'decision': self.decision.dict() if self.decision else None,
            'guardrails': self.guardrails.dict() if self.guardrails else None,
            'hitl': self.hitl.dict() if self.hitl else None,
            'audit_summary': self.audit.get_execution_summary()
        }
    
    @classmethod
    def from_checkpoint(cls, checkpoint_data: Dict[str, any], audit_trail: AuditTrail) -> 'PolicyValidationState':
        """Restore state from checkpoint data."""
        # Reconstruct component models
        case = Case(**checkpoint_data['case'])
        
        evidence_pack = None
        if checkpoint_data.get('evidence_pack'):
            evidence_pack = EvidencePack(**checkpoint_data['evidence_pack'])
        
        checklist = None
        if checkpoint_data.get('checklist'):
            checklist = Checklist(**checkpoint_data['checklist'])
        
        ml = None
        if checkpoint_data.get('ml'):
            ml = MLOutputs(**checkpoint_data['ml'])
        
        decision = None
        if checkpoint_data.get('decision'):
            decision = Decision(**checkpoint_data['decision'])
        
        guardrails = None
        if checkpoint_data.get('guardrails'):
            guardrails = GuardrailsResult(**checkpoint_data['guardrails'])
        
        hitl = None
        if checkpoint_data.get('hitl'):
            hitl = HITLState(**checkpoint_data['hitl'])
        
        # Create state instance
        return cls(
            case=case,
            evidence_pack=evidence_pack,
            checklist=checklist,
            ml=ml,
            decision=decision,
            guardrails=guardrails,
            hitl=hitl,
            audit=audit_trail,
            workflow_id=checkpoint_data['workflow_id'],
            workflow_version=checkpoint_data.get('workflow_version', '1.0.0'),
            state_version=checkpoint_data.get('state_version', '1.0.0'),
            current_node=checkpoint_data.get('current_node'),
            completed_nodes=checkpoint_data.get('completed_nodes', []),
            failed_nodes=checkpoint_data.get('failed_nodes', []),
            should_continue=checkpoint_data.get('should_continue', True),
            exit_reason=checkpoint_data.get('exit_reason'),
            errors=checkpoint_data.get('errors', []),
            warnings=checkpoint_data.get('warnings', []),
            config_version=checkpoint_data.get('config_version', '1.0.0')
        )


# Export all models for easy importing
__all__ = [
    'PolicyValidationState',
    'Case',
    'EvidencePack',
    'Checklist',
    'MLOutputs',
    'Decision',
    'GuardrailsResult',
    'HITLState',
    'AuditTrail'
]
