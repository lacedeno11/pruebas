"""Storage tool wrapper for LangGraph."""

import os
from typing import BinaryIO

from oncology_common.clients.storage import StorageClient


def get_storage_tool(
    endpoint: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    bucket: str | None = None,
) -> StorageClient:
    """Get configured storage client."""
    return StorageClient(
        endpoint=endpoint or os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        access_key=access_key or os.getenv("S3_ACCESS_KEY", "minioadmin"),
        secret_key=secret_key or os.getenv("S3_SECRET_KEY", "minioadmin"),
        bucket=bucket or os.getenv("S3_BUCKET", "oncology-xai"),
    )
