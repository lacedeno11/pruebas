"""
Case data models.

Represents the core case entity for policy validation requests.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CaseState(str, Enum):
    """Case lifecycle states."""

    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    PENDING_DATOS = "PENDING_DATOS"
    PENDING_POLITICA = "PENDING_POLITICA"
    PENDING_ASEGURADORA = "PENDING_ASEGURADORA"
    PENDING_SISTEMA = "PENDING_SISTEMA"
    HITL_REVIEW = "HITL_REVIEW"
    APPROVED = "APPROVED"
    OBSERVED = "OBSERVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class CasePriority(str, Enum):
    """Case priority levels."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Attachment(BaseModel):
    """Document attachment with integrity verification."""

    attachment_id: str = Field(..., description="Unique attachment identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    storage_path: str = Field(..., description="Object storage path")
    checksum: str = Field(..., description="SHA-256 hash for integrity")
    size_bytes: int = Field(..., ge=0)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class Case(BaseModel):
    """
    Core case entity for policy validation.

    Based on UC-OP-05 Case Ingest and UC-OP-01 flow requirements.
    """

    # Identifiers
    case_id: str = Field(..., description="Internal case identifier")
    crm_ticket_id: Optional[str] = Field(None, description="External CRM/ticketing reference")

    # Customer/Contract context
    customer_id: str = Field(..., description="Customer identifier")
    contract_id: Optional[str] = Field(None, description="Contract reference")
    insurer_id: str = Field(..., description="Insurance company identifier")
    plan_id: str = Field(..., description="Insurance plan/product identifier")

    # Service being validated
    service_code: Optional[str] = Field(None, description="Service catalog code")
    service_description: Optional[str] = Field(None, description="Free-text service description")
    service_date: Optional[datetime] = Field(None, description="Date of service")
    provider_id: Optional[str] = Field(None, description="Service provider identifier")

    # Attachments and documents
    attachments: list[Attachment] = Field(default_factory=list)

    # Operational context
    priority: CasePriority = Field(default=CasePriority.NORMAL)
    sla_target: Optional[datetime] = Field(None, description="SLA deadline")
    state: CaseState = Field(default=CaseState.CREATED)
    assigned_queue: Optional[str] = Field(None, description="Processing queue assignment")

    # Metadata
    channel: Optional[str] = Field(None, description="Ingestion channel (CRM, API, Portal)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User/system that created the case")

    # Normalization tracking
    normalization_log: dict = Field(
        default_factory=dict, description="Field normalization audit trail"
    )

    class Config:
        use_enum_values = True
