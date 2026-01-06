"""
DERCAS-ONCO-XAI V1 - Image Service Configuration

Configuration management for the Image Service.
"""

import os
from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Image Service configuration settings."""
    
    # Service configuration
    service_name: str = Field(default="image-service", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8002, description="Server port")
    
    # Database configuration
    database_url: str = Field(
        default="postgresql+asyncpg://oncology_user:oncology_pass@localhost:5432/oncology_db",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=30, description="Database max overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # S3/MinIO configuration
    s3_endpoint: str = Field(default="http://localhost:9000", description="S3 endpoint URL")
    s3_access_key: str = Field(default="minioadmin", description="S3 access key")
    s3_secret_key: str = Field(default="minioadmin", description="S3 secret key")
    s3_bucket: str = Field(default="oncology-images", description="S3 bucket name")
    s3_region: str = Field(default="us-east-1", description="S3 region")
    s3_secure: bool = Field(default=False, description="Use HTTPS for S3")
    
    # RabbitMQ configuration
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL"
    )
    
    # File upload configuration
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes (100MB)")
    allowed_formats: List[str] = Field(
        default=["png", "tiff", "tif"],
        description="Allowed file formats"
    )
    
    # Image processing configuration
    generate_thumbnails: bool = Field(default=True, description="Generate thumbnails for images")
    thumbnail_sizes: List[int] = Field(default=[150, 300, 600], description="Thumbnail sizes in pixels")
    
    # Storage configuration
    storage_path_prefix: str = Field(default="images", description="Storage path prefix")
    signed_url_expiry: int = Field(default=3600, description="Default signed URL expiry in seconds")
    
    # Validation configuration
    validate_image_integrity: bool = Field(default=True, description="Validate image file integrity")
    calculate_checksums: bool = Field(default=True, description="Calculate file checksums")
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        description="Log format"
    )
    
    # Magic bytes for file format validation
    magic_bytes: dict = Field(
        default={
            "png": [b"\x89PNG\r\n\x1a\n"],
            "tiff": [b"II*\x00", b"MM\x00*"],  # Little-endian and big-endian TIFF
            "tif": [b"II*\x00", b"MM\x00*"]
        },
        description="Magic bytes for file format validation"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "IMAGE_SERVICE_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_database_url() -> str:
    """Get database connection URL."""
    return get_settings().database_url


def get_storage_config() -> dict:
    """Get storage configuration."""
    settings = get_settings()
    return {
        "endpoint": settings.s3_endpoint,
        "access_key": settings.s3_access_key,
        "secret_key": settings.s3_secret_key,
        "bucket": settings.s3_bucket,
        "region": settings.s3_region,
        "secure": settings.s3_secure
    }


def is_development() -> bool:
    """Check if running in development mode."""
    return get_settings().debug


def get_allowed_formats() -> List[str]:
    """Get list of allowed file formats."""
    return get_settings().allowed_formats


def get_max_file_size() -> int:
    """Get maximum file size in bytes."""
    return get_settings().max_file_size
