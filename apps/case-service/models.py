"""
DERCAS-ONCO-XAI V1 - Case Service Models

SQLAlchemy 2.0 models for patients and cases.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, Text, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.models import CaseStatus

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
    
    # External identifier
    patient_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="External patient identifier"
    )
    
    # Demographics
    age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Patient age"
    )
    
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Patient gender"
    )
    
    medical_record_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Medical record number"
    )
    
    # Clinical metadata
    diagnosis_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Initial diagnosis date"
    )
    
    primary_site: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Primary tumor site"
    )
    
    histology: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Histological type"
    )
    
    stage: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Cancer stage"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp"
    )
    
    # Relationships
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, patient_id='{self.patient_id}')>"


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
    
    # External identifier
    case_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="External case identifier"
    )
    
    # Foreign key to patient
    patient_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated patient ID"
    )
    
    # Case status
    status: Mapped[CaseStatus] = mapped_column(
        SQLEnum(CaseStatus, name="case_status"),
        nullable=False,
        default=CaseStatus.CREATED,
        index=True,
        comment="Case processing status"
    )
    
    # Case metadata
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Case title"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Case description"
    )
    
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Case priority (1-5)"
    )
    
    # Clinical context
    clinical_context: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional clinical context"
    )
    
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Assigned clinician"
    )
    
    # Processing metadata
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Processing start time"
    )
    
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Processing completion time"
    )
    
    review_required_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for review requirement"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp"
    )
    
    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="cases"
    )
    
    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_id='{self.case_id}', status='{self.status}')>"
    
    def can_transition_to(self, new_status: CaseStatus) -> bool:
        """
        Check if case can transition to a new status.
        
        Args:
            new_status: Target status
            
        Returns:
            bool: True if transition is allowed
        """
        # Define allowed status transitions
        transitions = {
            CaseStatus.CREATED: [CaseStatus.READY, CaseStatus.CLOSED],
            CaseStatus.READY: [CaseStatus.PROCESSING, CaseStatus.CLOSED],
            CaseStatus.PROCESSING: [CaseStatus.REVIEW_REQUIRED, CaseStatus.CLOSED],
            CaseStatus.REVIEW_REQUIRED: [CaseStatus.PROCESSING, CaseStatus.CLOSED],
            CaseStatus.CLOSED: []  # Terminal state
        }
        
        return new_status in transitions.get(self.status, [])
    
    def is_active(self) -> bool:
        """Check if case is in an active state."""
        return self.status in [CaseStatus.CREATED, CaseStatus.READY, CaseStatus.PROCESSING]
    
    def requires_review(self) -> bool:
        """Check if case requires review."""
        return self.status == CaseStatus.REVIEW_REQUIRED
    
    def is_completed(self) -> bool:
        """Check if case is completed."""
        return self.status == CaseStatus.CLOSED
    
    def get_processing_duration(self) -> Optional[float]:
        """
        Get processing duration in seconds.
        
        Returns:
            float: Processing duration in seconds, or None if not applicable
        """
        if self.processing_started_at and self.processing_completed_at:
            delta = self.processing_completed_at - self.processing_started_at
            return delta.total_seconds()
        return None
