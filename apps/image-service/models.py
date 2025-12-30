"""
DERCAS-ONCO-XAI V1 - Image Service Models

SQLAlchemy 2.0 models for medical image storage and metadata.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class Image(Base):
    """Medical image model with storage and metadata information."""
    
    __tablename__ = "images"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # External identifier
    image_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="External image identifier"
    )
    
    # Case association
    case_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Associated case ID"
    )
    
    # File metadata
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename"
    )
    
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )
    
    file_format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="File format (png, tiff, etc.)"
    )
    
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="File checksum (SHA-256)"
    )
    
    # Storage metadata
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        comment="Storage path/key in S3"
    )
    
    storage_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Storage bucket name"
    )
    
    # Image metadata
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image width in pixels"
    )
    
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Image height in pixels"
    )
    
    channels: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of channels"
    )
    
    bit_depth: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Bit depth"
    )
    
    # Acquisition metadata
    acquisition_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Image acquisition date"
    )
    
    modality: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Imaging modality"
    )
    
    magnification: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Magnification level"
    )
    
    staining: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Staining method"
    )
    
    # Description and metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Image description"
    )
    
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional image metadata"
    )
    
    # Processing status
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether image has been processed"
    )
    
    processing_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Processing status"
    )
    
    # Upload metadata
    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="User who uploaded the image"
    )
    
    upload_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Upload source (web, api, etc.)"
    )
    
    # Validation status
    is_validated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether image has been validated"
    )
    
    validation_errors: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="Validation errors if any"
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
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Deletion timestamp (soft delete)"
    )
    
    def __repr__(self) -> str:
        return f"<Image(id={self.id}, image_id='{self.image_id}', case_id='{self.case_id}')>"
    
    def is_deleted(self) -> bool:
        """Check if image is soft deleted."""
        return self.deleted_at is not None
    
    def get_file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    def get_dimensions(self) -> Optional[tuple]:
        """Get image dimensions as (width, height)."""
        if self.width and self.height:
            return (self.width, self.height)
        return None
    
    def get_aspect_ratio(self) -> Optional[float]:
        """Get image aspect ratio."""
        if self.width and self.height and self.height > 0:
            return self.width / self.height
        return None
    
    def get_pixel_count(self) -> Optional[int]:
        """Get total pixel count."""
        if self.width and self.height:
            return self.width * self.height
        return None
    
    def is_high_resolution(self, threshold: int = 2048) -> bool:
        """Check if image is high resolution."""
        if self.width and self.height:
            return max(self.width, self.height) >= threshold
        return False
    
    def get_storage_url(self, base_url: str) -> str:
        """Get full storage URL."""
        return f"{base_url.rstrip('/')}/{self.storage_bucket}/{self.storage_path}"
    
    def can_be_processed(self) -> bool:
        """Check if image can be processed."""
        return (
            not self.is_deleted() and
            self.is_validated and
            not self.is_processed and
            not self.validation_errors
        )
    
    def mark_as_processed(self, status: str = "completed"):
        """Mark image as processed."""
        self.is_processed = True
        self.processing_status = status
        self.updated_at = datetime.utcnow()
    
    def mark_as_validated(self, errors: Optional[list] = None):
        """Mark image as validated."""
        self.is_validated = True
        self.validation_errors = errors
        self.updated_at = datetime.utcnow()
    
    def soft_delete(self):
        """Soft delete the image."""
        self.deleted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class ImageThumbnail(Base):
    """Image thumbnail model for different sizes."""
    
    __tablename__ = "image_thumbnails"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Parent image reference
    image_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Parent image ID"
    )
    
    # Thumbnail metadata
    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thumbnail size (max dimension)"
    )
    
    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thumbnail width in pixels"
    )
    
    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thumbnail height in pixels"
    )
    
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thumbnail file size in bytes"
    )
    
    # Storage metadata
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        comment="Thumbnail storage path/key in S3"
    )
    
    storage_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Storage bucket name"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    def __repr__(self) -> str:
        return f"<ImageThumbnail(id={self.id}, image_id={self.image_id}, size={self.size})>"
    
    def get_dimensions(self) -> tuple:
        """Get thumbnail dimensions as (width, height)."""
        return (self.width, self.height)
    
    def get_file_size_kb(self) -> float:
        """Get file size in kilobytes."""
        return self.file_size / 1024


class ImageProcessingJob(Base):
    """Image processing job tracking."""
    
    __tablename__ = "image_processing_jobs"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Job identifier
    job_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="External job identifier"
    )
    
    # Image reference
    image_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Associated image ID"
    )
    
    # Job details
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Job type (validation, thumbnail, analysis, etc.)"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="Job status"
    )
    
    # Processing details
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Job start time"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Job completion time"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if failed"
    )
    
    # Results
    result_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Job result data"
    )
    
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Progress percentage"
    )
    
    # Metadata
    worker_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Worker that processed the job"
    )
    
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retries"
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
    
    def __repr__(self) -> str:
        return f"<ImageProcessingJob(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"
    
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status in ["completed", "failed", "cancelled"]
    
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == "running"
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None
    
    def mark_as_started(self, worker_id: Optional[str] = None):
        """Mark job as started."""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.worker_id = worker_id
        self.updated_at = datetime.utcnow()
    
    def mark_as_completed(self, result_data: Optional[dict] = None):
        """Mark job as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100
        if result_data:
            self.result_data = result_data
        self.updated_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str):
        """Mark job as failed."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
