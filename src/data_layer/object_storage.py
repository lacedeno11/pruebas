"""
Object Storage layer for PDF/Excel versioned storage

This module provides versioned storage capabilities for documents and attachments
with support for multiple storage backends (local filesystem, S3, Azure Blob, etc.).

Features:
- Versioned document storage with checksums
- PDF and Excel file handling
- Metadata management and indexing
- Storage backend abstraction
- Integrity validation and corruption detection
- Automatic cleanup and retention policies
"""

import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from uuid import uuid4

import boto3
from azure.storage.blob import BlobServiceClient
from botocore.exceptions import ClientError, NoCredentialsError


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def store_file(self, file_path: str, content: bytes, metadata: Dict) -> str:
        """Store file and return storage path"""
        pass
    
    @abstractmethod
    def retrieve_file(self, storage_path: str) -> bytes:
        """Retrieve file content by storage path"""
        pass
    
    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Delete file by storage path"""
        pass
    
    @abstractmethod
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists at storage path"""
        pass
    
    @abstractmethod
    def get_file_metadata(self, storage_path: str) -> Dict:
        """Get file metadata"""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List files with optional prefix filter"""
        pass


class LocalFileSystemBackend(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, base_path: str = "data/storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def store_file(self, file_path: str, content: bytes, metadata: Dict) -> str:
        """Store file in local filesystem"""
        storage_path = self.base_path / file_path
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file content
        with open(storage_path, 'wb') as f:
            f.write(content)
        
        # Write metadata
        metadata_path = storage_path.with_suffix(storage_path.suffix + '.meta')
        with open(metadata_path, 'w') as f:
            import json
            json.dump(metadata, f, indent=2, default=str)
        
        return str(storage_path.relative_to(self.base_path))
    
    def retrieve_file(self, storage_path: str) -> bytes:
        """Retrieve file from local filesystem"""
        full_path = self.base_path / storage_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from local filesystem"""
        full_path = self.base_path / storage_path
        metadata_path = full_path.with_suffix(full_path.suffix + '.meta')
        
        try:
            if full_path.exists():
                full_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            return True
        except Exception:
            return False
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in local filesystem"""
        return (self.base_path / storage_path).exists()
    
    def get_file_metadata(self, storage_path: str) -> Dict:
        """Get file metadata from local filesystem"""
        full_path = self.base_path / storage_path
        metadata_path = full_path.with_suffix(full_path.suffix + '.meta')
        
        if not metadata_path.exists():
            return {}
        
        try:
            import json
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in local filesystem"""
        search_path = self.base_path / prefix if prefix else self.base_path
        files = []
        
        if search_path.is_dir():
            for file_path in search_path.rglob('*'):
                if file_path.is_file() and not file_path.suffix == '.meta':
                    relative_path = file_path.relative_to(self.base_path)
                    files.append(str(relative_path))
        
        return files


