"""Pydantic schemas for Audit Events."""
from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict


class AuditEventBase(BaseModel):
    """Base schema for Audit Event."""

    entity_type: str = Field(..., description="Type of entity")
    entity_id: Optional[str] = Field(None, description="Entity identifier")
    action: str = Field(..., description="Action performed")
    status: str = Field(..., description="Status of the action")
    user_id: Optional[str] = Field(None, description="User who performed the action")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")
    details_json: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    source_service: Optional[str] = Field(None, description="Source service")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AuditEventCreate(AuditEventBase):
    """Schema for creating an Audit Event."""
    pass


class AuditEventResponse(AuditEventBase):
    """Schema for Audit Event response."""

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event timestamp")

    model_config = ConfigDict(from_attributes=True)


class AuditEventListResponse(BaseModel):
    """Schema for paginated list of Audit Events."""

    events: List[AuditEventResponse] = Field(..., description="List of audit events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class AuditEventFilter(BaseModel):
    """Schema for filtering Audit Events."""

    case_id: Optional[str] = Field(None, description="Filter by case ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    action: Optional[str] = Field(None, description="Filter by action")
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[datetime] = Field(None, description="Filter from this date", alias="from")
    to_date: Optional[datetime] = Field(None, description="Filter to this date", alias="to")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=1000, description="Number of items per page")
