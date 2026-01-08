"""
Object Storage Interface

This module implements object storage interfaces for document and attachment management,
supporting multiple storage backends (S3, local filesystem, etc.).
"""

from typing import Dict, Any, List, Optional, BinaryIO, Union
from datetime import datetime, timedelta
import logging
import asyncio
import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class StorageBackend(str, Enum):
    """Storage backend types"""
    S3 = "s3"
    LOCAL = "local"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"


@dataclass
class StorageConfig:
    """Storage configuration"""
    backend: StorageBackend
    bucket_name: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    local_path: Optional[str] = None
    encryption_enabled: bool = True
    versioning_enabled: bool = True
    retention_days: int = 2555  # 7 years


@dataclass
class StorageObject:
    """Storage object metadata"""
    key: str
    size: int
    content_type: str
    checksum: str
    created_at: datetime
    modified_at: datetime
    version_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class UploadResult:
    """Upload operation result"""
    success: bool
    key: str
    size: int
    checksum: str
    version_id: Optional[str] = None
    error_message: Optional[str] = None
    upload_time_ms: int = 0


class ObjectStorageInterface(ABC):
    """Abstract interface for object storage operations"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.stats = {
            "uploads": 0,
            "downloads": 0,
            "deletes": 0,
            "errors": 0,
            "total_bytes_uploaded": 0,
            "total_bytes_downloaded": 0
        }
    
    @abstractmethod
    async def upload_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """Upload object to storage"""
        pass
    
    @abstractmethod
    async def download_object(self, key: str) -> Optional[bytes]:
        """Download object from storage"""
        pass
    
    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Delete object from storage"""
        pass
    
    @abstractmethod
    async def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata"""
        pass
    
    @abstractmethod
    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000
    ) -> List[StorageObject]:
        """List objects with optional prefix filter"""
        pass
    
    @abstractmethod
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Generate presigned URL for object access"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage operation statistics"""
        return self.stats.copy()
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum"""
        return hashlib.sha256(data).hexdigest()
    
    def _update_upload_stats(self, size: int, success: bool) -> None:
        """Update upload statistics"""
        if success:
            self.stats["uploads"] += 1
            self.stats["total_bytes_uploaded"] += size
        else:
            self.stats["errors"] += 1
    
    def _update_download_stats(self, size: int, success: bool) -> None:
        """Update download statistics"""
        if success:
            self.stats["downloads"] += 1
            self.stats["total_bytes_downloaded"] += size
        else:
            self.stats["errors"] += 1


class S3StorageAdapter(ObjectStorageInterface):
    """
    AWS S3 storage adapter implementation.
    
    Provides S3-compatible object storage with versioning,
    encryption, and lifecycle management.
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        
        if config.backend != StorageBackend.S3:
            raise ValueError("S3StorageAdapter requires S3 backend configuration")
        
        # Initialize S3 client
        self.s3_client = self._create_s3_client()
        self.bucket_name = config.bucket_name
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name is required")
    
    def _create_s3_client(self):
        """Create S3 client with configuration"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                region_name=self.config.region
            )
            
            client_config = {}
            if self.config.endpoint_url:
                client_config["endpoint_url"] = self.config.endpoint_url
            
            return session.client("s3", **client_config)
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to create S3 client: {e}")
            raise
    
    async def upload_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """Upload object to S3"""
        start_time = datetime.utcnow()
        
        try:
            # Convert data to bytes if needed
            if hasattr(data, 'read'):
                data_bytes = data.read()
            else:
                data_bytes = data
            
            # Calculate checksum
            checksum = self._calculate_checksum(data_bytes)
            
            # Prepare upload parameters
            upload_params = {
                "Bucket": self.bucket_name,
                "Key": key,
                "Body": data_bytes,
                "ContentType": content_type,
                "Metadata": metadata or {},
                "ChecksumSHA256": checksum
            }
            
            # Add server-side encryption if enabled
            if self.config.encryption_enabled:
                upload_params["ServerSideEncryption"] = "AES256"
            
            # Add tags if provided
            if tags:
                tag_string = "&".join([f"{k}={v}" for k, v in tags.items()])
                upload_params["Tagging"] = tag_string
            
            # Upload object
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.s3_client.put_object(**upload_params)
            )
            
            # Calculate upload time
            upload_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_upload_stats(len(data_bytes), True)
            
            logger.info(f"Successfully uploaded object to S3: {key}")
            
            return UploadResult(
                success=True,
                key=key,
                size=len(data_bytes),
                checksum=checksum,
                version_id=response.get("VersionId"),
                upload_time_ms=int(upload_time)
            )
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = f"S3 upload failed: {error_code} - {e.response['Error']['Message']}"
            
            logger.error(error_message)
            self._update_upload_stats(0, False)
            
            return UploadResult(
                success=False,
                key=key,
                size=0,
                checksum="",
                error_message=error_message,
                upload_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            error_message = f"Unexpected error during S3 upload: {str(e)}"
            logger.error(error_message)
            self._update_upload_stats(0, False)
            
            return UploadResult(
                success=False,
                key=key,
                size=0,
                checksum="",
                error_message=error_message,
                upload_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
    
    async def download_object(self, key: str) -> Optional[bytes]:
        """Download object from S3"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            )
            
            data = response["Body"].read()
            self._update_download_stats(len(data), True)
            
            logger.info(f"Successfully downloaded object from S3: {key}")
            return data
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Object not found in S3: {key}")
            else:
                logger.error(f"S3 download failed: {e}")
            
            self._update_download_stats(0, False)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 download: {e}")
            self._update_download_stats(0, False)
            return None
    
    async def delete_object(self, key: str) -> bool:
        """Delete object from S3"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            )
            
            self.stats["deletes"] += 1
            logger.info(f"Successfully deleted object from S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 delete: {e}")
            self.stats["errors"] += 1
            return False
    
    async def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata from S3"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            )
            
            return StorageObject(
                key=key,
                size=response["ContentLength"],
                content_type=response.get("ContentType", "application/octet-stream"),
                checksum=response.get("ChecksumSHA256", ""),
                created_at=response["LastModified"],
                modified_at=response["LastModified"],
                version_id=response.get("VersionId"),
                metadata=response.get("Metadata", {}),
                tags={}  # Would need separate call to get tags
            )
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Object not found in S3: {key}")
            else:
                logger.error(f"S3 head object failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting S3 object metadata: {e}")
            return None
    
    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000
    ) -> List[StorageObject]:
        """List objects in S3 bucket"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=limit
                )
            )
            
            objects = []
            for obj in response.get("Contents", []):
                storage_obj = StorageObject(
                    key=obj["Key"],
                    size=obj["Size"],
                    content_type="application/octet-stream",  # Default, would need head_object for actual type
                    checksum=obj.get("ETag", "").strip('"'),
                    created_at=obj["LastModified"],
                    modified_at=obj["LastModified"],
                    metadata={}
                )
                objects.append(storage_obj)
            
            return objects
            
        except ClientError as e:
            logger.error(f"S3 list objects failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing S3 objects: {e}")
            return []
    
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Generate presigned URL for S3 object"""
        try:
            if method.upper() == "GET":
                url = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": self.bucket_name, "Key": key},
                        ExpiresIn=expiration
                    )
                )
            elif method.upper() == "PUT":
                url = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.s3_client.generate_presigned_url(
                        "put_object",
                        Params={"Bucket": self.bucket_name, "Key": key},
                        ExpiresIn=expiration
                    )
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None


class LocalStorageAdapter(ObjectStorageInterface):
    """
    Local filesystem storage adapter implementation.
    
    Provides local file storage for development and testing.
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        
        if config.backend != StorageBackend.LOCAL:
            raise ValueError("LocalStorageAdapter requires LOCAL backend configuration")
        
        self.base_path = config.local_path or "./storage"
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_full_path(self, key: str) -> str:
        """Get full filesystem path for key"""
        # Ensure key doesn't escape base path
        safe_key = key.replace("..", "").lstrip("/")
        return os.path.join(self.base_path, safe_key)
    
    async def upload_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """Upload object to local storage"""
        start_time = datetime.utcnow()
        
        try:
            # Convert data to bytes if needed
            if hasattr(data, 'read'):
                data_bytes = data.read()
            else:
                data_bytes = data
            
            # Calculate checksum
            checksum = self._calculate_checksum(data_bytes)
            
            # Get full path and create directories
            full_path = self._get_full_path(key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'wb') as f:
                f.write(data_bytes)
            
            # Write metadata file if provided
            if metadata or tags:
                metadata_path = full_path + ".metadata"
                metadata_info = {
                    "content_type": content_type,
                    "checksum": checksum,
                    "metadata": metadata or {},
                    "tags": tags or {},
                    "created_at": datetime.utcnow().isoformat()
                }
                
                import json
                with open(metadata_path, 'w') as f:
                    json.dump(metadata_info, f, indent=2)
            
            # Calculate upload time
            upload_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_upload_stats(len(data_bytes), True)
            
            logger.info(f"Successfully uploaded object to local storage: {key}")
            
            return UploadResult(
                success=True,
                key=key,
                size=len(data_bytes),
                checksum=checksum,
                upload_time_ms=int(upload_time)
            )
            
        except Exception as e:
            error_message = f"Local storage upload failed: {str(e)}"
            logger.error(error_message)
            self._update_upload_stats(0, False)
            
            return UploadResult(
                success=False,
                key=key,
                size=0,
                checksum="",
                error_message=error_message,
                upload_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
    
    async def download_object(self, key: str) -> Optional[bytes]:
        """Download object from local storage"""
        try:
            full_path = self._get_full_path(key)
            
            if not os.path.exists(full_path):
                logger.warning(f"Object not found in local storage: {key}")
                self._update_download_stats(0, False)
                return None
            
            with open(full_path, 'rb') as f:
                data = f.read()
            
            self._update_download_stats(len(data), True)
            logger.info(f"Successfully downloaded object from local storage: {key}")
            return data
            
        except Exception as e:
            logger.error(f"Local storage download failed: {e}")
            self._update_download_stats(0, False)
            return None
    
    async def delete_object(self, key: str) -> bool:
        """Delete object from local storage"""
        try:
            full_path = self._get_full_path(key)
            metadata_path = full_path + ".metadata"
            
            # Delete main file
            if os.path.exists(full_path):
                os.remove(full_path)
            
            # Delete metadata file
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            self.stats["deletes"] += 1
            logger.info(f"Successfully deleted object from local storage: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Local storage delete failed: {e}")
            self.stats["errors"] += 1
            return False
    
    async def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata from local storage"""
        try:
            full_path = self._get_full_path(key)
            metadata_path = full_path + ".metadata"
            
            if not os.path.exists(full_path):
                return None
            
            # Get file stats
            stat = os.stat(full_path)
            
            # Load metadata if available
            metadata = {}
            content_type = "application/octet-stream"
            checksum = ""
            
            if os.path.exists(metadata_path):
                import json
                with open(metadata_path, 'r') as f:
                    metadata_info = json.load(f)
                    content_type = metadata_info.get("content_type", content_type)
                    checksum = metadata_info.get("checksum", "")
                    metadata = metadata_info.get("metadata", {})
            
            return StorageObject(
                key=key,
                size=stat.st_size,
                content_type=content_type,
                checksum=checksum,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to get local storage object metadata: {e}")
            return None
    
    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000
    ) -> List[StorageObject]:
        """List objects in local storage"""
        try:
            objects = []
            prefix_path = self._get_full_path(prefix)
            
            # Walk directory tree
            for root, dirs, files in os.walk(self.base_path):
                for file in files:
                    if file.endswith(".metadata"):
                        continue
                    
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.base_path)
                    
                    # Check prefix filter
                    if prefix and not relative_path.startswith(prefix):
                        continue
                    
                    # Get metadata
                    obj_metadata = await self.get_object_metadata(relative_path)
                    if obj_metadata:
                        objects.append(obj_metadata)
                    
                    # Check limit
                    if len(objects) >= limit:
                        break
                
                if len(objects) >= limit:
                    break
            
            return objects
            
        except Exception as e:
            logger.error(f"Failed to list local storage objects: {e}")
            return []
    
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Generate presigned URL (not supported for local storage)"""
        logger.warning("Presigned URLs not supported for local storage")
        return None


# Factory function

def create_object_storage(config: StorageConfig) -> ObjectStorageInterface:
    """
    Factory function to create object storage adapter.
    
    Args:
        config: Storage configuration
        
    Returns:
        Object storage adapter instance
    """
    if config.backend == StorageBackend.S3:
        return S3StorageAdapter(config)
    elif config.backend == StorageBackend.LOCAL:
        return LocalStorageAdapter(config)
    else:
        raise ValueError(f"Unsupported storage backend: {config.backend}")


# Helper functions

def create_s3_storage(
    bucket_name: str,
    region: str = "us-east-1",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    endpoint_url: Optional[str] = None
) -> S3StorageAdapter:
    """Create S3 storage adapter with configuration"""
    config = StorageConfig(
        backend=StorageBackend.S3,
        bucket_name=bucket_name,
        region=region,
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url
    )
    return S3StorageAdapter(config)


def create_local_storage(local_path: str = "./storage") -> LocalStorageAdapter:
    """Create local storage adapter with configuration"""
    config = StorageConfig(
        backend=StorageBackend.LOCAL,
        local_path=local_path
    )
    return LocalStorageAdapter(config)
