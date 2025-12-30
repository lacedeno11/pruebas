# DERCAS-ONCO-XAI V1 - Case Service Configuration
# Configuration settings for the Case Service

import os
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Case Service configuration settings."""
    
    # Application settings
    app_name: str = "DERCAS-ONCO-XAI Case Service"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Database settings
    database_url: str = Field(env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # RabbitMQ settings for event publishing
    rabbitmq_url: str = Field(env="RABBITMQ_URL")
    rabbitmq_exchange: str = Field(default="oncology-xai", env="RABBITMQ_EXCHANGE")
    rabbitmq_routing_key_prefix: str = Field(default="case", env="RABBITMQ_ROUTING_KEY_PREFIX")
    
    # Security settings
    secret_key: str = Field(env="SECRET_KEY")
    
    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    
    # Observability settings
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Pagination settings
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Validation settings
    max_patient_name_length: int = Field(default=255, env="MAX_PATIENT_NAME_LENGTH")
    max_case_description_length: int = Field(default=2000, env="MAX_CASE_DESCRIPTION_LENGTH")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("Database URL must be a PostgreSQL URL")
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
