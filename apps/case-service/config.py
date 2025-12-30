"""
DERCAS-ONCO-XAI V1 - Case Service Configuration

Configuration management for the Case Service.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Case Service configuration settings."""
    
    # Service configuration
    service_name: str = Field(default="case-service", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8001, description="Server port")
    
    # Database configuration
    database_url: str = Field(
        default="postgresql+asyncpg://oncology_user:oncology_pass@localhost:5432/oncology_db",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=30, description="Database max overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # RabbitMQ configuration
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL"
    )
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        description="Log format"
    )
    
    # Pagination defaults
    default_page_size: int = Field(default=20, description="Default page size for pagination")
    max_page_size: int = Field(default=100, description="Maximum page size for pagination")
    
    # Case management
    default_case_priority: int = Field(default=1, description="Default case priority")
    max_case_priority: int = Field(default=5, description="Maximum case priority")
    
    class Config:
        env_file = ".env"
        env_prefix = "CASE_SERVICE_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_database_url() -> str:
    """Get database connection URL."""
    return get_settings().database_url


def is_development() -> bool:
    """Check if running in development mode."""
    return get_settings().debug
