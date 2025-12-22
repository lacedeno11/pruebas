"""
Human-in-the-Loop (HITL) data model for Policy Validation Copilot

This module contains the HITL model for human review interfaces and
approval workflows as specified in Anexo A.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, Priority


class HITLQuestion(BaseEntity):
    """
    Question for human reviewer in HITL workflow.
    
    Represents specific questions that need human input
    for case resolution or decision making.
    """
    
    question_id: str = Field(..., description="Unique question identifier")
    question_text: str = Field(..., description="Question text for reviewer")
    question_type: str = Field(..., description="Type of question (BINARY, MULTIPLE_CHOICE, TEXT, NUMERIC)")
    
    # Question options (for multiple choice)
    options: List[str] = Field(default_factory=list, description="Available answer options")
    
    # Question metadata
    category: str = Field(..., description="Question category (POLICY, EVIDENCE, RISK, etc.)")
    priority: Priority = Field(Priority.MEDIUM, description="Question priority")
    required: bool = Field(True, description="Whether answer is required")
    
    # Context information
    context: Optional[str] = Field(None, description="Additional context for question")
    evidence_refs: List[UUID] = Field(default_factory=list, description="Related evidence item references")
    rule_refs: List[str] = Field(default_factory=list, description="Related rule references")
    
    # Answer tracking
    answered: bool = Field(False, description="Whether question has been answered")
    answer: Optional[str] = Field(None, description="Answer provided by reviewer")
    answer_confidence: Optional[float] = Field(None, description="Reviewer confidence in answer")
    
    # Metadata
    created_for_case: str = Field(..., description="Case ID this question was created for")
    created_by: str = Field(..., description="System or agent that created question")
    
    @validator('question_type')
    def validate_question_type(cls, v):
        """Validate question type is from allowed set."""
        valid_types = ['BINARY', 'MULTIPLE_CHOICE', 'TEXT', 'NUMERIC', 'DATE', 'RATING']
        if v not in valid_types:
            raise ValueError(f'Question type must be one of: {valid_types}')
        return v
    
    @validator('answer')
    def validate_answer_with_options(cls, v, values):
        """Validate answer is valid for question type."""
        if v is not None and 'question_type' in values and 'options' in values:
            q_type = values['question_type']
            options = values['options']
            
            if q_type == 'MULTIPLE_CHOICE' and options and v not in options:
                raise ValueError(f'Answer must be one of: {options}')
            
            if q_type == 'BINARY' and v not in ['YES', 'NO', 'TRUE', 'FALSE']:
                raise ValueError('Binary question answer must be YES/NO or TRUE/FALSE')
        
        return v


class HITLApproval(BaseEntity):
    """
    Approval record for HITL workflow.
    
    Tracks approval decisions made by human reviewers
    with rationale and supporting information.
    """
    
    approval_id: str = Field(..., description="Unique approval identifier")
    case_id: str = Field(..., description="Associated case identifier")
    
    # Approval decision
    decision: str = Field(..., description="Approval decision (APPROVED, REJECTED, ESCALATED)")
    rationale: str = Field(..., description="Rationale for approval decision")
    
    # Reviewer information
    reviewer_id: str = Field(..., description="Reviewer identifier")
    reviewer_role: str = Field(..., description="Reviewer role (AGENT, SUPERVISOR, SPECIALIST)")
    reviewer_level: int = Field(..., description="Reviewer authorization level")
    
    # Approval metadata
    approval_type: str = Field(..., description="Type of approval (CASE, EXCEPTION, POLICY)")
    approval_scope: List[str] = Field(default_factory=list, description="Scope of approval")
    
    # Supporting information
    supporting_evidence: List[UUID] = Field(default_factory=list, description="Supporting evidence references")
    additional_comments: Optional[str] = Field(None, description="Additional reviewer comments")
    
    # Conditions and restrictions
    conditions: List[str] = Field(default_factory=list, description="Conditions attached to approval")
    restrictions: List[str] = Field(default_factory=list, description="Restrictions on approval")
    expiry_date: Optional[datetime] = Field(None, description="Approval expiry date")
    
    # Workflow tracking
    approved_at: datetime = Field(default_factory=datetime.utcnow, description="Approval timestamp")
    escalated_from: Optional[str] = Field(None, description="Previous reviewer if escalated")
    
    @validator('decision')
    def validate_decision(cls, v):
        """Validate approval decision is from allowed set."""
        valid_decisions = ['APPROVED', 'REJECTED', 'ESCALATED', 'DEFERRED', 'CONDITIONAL']
        if v not in valid_decisions:
            raise ValueError(f'Decision must be one of: {valid_decisions}')
        return v
    
    @validator('reviewer_level')
    def validate_reviewer_level(cls, v):
        """Validate reviewer level is positive."""
        if v < 1:
            raise ValueError('Reviewer level must be positive')
        return v


class HITLAssignment(BaseEntity):
    """
    HITL assignment record for queue and agent management.
    
    Tracks assignment of cases to human reviewers with
    workload balancing and priority handling.
    """
    
    assignment_id: str = Field(..., description="Unique assignment identifier")
    case_id: str = Field(..., description="Associated case identifier")
    
    # Assignment details
    assigned_to: str = Field(..., description="Assigned reviewer identifier")
    assigned_queue: str = Field(..., description="Assigned queue name")
    assignment_reason: str = Field(..., description="Reason for assignment")
    
    # Priority and SLA
    priority: Priority = Field(Priority.MEDIUM, description="Assignment priority")
    sla_target: datetime = Field(..., description="SLA target for completion")
    escalation_threshold: datetime = Field(..., description="Escalation threshold")
    
    # Assignment status
    status: str = Field("ASSIGNED", description="Assignment status")
    accepted_at: Optional[datetime] = Field(None, description="When assignment was accepted")
    started_at: Optional[datetime] = Field(None, description="When work started")
    completed_at: Optional[datetime] = Field(None, description="When work completed")
    
    # Workload tracking
    estimated_effort_minutes: Optional[int] = Field(None, description="Estimated effort in minutes")
    actual_effort_minutes: Optional[int] = Field(None, description="Actual effort in minutes")
    
    # Assignment metadata
    assigned_at: datetime = Field(default_factory=datetime.utcnow, description="Assignment timestamp")
    assigned_by: str = Field(..., description="System or agent that made assignment")
    
    @validator('status')
    def validate_status(cls, v):
        """Validate assignment status is from allowed set."""
        valid_statuses = ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'ESCALATED', 'REASSIGNED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v
    
    @validator('escalation_threshold')
    def validate_escalation_threshold(cls, v, values):
        """Validate escalation threshold is before SLA target."""
        if 'sla_target' in values and v >= values['sla_target']:
            raise ValueError('Escalation threshold must be before SLA target')
        return v


class HITLState(BaseEntity):
    """
    Human-in-the-Loop state for LangGraph workflow.
    
    Contains HITL requirements, questions, answers, and approvals
    as specified in Anexo A state schema.
    """
    
    # Case association
    case_id: str = Field(..., description="Associated case identifier")
    
    # HITL requirement
    required: bool = Field(False, description="Whether HITL is required")
    requirement_reason: Optional[str] = Field(None, description="Reason HITL is required")
    requirement_triggers: List[str] = Field(default_factory=list, description="Triggers that activated HITL")
    
    # Questions and answers
    questions: List[HITLQuestion] = Field(default_factory=list, description="Questions for human reviewers")
    answers: Dict[str, str] = Field(default_factory=dict, description="Answers provided by reviewers")
    
    # Approvals
    approvals: List[HITLApproval] = Field(default_factory=list, description="Approval records")
    
    # Assignment tracking
    assignments: List[HITLAssignment] = Field(default_factory=list, description="Assignment records")
    current_assignment: Optional[str] = Field(None, description="Current active assignment ID")
    
    # Workflow status
    workflow_status: str = Field("PENDING", description="HITL workflow status")
    completion_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Completion percentage")
    
    # Review metadata
    review_started_at: Optional[datetime] = Field(None, description="When review started")
    review_completed_at: Optional[datetime] = Field(None, description="When review completed")
    total_review_time_minutes: Optional[int] = Field(None, description="Total review time in minutes")
    
    # Escalation tracking
    escalation_level: int = Field(0, description="Current escalation level")
    escalation_history: List[str] = Field(default_factory=list, description="Escalation history")
    max_escalation_level: int = Field(3, description="Maximum escalation level")
    
    # Quality metrics
    reviewer_confidence: Optional[float] = Field(None, description="Overall reviewer confidence")
    review_quality_score: Optional[float] = Field(None, description="Review quality assessment")
    
    @validator('workflow_status')
    def validate_workflow_status(cls, v):
        """Validate workflow status is from allowed set."""
        valid_statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'ESCALATED', 'CANCELLED']
        if v not in valid_statuses:
            raise ValueError(f'Workflow status must be one of: {valid_statuses}')
        return v
    
    @validator('escalation_level')
    def validate_escalation_level(cls, v, values):
        """Validate escalation level is within bounds."""
        if v < 0:
            raise ValueError('Escalation level cannot be negative')
        if 'max_escalation_level' in values and v > values['max_escalation_level']:
            raise ValueError('Escalation level cannot exceed maximum')
        return v
    
    def add_question(self, question: HITLQuestion) -> None:
        """Add a question to the HITL workflow."""
        self.questions.append(question)
        self.required = True
        if not self.requirement_reason:
            self.requirement_reason = f"Question required: {question.category}"
        self.updated_at = datetime.utcnow()
        self._update_completion_percentage()
    
    def answer_question(self, question_id: str, answer: str, confidence: Optional[float] = None) -> None:
        """Answer a question in the HITL workflow."""
        for question in self.questions:
            if question.question_id == question_id:
                question.answer = answer
                question.answered = True
                question.answer_confidence = confidence
                self.answers[question_id] = answer
                break
        
        self.updated_at = datetime.utcnow()
        self._update_completion_percentage()
    
    def add_approval(self, approval: HITLApproval) -> None:
        """Add an approval to the HITL workflow."""
        self.approvals.append(approval)
        self.updated_at = datetime.utcnow()
        
        # Update workflow status based on approval
        if approval.decision == 'APPROVED':
            self._check_completion()
        elif approval.decision == 'ESCALATED':
            self.escalate()
    
    def assign_to_reviewer(self, assignment: HITLAssignment) -> None:
        """Assign case to a reviewer."""
        self.assignments.append(assignment)
        self.current_assignment = assignment.assignment_id
        if self.workflow_status == 'PENDING':
            self.workflow_status = 'IN_PROGRESS'
            self.review_started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def escalate(self, reason: Optional[str] = None) -> None:
        """Escalate the HITL workflow to next level."""
        if self.escalation_level < self.max_escalation_level:
            self.escalation_level += 1
            self.escalation_history.append(f"Level {self.escalation_level}: {reason or 'Manual escalation'}")
            self.workflow_status = 'ESCALATED'
            self.updated_at = datetime.utcnow()
    
    def complete_review(self) -> None:
        """Mark the HITL review as completed."""
        self.workflow_status = 'COMPLETED'
        self.review_completed_at = datetime.utcnow()
        self.completion_percentage = 100.0
        
        if self.review_started_at:
            duration = self.review_completed_at - self.review_started_at
            self.total_review_time_minutes = int(duration.total_seconds() / 60)
        
        self.updated_at = datetime.utcnow()
    
    def _update_completion_percentage(self) -> None:
        """Update completion percentage based on answered questions."""
        if not self.questions:
            self.completion_percentage = 0.0
            return
        
        answered_count = sum(1 for q in self.questions if q.answered)
        self.completion_percentage = (answered_count / len(self.questions)) * 100.0
    
    def _check_completion(self) -> None:
        """Check if HITL workflow can be completed."""
        all_questions_answered = all(q.answered for q in self.questions)
        has_approval = any(a.decision == 'APPROVED' for a in self.approvals)
        
        if all_questions_answered and has_approval:
            self.complete_review()
    
    def is_overdue(self) -> bool:
        """Check if HITL review is overdue."""
        if not self.assignments:
            return False
        
        current_assignment = next(
            (a for a in self.assignments if a.assignment_id == self.current_assignment),
            None
        )
        
        if current_assignment:
            return datetime.utcnow() > current_assignment.sla_target
        
        return False
    
    def get_pending_questions(self) -> List[HITLQuestion]:
        """Get all unanswered questions."""
        return [q for q in self.questions if not q.answered]
    
    def get_required_questions(self) -> List[HITLQuestion]:
        """Get all required unanswered questions."""
        return [q for q in self.questions if not q.answered and q.required]
    
    def can_proceed(self) -> bool:
        """Check if workflow can proceed (all required questions answered)."""
        required_questions = self.get_required_questions()
        return len(required_questions) == 0
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "required": True,
                "requirement_reason": "Low confidence decision requires human review",
                "requirement_triggers": ["LOW_CONFIDENCE", "HIGH_RISK"],
                "workflow_status": "IN_PROGRESS",
                "completion_percentage": 75.0,
                "escalation_level": 0,
                "max_escalation_level": 3
            }
        }
