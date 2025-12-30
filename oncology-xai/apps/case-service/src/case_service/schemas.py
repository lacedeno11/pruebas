# DERCAS-ONCO-XAI V1 - Case Service Schemas
# Pydantic schemas for request/response validation

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class GenderEnum(str, Enum):
    """Patient gender enumeration."""
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    UNKNOWN = "U"


class CaseStatusEnum(str, Enum):
    """Case status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CasePriorityEnum(str, Enum):
    """Case priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ProcessingStatusEnum(str, Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Patient Schemas

class PatientBase(BaseModel):
    """Base patient schema."""
    external_id: Optional[str] = Field(None, max_length=255, description="External patient ID")
    first_name: str = Field(..., max_length=255, description="Patient first name")
    last_name: str = Field(..., max_length=255, description="Patient last name")
    date_of_birth: Optional[datetime] = Field(None, description="Patient date of birth")
    gender: Optional[GenderEnum] = Field(None, description="Patient gender")
    medical_record_number: Optional[str] = Field(None, max_length=100, description="Medical record number")
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Additional metadata")
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        """Validate patient names."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        """Validate date of birth."""
        if v and v > datetime.now():
            raise ValueError("Date of birth cannot be in the future")
        return v


class PatientCreate(PatientBase):
    """Schema for creating a patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""
    external_id: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[datetime] = None
    gender: Optional[GenderEnum] = None
    medical_record_number: Optional[str] = Field(None, max_length=100)
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        """Validate patient names."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else v


class PatientResponse(PatientBase):
    """Schema for patient response."""
    id: str = Field(..., description="Patient ID")
    full_name: str = Field(..., description="Patient full name")
    age: Optional[int] = Field(None, description="Patient age")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Created by user")
    updated_by: Optional[str] = Field(None, description="Updated by user")
    is_active: bool = Field(..., description="Whether patient is active")
    
    class Config:
        from_attributes = True


class PatientSummary(BaseModel):
    """Summary schema for patient listing."""
    id: str
    full_name: str
    age: Optional[int]
    gender: Optional[GenderEnum]
    medical_record_number: Optional[str]
    case_count: int = Field(0, description="Number of cases for this patient")
    created_at: datetime
    
    class Config:
        from_attributes = True


# Case Schemas

class CaseBase(BaseModel):
    """Base case schema."""
    external_id: Optional[str] = Field(None, max_length=255, description="External case ID")
    title: str = Field(..., max_length=500, description="Case title")
    description: Optional[str] = Field(None, description="Case description")
    status: CaseStatusEnum = Field(CaseStatusEnum.DRAFT, description="Case status")
    priority: CasePriorityEnum = Field(CasePriorityEnum.NORMAL, description="Case priority")
    diagnosis: Optional[str] = Field(None, description="Clinical diagnosis")
    clinical_notes: Optional[str] = Field(None, description="Clinical notes")
    case_date: Optional[datetime] = Field(None, description="Case date")
    admission_date: Optional[datetime] = Field(None, description="Admission date")
    discharge_date: Optional[datetime] = Field(None, description="Discharge date")
    tags: Optional[List[str]] = Field(None, description="Case tags")
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata", description="Additional metadata")
    
    @validator('title')
    def validate_title(cls, v):
        """Validate case title."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @validator('discharge_date')
    def validate_discharge_date(cls, v, values):
        """Validate discharge date is after admission date."""
        if v and 'admission_date' in values and values['admission_date']:
            if v < values['admission_date']:
                raise ValueError("Discharge date cannot be before admission date")
        return v


class CaseCreate(CaseBase):
    """Schema for creating a case."""
    patient_id: str = Field(..., description="Patient ID")


class CaseUpdate(BaseModel):
    """Schema for updating a case."""
    external_id: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    status: Optional[CaseStatusEnum] = None
    priority: Optional[CasePriorityEnum] = None
    diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None
    case_date: Optional[datetime] = None
    admission_date: Optional[datetime] = None
    discharge_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    processing_status: Optional[ProcessingStatusEnum] = None
    processing_progress: Optional[int] = Field(None, ge=0, le=100)
    processing_error: Optional[str] = None
    has_images: Optional[bool] = None
    has_ehr_data: Optional[bool] = None
    has_inference_results: Optional[bool] = None
    has_graph_data: Optional[bool] = None
    
    @validator('title')
    def validate_title(cls, v):
        """Validate case title."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Title cannot be empty")
        return v.strip() if v else v


class CaseResponse(CaseBase):
    """Schema for case response."""
    id: str = Field(..., description="Case ID")
    patient_id: str = Field(..., description="Patient ID")
    processing_status: ProcessingStatusEnum = Field(..., description="Processing status")
    processing_progress: int = Field(..., description="Processing progress")
    processing_error: Optional[str] = Field(None, description="Processing error")
    has_images: bool = Field(..., description="Has images")
    has_ehr_data: bool = Field(..., description="Has EHR data")
    has_inference_results: bool = Field(..., description="Has inference results")
    has_graph_data: bool = Field(..., description="Has graph data")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Created by user")
    updated_by: Optional[str] = Field(None, description="Updated by user")
    is_active: bool = Field(..., description="Whether case is active")
    patient: Optional[PatientSummary] = Field(None, description="Patient information")
    
    class Config:
        from_attributes = True


class CaseSummary(BaseModel):
    """Summary schema for case listing."""
    id: str
    title: str
    status: CaseStatusEnum
    priority: CasePriorityEnum
    processing_status: ProcessingStatusEnum
    processing_progress: int
    case_date: Optional[datetime]
    created_at: datetime
    patient_name: str
    has_images: bool
    has_inference_results: bool
    
    class Config:
        from_attributes = True


class CaseWithPatient(CaseResponse):
    """Case response with full patient details."""
    patient: PatientResponse
    
    class Config:
        from_attributes = True


# Pagination Schemas

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    
    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        """Calculate total pages."""
        total = values.get('total', 0)
        size = values.get('size', 1)
        return (total + size - 1) // size if total > 0 else 0


class PaginatedPatients(PaginatedResponse):
    """Paginated patients response."""
    items: List[PatientSummary]


class PaginatedCases(PaginatedResponse):
    """Paginated cases response."""
    items: List[CaseSummary]


# Filter Schemas

class PatientFilters(BaseModel):
    """Patient filtering parameters."""
    search: Optional[str] = Field(None, description="Search in name or MRN")
    gender: Optional[GenderEnum] = Field(None, description="Filter by gender")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


class CaseFilters(BaseModel):
    """Case filtering parameters."""
    search: Optional[str] = Field(None, description="Search in title or description")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    status: Optional[CaseStatusEnum] = Field(None, description="Filter by status")
    priority: Optional[CasePriorityEnum] = Field(None, description="Filter by priority")
    processing_status: Optional[ProcessingStatusEnum] = Field(None, description="Filter by processing status")
    has_images: Optional[bool] = Field(None, description="Filter by image availability")
    has_inference_results: Optional[bool] = Field(None, description="Filter by inference results")
    case_date_after: Optional[datetime] = Field(None, description="Case date after")
    case_date_before: Optional[datetime] = Field(None, description="Case date before")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


# Event Schemas

class CaseEventData(BaseModel):
    """Case event data for event emission."""
    case_id: str
    patient_id: str
    title: str
    status: CaseStatusEnum
    processing_status: ProcessingStatusEnum
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PatientEventData(BaseModel):
    """Patient event data for event emission."""
    patient_id: str
    full_name: str
    medical_record_number: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


# Health Check Schema

class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime
    service: str = "case-service"
    version: str = "1.0.0"
    database: str = "connected"
    
    class Config:
        from_attributes = True
