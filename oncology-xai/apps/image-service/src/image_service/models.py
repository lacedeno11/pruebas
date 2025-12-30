# DERCAS-ONCO-XAI V1 - Image Service Models
# SQLAlchemy 2.0 models for image metadata and storage

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, DateTime, Integer, Boolean, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
import uuid


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Image(Base):
    """Image model for storing image metadata and storage information."""
    
    __tablename__ = "images"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique image identifier"
    )
    
    # Case association
    case_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="Associated case ID"
    )
    
    # File information
    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original filename as uploaded"
    )
    
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME content type"
    )
    
    file_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Image format (png, biff, etc.)"
    )
    
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )
    
    # Checksums for integrity
    md5_hash: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="MD5 hash of file content"
    )
    
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA256 hash of file content"
    )
    
    # Storage information
    storage_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Storage path in object store"
    )
    
    storage_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Storage bucket name"
    )
    
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Object key in storage"
    )
    
    # Image properties
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
    
    color_mode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Color mode (RGB, RGBA, L, etc.)"
    )
    
    bit_depth: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Bit depth per channel"
    )
    
    # Medical imaging metadata
    modality: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Imaging modality (CT, MRI, H&E, etc.)"
    )
    
    acquisition_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Image acquisition date"
    )
    
    patient_position: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Patient position during acquisition"
    )
    
    slice_thickness: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Slice thickness in mm"
    )
    
    pixel_spacing: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Pixel spacing (x,y) in mm"
    )
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
        comment="Processing status (uploaded, processing, processed, failed)"
    )
    
    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Processing error message if failed"
    )
    
    # Thumbnails and derivatives
    has_thumbnail: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether thumbnail has been generated"
    )
    
    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Thumbnail storage path"
    )
    
    # Validation status
    is_validated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether image has been validated"
    )
    
    validation_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Validation error message if failed"
    )
    
    # Access tracking
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times image has been viewed"
    )
    
    last_accessed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last access timestamp"
    )
    
    # Metadata and tags
    tags: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Image tags for categorization"
    )
    
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional image metadata"
    )
    
    # DICOM metadata (if applicable)
    dicom_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="DICOM metadata if applicable"
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
    
    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who uploaded the image"
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
        comment="Whether the image record is active"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_images_case_id", "case_id"),
        Index("idx_images_storage_key", "storage_key"),
        Index("idx_images_md5_hash", "md5_hash"),
        Index("idx_images_sha256_hash", "sha256_hash"),
        Index("idx_images_file_format", "file_format"),
        Index("idx_images_processing_status", "processing_status"),
        Index("idx_images_modality", "modality"),
        Index("idx_images_created_at", "created_at"),
        Index("idx_images_active", "is_active"),
        Index("idx_images_uploaded_by", "uploaded_by"),
        Index("idx_images_acquisition_date", "acquisition_date"),
    )
    
    def __repr__(self) -> str:
        return f"<Image(id={self.id}, filename={self.original_filename}, format={self.file_format})>"
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size / (1024 * 1024)
    
    @property
    def file_size_kb(self) -> float:
        """Get file size in KB."""
        return self.file_size / 1024
    
    @property
    def dimensions(self) -> Optional[str]:
        """Get image dimensions as string."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None
    
    @property
    def aspect_ratio(self) -> Optional[float]:
        """Calculate aspect ratio."""
        if self.width and self.height and self.height > 0:
            return self.width / self.height
        return None
    
    @property
    def is_processed(self) -> bool:
        """Check if image has been processed."""
        return self.processing_status == "processed"
    
    @property
    def is_processing(self) -> bool:
        """Check if image is currently being processed."""
        return self.processing_status == "processing"
    
    @property
    def has_errors(self) -> bool:
        """Check if image has processing or validation errors."""
        return (self.processing_status == "failed" or 
                self.processing_error is not None or
                self.validation_error is not None)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the image."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the image."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        if self.metadata_ is None:
            self.metadata_ = {}
        self.metadata_[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        if self.metadata_:
            return self.metadata_.get(key, default)
        return default
    
    def set_dicom_metadata(self, key: str, value: Any) -> None:
        """Set DICOM metadata value."""
        if self.dicom_metadata is None:
            self.dicom_metadata = {}
        self.dicom_metadata[key] = value
    
    def get_dicom_metadata(self, key: str, default: Any = None) -> Any:
        """Get DICOM metadata value."""
        if self.dicom_metadata:
            return self.dicom_metadata.get(key, default)
        return default
    
    def update_processing_status(self, status: str, error: Optional[str] = None) -> None:
        """Update processing status."""
        self.processing_status = status
        if error:
            self.processing_error = error
        elif status != "failed":
            self.processing_error = None
    
    def mark_validated(self, is_valid: bool, error: Optional[str] = None) -> None:
        """Mark image as validated."""
        self.is_validated = is_valid
        if not is_valid and error:
            self.validation_error = error
        elif is_valid:
            self.validation_error = None
    
    def increment_view_count(self) -> None:
        """Increment view count and update last accessed time."""
        self.view_count += 1
        self.last_accessed = datetime.utcnow()
    
    def get_storage_url(self, base_url: str) -> str:
        """Get full storage URL."""
        return f"{base_url.rstrip('/')}/{self.storage_bucket}/{self.storage_key}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert image to dictionary."""
        return {
            "id": self.id,
            "case_id": self.case_id,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "file_format": self.file_format,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "md5_hash": self.md5_hash,
            "sha256_hash": self.sha256_hash,
            "storage_path": self.storage_path,
            "storage_bucket": self.storage_bucket,
            "storage_key": self.storage_key,
            "width": self.width,
            "height": self.height,
            "dimensions": self.dimensions,
            "color_mode": self.color_mode,
            "bit_depth": self.bit_depth,
            "modality": self.modality,
            "acquisition_date": self.acquisition_date.isoformat() if self.acquisition_date else None,
            "patient_position": self.patient_position,
            "slice_thickness": self.slice_thickness,
            "pixel_spacing": self.pixel_spacing,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "has_thumbnail": self.has_thumbnail,
            "thumbnail_path": self.thumbnail_path,
            "is_validated": self.is_validated,
            "validation_error": self.validation_error,
            "view_count": self.view_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "tags": self.tags,
            "metadata": self.metadata_,
            "dicom_metadata": self.dicom_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "uploaded_by": self.uploaded_by,
            "updated_by": self.updated_by,
            "is_active": self.is_active
        }
