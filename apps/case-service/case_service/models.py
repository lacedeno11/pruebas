"""
DERCAS-ONCO-XAI Case Service Models

SQLAlchemy 2.0 models for patients and cases.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from dercas_common.models import CaseStatus
from .database import Base


class Patient(Base):
    """Patient model."""
    
    __tablename__ = "patients"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Patient information
    mrn: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Contact information
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Address information
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Medical information
    primary_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, mrn={self.mrn}, name={self.first_name} {self.last_name})>"


class Case(Base):
    """Case model."""
    
    __tablename__ = "cases"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign key to patient
    patient_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Case information
    case_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Case status and workflow
    status: Mapped[CaseStatus] = mapped_column(
        SQLEnum(CaseStatus, name="case_status"),
        default=CaseStatus.CREATED,
        nullable=False,
        index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Clinical information
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dates
    case_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Assignment
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Tags and metadata
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of tags
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of metadata
    
    # Audit fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="cases"
    )
    
    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_number={self.case_number}, status={self.status})>"
    
    @property
    def is_closed(self) -> bool:
        """Check if case is closed."""
        return self.status == CaseStatus.CLOSED
    
    @property
    def is_processing(self) -> bool:
        """Check if case is currently being processed."""
        return self.status == CaseStatus.PROCESSING
    
    @property
    def requires_review(self) -> bool:
        """Check if case requires review."""
        return self.status == CaseStatus.REVIEW_REQUIRED
    
    def can_transition_to(self, new_status: CaseStatus) -> bool:
        """Check if case can transition to new status."""
        # Define valid status transitions
        valid_transitions = {
            CaseStatus.CREATED: [CaseStatus.READY, CaseStatus.CLOSED],
            CaseStatus.READY: [CaseStatus.PROCESSING, CaseStatus.CLOSED],
            CaseStatus.PROCESSING: [CaseStatus.REVIEW_REQUIRED, CaseStatus.CLOSED],
            CaseStatus.REVIEW_REQUIRED: [CaseStatus.PROCESSING, CaseStatus.CLOSED],
            CaseStatus.CLOSED: []  # Closed cases cannot transition
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def update_status(self, new_status: CaseStatus, updated_by: str) -> bool:
        """Update case status with validation."""
        if not self.can_transition_to(new_status):
            return False
        
        self.status = new_status
        self.updated_by = updated_by
        
        # Set closed date if transitioning to closed
        if new_status == CaseStatus.CLOSED and not self.closed_date:
            self.closed_date = datetime.utcnow()
        
        return True
