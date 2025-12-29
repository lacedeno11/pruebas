"""S3/MinIO storage client."""

import hashlib
from datetime import timedelta
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class StorageClient:
    """S3-compatible storage client for MinIO."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> tuple[str, str]:
        """Upload a file and return (uri, checksum)."""
        # Calculate checksum
        file_obj.seek(0)
        checksum = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)

        # Upload
        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

        uri = f"s3://{self.bucket}/{key}"
        return uri, f"sha256:{checksum}"

    def download_file(self, key: str) -> bytes:
        """Download a file and return its contents."""
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "get_object",
    ) -> str:
        """Generate a presigned URL for the object."""
        return self.client.generate_presigned_url(
            ClientMethod=method,
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, key: str) -> bool:
        """Delete a file from storage."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def file_exists(self, key: str) -> bool:
        """Check if a file exists."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def get_file_size(self, key: str) -> int | None:
        """Get file size in bytes."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return response.get("ContentLength")
        except ClientError:
            return None

    @staticmethod
    def key_from_uri(uri: str) -> str:
        """Extract key from s3:// URI."""
        if uri.startswith("s3://"):
            parts = uri[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else ""
        return uri
