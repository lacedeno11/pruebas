"""
DERCAS-ONCO-XAI V1 - Image Service Business Logic

Business logic services for image management and storage.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import uuid4

import aiofiles
from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.errors import (
    ErrorCode,
    ResourceNotFoundError,
    ResourceConflictError,
    BusinessLogicError,
    FileError,
    ExternalServiceError
)

from .models import Image, ImageThumbnail, ImageProcessingJob
from .config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage with MinIO S3."""
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        region: str = "us-east-1",
        secure: bool = False
    ):
        self.endpoint = endpoint.replace("http://", "").replace("https://", "")
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region = region
        self.secure = secure
        self.client: Optional[Minio] = None
        
        logger.info(f"Initialized storage service for bucket: {bucket_name}")
    
    async def initialize(self):
        """Initialize MinIO client and ensure bucket exists."""
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region=self.region
            )
            
            # Check if bucket exists, create if not
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name, location=self.region)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket exists: {self.bucket_name}")
            
            # Set bucket policy for public read access (for development)
            # In production, use signed URLs for all access
            
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {e}")
            raise ExternalServiceError(
                service_name="MinIO",
                message=f"Storage initialization failed: {e}"
            )
    
    async def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Upload file to storage.
        
        Args:
            file_data: File content as bytes
            object_key: Storage object key/path
            content_type: MIME content type
            metadata: Additional metadata
            
        Returns:
            dict: Upload result with storage information
        """
        if not self.client:
            raise RuntimeError("Storage service not initialized")
        
        try:
            # Upload file
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=file_data,
                length=len(file_data),
                content_type=content_type,
                metadata=metadata or {}
            )
            
            logger.info(f"Uploaded file to storage: {object_key}")
            
            return {
                "bucket": self.bucket_name,
                "object_key": object_key,
                "etag": result.etag,
                "size": len(file_data),
                "content_type": content_type
            }
            
        except S3Error as e:
            logger.error(f"S3 error uploading file {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Failed to upload file: {e}"
            )
        except Exception as e:
            logger.error(f"Error uploading file {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Storage upload failed: {e}"
            )
    
    async def download_file(self, object_key: str) -> bytes:
        """
        Download file from storage.
        
        Args:
            object_key: Storage object key/path
            
        Returns:
            bytes: File content
        """
        if not self.client:
            raise RuntimeError("Storage service not initialized")
        
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.debug(f"Downloaded file from storage: {object_key}")
            return data
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ResourceNotFoundError(
                    resource_type="File",
                    resource_id=object_key
                )
            logger.error(f"S3 error downloading file {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Failed to download file: {e}"
            )
        except Exception as e:
            logger.error(f"Error downloading file {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Storage download failed: {e}"
            )
    
    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            object_key: Storage object key/path
            
        Returns:
            bool: True if deleted successfully
        """
        if not self.client:
            raise RuntimeError("Storage service not initialized")
        
        try:
            self.client.remove_object(self.bucket_name, object_key)
            logger.info(f"Deleted file from storage: {object_key}")
            return True
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found for deletion: {object_key}")
                return False
            logger.error(f"S3 error deleting file {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Failed to delete file: {e}"
            )
        except Exception as e:
            logger.error(f"Error deleting file {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Storage deletion failed: {e}"
            )
    
    async def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            object_key: Storage object key/path
            
        Returns:
            bool: True if file exists
        """
        if not self.client:
            raise RuntimeError("Storage service not initialized")
        
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
    
    async def generate_presigned_url(
        self,
        object_key: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate presigned URL for file access.
        
        Args:
            object_key: Storage object key/path
            expires_in: URL expiration time in seconds
            method: HTTP method (GET, PUT, etc.)
            
        Returns:
            str: Presigned URL
        """
        if not self.client:
            raise RuntimeError("Storage service not initialized")
        
        try:
            expires = timedelta(seconds=expires_in)
            
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_key,
                    expires=expires
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_key,
                    expires=expires
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            logger.debug(f"Generated presigned URL for {object_key}")
            return url
            
        except Exception as e:
            logger.error(f"Error generating presigned URL for {object_key}: {e}")
            raise FileError(
                error_code=ErrorCode.STORAGE_ERROR,
                message=f"Failed to generate presigned URL: {e}"
            )
    
    async def health_check(self) -> bool:
        """Check storage service health."""
        if not self.client:
            return False
        
        try:
            # Try to list objects in bucket (limit to 1)
            objects = list(self.client.list_objects(self.bucket_name, max_keys=1))
            return True
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False
    
    async def close(self):
        """Close storage service connections."""
        # MinIO client doesn't require explicit closing
        logger.info("Storage service closed")


