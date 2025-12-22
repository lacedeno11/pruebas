"""
Base models and common types for Policy Validation Copilot

This module contains base Pydantic models and common type definitions
used throughout the Policy Validation Copilot system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class BaseEntity(BaseModel):
    """Base entity with common fields for all models."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    version: int = Field(default=1, description="Entity version for optimistic locking")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class CaseStatus(str, Enum):
    """Case status enumeration."""
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    APROBADO = "APROBADO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    PENDIENTE_POLITICA = "PENDIENTE_POLITICA"
    PENDIENTE_DATOS = "PENDIENTE_DATOS"
    PENDIENTE_ASEGURADORA = "PENDIENTE_ASEGURADORA"
    PENDIENTE_SISTEMA = "PENDIENTE_SISTEMA"
    ESCALADO_HITL = "ESCALADO_HITL"
    CLOSED = "CLOSED"


class Priority(str, Enum):
    """Priority levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    """Confidence level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GuardrailDecision(str, Enum):
    """Guardrail decision enumeration."""
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REQUIRE_HITL = "REQUIRE_HITL"


class ChecklistOutcome(str, Enum):
    """Checklist item outcome enumeration."""
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AnomalyFlag(str, Enum):
    """Anomaly detection flags."""
    NONE = "NONE"
    PATTERN_DEVIATION = "PATTERN_DEVIATION"
    VOLUME_ANOMALY = "VOLUME_ANOMALY"
    TIMING_ANOMALY = "TIMING_ANOMALY"
    FEATURE_ANOMALY = "FEATURE_ANOMALY"
    BEHAVIORAL_ANOMALY = "BEHAVIORAL_ANOMALY"


class DocumentPointer(BaseModel):
    """Document pointer for exact references."""
    
    page_number: Optional[int] = Field(None, description="Page number in document")
    cell_reference: Optional[str] = Field(None, description="Cell reference for Excel files")
    section: Optional[str] = Field(None, description="Section or paragraph reference")
    line_number: Optional[int] = Field(None, description="Line number in text")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Bounding box coordinates")
    
    @validator('cell_reference')
    def validate_cell_reference(cls, v):
        """Validate Excel cell reference format."""
        if v and not v.match(r'^[A-Z]+\d+$'):
            raise ValueError('Cell reference must be in format like A1, B2, etc.')
        return v


class Attachment(BaseModel):
    """File attachment model."""
    
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., description="File size in bytes")
    checksum: str = Field(..., description="SHA-256 checksum")
    storage_path: str = Field(..., description="Path in object storage")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    
    @validator('checksum')
    def validate_checksum(cls, v):
        """Validate SHA-256 checksum format."""
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Checksum must be a valid SHA-256 hash')
        return v.lower()


class ModelVersion(BaseModel):
    """ML model version information."""
    
    model_name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    registry_uri: Optional[str] = Field(None, description="Model registry URI")
    deployed_at: datetime = Field(default_factory=datetime.utcnow, description="Deployment timestamp")
    performance_metrics: Optional[Dict[str, float]] = Field(None, description="Model performance metrics")


class ThresholdConfig(BaseModel):
    """Threshold configuration for decision making."""
    
    confidence_high: float = Field(0.8, ge=0.0, le=1.0, description="High confidence threshold")
    confidence_medium: float = Field(0.6, ge=0.0, le=1.0, description="Medium confidence threshold")
    risk_low: float = Field(0.3, ge=0.0, le=1.0, description="Low risk threshold")
    risk_medium: float = Field(0.6, ge=0.0, le=1.0, description="Medium risk threshold")
    coverage_ok: float = Field(0.7, ge=0.0, le=1.0, description="Acceptable coverage threshold")
    anomaly_high: float = Field(0.8, ge=0.0, le=1.0, description="High anomaly threshold")
    version: str = Field(..., description="Threshold configuration version")
    
    @validator('confidence_medium')
    def validate_confidence_order(cls, v, values):
        """Ensure confidence thresholds are in correct order."""
        if 'confidence_high' in values and v >= values['confidence_high']:
            raise ValueError('Medium confidence must be less than high confidence')
        return v
    
    @validator('risk_medium')
    def validate_risk_order(cls, v, values):
        """Ensure risk thresholds are in correct order."""
        if 'risk_low' in values and v <= values['risk_low']:
            raise ValueError('Medium risk must be greater than low risk')
        return v
