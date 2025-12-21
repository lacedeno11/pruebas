"""
Storage Service.

Handles object storage operations for documents and attachments.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, BinaryIO
from pathlib import Path

from policy_validation_copilot.models.case import Attachment

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Error in storage operations."""

    pass


class StorageService:
    """
    Object storage service for documents.

    Provides versioned, immutable storage with integrity verification.
    """

    def __init__(
        self,
        bucket: str = "policy-documents",
        base_path: Optional[str] = None,
    ):
        self.bucket = bucket
        self.base_path = Path(base_path) if base_path else Path("/tmp/policy-storage")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _compute_checksum(self, content: bytes) -> str:
        """Compute SHA-256 checksum."""
        return hashlib.sha256(content).hexdigest()

    def _get_storage_path(self, doc_id: str, version: str) -> Path:
        """Get storage path for a document."""
        return self.base_path / self.bucket / doc_id / version

    async def store_document(
        self,
        doc_id: str,
        version: str,
        content: bytes,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Store a document with versioning.

        Returns storage info including path and checksum.
        """
        checksum = self._compute_checksum(content)
        storage_path = self._get_storage_path(doc_id, version)
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            storage_path.write_bytes(content)

            # Store metadata
            meta_path = storage_path.with_suffix(".meta.json")
            import json
            meta = {
                "doc_id": doc_id,
                "version": version,
                "checksum": checksum,
                "content_type": content_type,
                "size_bytes": len(content),
                "stored_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
            meta_path.write_text(json.dumps(meta))

            logger.info(f"Stored document {doc_id} version {version}")

            return {
                "doc_id": doc_id,
                "version": version,
                "storage_path": str(storage_path),
                "checksum": checksum,
                "size_bytes": len(content),
            }

        except Exception as e:
            logger.error(f"Failed to store document {doc_id}: {e}")
            raise StorageError(f"Storage failed: {e}") from e

    async def retrieve_document(
        self,
        doc_id: str,
        version: str,
    ) -> tuple[bytes, dict]:
        """
        Retrieve a document by ID and version.

        Returns content and metadata, verifies integrity.
        """
        storage_path = self._get_storage_path(doc_id, version)
        meta_path = storage_path.with_suffix(".meta.json")

        if not storage_path.exists():
            raise StorageError(f"Document not found: {doc_id}/{version}")

        try:
            content = storage_path.read_bytes()

            import json
            metadata = {}
            if meta_path.exists():
                metadata = json.loads(meta_path.read_text())

            # Verify integrity
            checksum = self._compute_checksum(content)
            if metadata.get("checksum") and metadata["checksum"] != checksum:
                raise StorageError(
                    f"Integrity check failed for {doc_id}/{version}"
                )

            return content, metadata

        except StorageError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve document {doc_id}: {e}")
            raise StorageError(f"Retrieval failed: {e}") from e

    async def store_attachment(
        self,
        case_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Attachment:
        """
        Store a case attachment.

        Returns Attachment model with storage info.
        """
        from uuid import uuid4

        attachment_id = str(uuid4())
        checksum = self._compute_checksum(content)

        storage_path = self.base_path / "attachments" / case_id / attachment_id
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)

        return Attachment(
            attachment_id=attachment_id,
            filename=filename,
            content_type=content_type,
            storage_path=str(storage_path),
            checksum=checksum,
            size_bytes=len(content),
        )

    async def verify_integrity(self, doc_id: str, version: str) -> bool:
        """Verify document integrity by checksum."""
        try:
            content, metadata = await self.retrieve_document(doc_id, version)
            current_checksum = self._compute_checksum(content)
            return current_checksum == metadata.get("checksum")
        except StorageError:
            return False

    async def list_versions(self, doc_id: str) -> list[dict]:
        """List all versions of a document."""
        doc_path = self.base_path / self.bucket / doc_id
        if not doc_path.exists():
            return []

        versions = []
        import json
        for version_dir in doc_path.iterdir():
            if version_dir.is_dir():
                continue
            meta_path = version_dir.with_suffix(".meta.json")
            if meta_path.exists():
                versions.append(json.loads(meta_path.read_text()))

        return sorted(versions, key=lambda x: x.get("stored_at", ""), reverse=True)
