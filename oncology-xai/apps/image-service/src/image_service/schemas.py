# DERCAS-ONCO-XAI V1 - Image Service Schemas
# Pydantic schemas for request/response validation

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProcessingStatusEnum(str, Enum):
    """Image processing status enumeration."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ImageFormatEnum(str, Enum):
    """Supported image format enumeration."""
    PNG = "png"
    BIFF = "biff"
    TIFF = "tiff"


class ModalityEnum(str, Enum):
    """Medical imaging modality enumeration."""
    CT = "CT"
    MRI = "MRI"
    XRAY = "X-Ray"
    HISTOLOGY = "H&E"
    IMMUNOHISTOCHEMISTRY = "IHC"
    FLUORESCENCE = "Fluorescence"
    OTHER = "Other"


# Base Schemas

class ImageBase(BaseModel):
    """Base image schema."""
    case_id: Optional[str] = Field(None, description="Associated case ID")
    modality: Optional[ModalityEnum] = Field(None, description="Imaging modality")
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition date")
    patient_position: Optional[str] = Field(None, description="Patient position")
    slice_thickness: Optional[float] = Field(None, ge=0, description="Slice thickness in mm")
    pixel_spacing: Optional[str] = Field(None, description="Pixel spacing (x,y) in mm")
    tags: Optional[List[str]] = Field(None, description="Image tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ImageUpload(ImageBase):
    """Schema for image upload request."""
    pass


class ImageUpdate(BaseModel):
    """Schema for image update request."""
    case_id: Optional[str] = Field(None, description="Associated case ID")
    modality: Optional[ModalityEnum] = Field(None, description="Imaging modality")
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition date")
    patient_position: Optional[str] = Field(None, description="Patient position")
    slice_thickness: Optional[float] = Field(None, ge=0, description="Slice thickness in mm")
    pixel_spacing: Optional[str] = Field(None, description="Pixel spacing (x,y) in mm")
    tags: Optional[List[str]] = Field(None, description="Image tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    processing_status: Optional[ProcessingStatusEnum] = Field(None, description="Processing status")


class ImageResponse(ImageBase):
    """Schema for image response."""
    id: str = Field(..., description="Image ID")
    original_filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    file_format: ImageFormatEnum = Field(..., description="Image format")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in MB")
    md5_hash: str = Field(..., description="MD5 hash")
    sha256_hash: str = Field(..., description="SHA256 hash")
    storage_path: str = Field(..., description="Storage path")
    storage_bucket: str = Field(..., description="Storage bucket")
    storage_key: str = Field(..., description="Storage key")
    
    # Image properties
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    dimensions: Optional[str] = Field(None, description="Image dimensions (WxH)")
    color_mode: Optional[str] = Field(None, description="Color mode")
    bit_depth: Optional[int] = Field(None, description="Bit depth")
    
    # Processing status
    processing_status: ProcessingStatusEnum = Field(..., description="Processing status")
    processing_error: Optional[str] = Field(None, description="Processing error")
    
    # Validation status
    is_validated: bool = Field(..., description="Whether image is validated")
    validation_error: Optional[str] = Field(None, description="Validation error")
    
    # Thumbnails
    has_thumbnail: bool = Field(..., description="Whether thumbnail exists")
    thumbnail_path: Optional[str] = Field(None, description="Thumbnail path")
    
    # Access tracking
    view_count: int = Field(..., description="View count")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    
    # DICOM metadata
    dicom_metadata: Optional[Dict[str, Any]] = Field(None, description="DICOM metadata")
    
    # Audit fields
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    uploaded_by: Optional[str] = Field(None, description="Uploaded by user")
    updated_by: Optional[str] = Field(None, description="Updated by user")
    is_active: bool = Field(..., description="Whether image is active")
    
    class Config:
        from_attributes = True


class ImageSummary(BaseModel):
    """Summary schema for image listing."""
    id: str
    original_filename: str
    file_format: ImageFormatEnum
    file_size_mb: float
    dimensions: Optional[str]
    modality: Optional[ModalityEnum]
    processing_status: ProcessingStatusEnum
    has_thumbnail: bool
    view_count: int
    created_at: datetime
    case_id: Optional[str]
    
    class Config:
        from_attributes = True


class ImageUploadResponse(BaseModel):
    """Response schema for image upload."""
    image_id: str = Field(..., description="Generated image ID")
    original_filename: str = Field(..., description="Original filename")
    file_format: str = Field(..., description="Detected file format")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in MB")
    dimensions: Optional[str] = Field(None, description="Image dimensions")
    storage_key: str = Field(..., description="Storage key")
    md5_hash: str = Field(..., description="MD5 hash")
    sha256_hash: str = Field(..., description="SHA256 hash")
    processing_status: str = Field(..., description="Processing status")
    validation_warnings: Optional[List[str]] = Field(None, description="Validation warnings")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")


class SignedUrlResponse(BaseModel):
    """Response schema for signed URL generation."""
    image_id: str = Field(..., description="Image ID")
    signed_url: str = Field(..., description="Signed URL")
    expires_at: datetime = Field(..., description="URL expiration time")
    expires_in_seconds: int = Field(..., description="Seconds until expiration")


class ViewerUrlResponse(BaseModel):
    """Response schema for viewer URL generation."""
    image_id: str = Field(..., description="Image ID")
    viewer_url: str = Field(..., description="Viewer URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    expires_at: datetime = Field(..., description="URL expiration time")
    expires_in_seconds: int = Field(..., description="Seconds until expiration")


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


class PaginatedImages(PaginatedResponse):
    """Paginated images response."""
    items: List[ImageSummary]


# Filter Schemas

class ImageFilters(BaseModel):
    """Image filtering parameters."""
    case_id: Optional[str] = Field(None, description="Filter by case ID")
    file_format: Optional[ImageFormatEnum] = Field(None, description="Filter by format")
    modality: Optional[ModalityEnum] = Field(None, description="Filter by modality")
    processing_status: Optional[ProcessingStatusEnum] = Field(None, description="Filter by processing status")
    has_thumbnail: Optional[bool] = Field(None, description="Filter by thumbnail availability")
    uploaded_by: Optional[str] = Field(None, description="Filter by uploader")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    min_file_size: Optional[int] = Field(None, ge=0, description="Minimum file size in bytes")
    max_file_size: Optional[int] = Field(None, ge=0, description="Maximum file size in bytes")
    min_width: Optional[int] = Field(None, ge=0, description="Minimum width in pixels")
    max_width: Optional[int] = Field(None, ge=0, description="Maximum width in pixels")
    min_height: Optional[int] = Field(None, ge=0, description="Minimum height in pixels")
    max_height: Optional[int] = Field(None, ge=0, description="Maximum height in pixels")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    search: Optional[str] = Field(None, description="Search in filename")


# Validation Schemas

class ValidationResult(BaseModel):
    """Image validation result."""
    is_valid: bool = Field(..., description="Whether image is valid")
    format: Optional[str] = Field(None, description="Detected format")
    mime_type: Optional[str] = Field(None, description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    color_mode: Optional[str] = Field(None, description="Color mode")
    bit_depth: Optional[int] = Field(None, description="Bit depth")
    md5_hash: Optional[str] = Field(None, description="MD5 hash")
    sha256_hash: Optional[str] = Field(None, description="SHA256 hash")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


# Statistics Schemas

class ImageStatistics(BaseModel):
    """Image statistics."""
    total_images: int = Field(..., description="Total number of images")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    total_size_mb: float = Field(..., description="Total size in MB")
    total_size_gb: float = Field(..., description="Total size in GB")
    by_format: Dict[str, int] = Field(..., description="Count by format")
    by_modality: Dict[str, int] = Field(..., description="Count by modality")
    by_processing_status: Dict[str, int] = Field(..., description="Count by processing status")
    average_file_size_mb: float = Field(..., description="Average file size in MB")
    average_dimensions: Optional[str] = Field(None, description="Average dimensions")
    with_thumbnails: int = Field(..., description="Images with thumbnails")
    total_views: int = Field(..., description="Total view count")


# Event Schemas

class ImageEventData(BaseModel):
    """Image event data for event emission."""
    image_id: str
    case_id: Optional[str] = None
    original_filename: str
    file_format: str
    file_size: int
    processing_status: str
    uploaded_by: Optional[str] = None
    updated_by: Optional[str] = None


# Health Check Schema

class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime
    service: str = "image-service"
    version: str = "1.0.0"
    database: str = "connected"
    storage: str = "connected"
    
    class Config:
        from_attributes = True


# Error Schemas

class ValidationError(BaseModel):
    """Validation error response."""
    error: str = "Validation failed"
    message: str
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    correlation_id: Optional[str] = None


class UploadError(BaseModel):
    """Upload error response."""
    error: str = "Upload failed"
    message: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class StorageError(BaseModel):
    """Storage error response."""
    error: str = "Storage error"
    message: str
    storage_key: Optional[str] = None
    correlation_id: Optional[str] = None
