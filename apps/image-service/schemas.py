"""
DERCAS-ONCO-XAI V1 - Image Service Schemas

Pydantic request/response schemas for the Image Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')


# Base schemas
class ImageBase(BaseModel):
    """Base image schema."""
    image_id: str = Field(..., description="External image identifier", min_length=1, max_length=100)
    case_id: str = Field(..., description="Associated case ID", min_length=1, max_length=100)
    filename: str = Field(..., description="Original filename", max_length=255)
    description: Optional[str] = Field(None, description="Image description", max_length=1000)


class ImageMetadata(BaseModel):
    """Image metadata schema."""
    width: Optional[int] = Field(None, description="Image width in pixels", gt=0)
    height: Optional[int] = Field(None, description="Image height in pixels", gt=0)
    channels: Optional[int] = Field(None, description="Number of channels", gt=0)
    bit_depth: Optional[int] = Field(None, description="Bit depth", gt=0)
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition date")
    modality: Optional[str] = Field(None, description="Imaging modality", max_length=50)
    magnification: Optional[float] = Field(None, description="Magnification level", gt=0)
    staining: Optional[str] = Field(None, description="Staining method", max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Request schemas
class ImageUploadRequest(BaseModel):
    """Schema for image upload request."""
    case_id: str = Field(..., description="Associated case ID")
    description: Optional[str] = Field(None, description="Image description", max_length=1000)
    
    @validator('case_id')
    def validate_case_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Case ID cannot be empty')
        return v.strip()


class ImageUpdateRequest(BaseModel):
    """Schema for image update request."""
    description: Optional[str] = Field(None, description="Image description", max_length=1000)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition date")
    modality: Optional[str] = Field(None, description="Imaging modality", max_length=50)
    magnification: Optional[float] = Field(None, description="Magnification level", gt=0)
    staining: Optional[str] = Field(None, description="Staining method", max_length=100)


# Response schemas
class ImageResponse(BaseModel):
    """Schema for image response."""
    id: UUID = Field(..., description="Internal image ID")
    image_id: str = Field(..., description="External image identifier")
    case_id: str = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_format: str = Field(..., description="File format")
    checksum: str = Field(..., description="File checksum (SHA-256)")
    
    # Storage information
    storage_path: str = Field(..., description="Storage path/key")
    storage_bucket: str = Field(..., description="Storage bucket name")
    
    # Image metadata
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    channels: Optional[int] = Field(None, description="Number of channels")
    bit_depth: Optional[int] = Field(None, description="Bit depth")
    
    # Acquisition metadata
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition date")
    modality: Optional[str] = Field(None, description="Imaging modality")
    magnification: Optional[float] = Field(None, description="Magnification level")
    staining: Optional[str] = Field(None, description="Staining method")
    
    # Description and metadata
    description: Optional[str] = Field(None, description="Image description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # Processing status
    is_processed: bool = Field(..., description="Whether image has been processed")
    processing_status: Optional[str] = Field(None, description="Processing status")
    
    # Upload metadata
    uploaded_by: Optional[str] = Field(None, description="User who uploaded the image")
    upload_source: Optional[str] = Field(None, description="Upload source")
    
    # Validation status
    is_validated: bool = Field(..., description="Whether image has been validated")
    validation_errors: Optional[List[str]] = Field(None, description="Validation errors")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Computed fields
    file_size_mb: float = Field(..., description="File size in megabytes")
    dimensions: Optional[str] = Field(None, description="Image dimensions (WxH)")
    aspect_ratio: Optional[float] = Field(None, description="Image aspect ratio")
    pixel_count: Optional[int] = Field(None, description="Total pixel count")
    is_high_resolution: bool = Field(..., description="Whether image is high resolution")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object with computed fields."""
        data = {
            'id': obj.id,
            'image_id': obj.image_id,
            'case_id': obj.case_id,
            'filename': obj.filename,
            'file_size': obj.file_size,
            'file_format': obj.file_format,
            'checksum': obj.checksum,
            'storage_path': obj.storage_path,
            'storage_bucket': obj.storage_bucket,
            'width': obj.width,
            'height': obj.height,
            'channels': obj.channels,
            'bit_depth': obj.bit_depth,
            'acquisition_date': obj.acquisition_date,
            'modality': obj.modality,
            'magnification': obj.magnification,
            'staining': obj.staining,
            'description': obj.description,
            'metadata': obj.metadata,
            'is_processed': obj.is_processed,
            'processing_status': obj.processing_status,
            'uploaded_by': obj.uploaded_by,
            'upload_source': obj.upload_source,
            'is_validated': obj.is_validated,
            'validation_errors': obj.validation_errors,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'file_size_mb': obj.get_file_size_mb(),
            'dimensions': f"{obj.width}x{obj.height}" if obj.width and obj.height else None,
            'aspect_ratio': obj.get_aspect_ratio(),
            'pixel_count': obj.get_pixel_count(),
            'is_high_resolution': obj.is_high_resolution()
        }
        return cls(**data)


