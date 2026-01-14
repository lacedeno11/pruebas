"""
DERCAS-ONCO-XAI API Gateway Configuration

Configuration settings for the API Gateway service.
"""

import os
from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """API Gateway configuration settings."""
    
    # Server configuration
    HOST: str = Field(default="0.0.0.0", env="API_GATEWAY_HOST")
    PORT: int = Field(default=8000, env="API_GATEWAY_PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    MAX_REQUEST_SIZE_BYTES: int = Field(default=100 * 1024 * 1024, env="MAX_REQUEST_SIZE_BYTES")  # 100MB
    
    # Authentication (Keycloak)
    KEYCLOAK_URL: str = Field(..., env="KEYCLOAK_URL")
    KEYCLOAK_REALM: str = Field(default="dercas", env="KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID: str = Field(default="dercas-api", env="KEYCLOAK_CLIENT_ID")
    
    @property
    def KEYCLOAK_JWKS_URL(self) -> str:
        """Get Keycloak JWKS URL."""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    @property
    def KEYCLOAK_ISSUER(self) -> str:
        """Get Keycloak issuer."""
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}"
    
    @property
    def KEYCLOAK_AUDIENCE(self) -> str:
        """Get Keycloak audience."""
        return self.KEYCLOAK_CLIENT_ID
    
    # Internal service URLs
    CASE_SERVICE_URL: str = Field(default="http://case-service:8001", env="CASE_SERVICE_URL")
    IMAGE_SERVICE_URL: str = Field(default="http://image-service:8002", env="IMAGE_SERVICE_URL")
    INFERENCE_SERVICE_URL: str = Field(default="http://inference-service:8003", env="INFERENCE_SERVICE_URL")
    EHR_SERVICE_URL: str = Field(default="http://ehr-service:8004", env="EHR_SERVICE_URL")
    GRAPH_SERVICE_URL: str = Field(default="http://graph-service:8005", env="GRAPH_SERVICE_URL")
    ONTOLOGY_ADMIN_SERVICE_URL: str = Field(default="http://ontology-admin-service:8006", env="ONTOLOGY_ADMIN_SERVICE_URL")
    AUDIT_SERVICE_URL: str = Field(default="http://audit-service:8007", env="AUDIT_SERVICE_URL")
    
    # Service timeouts
    SERVICE_TIMEOUT_SECONDS: int = Field(default=30, env="SERVICE_TIMEOUT_SECONDS")
    UPLOAD_TIMEOUT_SECONDS: int = Field(default=300, env="UPLOAD_TIMEOUT_SECONDS")  # 5 minutes for uploads
    
    # Health check configuration
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