class ImageService:
    """Service for image management operations."""
    
    def __init__(self, db: AsyncSession, storage_service: StorageService):
        self.db = db
        self.storage_service = storage_service
        self.settings = get_settings()
    
    async def upload_image(
        self,
        case_id: str,
        file: UploadFile,
        description: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> Image:
        """
        Upload and store an image.
        
        Args:
            case_id: Associated case ID
            file: Uploaded file
            description: Image description
            uploaded_by: User who uploaded the image
            
        Returns:
            Image: Created image record
        """
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate by checksum
        existing_image = await self._get_image_by_checksum(checksum)
        if existing_image:
            raise ResourceConflictError(
                message=f"Image with identical content already exists: {existing_image.image_id}"
            )
        
        # Generate unique identifiers
        image_id = f"img_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
        
        # Determine file format from filename
        file_format = self._get_file_format(file.filename or "unknown")
        
        # Generate storage path
        storage_path = self._generate_storage_path(case_id, image_id, file_format)
        
        try:
            # Upload to storage
            upload_result = await self.storage_service.upload_file(
                file_data=file_content,
                object_key=storage_path,
                content_type=file.content_type or "application/octet-stream",
                metadata={
                    "case_id": case_id,
                    "image_id": image_id,
                    "original_filename": file.filename or "unknown",
                    "uploaded_by": uploaded_by or "unknown"
                }
            )
            
            # Create image record
            image = Image(
                image_id=image_id,
                case_id=case_id,
                filename=file.filename or "unknown",
                file_size=file_size,
                file_format=file_format,
                checksum=checksum,
                storage_path=storage_path,
                storage_bucket=self.settings.s3_bucket,
                description=description,
                uploaded_by=uploaded_by,
                upload_source="api"
            )
            
            self.db.add(image)
            await self.db.commit()
            await self.db.refresh(image)
            
            logger.info(f"Image uploaded successfully: {image_id}")
            return image
            
        except Exception as e:
            # Clean up storage if database operation fails
            try:
                await self.storage_service.delete_file(storage_path)
            except:
                pass  # Ignore cleanup errors
            
            logger.error(f"Failed to upload image: {e}")
            raise
    
    async def get_image_by_id(self, image_id: str) -> Optional[Image]:
        """
        Get image by external ID.
        
        Args:
            image_id: External image ID
            
        Returns:
            Image: Image record or None if not found
        """
        stmt = select(Image).where(
            and_(
                Image.image_id == image_id,
                Image.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_case_images(self, case_id: str) -> List[Image]:
        """
        List all images for a case.
        
        Args:
            case_id: Case ID
            
        Returns:
            List[Image]: List of images for the case
        """
        stmt = select(Image).where(
            and_(
                Image.case_id == case_id,
                Image.deleted_at.is_(None)
            )
        ).order_by(Image.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_image(self, image_id: str) -> bool:
        """
        Delete an image (soft delete).
        
        Args:
            image_id: External image ID
            
        Returns:
            bool: True if deleted successfully
        """
        image = await self.get_image_by_id(image_id)
        if not image:
            return False
        
        try:
            # Soft delete in database
            image.soft_delete()
            await self.db.commit()
            
            # Delete from storage (async, don't wait)
            # In production, you might want to queue this for background processing
            try:
                await self.storage_service.delete_file(image.storage_path)
            except Exception as e:
                logger.warning(f"Failed to delete file from storage: {e}")
            
            logger.info(f"Image deleted: {image_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image {image_id}: {e}")
            raise
    
    async def update_image_metadata(
        self,
        image_id: str,
        metadata_update: dict
    ) -> Optional[Image]:
        """
        Update image metadata.
        
        Args:
            image_id: External image ID
            metadata_update: Metadata updates
            
        Returns:
            Image: Updated image or None if not found
        """
        image = await self.get_image_by_id(image_id)
        if not image:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'description', 'acquisition_date', 'modality', 
            'magnification', 'staining', 'metadata'
        ]
        
        for field, value in metadata_update.items():
            if field in allowed_fields:
                setattr(image, field, value)
        
        image.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(image)
        
        logger.info(f"Updated image metadata: {image_id}")
        return image
    
    async def mark_image_as_processed(
        self,
        image_id: str,
        processing_status: str = "completed",
        result_data: Optional[dict] = None
    ) -> Optional[Image]:
        """
        Mark image as processed.
        
        Args:
            image_id: External image ID
            processing_status: Processing status
            result_data: Processing result data
            
        Returns:
            Image: Updated image or None if not found
        """
        image = await self.get_image_by_id(image_id)
        if not image:
            return None
        
        image.mark_as_processed(processing_status)
        
        if result_data and image.metadata:
            image.metadata.update({"processing_results": result_data})
        elif result_data:
            image.metadata = {"processing_results": result_data}
        
        await self.db.commit()
        await self.db.refresh(image)
        
        logger.info(f"Marked image as processed: {image_id}")
        return image
    
    async def get_image_statistics(self, case_id: Optional[str] = None) -> dict:
        """
        Get image statistics.
        
        Args:
            case_id: Optional case ID to filter by
            
        Returns:
            dict: Image statistics
        """
        base_query = select(Image).where(Image.deleted_at.is_(None))
        
        if case_id:
            base_query = base_query.where(Image.case_id == case_id)
        
        # Total images
        total_stmt = select(func.count(Image.id)).where(Image.deleted_at.is_(None))
        if case_id:
            total_stmt = total_stmt.where(Image.case_id == case_id)
        
        total_result = await self.db.execute(total_stmt)
        total_images = total_result.scalar()
        
        # Images by format
        format_stmt = select(Image.file_format, func.count(Image.id)).where(
            Image.deleted_at.is_(None)
        ).group_by(Image.file_format)
        if case_id:
            format_stmt = format_stmt.where(Image.case_id == case_id)
        
        format_result = await self.db.execute(format_stmt)
        images_by_format = {fmt: count for fmt, count in format_result.all()}
        
        # Total storage size
        size_stmt = select(func.sum(Image.file_size)).where(Image.deleted_at.is_(None))
        if case_id:
            size_stmt = size_stmt.where(Image.case_id == case_id)
        
        size_result = await self.db.execute(size_stmt)
        total_size = size_result.scalar() or 0
        
        # Processed images
        processed_stmt = select(func.count(Image.id)).where(
            and_(
                Image.deleted_at.is_(None),
                Image.is_processed == True
            )
        )
        if case_id:
            processed_stmt = processed_stmt.where(Image.case_id == case_id)
        
        processed_result = await self.db.execute(processed_stmt)
        processed_images = processed_result.scalar()
        
        return {
            "total_images": total_images,
            "images_by_format": images_by_format,
            "total_storage_size_bytes": total_size,
            "total_storage_size_mb": total_size / (1024 * 1024) if total_size else 0,
            "average_file_size_mb": (total_size / total_images / (1024 * 1024)) if total_images else 0,
            "processed_images": processed_images,
            "case_id": case_id
        }
    
    async def _get_image_by_checksum(self, checksum: str) -> Optional[Image]:
        """Get image by checksum."""
        stmt = select(Image).where(
            and_(
                Image.checksum == checksum,
                Image.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def _get_file_format(self, filename: str) -> str:
        """Extract file format from filename."""
        if not filename:
            return "unknown"
        
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        return ext if ext in self.settings.allowed_formats else "unknown"
    
    def _generate_storage_path(self, case_id: str, image_id: str, file_format: str) -> str:
        """Generate storage path for image."""
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        return f"{self.settings.storage_path_prefix}/{date_prefix}/{case_id}/{image_id}.{file_format}"
