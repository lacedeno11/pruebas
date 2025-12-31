"""
DERCAS-ONCO-XAI Case Service Configuration

Configuration settings for the Case Service.
"""

import os
from functools import lru_cache

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Case Service configuration settings."""
    
    # Server configuration
    HOST: str = Field(default="0.0.0.0", env="CASE_SERVICE_HOST")
    PORT: int = Field(default=8001, env="CASE_SERVICE_PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # RabbitMQ configuration
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")
    
    # Service configuration
    SERVICE_NAME: str = Field(default="case-service", env="SERVICE_NAME")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
