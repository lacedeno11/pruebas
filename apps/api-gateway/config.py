"""
DERCAS-ONCO-XAI V1 - API Gateway Configuration

Configuration management for the API Gateway service.
"""

import os
from functools import lru_cache
from typing import Dict, Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """API Gateway configuration settings."""
    
    # Service configuration
    service_name: str = Field(default="api-gateway", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # Keycloak configuration
    keycloak_url: str = Field(..., description="Keycloak server URL")
    keycloak_realm: str = Field(default="oncology", description="Keycloak realm")
    keycloak_client_id: str = Field(default="oncology-api", description="Keycloak client ID")
    
    # Redis configuration (for rate limiting)
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    
    # Rate limiting configuration
    default_rate_limit: int = Field(default=100, description="Default requests per minute")
    image_upload_rate_limit: int = Field(default=10, description="Image upload requests per minute")
    
    # Service URLs
    case_service_url: str = Field(default="http://localhost:8001", description="Case service URL")
    image_service_url: str = Field(default="http://localhost:8002", description="Image service URL")
    inference_service_url: str = Field(default="http://localhost:8003", description="Inference service URL")
    ehr_service_url: str = Field(default="http://localhost:8004", description="EHR service URL")
    graph_service_url: str = Field(default="http://localhost:8005", description="Graph service URL")
    ontology_admin_service_url: str = Field(default="http://localhost:8006", description="Ontology admin service URL")
    audit_service_url: str = Field(default="http://localhost:8007", description="Audit service URL")
    
    # Request limits
    max_request_size: int = Field(default=100 * 1024 * 1024, description="Maximum request size in bytes (100MB)")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    # CORS configuration
    cors_origins: list = Field(default=["*"], description="CORS allowed origins")
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        description="Log format"
    )
    
    @property
    def service_urls(self) -> Dict[str, str]:
        """Get service URLs mapping."""
        return {
            "case-service": self.case_service_url,
            "image-service": self.image_service_url,
            "inference-service": self.inference_service_url,
            "ehr-service": self.ehr_service_url,
            "graph-service": self.graph_service_url,
            "ontology-admin-service": self.ontology_admin_service_url,
            "audit-service": self.audit_service_url,
        }
    
    class Config:
        env_file = ".env"
        env_prefix = "GATEWAY_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_service_url(service_name: str) -> Optional[str]:
    """Get URL for a specific service."""
    settings = get_settings()
    return settings.service_urls.get(service_name)


def is_development() -> bool:
    """Check if running in development mode."""
    return get_settings().debug


def get_cors_config() -> Dict[str, any]:
    """Get CORS configuration."""
    settings = get_settings()
    return {
        "allow_origins": settings.cors_origins,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
