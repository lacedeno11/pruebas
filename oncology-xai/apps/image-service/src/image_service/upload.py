# DERCAS-ONCO-XAI V1 - Image Service Upload Handler
# Multipart upload handling with validation and storage

import os
import tempfile
import shutil
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
import aiofiles
import structlog

from .config import Settings
from .validation import ImageValidator
from .storage import ImageStorage
from .models import Image

logger = structlog.get_logger(__name__)


class ImageUploadHandler:
    """Handle image uploads with validation and storage."""
    
    def __init__(self, settings: Settings, storage: ImageStorage, validator: ImageValidator):
        """
        Initialize upload handler.
        
        Args:
            settings: Application settings
            storage: Storage manager
            validator: Image validator
        """
        self.settings = settings
        self.storage = storage
        self.validator = validator
        
        # Ensure temp directory exists
        os.makedirs(self.settings.temp_dir, exist_ok=True)
        
        logger.info(
            "Upload handler initialized",
            temp_dir=self.settings.temp_dir,
            max_file_size_mb=self.settings.get_max_file_size_mb()
        )
    
    async def handle_upload(
        self,
        upload_file: UploadFile,
        case_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle complete image upload process.
        
        Args:
            upload_file: FastAPI upload file
            case_id: Optional case ID to associate with
            user_id: User uploading the image
            metadata: Additional metadata
            
        Returns:
            Upload result with image information
            
        Raises:
            HTTPException: If upload fails
        """
        temp_file_path = None
        
        try:
            # Validate upload file
            self._validate_upload_file(upload_file)
            
            # Create temporary file
            temp_file_path = await self._save_temp_file(upload_file)
            
            # Validate image
            validation_result = self.validator.validate_file(
                temp_file_path, 
                upload_file.filename
            )
            
            if not validation_result['is_valid']:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "Image validation failed",
                        "validation_errors": validation_result['errors'],
                        "validation_warnings": validation_result.get('warnings', [])
                    }
                )
            
            # Generate image ID and storage key
            import uuid
            image_id = str(uuid.uuid4())
            storage_key = self.storage.generate_storage_key(
                image_id, 
                upload_file.filename, 
                case_id
            )
            
            # Upload to storage
            upload_metadata = {
                "image-id": image_id,
                "original-filename": upload_file.filename,
                "uploaded-by": user_id or "unknown",
                "case-id": case_id or ""
            }
            
            if metadata:
                # Add custom metadata with prefix
                for key, value in metadata.items():
                    upload_metadata[f"custom-{key}"] = str(value)
            
            storage_result = await self.storage.upload_file(
                temp_file_path,
                storage_key,
                validation_result['mime_type'],
                upload_metadata
            )
            
            # Prepare image data for database
            image_data = {
                "id": image_id,
                "case_id": case_id,
                "original_filename": upload_file.filename,
                "content_type": validation_result['mime_type'],
                "file_format": validation_result['format'],
                "file_size": validation_result['file_size'],
                "md5_hash": validation_result['md5_hash'],
                "sha256_hash": validation_result['sha256_hash'],
                "storage_path": f"{self.storage.bucket_name}/{storage_key}",
                "storage_bucket": self.storage.bucket_name,
                "storage_key": storage_key,
                "width": validation_result.get('width'),
                "height": validation_result.get('height'),
                "color_mode": validation_result.get('color_mode'),
                "bit_depth": validation_result.get('bit_depth'),
                "processing_status": "uploaded",
                "is_validated": True,
                "uploaded_by": user_id,
                "metadata_": metadata or {}
            }
            
            # Add validation warnings to metadata if any
            if validation_result.get('warnings'):
                image_data["metadata_"]["validation_warnings"] = validation_result['warnings']
            
            result = {
                "image_id": image_id,
                "storage_key": storage_key,
                "storage_result": storage_result,
                "validation_result": validation_result,
                "image_data": image_data
            }
            
            logger.info(
                "Image upload completed successfully",
                image_id=image_id,
                filename=upload_file.filename,
                size_mb=round(validation_result['file_size'] / (1024 * 1024), 2),
                format=validation_result['format'],
                case_id=case_id,
                user_id=user_id
            )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Image upload failed",
                filename=upload_file.filename if upload_file else "unknown",
                error=str(e),
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image upload failed"
            )
        
        finally:
            # Clean up temporary file
            if temp_file_path and self.settings.cleanup_temp_files:
                await self._cleanup_temp_file(temp_file_path)
    
    def _validate_upload_file(self, upload_file: UploadFile) -> None:
        """
        Validate upload file basic properties.
        
        Args:
            upload_file: FastAPI upload file
            
        Raises:
            HTTPException: If validation fails
        """
        if not upload_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        if not upload_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        # Check file extension
        file_ext = Path(upload_file.filename).suffix.lower().lstrip('.')
        if file_ext not in ['png', 'biff', 'tiff', 'tif']:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File extension '{file_ext}' is not allowed. Allowed: png, biff, tiff, tif"
            )
        
        # Check content type if provided
        if upload_file.content_type:
            allowed_content_types = [
                'image/png',
                'image/tiff',
                'image/tif',
                'application/octet-stream'  # Sometimes browsers send this
            ]
            
            if upload_file.content_type not in allowed_content_types:
                logger.warning(
                    "Unexpected content type",
                    content_type=upload_file.content_type,
                    filename=upload_file.filename
                )
    
    async def _save_temp_file(self, upload_file: UploadFile) -> str:
        """
        Save upload file to temporary location.
        
        Args:
            upload_file: FastAPI upload file
            
        Returns:
            Path to temporary file
            
        Raises:
            HTTPException: If save fails
        """
        try:
            # Create temporary file
            file_ext = Path(upload_file.filename).suffix
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=file_ext,
                dir=self.settings.temp_dir
            )
            
            try:
                # Read and write file in chunks
                total_size = 0
                
                with os.fdopen(temp_fd, 'wb') as temp_file:
                    while True:
                        chunk = await upload_file.read(self.settings.upload_chunk_size)
                        if not chunk:
                            break
                        
                        total_size += len(chunk)
                        
                        # Check size limit
                        if total_size > self.settings.max_file_size:
                            raise HTTPException(
                                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail=f"File too large. Maximum size: {self.settings.get_max_file_size_mb():.1f}MB"
                            )
                        
                        temp_file.write(chunk)
                
                # Reset upload file position for potential re-reading
                await upload_file.seek(0)
                
                logger.debug(
                    "Temporary file saved",
                    temp_path=temp_path,
                    size_mb=round(total_size / (1024 * 1024), 2)
                )
                
                return temp_path
                
            except Exception:
                # Clean up temp file if writing failed
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to save temporary file", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process uploaded file"
            )
    
    async def _cleanup_temp_file(self, temp_path: str) -> None:
        """
        Clean up temporary file.
        
        Args:
            temp_path: Path to temporary file
        """
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.debug("Temporary file cleaned up", temp_path=temp_path)
        except Exception as e:
            logger.warning("Failed to clean up temporary file", temp_path=temp_path, error=str(e))
    
    async def handle_stream_upload(
        self,
        file_stream: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        case_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle upload from a stream (for direct API uploads).
        
        Args:
            file_stream: File stream
            filename: Original filename
            content_type: MIME content type
            file_size: File size in bytes
            case_id: Optional case ID
            user_id: User uploading the image
            metadata: Additional metadata
            
        Returns:
            Upload result
        """
        try:
            # Validate stream parameters
            if file_size > self.settings.max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size: {self.settings.get_max_file_size_mb():.1f}MB"
                )
            
            # Validate stream using validator
            validation_result = self.validator.validate_stream(
                file_stream, 
                filename, 
                self.settings.max_file_size
            )
            
            if not validation_result['is_valid']:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "Image validation failed",
                        "validation_errors": validation_result['errors']
                    }
                )
            
            # Generate image ID and storage key
            import uuid
            image_id = str(uuid.uuid4())
            storage_key = self.storage.generate_storage_key(
                image_id, 
                filename, 
                case_id
            )
            
            # Reset stream position
            file_stream.seek(0)
            
            # Upload to storage
            upload_metadata = {
                "image-id": image_id,
                "original-filename": filename,
                "uploaded-by": user_id or "unknown",
                "case-id": case_id or ""
            }
            
            if metadata:
                for key, value in metadata.items():
                    upload_metadata[f"custom-{key}"] = str(value)
            
            storage_result = await self.storage.upload_stream(
                file_stream,
                storage_key,
                file_size,
                content_type,
                upload_metadata
            )
            
            # Prepare image data
            image_data = {
                "id": image_id,
                "case_id": case_id,
                "original_filename": filename,
                "content_type": content_type,
                "file_format": validation_result['format'],
                "file_size": file_size,
                "md5_hash": validation_result['md5_hash'],
                "sha256_hash": validation_result['sha256_hash'],
                "storage_path": f"{self.storage.bucket_name}/{storage_key}",
                "storage_bucket": self.storage.bucket_name,
                "storage_key": storage_key,
                "processing_status": "uploaded",
                "is_validated": True,
                "uploaded_by": user_id,
                "metadata_": metadata or {}
            }
            
            result = {
                "image_id": image_id,
                "storage_key": storage_key,
                "storage_result": storage_result,
                "validation_result": validation_result,
                "image_data": image_data
            }
            
            logger.info(
                "Stream upload completed successfully",
                image_id=image_id,
                filename=filename,
                size_mb=round(file_size / (1024 * 1024), 2),
                format=validation_result['format'],
                case_id=case_id,
                user_id=user_id
            )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Stream upload failed",
                filename=filename,
                error=str(e),
                user_id=user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stream upload failed"
            )
    
    async def generate_thumbnail(self, image_path: str, thumbnail_path: str) -> Dict[str, Any]:
        """
        Generate thumbnail for an image.
        
        Args:
            image_path: Path to original image
            thumbnail_path: Path to save thumbnail
            
        Returns:
            Thumbnail generation result
        """
        try:
            from PIL import Image as PILImage
            
            with PILImage.open(image_path) as img:
                # Calculate thumbnail size maintaining aspect ratio
                img.thumbnail(self.settings.thumbnail_size, PILImage.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, optimize=True, quality=self.settings.image_quality)
                
                thumbnail_size = os.path.getsize(thumbnail_path)
                
                result = {
                    "thumbnail_path": thumbnail_path,
                    "thumbnail_size": thumbnail_size,
                    "thumbnail_dimensions": img.size
                }
                
                logger.info(
                    "Thumbnail generated",
                    original_path=image_path,
                    thumbnail_path=thumbnail_path,
                    thumbnail_size_kb=round(thumbnail_size / 1024, 2),
                    dimensions=f"{img.size[0]}x{img.size[1]}"
                )
                
                return result
                
        except Exception as e:
            logger.error(
                "Thumbnail generation failed",
                image_path=image_path,
                error=str(e)
            )
            raise


# Global upload handler instance
_upload_handler: Optional[ImageUploadHandler] = None


async def get_upload_handler(
    settings: Settings = None,
    storage: ImageStorage = None,
    validator: ImageValidator = None
) -> ImageUploadHandler:
    """Get upload handler instance."""
    global _upload_handler
    if _upload_handler is None:
        if settings is None:
            from .config import get_settings
            settings = get_settings()
        
        if storage is None:
            from .storage import get_storage
            storage = await get_storage(settings)
        
        if validator is None:
            from .validation import create_image_validator
            validator = create_image_validator(
                settings.allowed_formats,
                settings.validate_magic_bytes
            )
        
        _upload_handler = ImageUploadHandler(settings, storage, validator)
    
    return _upload_handler


async def cleanup_upload_handler() -> None:
    """Cleanup upload handler resources."""
    global _upload_handler
    if _upload_handler is not None:
        # Clean up any remaining temp files
        try:
            temp_dir = _upload_handler.settings.temp_dir
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        try:
                            os.unlink(file_path)
                        except Exception:
                            pass
        except Exception:
            pass
        
        _upload_handler = None
    
    logger.info("Upload handler cleanup completed")