class S3Backend(StorageBackend):
    """Amazon S3 storage backend"""
    
    def __init__(self, bucket_name: str, aws_access_key_id: str = None, 
                 aws_secret_access_key: str = None, region_name: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.s3_client.create_bucket(Bucket=self.bucket_name)
    
    def store_file(self, file_path: str, content: bytes, metadata: Dict) -> str:
        """Store file in S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=content,
                Metadata={k: str(v) for k, v in metadata.items()}
            )
            return file_path
        except Exception as e:
            raise RuntimeError(f"Failed to store file in S3: {e}")
    
    def retrieve_file(self, storage_path: str) -> bytes:
        """Retrieve file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_path)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {storage_path}")
            raise RuntimeError(f"Failed to retrieve file from S3: {e}")
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except Exception:
            return False
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_path)
            return True
        except ClientError:
            return False
    
    def get_file_metadata(self, storage_path: str) -> Dict:
        """Get file metadata from S3"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_path)
            return response.get('Metadata', {})
        except ClientError:
            return {}
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in S3"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception:
            return []


class AzureBlobBackend(StorageBackend):
    """Azure Blob Storage backend"""
    
    def __init__(self, connection_string: str, container_name: str):
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure Azure container exists"""
        try:
            self.blob_service_client.get_container_client(self.container_name).get_container_properties()
        except Exception:
            self.blob_service_client.create_container(self.container_name)
    
    def store_file(self, file_path: str, content: bytes, metadata: Dict) -> str:
        """Store file in Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=file_path
            )
            blob_client.upload_blob(
                content, 
                overwrite=True,
                metadata={k: str(v) for k, v in metadata.items()}
            )
            return file_path
        except Exception as e:
            raise RuntimeError(f"Failed to store file in Azure Blob: {e}")
    
    def retrieve_file(self, storage_path: str) -> bytes:
        """Retrieve file from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=storage_path
            )
            return blob_client.download_blob().readall()
        except Exception as e:
            raise FileNotFoundError(f"File not found: {storage_path}")
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=storage_path
            )
            blob_client.delete_blob()
            return True
        except Exception:
            return False
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=storage_path
            )
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False
    
    def get_file_metadata(self, storage_path: str) -> Dict:
        """Get file metadata from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=storage_path
            )
            properties = blob_client.get_blob_properties()
            return properties.metadata or {}
        except Exception:
            return {}
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in Azure Blob Storage"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception:
            return []


class DocumentVersion:
    """Document version metadata"""
    
    def __init__(self, doc_id: str, version: str, filename: str, 
                 content_type: str, size: int, checksum: str,
                 storage_path: str, created_at: datetime = None):
        self.doc_id = doc_id
        self.version = version
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.checksum = checksum
        self.storage_path = storage_path
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'doc_id': self.doc_id,
            'version': self.version,
            'filename': self.filename,
            'content_type': self.content_type,
            'size': self.size,
            'checksum': self.checksum,
            'storage_path': self.storage_path,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentVersion':
        """Create from dictionary"""
        created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        return cls(
            doc_id=data['doc_id'],
            version=data['version'],
            filename=data['filename'],
            content_type=data['content_type'],
            size=data['size'],
            checksum=data['checksum'],
            storage_path=data['storage_path'],
            created_at=created_at
        )


class ObjectStorageManager:
    """Main object storage manager with versioning support"""
    
    def __init__(self, backend: StorageBackend, enable_versioning: bool = True):
        self.backend = backend
        self.enable_versioning = enable_versioning
        self._version_registry: Dict[str, List[DocumentVersion]] = {}
    
    def calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA-256 checksum of content"""
        return hashlib.sha256(content).hexdigest()
    
    def generate_storage_path(self, doc_id: str, version: str, filename: str) -> str:
        """Generate storage path for document"""
        # Create hierarchical path: doc_id/version/filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        return f"{doc_id}/{version}/{safe_filename}"
    
    def store_document(self, doc_id: str, content: bytes, filename: str,
                      content_type: str, version: str = None,
                      metadata: Dict = None) -> DocumentVersion:
        """Store document with versioning"""
        if version is None:
            version = self._generate_version(doc_id)
        
        checksum = self.calculate_checksum(content)
        storage_path = self.generate_storage_path(doc_id, version, filename)
        
        # Prepare metadata
        doc_metadata = {
            'doc_id': doc_id,
            'version': version,
            'filename': filename,
            'content_type': content_type,
            'size': len(content),
            'checksum': checksum,
            'created_at': datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        # Store file
        actual_storage_path = self.backend.store_file(storage_path, content, doc_metadata)
        
        # Create version record
        doc_version = DocumentVersion(
            doc_id=doc_id,
            version=version,
            filename=filename,
            content_type=content_type,
            size=len(content),
            checksum=checksum,
            storage_path=actual_storage_path
        )
        
        # Update version registry
        if self.enable_versioning:
            if doc_id not in self._version_registry:
                self._version_registry[doc_id] = []
            self._version_registry[doc_id].append(doc_version)
        
        return doc_version
    
    def retrieve_document(self, doc_id: str, version: str = None) -> Tuple[bytes, DocumentVersion]:
        """Retrieve document by ID and version"""
        if version is None:
            version = self.get_latest_version(doc_id)
        
        doc_version = self.get_document_version(doc_id, version)
        if not doc_version:
            raise FileNotFoundError(f"Document not found: {doc_id} v{version}")
        
        content = self.backend.retrieve_file(doc_version.storage_path)
        
        # Verify checksum
        actual_checksum = self.calculate_checksum(content)
        if actual_checksum != doc_version.checksum:
            raise RuntimeError(f"Checksum mismatch for {doc_id} v{version}")
        
        return content, doc_version
    
    def delete_document(self, doc_id: str, version: str = None) -> bool:
        """Delete document version"""
        if version is None:
            # Delete all versions
            versions = self.list_document_versions(doc_id)
            success = True
            for v in versions:
                success &= self.backend.delete_file(v.storage_path)
            
            # Remove from registry
            if doc_id in self._version_registry:
                del self._version_registry[doc_id]
            
            return success
        else:
            # Delete specific version
            doc_version = self.get_document_version(doc_id, version)
            if not doc_version:
                return False
            
            success = self.backend.delete_file(doc_version.storage_path)
            
            # Remove from registry
            if doc_id in self._version_registry:
                self._version_registry[doc_id] = [
                    v for v in self._version_registry[doc_id] if v.version != version
                ]
                if not self._version_registry[doc_id]:
                    del self._version_registry[doc_id]
            
            return success
    
    def document_exists(self, doc_id: str, version: str = None) -> bool:
        """Check if document exists"""
        if version is None:
            return doc_id in self._version_registry and len(self._version_registry[doc_id]) > 0
        
        doc_version = self.get_document_version(doc_id, version)
        return doc_version is not None and self.backend.file_exists(doc_version.storage_path)
    
    def list_document_versions(self, doc_id: str) -> List[DocumentVersion]:
        """List all versions of a document"""
        return self._version_registry.get(doc_id, [])
    
    def get_document_version(self, doc_id: str, version: str) -> Optional[DocumentVersion]:
        """Get specific document version"""
        versions = self._version_registry.get(doc_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    def get_latest_version(self, doc_id: str) -> str:
        """Get latest version of document"""
        versions = self._version_registry.get(doc_id, [])
        if not versions:
            raise FileNotFoundError(f"No versions found for document: {doc_id}")
        
        # Sort by created_at and return latest
        latest = max(versions, key=lambda v: v.created_at)
        return latest.version
    
    def _generate_version(self, doc_id: str) -> str:
        """Generate new version number"""
        existing_versions = self.list_document_versions(doc_id)
        if not existing_versions:
            return "1.0.0"
        
        # Simple version increment (major.minor.patch)
        latest_version = max(existing_versions, key=lambda v: v.created_at).version
        try:
            major, minor, patch = map(int, latest_version.split('.'))
            return f"{major}.{minor}.{patch + 1}"
        except ValueError:
            # Fallback to timestamp-based version
            return datetime.utcnow().strftime("%Y%m%d.%H%M%S")
    
    def cleanup_old_versions(self, doc_id: str, keep_versions: int = 5) -> int:
        """Cleanup old versions, keeping only the specified number"""
        versions = self.list_document_versions(doc_id)
        if len(versions) <= keep_versions:
            return 0
        
        # Sort by created_at and keep only the latest versions
        sorted_versions = sorted(versions, key=lambda v: v.created_at, reverse=True)
        versions_to_delete = sorted_versions[keep_versions:]
        
        deleted_count = 0
        for version in versions_to_delete:
            if self.backend.delete_file(version.storage_path):
                deleted_count += 1
                # Remove from registry
                self._version_registry[doc_id] = [
                    v for v in self._version_registry[doc_id] if v.version != version.version
                ]
        
        return deleted_count
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        total_documents = len(self._version_registry)
        total_versions = sum(len(versions) for versions in self._version_registry.values())
        total_size = sum(
            sum(v.size for v in versions)
            for versions in self._version_registry.values()
        )
        
        return {
            'total_documents': total_documents,
            'total_versions': total_versions,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }
    
    def validate_integrity(self, doc_id: str = None) -> Dict:
        """Validate integrity of stored documents"""
        results = {
            'valid': [],
            'invalid': [],
            'missing': []
        }
        
        documents_to_check = [doc_id] if doc_id else list(self._version_registry.keys())
        
        for doc_id in documents_to_check:
            versions = self.list_document_versions(doc_id)
            for version in versions:
                try:
                    if not self.backend.file_exists(version.storage_path):
                        results['missing'].append(f"{doc_id} v{version.version}")
                        continue
                    
                    content = self.backend.retrieve_file(version.storage_path)
                    actual_checksum = self.calculate_checksum(content)
                    
                    if actual_checksum == version.checksum:
                        results['valid'].append(f"{doc_id} v{version.version}")
                    else:
                        results['invalid'].append(f"{doc_id} v{version.version}")
                
                except Exception as e:
                    results['invalid'].append(f"{doc_id} v{version.version}: {str(e)}")
        
        return results


# Factory function for creating storage managers
def create_storage_manager(backend_type: str = "local", **kwargs) -> ObjectStorageManager:
    """Factory function to create storage manager with specified backend"""
    
    if backend_type == "local":
        base_path = kwargs.get("base_path", "data/storage")
        backend = LocalFileSystemBackend(base_path)
    
    elif backend_type == "s3":
        bucket_name = kwargs.get("bucket_name")
        if not bucket_name:
            raise ValueError("bucket_name is required for S3 backend")
        
        backend = S3Backend(
            bucket_name=bucket_name,
            aws_access_key_id=kwargs.get("aws_access_key_id"),
            aws_secret_access_key=kwargs.get("aws_secret_access_key"),
            region_name=kwargs.get("region_name", "us-east-1")
        )
    
    elif backend_type == "azure":
        connection_string = kwargs.get("connection_string")
        container_name = kwargs.get("container_name")
        if not connection_string or not container_name:
            raise ValueError("connection_string and container_name are required for Azure backend")
        
        backend = AzureBlobBackend(connection_string, container_name)
    
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")
    
    enable_versioning = kwargs.get("enable_versioning", True)
    return ObjectStorageManager(backend, enable_versioning)


# Utility functions for common file operations
def store_pdf_document(storage_manager: ObjectStorageManager, doc_id: str, 
                      pdf_content: bytes, filename: str, metadata: Dict = None) -> DocumentVersion:
    """Store PDF document with proper content type"""
    return storage_manager.store_document(
        doc_id=doc_id,
        content=pdf_content,
        filename=filename,
        content_type="application/pdf",
        metadata=metadata
    )


def store_excel_document(storage_manager: ObjectStorageManager, doc_id: str,
                        excel_content: bytes, filename: str, metadata: Dict = None) -> DocumentVersion:
    """Store Excel document with proper content type"""
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if filename.lower().endswith('.xls'):
        content_type = "application/vnd.ms-excel"
    
    return storage_manager.store_document(
        doc_id=doc_id,
        content=excel_content,
        filename=filename,
        content_type=content_type,
        metadata=metadata
    )


def batch_upload_documents(storage_manager: ObjectStorageManager, 
                          documents: List[Dict]) -> List[DocumentVersion]:
    """Batch upload multiple documents"""
    results = []
    
    for doc_info in documents:
        try:
            doc_version = storage_manager.store_document(
                doc_id=doc_info['doc_id'],
                content=doc_info['content'],
                filename=doc_info['filename'],
                content_type=doc_info['content_type'],
                version=doc_info.get('version'),
                metadata=doc_info.get('metadata')
            )
            results.append(doc_version)
        except Exception as e:
            # Log error but continue with other documents
            print(f"Failed to upload {doc_info.get('filename', 'unknown')}: {e}")
    
    return results
