# DERCAS-ONCO-XAI V1 - Image Service Configuration
# Configuration settings for the Image Service

import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Image Service configuration settings."""
    
    # Application settings
    app_name: str = "DERCAS-ONCO-XAI Image Service"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8002, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Database settings
    database_url: str = Field(env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # MinIO/S3 settings
    s3_endpoint: str = Field(env="S3_ENDPOINT")
    s3_access_key: str = Field(env="S3_ACCESS_KEY")
    s3_secret_key: str = Field(env="S3_SECRET_KEY")
    s3_bucket: str = Field(default="oncology-xai-images", env="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", env="S3_REGION")
    s3_secure: bool = Field(default=False, env="S3_SECURE")
    
    # RabbitMQ settings for event publishing
    rabbitmq_url: str = Field(env="RABBITMQ_URL")
    rabbitmq_exchange: str = Field(default="oncology-xai", env="RABBITMQ_EXCHANGE")
    rabbitmq_routing_key_prefix: str = Field(default="image", env="RABBITMQ_ROUTING_KEY_PREFIX")
    
    # Security settings
    secret_key: str = Field(env="SECRET_KEY")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    
    # Image processing settings
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_formats: List[str] = Field(default=["png", "biff"], env="ALLOWED_FORMATS")
    image_quality: int = Field(default=95, env="IMAGE_QUALITY")
    thumbnail_size: tuple = Field(default=(256, 256), env="THUMBNAIL_SIZE")
    
    # Upload settings
    upload_chunk_size: int = Field(default=8192, env="UPLOAD_CHUNK_SIZE")
    temp_dir: str = Field(default="/tmp/image-uploads", env="TEMP_DIR")
    cleanup_temp_files: bool = Field(default=True, env="CLEANUP_TEMP_FILES")
    
    # Signed URL settings
    signed_url_expiry: int = Field(default=3600, env="SIGNED_URL_EXPIRY")  # 1 hour
    viewer_url_expiry: int = Field(default=86400, env="VIEWER_URL_EXPIRY")  # 24 hours
    
    # Validation settings
    validate_magic_bytes: bool = Field(default=True, env="VALIDATE_MAGIC_BYTES")
    strict_format_validation: bool = Field(default=True, env="STRICT_FORMAT_VALIDATION")
    
    # Observability settings
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Pagination settings
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Case service integration
    case_service_url: str = Field(default="http://case-service:8001", env="CASE_SERVICE_URL")
    case_service_timeout: float = Field(default=30.0, env="CASE_SERVICE_TIMEOUT")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_formats", pre=True)
    def parse_allowed_formats(cls, v):
        """Parse allowed formats from string or list."""
        if isinstance(v, str):
            return [fmt.strip().lower() for fmt in v.split(",")]
        return [fmt.lower() for fmt in v]
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("Database URL must be a PostgreSQL URL")
        return v
    
    @validator("max_file_size")
    def validate_max_file_size(cls, v):
        """Validate maximum file size."""
        if v <= 0:
            raise ValueError("Maximum file size must be positive")
        if v > 1024 * 1024 * 1024:  # 1GB
            raise ValueError("Maximum file size cannot exceed 1GB")
        return v
    
    @validator("thumbnail_size", pre=True)
    def parse_thumbnail_size(cls, v):
        """Parse thumbnail size from string or tuple."""
        if isinstance(v, str):
            try:
                width, height = v.split(",")
                return (int(width.strip()), int(height.strip()))
            except (ValueError, AttributeError):
                return (256, 256)
        return v
    
    def get_async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url
    
    def get_sync_database_url(self) -> str:
        """Get sync database URL for Alembic."""
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return self.database_url
    
    def get_s3_config(self) -> dict:
        """Get S3/MinIO configuration dictionary."""
        return {
            "endpoint": self.s3_endpoint,
            "access_key": self.s3_access_key,
            "secret_key": self.s3_secret_key,
            "bucket": self.s3_bucket,
            "region": self.s3_region,
            "secure": self.s3_secure
        }
    
    def is_format_allowed(self, format_name: str) -> bool:
        """Check if image format is allowed."""
        return format_name.lower() in self.allowed_formats
    
    def get_max_file_size_mb(self) -> float:
        """Get maximum file size in MB."""
        return self.max_file_size / (1024 * 1024)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
