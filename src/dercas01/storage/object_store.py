"""
Object Storage Interface for DERCAS 01 Policy Validation Copilot

Provides file storage interface for PDF/Excel documents with versioning, checksums,
and integrity verification. Supports local filesystem and cloud storage backends.
"""

import hashlib
import json
import logging
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from ..models.enums import DocumentType, StorageType

logger = logging.getLogger(__name__)


class StorageConfig:
    """Configuration for object storage."""
    
    def __init__(
        self,
        storage_type: StorageType = StorageType.LOCAL,
        base_path: str = "./data/documents",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        allowed_extensions: List[str] = None,
        enable_versioning: bool = True,
        enable_compression: bool = False,
        checksum_algorithm: str = "sha256",
    ):
        self.storage_type = storage_type
        self.base_path = base_path
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or [".pdf", ".xlsx", ".xls", ".docx", ".doc"]
        self.enable_versioning = enable_versioning
        self.enable_compression = enable_compression
        self.checksum_algorithm = checksum_algorithm


class StoredDocument:
    """Represents a stored document with metadata."""
    
    def __init__(
        self,
        file_id: str,
        version: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        checksum: str,
        content_type: str,
        document_type: DocumentType,
        metadata: Dict[str, Any],
        created_at: datetime,
        created_by: Optional[str] = None,
    ):
        self.file_id = file_id
        self.version = version
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.checksum = checksum
        self.content_type = content_type
        self.document_type = document_type
        self.metadata = metadata
        self.created_at = created_at
        self.created_by = created_by
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_id": self.file_id,
            "version": self.version,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "content_type": self.content_type,
            "document_type": self.document_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredDocument":
        """Create from dictionary representation."""
        return cls(
            file_id=data["file_id"],
            version=data["version"],
            original_filename=data["original_filename"],
            file_path=data["file_path"],
            file_size=data["file_size"],
            checksum=data["checksum"],
            content_type=data["content_type"],
            document_type=DocumentType(data["document_type"]),
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by"),
        )


