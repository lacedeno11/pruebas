"""Configuration management for Inference Service."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "Oncology XAI Inference Service"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8003

    # Database settings
    database_url: PostgresDsn = Field(
        default="postgresql://postgres:postgres@localhost:5432/inference_db",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, validation_alias="DATABASE_MAX_OVERFLOW")

    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    # Celery settings
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="CELERY_RESULT_BACKEND",
    )

    # RabbitMQ settings
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        validation_alias="RABBITMQ_URL",
    )
    rabbitmq_exchange: str = Field(
        default="oncology_xai",
        validation_alias="RABBITMQ_EXCHANGE",
    )
    rabbitmq_routing_key: str = Field(
        default="inference.completed",
        validation_alias="RABBITMQ_ROUTING_KEY",
    )

    # Image Service settings
    image_service_url: str = Field(
        default="http://localhost:8001",
        validation_alias="IMAGE_SERVICE_URL",
    )

    # Logging settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(
        default="json",
        validation_alias="LOG_FORMAT",
    )

    @property
    def database_url_str(self) -> str:
        """Get database URL as string."""
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
