# DERCAS-ONCO-XAI V1 - API Gateway Configuration
# Configuration settings for the API Gateway service

import os
from typing import Dict, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API Gateway configuration settings."""
    
    # Application settings
    app_name: str = "DERCAS-ONCO-XAI API Gateway"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Security settings
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="RS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Keycloak settings
    keycloak_url: str = Field(env="KEYCLOAK_URL")
    keycloak_realm: str = Field(default="oncology-xai", env="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="api-gateway", env="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: Optional[str] = Field(default=None, env="KEYCLOAK_CLIENT_SECRET")
    
    # JWKS settings
    jwks_url: Optional[str] = Field(default=None, env="JWKS_URL")
    jwks_cache_ttl: int = Field(default=3600, env="JWKS_CACHE_TTL")
    
    # Rate limiting settings
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    # Internal service URLs
    case_service_url: str = Field(default="http://case-service:8001", env="CASE_SERVICE_URL")
    image_service_url: str = Field(default="http://image-service:8002", env="IMAGE_SERVICE_URL")
    inference_service_url: str = Field(default="http://inference-service:8003", env="INFERENCE_SERVICE_URL")
    ehr_service_url: str = Field(default="http://ehr-service:8004", env="EHR_SERVICE_URL")
    graph_service_url: str = Field(default="http://graph-service:8005", env="GRAPH_SERVICE_URL")
    ontology_admin_service_url: str = Field(default="http://ontology-admin-service:8006", env="ONTOLOGY_ADMIN_SERVICE_URL")
    audit_service_url: str = Field(default="http://audit-service:8007", env="AUDIT_SERVICE_URL")
    
    # Proxy settings
    proxy_timeout: float = Field(default=30.0, env="PROXY_TIMEOUT")
    proxy_retries: int = Field(default=3, env="PROXY_RETRIES")
    proxy_backoff_factor: float = Field(default=0.3, env="PROXY_BACKOFF_FACTOR")
    
    # Health check settings
    health_check_timeout: float = Field(default=5.0, env="HEALTH_CHECK_TIMEOUT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Observability settings
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database settings (for session storage if needed)
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    
    @validator("jwks_url", pre=True, always=True)
    def set_jwks_url(cls, v: Optional[str], values: Dict) -> str:
        """Set JWKS URL based on Keycloak configuration if not provided."""
        if v is None:
            keycloak_url = values.get("keycloak_url", "")
            keycloak_realm = values.get("keycloak_realm", "oncology-xai")
            return f"{keycloak_url}/realms/{keycloak_realm}/protocol/openid_connect/certs"
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("cors_methods", pre=True)
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @validator("cors_headers", pre=True)
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v
    
    def get_service_url(self, service_name: str) -> str:
        """Get service URL by service name."""
        service_urls = {
            "case": self.case_service_url,
            "image": self.image_service_url,
            "inference": self.inference_service_url,
            "ehr": self.ehr_service_url,
            "graph": self.graph_service_url,
            "ontology-admin": self.ontology_admin_service_url,
            "audit": self.audit_service_url,
        }
        
        url = service_urls.get(service_name)
        if not url:
            raise ValueError(f"Unknown service: {service_name}")
        
        return url
    
    def get_service_routes(self) -> Dict[str, Dict[str, str]]:
        """Get service routing configuration."""
        return {
            "/api/v1/patients": {
                "service": "case",
                "url": self.case_service_url,
                "strip_prefix": False
            },
            "/api/v1/cases": {
                "service": "case",
                "url": self.case_service_url,
                "strip_prefix": False
            },
            "/api/v1/images": {
                "service": "image",
                "url": self.image_service_url,
                "strip_prefix": False
            },
            "/api/v1/inference": {
                "service": "inference",
                "url": self.inference_service_url,
                "strip_prefix": False
            },
            "/api/v1/jobs": {
                "service": "inference",
                "url": self.inference_service_url,
                "strip_prefix": False
            },
            "/api/v1/ehr": {
                "service": "ehr",
                "url": self.ehr_service_url,
                "strip_prefix": False
            },
            "/api/v1/graph": {
                "service": "graph",
                "url": self.graph_service_url,
                "strip_prefix": False
            },
            "/api/v1/ontology": {
                "service": "ontology-admin",
                "url": self.ontology_admin_service_url,
                "strip_prefix": False
            },
            "/api/v1/audit": {
                "service": "audit",
                "url": self.audit_service_url,
                "strip_prefix": False
            }
        }
    
    def get_role_permissions(self) -> Dict[str, List[str]]:
        """Get role-based permissions configuration."""
        return {
            "clinician": [
                "patients:read",
                "patients:write",
                "cases:read",
                "cases:write",
                "images:read",
                "images:write",
                "inference:read",
                "inference:write",
                "ehr:read",
                "ehr:write",
                "graph:read",
                "audit:read"
            ],
            "admin": [
                "patients:read",
                "patients:write",
                "cases:read",
                "cases:write",
                "images:read",
                "images:write",
                "inference:read",
                "inference:write",
                "ehr:read",
                "ehr:write",
                "graph:read",
                "graph:write",
                "ontology:read",
                "ontology:write",
                "audit:read",
                "audit:write"
            ],
            "auditor": [
                "patients:read",
                "cases:read",
                "images:read",
                "inference:read",
                "ehr:read",
                "graph:read",
                "audit:read",
                "audit:write"
            ]
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
