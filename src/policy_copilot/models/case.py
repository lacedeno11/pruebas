"""
Case data model for Policy Validation Copilot

This module contains the Case model representing the core case entity
with all required fields as specified in Anexo A.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseEntity, CaseStatus, Priority, Attachment


class Case(BaseEntity):
    """
    Case model representing a policy validation request.
    
    Contains all case-related information including identifiers,
    service details, dates, attachments, SLA, state, and queue assignment.
    """
    
    # Core identifiers
    case_id: str = Field(..., description="Unique case identifier")
    crm_ticket_id: Optional[str] = Field(None, description="CRM/Ticketing system ticket ID")
    
    # Customer and contract information
    customer_id: str = Field(..., description="Customer identifier")
    contract_id: Optional[str] = Field(None, description="Contract identifier")
    
    # Insurance and plan details
    insurer_id: str = Field(..., description="Insurance company identifier")
    plan_id: str = Field(..., description="Insurance plan identifier")
    
    # Service information
    service_code: Optional[str] = Field(None, description="Standardized service code")
    service_description: Optional[str] = Field(None, description="Free text service description")
    service_date: datetime = Field(..., description="Date when service was provided")
    provider_id: Optional[str] = Field(None, description="Healthcare provider identifier")
    
    # Attachments and documentation
    attachments: List[Attachment] = Field(default_factory=list, description="Case attachments")
    
    # Operational information
    priority: Priority = Field(Priority.MEDIUM, description="Case priority level")
    sla_target: datetime = Field(..., description="SLA target completion time")
    channel: str = Field(..., description="Origination channel (CRM, API, etc.)")
    
    # State management
    state: CaseStatus = Field(CaseStatus.CREATED, description="Current case status")
    assigned_queue: Optional[str] = Field(None, description="Assigned processing queue")
    assigned_agent: Optional[str] = Field(None, description="Assigned agent identifier")
    
    # Historical context
    previous_cases: List[str] = Field(default_factory=list, description="Related previous case IDs")
    escalation_count: int = Field(0, description="Number of escalations")
    
    # Metadata
    source_system: str = Field(..., description="Source system identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    
    @validator('case_id')
    def validate_case_id(cls, v):
        """Validate case ID format."""
        if not v or len(v) < 3:
            raise ValueError('Case ID must be at least 3 characters long')
        return v
    
    @validator('service_date')
    def validate_service_date(cls, v):
        """Validate service date is not in the future."""
        if v > datetime.utcnow():
            raise ValueError('Service date cannot be in the future')
        return v
    
    @validator('sla_target')
    def validate_sla_target(cls, v, values):
        """Validate SLA target is after creation."""
        if 'created_at' in values and v <= values['created_at']:
            raise ValueError('SLA target must be after case creation')
        return v
    
    @validator('escalation_count')
    def validate_escalation_count(cls, v):
        """Validate escalation count is non-negative."""
        if v < 0:
            raise ValueError('Escalation count cannot be negative')
        return v
    
    def is_overdue(self) -> bool:
        """Check if case is overdue based on SLA target."""
        return datetime.utcnow() > self.sla_target
    
    def add_attachment(self, attachment: Attachment) -> None:
        """Add an attachment to the case."""
        self.attachments.append(attachment)
        self.updated_at = datetime.utcnow()
    
    def escalate(self, reason: str) -> None:
        """Escalate the case."""
        self.escalation_count += 1
        self.priority = Priority.HIGH if self.priority != Priority.CRITICAL else Priority.CRITICAL
        self.updated_at = datetime.utcnow()
    
    def assign_to_queue(self, queue: str) -> None:
        """Assign case to a processing queue."""
        self.assigned_queue = queue
        self.updated_at = datetime.utcnow()
    
    def assign_to_agent(self, agent_id: str) -> None:
        """Assign case to a specific agent."""
        self.assigned_agent = agent_id
        self.updated_at = datetime.utcnow()
    
    def update_status(self, new_status: CaseStatus) -> None:
        """Update case status."""
        self.state = new_status
        self.updated_at = datetime.utcnow()
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        schema_extra = {
            "example": {
                "case_id": "CASE-2024-001234",
                "crm_ticket_id": "TKT-567890",
                "customer_id": "CUST-123456",
                "contract_id": "CONT-789012",
                "insurer_id": "INS-001",
                "plan_id": "PLAN-PREMIUM-001",
                "service_code": "SVC-CONSULTATION",
                "service_description": "Medical consultation",
                "service_date": "2024-01-15T10:30:00Z",
                "provider_id": "PROV-12345",
                "priority": "MEDIUM",
                "sla_target": "2024-01-17T18:00:00Z",
                "channel": "CRM_WEBHOOK",
                "state": "CREATED",
                "source_system": "CRM_SYSTEM_V2"
            }
        }
