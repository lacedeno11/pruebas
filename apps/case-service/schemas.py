"""
DERCAS-ONCO-XAI V1 - Case Service Schemas

Pydantic request/response schemas for the Case Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.models import CaseStatus


# Patient schemas
class PatientBase(BaseModel):
    """Base patient schema."""
    patient_id: str = Field(..., description="External patient identifier", min_length=1, max_length=100)
    age: Optional[int] = Field(None, description="Patient age", ge=0, le=150)
    gender: Optional[str] = Field(None, description="Patient gender", max_length=20)
    medical_record_number: Optional[str] = Field(None, description="Medical record number", max_length=100)
    diagnosis_date: Optional[datetime] = Field(None, description="Initial diagnosis date")
    primary_site: Optional[str] = Field(None, description="Primary tumor site", max_length=200)
    histology: Optional[str] = Field(None, description="Histological type", max_length=200)
    stage: Optional[str] = Field(None, description="Cancer stage", max_length=50)


class PatientCreate(PatientBase):
    """Schema for creating a patient."""
    
    @validator('patient_id')
    def validate_patient_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Patient ID cannot be empty')
        return v.strip()
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""
    age: Optional[int] = Field(None, description="Patient age", ge=0, le=150)
    gender: Optional[str] = Field(None, description="Patient gender", max_length=20)
    medical_record_number: Optional[str] = Field(None, description="Medical record number", max_length=100)
    diagnosis_date: Optional[datetime] = Field(None, description="Initial diagnosis date")
    primary_site: Optional[str] = Field(None, description="Primary tumor site", max_length=200)
    histology: Optional[str] = Field(None, description="Histological type", max_length=200)
    stage: Optional[str] = Field(None, description="Cancer stage", max_length=50)


class PatientResponse(PatientBase):
    """Schema for patient response."""
    id: UUID = Field(..., description="Internal patient ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


# Case schemas
class CaseBase(BaseModel):
    """Base case schema."""
    case_id: str = Field(..., description="External case identifier", min_length=1, max_length=100)
    title: Optional[str] = Field(None, description="Case title", max_length=200)
    description: Optional[str] = Field(None, description="Case description", max_length=1000)
    priority: int = Field(default=1, description="Case priority", ge=1, le=5)
    clinical_context: Optional[Dict[str, Any]] = Field(None, description="Additional clinical context")
    assigned_to: Optional[str] = Field(None, description="Assigned clinician", max_length=100)


class CaseCreate(CaseBase):
    """Schema for creating a case."""
    patient_id: UUID = Field(..., description="Associated patient ID")
    
    @validator('case_id')
    def validate_case_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Case ID cannot be empty')
        return v.strip()
    
    @validator('priority')
    def validate_priority(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Priority must be between 1 and 5')
        return v


class CaseUpdate(BaseModel):
    """Schema for updating a case."""
    status: Optional[CaseStatus] = Field(None, description="Case status")
    title: Optional[str] = Field(None, description="Case title", max_length=200)
    description: Optional[str] = Field(None, description="Case description", max_length=1000)
    priority: Optional[int] = Field(None, description="Case priority", ge=1, le=5)
    clinical_context: Optional[Dict[str, Any]] = Field(None, description="Additional clinical context")
    assigned_to: Optional[str] = Field(None, description="Assigned clinician", max_length=100)
    review_required_reason: Optional[str] = Field(None, description="Reason for review requirement", max_length=500)
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Priority must be between 1 and 5')
        return v


class CaseResponse(CaseBase):
    """Schema for case response."""
    id: UUID = Field(..., description="Internal case ID")
    patient_id: UUID = Field(..., description="Associated patient ID")
    status: CaseStatus = Field(..., description="Case status")
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    review_required_reason: Optional[str] = Field(None, description="Reason for review requirement")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Computed fields
    is_active: bool = Field(..., description="Whether case is in an active state")
    requires_review: bool = Field(..., description="Whether case requires review")
    is_completed: bool = Field(..., description="Whether case is completed")
    processing_duration_seconds: Optional[float] = Field(None, description="Processing duration in seconds")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object with computed fields."""
        data = {
            'id': obj.id,
            'case_id': obj.case_id,
            'patient_id': obj.patient_id,
            'status': obj.status,
            'title': obj.title,
            'description': obj.description,
            'priority': obj.priority,
            'clinical_context': obj.clinical_context,
            'assigned_to': obj.assigned_to,
            'processing_started_at': obj.processing_started_at,
            'processing_completed_at': obj.processing_completed_at,
            'review_required_reason': obj.review_required_reason,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'is_active': obj.is_active(),
            'requires_review': obj.requires_review(),
            'is_completed': obj.is_completed(),
            'processing_duration_seconds': obj.get_processing_duration()
        }
        return cls(**data)