class ObjectStorageInterface(ABC):
    """Abstract interface for object storage backends."""
    
    @abstractmethod
    def store_file(
        self,
        file_content: bytes,
        filename: str,
        document_type: DocumentType,
        metadata: Dict[str, Any],
        file_id: Optional[str] = None,
        version: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> StoredDocument:
        """Store a file and return document metadata."""
        pass
    
    @abstractmethod
    def retrieve_file(self, file_id: str, version: Optional[str] = None) -> Tuple[bytes, StoredDocument]:
        """Retrieve file content and metadata."""
        pass
    
    @abstractmethod
    def delete_file(self, file_id: str, version: Optional[str] = None) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    def list_files(
        self,
        document_type: Optional[DocumentType] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[StoredDocument]:
        """List stored files with optional filtering."""
        pass
    
    @abstractmethod
    def get_file_info(self, file_id: str, version: Optional[str] = None) -> Optional[StoredDocument]:
        """Get file metadata without content."""
        pass
    
    @abstractmethod
    def verify_integrity(self, file_id: str, version: Optional[str] = None) -> bool:
        """Verify file integrity using checksum."""
        pass


class LocalFileStorage(ObjectStorageInterface):
    """Local filesystem storage implementation."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = Path(config.base_path)
        self.metadata_path = self.base_path / "metadata"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different document types
        for doc_type in DocumentType:
            (self.base_path / doc_type.value.lower()).mkdir(exist_ok=True)
    
    def _calculate_checksum(self, content: bytes) -> str:
        """Calculate checksum for file content."""
        if self.config.checksum_algorithm == "sha256":
            return hashlib.sha256(content).hexdigest()
        elif self.config.checksum_algorithm == "md5":
            return hashlib.md5(content).hexdigest()
        else:
            raise ValueError(f"Unsupported checksum algorithm: {self.config.checksum_algorithm}")
    
    def _get_file_path(self, file_id: str, version: str, document_type: DocumentType, extension: str) -> Path:
        """Get the storage path for a file."""
        doc_type_dir = self.base_path / document_type.value.lower()
        if self.config.enable_versioning:
            return doc_type_dir / f"{file_id}_v{version}{extension}"
        else:
            return doc_type_dir / f"{file_id}{extension}"
    
    def _get_metadata_path(self, file_id: str, version: str) -> Path:
        """Get the metadata file path."""
        if self.config.enable_versioning:
            return self.metadata_path / f"{file_id}_v{version}.json"
        else:
            return self.metadata_path / f"{file_id}.json"
    
    def _validate_file(self, content: bytes, filename: str) -> None:
        """Validate file before storage."""
        # Check file size
        if len(content) > self.config.max_file_size:
            raise ValueError(f"File size {len(content)} exceeds maximum {self.config.max_file_size}")
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.config.allowed_extensions:
            raise ValueError(f"File extension {file_ext} not allowed. Allowed: {self.config.allowed_extensions}")
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename."""
        ext = Path(filename).suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
        }
        return content_types.get(ext, "application/octet-stream")
    
    def store_file(
        self,
        file_content: bytes,
        filename: str,
        document_type: DocumentType,
        metadata: Dict[str, Any],
        file_id: Optional[str] = None,
        version: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> StoredDocument:
        """Store a file in local filesystem."""
        try:
            # Validate file
            self._validate_file(file_content, filename)
            
            # Generate IDs if not provided
            if file_id is None:
                file_id = str(uuid4())
            if version is None:
                version = "1"
            
            # Calculate checksum
            checksum = self._calculate_checksum(file_content)
            
            # Determine file extension and content type
            file_ext = Path(filename).suffix
            content_type = self._get_content_type(filename)
            
            # Get storage paths
            file_path = self._get_file_path(file_id, version, document_type, file_ext)
            metadata_path = self._get_metadata_path(file_id, version)
            
            # Check if file already exists
            if file_path.exists() and not self.config.enable_versioning:
                raise ValueError(f"File {file_id} already exists and versioning is disabled")
            
            # Store file content
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Create document metadata
            stored_doc = StoredDocument(
                file_id=file_id,
                version=version,
                original_filename=filename,
                file_path=str(file_path),
                file_size=len(file_content),
                checksum=checksum,
                content_type=content_type,
                document_type=document_type,
                metadata=metadata,
                created_at=datetime.utcnow(),
                created_by=created_by,
            )
            
            # Store metadata
            with open(metadata_path, "w") as f:
                json.dump(stored_doc.to_dict(), f, indent=2)
            
            logger.info(f"Stored file {file_id} version {version} at {file_path}")
            return stored_doc
            
        except Exception as e:
            logger.error(f"Failed to store file {filename}: {e}")
            raise
    
    def retrieve_file(self, file_id: str, version: Optional[str] = None) -> Tuple[bytes, StoredDocument]:
        """Retrieve file content and metadata."""
        try:
            # Get latest version if not specified
            if version is None:
                version = self._get_latest_version(file_id)
                if version is None:
                    raise FileNotFoundError(f"File {file_id} not found")
            
            # Get metadata
            metadata_path = self._get_metadata_path(file_id, version)
            if not metadata_path.exists():
                raise FileNotFoundError(f"Metadata for file {file_id} version {version} not found")
            
            with open(metadata_path, "r") as f:
                metadata_dict = json.load(f)
            
            stored_doc = StoredDocument.from_dict(metadata_dict)
            
            # Read file content
            file_path = Path(stored_doc.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File content for {file_id} version {version} not found")
            
            with open(file_path, "rb") as f:
                content = f.read()
            
            # Verify integrity
            if not self._verify_content_integrity(content, stored_doc.checksum):
                raise ValueError(f"File integrity check failed for {file_id} version {version}")
            
            logger.info(f"Retrieved file {file_id} version {version}")
            return content, stored_doc
            
        except Exception as e:
            logger.error(f"Failed to retrieve file {file_id}: {e}")
            raise
    
    def delete_file(self, file_id: str, version: Optional[str] = None) -> bool:
        """Delete a file and its metadata."""
        try:
            if version is None:
                # Delete all versions
                versions = self._get_all_versions(file_id)
                success = True
                for v in versions:
                    success &= self.delete_file(file_id, v)
                return success
            else:
                # Delete specific version
                metadata_path = self._get_metadata_path(file_id, version)
                if not metadata_path.exists():
                    return False
                
                # Get file path from metadata
                with open(metadata_path, "r") as f:
                    metadata_dict = json.load(f)
                
                file_path = Path(metadata_dict["file_path"])
                
                # Delete file and metadata
                if file_path.exists():
                    file_path.unlink()
                metadata_path.unlink()
                
                logger.info(f"Deleted file {file_id} version {version}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    def list_files(
        self,
        document_type: Optional[DocumentType] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[StoredDocument]:
        """List stored files with optional filtering."""
        try:
            files = []
            
            # Scan metadata directory
            for metadata_file in self.metadata_path.glob("*.json"):
                try:
                    with open(metadata_file, "r") as f:
                        metadata_dict = json.load(f)
                    
                    stored_doc = StoredDocument.from_dict(metadata_dict)
                    
                    # Apply filters
                    if document_type and stored_doc.document_type != document_type:
                        continue
                    
                    if metadata_filter:
                        match = True
                        for key, value in metadata_filter.items():
                            if key not in stored_doc.metadata or stored_doc.metadata[key] != value:
                                match = False
                                break
                        if not match:
                            continue
                    
                    files.append(stored_doc)
                    
                    if limit and len(files) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to read metadata file {metadata_file}: {e}")
                    continue
            
            # Sort by creation date (newest first)
            files.sort(key=lambda x: x.created_at, reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def get_file_info(self, file_id: str, version: Optional[str] = None) -> Optional[StoredDocument]:
        """Get file metadata without content."""
        try:
            if version is None:
                version = self._get_latest_version(file_id)
                if version is None:
                    return None
            
            metadata_path = self._get_metadata_path(file_id, version)
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, "r") as f:
                metadata_dict = json.load(f)
            
            return StoredDocument.from_dict(metadata_dict)
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_id}: {e}")
            return None
    
    def verify_integrity(self, file_id: str, version: Optional[str] = None) -> bool:
        """Verify file integrity using checksum."""
        try:
            content, stored_doc = self.retrieve_file(file_id, version)
            return self._verify_content_integrity(content, stored_doc.checksum)
            
        except Exception as e:
            logger.error(f"Failed to verify integrity for {file_id}: {e}")
            return False
    
    def _verify_content_integrity(self, content: bytes, expected_checksum: str) -> bool:
        """Verify content integrity against expected checksum."""
        actual_checksum = self._calculate_checksum(content)
        return actual_checksum == expected_checksum
    
    def _get_latest_version(self, file_id: str) -> Optional[str]:
        """Get the latest version number for a file."""
        versions = self._get_all_versions(file_id)
        if not versions:
            return None
        
        # Sort versions numerically
        try:
            versions.sort(key=lambda x: int(x))
            return versions[-1]
        except ValueError:
            # Fallback to string sorting
            versions.sort()
            return versions[-1]
    
    def _get_all_versions(self, file_id: str) -> List[str]:
        """Get all version numbers for a file."""
        versions = []
        pattern = f"{file_id}_v*.json"
        
        for metadata_file in self.metadata_path.glob(pattern):
            # Extract version from filename
            filename = metadata_file.stem
            if "_v" in filename:
                version = filename.split("_v")[-1]
                versions.append(version)
        
        return versions
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            stats = {
                "total_files": 0,
                "total_size": 0,
                "document_types": {},
                "storage_path": str(self.base_path),
                "last_updated": datetime.utcnow().isoformat(),
            }
            
            files = self.list_files()
            stats["total_files"] = len(files)
            
            for file_doc in files:
                stats["total_size"] += file_doc.file_size
                
                doc_type = file_doc.document_type.value
                if doc_type not in stats["document_types"]:
                    stats["document_types"][doc_type] = {"count": 0, "size": 0}
                
                stats["document_types"][doc_type]["count"] += 1
                stats["document_types"][doc_type]["size"] += file_doc.file_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}


class ObjectStore:
    """Main object store interface that delegates to storage backends."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        
        # Initialize storage backend based on configuration
        if config.storage_type == StorageType.LOCAL:
            self.backend = LocalFileStorage(config)
        else:
            raise ValueError(f"Unsupported storage type: {config.storage_type}")
    
    def store_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: DocumentType,
        metadata: Optional[Dict[str, Any]] = None,
        file_id: Optional[str] = None,
        version: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> StoredDocument:
        """Store a document with metadata."""
        if metadata is None:
            metadata = {}
        
        return self.backend.store_file(
            file_content=file_content,
            filename=filename,
            document_type=document_type,
            metadata=metadata,
            file_id=file_id,
            version=version,
            created_by=created_by,
        )
    
    def retrieve_document(self, file_id: str, version: Optional[str] = None) -> Tuple[bytes, StoredDocument]:
        """Retrieve document content and metadata."""
        return self.backend.retrieve_file(file_id, version)
    
    def delete_document(self, file_id: str, version: Optional[str] = None) -> bool:
        """Delete a document."""
        return self.backend.delete_file(file_id, version)
    
    def list_documents(
        self,
        document_type: Optional[DocumentType] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[StoredDocument]:
        """List documents with optional filtering."""
        return self.backend.list_files(document_type, metadata_filter, limit)
    
    def get_document_info(self, file_id: str, version: Optional[str] = None) -> Optional[StoredDocument]:
        """Get document metadata."""
        return self.backend.get_file_info(file_id, version)
    
    def verify_document_integrity(self, file_id: str, version: Optional[str] = None) -> bool:
        """Verify document integrity."""
        return self.backend.verify_integrity(file_id, version)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if hasattr(self.backend, "get_storage_stats"):
            return self.backend.get_storage_stats()
        return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage."""
        try:
            # Test basic operations
            test_content = b"health check test"
            test_filename = "health_check.txt"
            test_metadata = {"test": True}
            
            # Store test file
            stored_doc = self.store_document(
                file_content=test_content,
                filename=test_filename,
                document_type=DocumentType.POLICY,
                metadata=test_metadata,
                file_id="health_check_test",
            )
            
            # Retrieve test file
            retrieved_content, retrieved_doc = self.retrieve_document(stored_doc.file_id)
            
            # Verify integrity
            integrity_ok = self.verify_document_integrity(stored_doc.file_id)
            
            # Clean up test file
            self.delete_document(stored_doc.file_id)
            
            # Check results
            content_match = retrieved_content == test_content
            metadata_match = retrieved_doc.metadata.get("test") == True
            
            return {
                "healthy": content_match and metadata_match and integrity_ok,
                "storage_type": self.config.storage_type.value,
                "base_path": self.config.base_path,
                "tests": {
                    "store_retrieve": content_match,
                    "metadata_preservation": metadata_match,
                    "integrity_check": integrity_ok,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "storage_type": self.config.storage_type.value,
                "timestamp": datetime.utcnow().isoformat(),
            }


# Utility functions

def create_object_store(config: Optional[StorageConfig] = None) -> ObjectStore:
    """Create an ObjectStore instance with default or custom configuration."""
    if config is None:
        config = StorageConfig()
    
    return ObjectStore(config)


def calculate_file_checksum(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """Calculate checksum for a file."""
    file_path = Path(file_path)
    
    if algorithm == "sha256":
        hash_obj = hashlib.sha256()
    elif algorithm == "md5":
        hash_obj = hashlib.md5()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def validate_document_format(file_content: bytes, filename: str) -> Dict[str, Any]:
    """Validate document format and extract basic information."""
    file_ext = Path(filename).suffix.lower()
    
    validation_result = {
        "valid": False,
        "format": file_ext,
        "size": len(file_content),
        "errors": [],
        "warnings": [],
    }
    
    try:
        # Basic format validation
        if file_ext == ".pdf":
            # Check PDF magic bytes
            if file_content.startswith(b"%PDF-"):
                validation_result["valid"] = True
            else:
                validation_result["errors"].append("Invalid PDF format")
        
        elif file_ext in [".xlsx", ".xls"]:
            # Check Excel magic bytes
            if file_ext == ".xlsx" and file_content.startswith(b"PK"):
                validation_result["valid"] = True
            elif file_ext == ".xls" and file_content.startswith(b"\xd0\xcf\x11\xe0"):
                validation_result["valid"] = True
            else:
                validation_result["errors"].append("Invalid Excel format")
        
        elif file_ext in [".docx", ".doc"]:
            # Check Word magic bytes
            if file_ext == ".docx" and file_content.startswith(b"PK"):
                validation_result["valid"] = True
            elif file_ext == ".doc" and file_content.startswith(b"\xd0\xcf\x11\xe0"):
                validation_result["valid"] = True
            else:
                validation_result["errors"].append("Invalid Word format")
        
        else:
            validation_result["errors"].append(f"Unsupported file format: {file_ext}")
        
        # Size warnings
        if len(file_content) > 50 * 1024 * 1024:  # 50MB
            validation_result["warnings"].append("Large file size may impact processing performance")
        
        if len(file_content) == 0:
            validation_result["errors"].append("Empty file")
            validation_result["valid"] = False
        
    except Exception as e:
        validation_result["errors"].append(f"Validation error: {str(e)}")
        validation_result["valid"] = False
    
    return validation_result