class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""
    id: UUID = Field(..., description="Internal image ID")
    image_id: str = Field(..., description="External image identifier")
    case_id: str = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_format: str = Field(..., description="File format")
    checksum: str = Field(..., description="File checksum (SHA-256)")
    storage_path: str = Field(..., description="Storage path/key")
    upload_status: str = Field(default="uploaded", description="Upload status")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    """Schema for image list response."""
    images: List[ImageResponse] = Field(..., description="List of images")
    total: int = Field(..., description="Total number of images")
    case_id: str = Field(..., description="Associated case ID")


class ViewerUrlResponse(BaseModel):
    """Schema for viewer URL response."""
    image_id: str = Field(..., description="Image identifier")
    viewer_url: str = Field(..., description="Signed URL for viewing the image")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    expires_at: Optional[datetime] = Field(None, description="URL expiration timestamp")


class ThumbnailResponse(BaseModel):
    """Schema for thumbnail response."""
    id: UUID = Field(..., description="Thumbnail ID")
    image_id: UUID = Field(..., description="Parent image ID")
    size: int = Field(..., description="Thumbnail size")
    width: int = Field(..., description="Thumbnail width")
    height: int = Field(..., description="Thumbnail height")
    file_size: int = Field(..., description="Thumbnail file size")
    storage_path: str = Field(..., description="Thumbnail storage path")
    viewer_url: Optional[str] = Field(None, description="Signed URL for viewing")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class ProcessingJobResponse(BaseModel):
    """Schema for processing job response."""
    id: UUID = Field(..., description="Job ID")
    job_id: str = Field(..., description="External job identifier")
    image_id: UUID = Field(..., description="Associated image ID")
    job_type: str = Field(..., description="Job type")
    status: str = Field(..., description="Job status")
    progress_percentage: int = Field(..., description="Progress percentage")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result_data: Optional[Dict[str, Any]] = Field(None, description="Job result data")
    worker_id: Optional[str] = Field(None, description="Worker ID")
    retry_count: int = Field(..., description="Number of retries")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Computed fields
    duration_seconds: Optional[float] = Field(None, description="Job duration in seconds")
    is_completed: bool = Field(..., description="Whether job is completed")
    is_running: bool = Field(..., description="Whether job is running")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Create response from ORM object with computed fields."""
        data = {
            'id': obj.id,
            'job_id': obj.job_id,
            'image_id': obj.image_id,
            'job_type': obj.job_type,
            'status': obj.status,
            'progress_percentage': obj.progress_percentage,
            'started_at': obj.started_at,
            'completed_at': obj.completed_at,
            'error_message': obj.error_message,
            'result_data': obj.result_data,
            'worker_id': obj.worker_id,
            'retry_count': obj.retry_count,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'duration_seconds': obj.get_duration_seconds(),
            'is_completed': obj.is_completed(),
            'is_running': obj.is_running()
        }
        return cls(**data)


# Search and filter schemas
class ImageSearchFilters(BaseModel):
    """Schema for image search filters."""
    case_id: Optional[str] = Field(None, description="Filter by case ID")
    file_format: Optional[str] = Field(None, description="Filter by file format")
    is_processed: Optional[bool] = Field(None, description="Filter by processing status")
    is_validated: Optional[bool] = Field(None, description="Filter by validation status")
    uploaded_by: Optional[str] = Field(None, description="Filter by uploader")
    modality: Optional[str] = Field(None, description="Filter by imaging modality")
    min_file_size: Optional[int] = Field(None, description="Minimum file size in bytes", gt=0)
    max_file_size: Optional[int] = Field(None, description="Maximum file size in bytes", gt=0)
    min_width: Optional[int] = Field(None, description="Minimum image width", gt=0)
    max_width: Optional[int] = Field(None, description="Maximum image width", gt=0)
    min_height: Optional[int] = Field(None, description="Minimum image height", gt=0)
    max_height: Optional[int] = Field(None, description="Maximum image height", gt=0)
    created_after: Optional[datetime] = Field(None, description="Filter images created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter images created before this date")
    
    @validator('max_file_size')
    def validate_file_size_range(cls, v, values):
        min_size = values.get('min_file_size')
        if min_size is not None and v is not None and v < min_size:
            raise ValueError('max_file_size must be greater than or equal to min_file_size')
        return v
    
    @validator('max_width')
    def validate_width_range(cls, v, values):
        min_width = values.get('min_width')
        if min_width is not None and v is not None and v < min_width:
            raise ValueError('max_width must be greater than or equal to min_width')
        return v
    
    @validator('max_height')
    def validate_height_range(cls, v, values):
        min_height = values.get('min_height')
        if min_height is not None and v is not None and v < min_height:
            raise ValueError('max_height must be greater than or equal to min_height')
        return v


# Statistics schemas
class ImageStatistics(BaseModel):
    """Schema for image statistics."""
    total_images: int = Field(..., description="Total number of images")
    images_by_format: Dict[str, int] = Field(..., description="Image count by format")
    images_by_case: Dict[str, int] = Field(..., description="Image count by case")
    images_by_status: Dict[str, int] = Field(..., description="Image count by processing status")
    total_storage_size_bytes: int = Field(..., description="Total storage size in bytes")
    total_storage_size_mb: float = Field(..., description="Total storage size in MB")
    average_file_size_mb: float = Field(..., description="Average file size in MB")
    processed_images: int = Field(..., description="Number of processed images")
    validated_images: int = Field(..., description="Number of validated images")
    high_resolution_images: int = Field(..., description="Number of high resolution images")


# Validation schemas
class FileValidationResult(BaseModel):
    """Schema for file validation result."""
    is_valid: bool = Field(..., description="Whether file is valid")
    file_format: Optional[str] = Field(None, description="Detected file format")
    file_size: int = Field(..., description="File size in bytes")
    checksum: str = Field(..., description="File checksum")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extracted metadata")


# Bulk operation schemas
class BulkImageOperation(BaseModel):
    """Schema for bulk image operations."""
    image_ids: List[str] = Field(..., description="List of image IDs", min_items=1, max_items=100)
    operation: str = Field(..., description="Operation to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")
    
    @validator('image_ids')
    def validate_image_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate image IDs are not allowed')
        return v


class BulkOperationResult(BaseModel):
    """Schema for bulk operation results."""
    total_requested: int = Field(..., description="Total number of items requested")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="List of errors")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Operation results")


# Health check schemas
class StorageHealthCheck(BaseModel):
    """Schema for storage health check."""
    is_connected: bool = Field(..., description="Storage connection status")
    bucket_accessible: bool = Field(..., description="Bucket accessibility status")
    total_objects: Optional[int] = Field(None, description="Total number of objects")
    total_size_bytes: Optional[int] = Field(None, description="Total storage size")
    last_check: datetime = Field(..., description="Last health check timestamp")


class ServiceHealthCheck(BaseModel):
    """Schema for service health check."""
    database_connected: bool = Field(..., description="Database connection status")
    storage_connected: bool = Field(..., description="Storage connection status")
    event_bus_connected: bool = Field(..., description="Event bus connection status")
    total_images: int = Field(..., description="Total number of images")
    processed_images: int = Field(..., description="Number of processed images")
    storage_usage_mb: float = Field(..., description="Storage usage in MB")


# Event schemas (for API responses)
class ImageEventInfo(BaseModel):
    """Schema for image event information."""
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    details: Optional[Dict[str, Any]] = Field(None, description="Event details")
