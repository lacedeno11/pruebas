# DERCAS-ONCO-XAI V1 - Case Service Models
# SQLAlchemy 2.0 models for patients and cases

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Patient(Base):
    """Patient model for storing patient information."""
    
    __tablename__ = "patients"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique patient identifier"
    )
    
    # Patient information
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="External patient ID from hospital system"
    )
    
    first_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Patient first name"
    )
    
    last_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Patient last name"
    )
    
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Patient date of birth"
    )
    
    gender: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Patient gender (M/F/O/U)"
    )
    
    medical_record_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Medical record number"
    )
    
    # Metadata
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional patient metadata"
    )
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )
    
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who created the record"
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who last updated the record"
    )
    
    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the patient record is active"
    )
    
    # Relationships
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_patients_external_id", "external_id"),
        Index("idx_patients_mrn", "medical_record_number"),
        Index("idx_patients_name", "last_name", "first_name"),
        Index("idx_patients_created_at", "created_at"),
        Index("idx_patients_active", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name={self.first_name} {self.last_name})>"
    
    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> Optional[int]:
        """Calculate patient's age if date of birth is available."""
        if self.date_of_birth:
            today = datetime.now().date()
            birth_date = self.date_of_birth.date()
            age = today.year - birth_date.year
            if today < birth_date.replace(year=today.year):
                age -= 1
            return age
        return None


class Case(Base):
    """Case model for storing clinical cases."""
    
    __tablename__ = "cases"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique case identifier"
    )
    
    # Foreign key to patient
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to patient"
    )
    
    # Case information
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="External case ID from hospital system"
    )
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Case title or summary"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed case description"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        comment="Case status (draft, active, completed, archived)"
    )
    
    priority: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        nullable=False,
        comment="Case priority (low, normal, high, urgent)"
    )
    
    # Clinical information
    diagnosis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Clinical diagnosis or working diagnosis"
    )
    
    clinical_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Clinical notes and observations"
    )
    
    # Dates
    case_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when the case occurred"
    )
    
    admission_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Patient admission date"
    )
    
    discharge_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Patient discharge date"
    )
    
    # Metadata and tags
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Case tags for categorization"
    )
    
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional case metadata"
    )
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        comment="AI processing status (pending, processing, completed, failed)"
    )
    
    processing_progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Processing progress percentage (0-100)"
    )
    
    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Processing error message if failed"
    )
    
    # Results summary
    has_images: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether case has associated images"
    )
    
    has_ehr_data: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether case has EHR data"
    )
    
    has_inference_results: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether case has inference results"
    )
    
    has_graph_data: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether case has knowledge graph data"
    )
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )
    
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who created the record"
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who last updated the record"
    )
    
    # Soft delete
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the case record is active"
    )
    
    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="cases",
        lazy="selectin"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_cases_patient_id", "patient_id"),
        Index("idx_cases_external_id", "external_id"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_priority", "priority"),
        Index("idx_cases_processing_status", "processing_status"),
        Index("idx_cases_case_date", "case_date"),
        Index("idx_cases_created_at", "created_at"),
        Index("idx_cases_active", "is_active"),
        Index("idx_cases_has_images", "has_images"),
        Index("idx_cases_has_inference", "has_inference_results"),
    )
    
    def __repr__(self) -> str:
        return f"<Case(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if case processing is completed."""
        return self.processing_status == "completed"
    
    @property
    def is_processing(self) -> bool:
        """Check if case is currently being processed."""
        return self.processing_status == "processing"
    
    @property
    def has_errors(self) -> bool:
        """Check if case has processing errors."""
        return self.processing_status == "failed" or self.processing_error is not None
    
    def update_processing_status(self, status: str, progress: int = None, error: str = None) -> None:
        """Update case processing status."""
        self.processing_status = status
        if progress is not None:
            self.processing_progress = max(0, min(100, progress))
        if error is not None:
            self.processing_error = error
        elif status != "failed":
            self.processing_error = None
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the case."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the case."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def set_metadata(self, key: str, value: any) -> None:
        """Set metadata value."""
        if self.metadata_ is None:
            self.metadata_ = {}
        self.metadata_[key] = value
    
    def get_metadata(self, key: str, default: any = None) -> any:
        """Get metadata value."""
        if self.metadata_:
            return self.metadata_.get(key, default)
        return default