class CaseWithPatient(CaseResponse):
    """Schema for case response with patient information."""
    patient: PatientResponse = Field(..., description="Associated patient information")


# Status transition schemas
class CaseStatusTransition(BaseModel):
    """Schema for case status transitions."""
    new_status: CaseStatus = Field(..., description="New case status")
    reason: Optional[str] = Field(None, description="Reason for status change", max_length=500)
    
    @validator('reason')
    def validate_reason(cls, v, values):
        # Require reason for certain status transitions
        new_status = values.get('new_status')
        if new_status == CaseStatus.REVIEW_REQUIRED and not v:
            raise ValueError('Reason is required when setting status to REVIEW_REQUIRED')
        if new_status == CaseStatus.CLOSED and not v:
            raise ValueError('Reason is required when closing a case')
        return v


# Search and filter schemas
class CaseSearchFilters(BaseModel):
    """Schema for case search filters."""
    status: Optional[CaseStatus] = Field(None, description="Filter by case status")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned clinician")
    priority_min: Optional[int] = Field(None, description="Minimum priority", ge=1, le=5)
    priority_max: Optional[int] = Field(None, description="Maximum priority", ge=1, le=5)
    created_after: Optional[datetime] = Field(None, description="Filter cases created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter cases created before this date")
    
    @validator('priority_max')
    def validate_priority_range(cls, v, values):
        priority_min = values.get('priority_min')
        if priority_min is not None and v is not None and v < priority_min:
            raise ValueError('priority_max must be greater than or equal to priority_min')
        return v


class PatientSearchFilters(BaseModel):
    """Schema for patient search filters."""
    age_min: Optional[int] = Field(None, description="Minimum age", ge=0, le=150)
    age_max: Optional[int] = Field(None, description="Maximum age", ge=0, le=150)
    gender: Optional[str] = Field(None, description="Filter by gender")
    primary_site: Optional[str] = Field(None, description="Filter by primary tumor site")
    histology: Optional[str] = Field(None, description="Filter by histology")
    stage: Optional[str] = Field(None, description="Filter by cancer stage")
    
    @validator('age_max')
    def validate_age_range(cls, v, values):
        age_min = values.get('age_min')
        if age_min is not None and v is not None and v < age_min:
            raise ValueError('age_max must be greater than or equal to age_min')
        return v


# Statistics schemas
class CaseStatistics(BaseModel):
    """Schema for case statistics."""
    total_cases: int = Field(..., description="Total number of cases")
    cases_by_status: Dict[str, int] = Field(..., description="Case count by status")
    cases_by_priority: Dict[str, int] = Field(..., description="Case count by priority")
    average_processing_time_seconds: Optional[float] = Field(None, description="Average processing time")
    active_cases: int = Field(..., description="Number of active cases")
    cases_requiring_review: int = Field(..., description="Number of cases requiring review")


class PatientStatistics(BaseModel):
    """Schema for patient statistics."""
    total_patients: int = Field(..., description="Total number of patients")
    patients_by_gender: Dict[str, int] = Field(..., description="Patient count by gender")
    patients_by_age_group: Dict[str, int] = Field(..., description="Patient count by age group")
    patients_by_stage: Dict[str, int] = Field(..., description="Patient count by cancer stage")
    average_age: Optional[float] = Field(None, description="Average patient age")


# Bulk operation schemas
class BulkCaseUpdate(BaseModel):
    """Schema for bulk case updates."""
    case_ids: List[str] = Field(..., description="List of case IDs to update", min_items=1, max_items=100)
    updates: CaseUpdate = Field(..., description="Updates to apply to all cases")
    
    @validator('case_ids')
    def validate_case_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate case IDs are not allowed')
        return v


class BulkOperationResult(BaseModel):
    """Schema for bulk operation results."""
    total_requested: int = Field(..., description="Total number of items requested for update")
    successful: int = Field(..., description="Number of successful updates")
    failed: int = Field(..., description="Number of failed updates")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="List of errors for failed updates")


# Event schemas (for API responses)
class CaseEventInfo(BaseModel):
    """Schema for case event information."""
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changes made to the case")


# Health check schemas
class ServiceHealth(BaseModel):
    """Schema for service health information."""
    database_connected: bool = Field(..., description="Database connection status")
    event_bus_connected: bool = Field(..., description="Event bus connection status")
    total_patients: int = Field(..., description="Total number of patients")
    total_cases: int = Field(..., description="Total number of cases")
    active_cases: int = Field(..., description="Number of active cases")
