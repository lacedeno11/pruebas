# DERCAS-ONCO-XAI V1 - Image Service Storage
# MinIO/S3 integration for image storage and retrieval

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from urllib.parse import urlparse
import aiofiles
from minio import Minio
from minio.error import S3Error
import structlog

from .config import Settings

logger = structlog.get_logger(__name__)


class ImageStorage:
    """MinIO/S3 storage manager for medical images."""
    
    def __init__(self, settings: Settings):
        """
        Initialize storage manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.s3_config = settings.get_s3_config()
        
        # Initialize MinIO client
        self.client = Minio(
            endpoint=self._parse_endpoint(self.s3_config['endpoint']),
            access_key=self.s3_config['access_key'],
            secret_key=self.s3_config['secret_key'],
            secure=self.s3_config['secure'],
            region=self.s3_config['region']
        )
        
        self.bucket_name = self.s3_config['bucket']
        
        logger.info(
            "Storage manager initialized",
            endpoint=self.s3_config['endpoint'],
            bucket=self.bucket_name,
            secure=self.s3_config['secure']
        )
    
    def _parse_endpoint(self, endpoint: str) -> str:
        """Parse endpoint URL to extract host:port."""
        parsed = urlparse(endpoint)
        if parsed.port:
            return f"{parsed.hostname}:{parsed.port}"
        return parsed.hostname
    
    async def ensure_bucket_exists(self) -> None:
        """Ensure the storage bucket exists."""
        try:
            # Run in thread pool since minio client is sync
            loop = asyncio.get_event_loop()
            
            # Check if bucket exists
            bucket_exists = await loop.run_in_executor(
                None, self.client.bucket_exists, self.bucket_name
            )
            
            if not bucket_exists:
                # Create bucket
                await loop.run_in_executor(
                    None, self.client.make_bucket, self.bucket_name
                )
                logger.info("Storage bucket created", bucket=self.bucket_name)
            else:
                logger.info("Storage bucket exists", bucket=self.bucket_name)
                
        except S3Error as e:
            logger.error("Failed to ensure bucket exists", error=str(e))
            raise
    
    def generate_storage_key(self, image_id: str, filename: str, case_id: str = None) -> str:
        """
        Generate storage key for an image.
        
        Args:
            image_id: Unique image ID
            filename: Original filename
            case_id: Optional case ID for organization
            
        Returns:
            Storage key path
        """
        # Extract file extension
        file_ext = Path(filename).suffix.lower()
        
        # Create hierarchical path
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        
        if case_id:
            # Organize by case
            storage_key = f"cases/{case_id}/{date_prefix}/{image_id}{file_ext}"
        else:
            # General images
            storage_key = f"images/{date_prefix}/{image_id}{file_ext}"
        
        return storage_key
    
    def generate_thumbnail_key(self, storage_key: str) -> str:
        """
        Generate thumbnail storage key from original key.
        
        Args:
            storage_key: Original storage key
            
        Returns:
            Thumbnail storage key
        """
        path = Path(storage_key)
        return str(path.parent / f"{path.stem}_thumb{path.suffix}")
    
    async def upload_file(
        self,
        file_path: str,
        storage_key: str,
        content_type: str = "application/octet-stream",
        metadata: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to storage.
        
        Args:
            file_path: Local file path
            storage_key: Storage key/path
            content_type: MIME content type
            metadata: Additional metadata
            
        Returns:
            Upload result dictionary
        """
        try:
            file_path = Path(file_path)
            file_size = file_path.stat().st_size
            
            # Prepare metadata
            upload_metadata = {
                "uploaded-at": datetime.utcnow().isoformat(),
                "original-size": str(file_size),
                "content-type": content_type
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload file
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.fput_object,
                self.bucket_name,
                storage_key,
                str(file_path),
                content_type,
                upload_metadata
            )
            
            # Get object info
            object_info = await loop.run_in_executor(
                None,
                self.client.stat_object,
                self.bucket_name,
                storage_key
            )
            
            upload_result = {
                "bucket": self.bucket_name,
                "key": storage_key,
                "size": object_info.size,
                "etag": object_info.etag,
                "last_modified": object_info.last_modified,
                "content_type": object_info.content_type,
                "metadata": object_info.metadata,
                "version_id": getattr(object_info, 'version_id', None)
            }
            
            logger.info(
                "File uploaded successfully",
                storage_key=storage_key,
                size=file_size,
                content_type=content_type
            )
            
            return upload_result
            
        except S3Error as e:
            logger.error(
                "File upload failed",
                storage_key=storage_key,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected upload error",
                storage_key=storage_key,
                error=str(e)
            )
            raise
    
    async def upload_stream(
        self,
        file_stream: BinaryIO,
        storage_key: str,
        file_size: int,
        content_type: str = "application/octet-stream",
        metadata: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Upload file from stream.
        
        Args:
            file_stream: File stream
            storage_key: Storage key/path
            file_size: Size of the file
            content_type: MIME content type
            metadata: Additional metadata
            
        Returns:
            Upload result dictionary
        """
        try:
            # Prepare metadata
            upload_metadata = {
                "uploaded-at": datetime.utcnow().isoformat(),
                "original-size": str(file_size),
                "content-type": content_type
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload stream
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.put_object,
                self.bucket_name,
                storage_key,
                file_stream,
                file_size,
                content_type,
                upload_metadata
            )
            
            # Get object info
            object_info = await loop.run_in_executor(
                None,
                self.client.stat_object,
                self.bucket_name,
                storage_key
            )
            
            upload_result = {
                "bucket": self.bucket_name,
                "key": storage_key,
                "size": object_info.size,
                "etag": object_info.etag,
                "last_modified": object_info.last_modified,
                "content_type": object_info.content_type,
                "metadata": object_info.metadata,
                "version_id": getattr(object_info, 'version_id', None)
            }
            
            logger.info(
                "Stream uploaded successfully",
                storage_key=storage_key,
                size=file_size,
                content_type=content_type
            )
            
            return upload_result
            
        except S3Error as e:
            logger.error(
                "Stream upload failed",
                storage_key=storage_key,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected stream upload error",
                storage_key=storage_key,
                error=str(e)
            )
            raise
    
    async def download_file(self, storage_key: str, local_path: str) -> Dict[str, Any]:
        """
        Download file from storage.
        
        Args:
            storage_key: Storage key/path
            local_path: Local file path to save
            
        Returns:
            Download result dictionary
        """
        try:
            # Download file
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.fget_object,
                self.bucket_name,
                storage_key,
                local_path
            )
            
            # Get file info
            file_size = Path(local_path).stat().st_size
            
            download_result = {
                "bucket": self.bucket_name,
                "key": storage_key,
                "local_path": local_path,
                "size": file_size
            }
            
            logger.info(
                "File downloaded successfully",
                storage_key=storage_key,
                local_path=local_path,
                size=file_size
            )
            
            return download_result
            
        except S3Error as e:
            logger.error(
                "File download failed",
                storage_key=storage_key,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected download error",
                storage_key=storage_key,
                error=str(e)
            )
            raise
    
    async def get_object_info(self, storage_key: str) -> Dict[str, Any]:
        """
        Get object information.
        
        Args:
            storage_key: Storage key/path
            
        Returns:
            Object information dictionary
        """
        try:
            loop = asyncio.get_event_loop()
            object_info = await loop.run_in_executor(
                None,
                self.client.stat_object,
                self.bucket_name,
                storage_key
            )
            
            return {
                "bucket": self.bucket_name,
                "key": storage_key,
                "size": object_info.size,
                "etag": object_info.etag,
                "last_modified": object_info.last_modified,
                "content_type": object_info.content_type,
                "metadata": object_info.metadata,
                "version_id": getattr(object_info, 'version_id', None)
            }
            
        except S3Error as e:
            logger.error(
                "Failed to get object info",
                storage_key=storage_key,
                error=str(e)
            )
            raise
    
    async def delete_object(self, storage_key: str) -> bool:
        """
        Delete object from storage.
        
        Args:
            storage_key: Storage key/path
            
        Returns:
            True if deleted successfully
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.remove_object,
                self.bucket_name,
                storage_key
            )
            
            logger.info("Object deleted successfully", storage_key=storage_key)
            return True
            
        except S3Error as e:
            logger.error(
                "Object deletion failed",
                storage_key=storage_key,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected deletion error",
                storage_key=storage_key,
                error=str(e)
            )
            raise
    
    async def generate_presigned_url(
        self,
        storage_key: str,
        expiry: int = None,
        method: str = "GET"
    ) -> str:
        """
        Generate presigned URL for object access.
        
        Args:
            storage_key: Storage key/path
            expiry: URL expiry in seconds (default from settings)
            method: HTTP method (GET, PUT, etc.)
            
        Returns:
            Presigned URL
        """
        try:
            if expiry is None:
                expiry = self.settings.signed_url_expiry
            
            expiry_timedelta = timedelta(seconds=expiry)
            
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                self.client.presigned_get_object,
                self.bucket_name,
                storage_key,
                expiry_timedelta
            )
            
            logger.info(
                "Presigned URL generated",
                storage_key=storage_key,
                expiry_seconds=expiry,
                method=method
            )
            
            return url
            
        except S3Error as e:
            logger.error(
                "Failed to generate presigned URL",
                storage_key=storage_key,
                error=str(e)
            )
            raise
    
    async def generate_viewer_url(self, storage_key: str) -> str:
        """
        Generate viewer URL with longer expiry for image viewing.
        
        Args:
            storage_key: Storage key/path
            
        Returns:
            Viewer URL
        """
        return await self.generate_presigned_url(
            storage_key,
            expiry=self.settings.viewer_url_expiry
        )
    
    async def list_objects(
        self,
        prefix: str = "",
        recursive: bool = False,
        max_keys: int = 1000
    ) -> list:
        """
        List objects in storage.
        
        Args:
            prefix: Object key prefix filter
            recursive: Whether to list recursively
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object information
        """
        try:
            loop = asyncio.get_event_loop()
            objects = await loop.run_in_executor(
                None,
                lambda: list(self.client.list_objects(
                    self.bucket_name,
                    prefix=prefix,
                    recursive=recursive
                ))
            )
            
            # Limit results
            objects = objects[:max_keys]
            
            # Convert to dict format
            object_list = []
            for obj in objects:
                object_list.append({
                    "key": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified,
                    "content_type": getattr(obj, 'content_type', None)
                })
            
            logger.info(
                "Objects listed",
                prefix=prefix,
                count=len(object_list),
                recursive=recursive
            )
            
            return object_list
            
        except S3Error as e:
            logger.error(
                "Failed to list objects",
                prefix=prefix,
                error=str(e)
            )
            raise
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Copy object within storage.
        
        Args:
            source_key: Source storage key
            dest_key: Destination storage key
            metadata: Additional metadata for destination
            
        Returns:
            Copy result dictionary
        """
        try:
            from minio.commonconfig import CopySource
            
            copy_source = CopySource(self.bucket_name, source_key)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.copy_object,
                self.bucket_name,
                dest_key,
                copy_source,
                metadata
            )
            
            copy_result = {
                "source_bucket": self.bucket_name,
                "source_key": source_key,
                "dest_bucket": self.bucket_name,
                "dest_key": dest_key,
                "etag": result.etag,
                "version_id": getattr(result, 'version_id', None)
            }
            
            logger.info(
                "Object copied successfully",
                source_key=source_key,
                dest_key=dest_key
            )
            
            return copy_result
            
        except S3Error as e:
            logger.error(
                "Object copy failed",
                source_key=source_key,
                dest_key=dest_key,
                error=str(e)
            )
            raise
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics dictionary
        """
        try:
            # List all objects to calculate stats
            objects = await self.list_objects(recursive=True, max_keys=10000)
            
            total_size = sum(obj['size'] for obj in objects)
            total_count = len(objects)
            
            # Group by format
            format_stats = {}
            for obj in objects:
                ext = Path(obj['key']).suffix.lower().lstrip('.')
                if ext:
                    format_stats[ext] = format_stats.get(ext, 0) + 1
            
            stats = {
                "bucket": self.bucket_name,
                "total_objects": total_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
                "format_distribution": format_stats,
                "average_size_bytes": round(total_size / total_count, 2) if total_count > 0 else 0
            }
            
            logger.info("Storage stats calculated", **stats)
            return stats
            
        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            raise


# Global storage instance
_storage_instance: Optional[ImageStorage] = None


async def get_storage(settings: Settings = None) -> ImageStorage:
    """Get storage manager instance."""
    global _storage_instance
    if _storage_instance is None:
        if settings is None:
            from .config import get_settings
            settings = get_settings()
        _storage_instance = ImageStorage(settings)
        await _storage_instance.ensure_bucket_exists()
    return _storage_instance


async def cleanup_storage() -> None:
    """Cleanup storage resources."""
    global _storage_instance
    if _storage_instance is not None:
        # MinIO client doesn't need explicit cleanup
        _storage_instance = None
    logger.info("Storage cleanup completed")
