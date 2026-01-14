"""Configuration settings for Policy Validation Copilot"""

from typing import Optional, List
from pydantic import BaseSettings, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Environment Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/policy_validation",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Vector Database Configuration
    chromadb_host: str = Field(default="localhost", env="CHROMADB_HOST")
    chromadb_port: int = Field(default=8001, env="CHROMADB_PORT")
    chromadb_collection_name: str = Field(default="policy_documents", env="CHROMADB_COLLECTION_NAME")
    
    # ML Services Configuration
    ml_model_registry_url: str = Field(default="http://localhost:8002", env="ML_MODEL_REGISTRY_URL")
    ml_feature_store_url: str = Field(default="http://localhost:8003", env="ML_FEATURE_STORE_URL")
    ml_classification_model_version: str = Field(default="v1.0.0", env="ML_CLASSIFICATION_MODEL_VERSION")
    ml_anomaly_model_version: str = Field(default="v1.0.0", env="ML_ANOMALY_MODEL_VERSION")
    ml_eta_model_version: str = Field(default="v1.0.0", env="ML_ETA_MODEL_VERSION")
    
    # Authentication and Security
    secret_key: str = Field(default="your-secret-key-here-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # RBAC/ABAC Configuration
    rbac_enabled: bool = Field(default=True, env="RBAC_ENABLED")
    abac_enabled: bool = Field(default=True, env="ABAC_ENABLED")
    admin_email: str = Field(default="admin@example.com", env="ADMIN_EMAIL")
    admin_password: str = Field(default="admin123", env="ADMIN_PASSWORD")
    
    # Guardrails Configuration
    guardrails_enabled: bool = Field(default=True, env="GUARDRAILS_ENABLED")
    pii_detection_enabled: bool = Field(default=True, env="PII_DETECTION_ENABLED")
    allowlist_sources_only: bool = Field(default=True, env="ALLOWLIST_SOURCES_ONLY")
    injection_detection_enabled: bool = Field(default=True, env="INJECTION_DETECTION_ENABLED")
    evidence_anchoring_required: bool = Field(default=True, env="EVIDENCE_ANCHORING_REQUIRED")
    
    # External Integrations
    crm_api_url: Optional[str] = Field(default=None, env="CRM_API_URL")
    crm_api_key: Optional[str] = Field(default=None, env="CRM_API_KEY")
    crm_webhook_secret: Optional[str] = Field(default=None, env="CRM_WEBHOOK_SECRET")
    
    insurer_api_timeout: int = Field(default=30, env="INSURER_API_TIMEOUT")
    insurer_api_retries: int = Field(default=3, env="INSURER_API_RETRIES")
    insurer_api_backoff_factor: float = Field(default=2.0, env="INSURER_API_BACKOFF_FACTOR")
    
    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    celery_result_serializer: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    celery_accept_content: List[str] = Field(default=["json"], env="CELERY_ACCEPT_CONTENT")
    celery_timezone: str = Field(default="UTC", env="CELERY_TIMEZONE")
    
    # LangGraph Configuration
    langgraph_checkpointer_type: str = Field(default="postgres", env="LANGGRAPH_CHECKPOINTER_TYPE")
    langgraph_max_iterations: int = Field(default=50, env="LANGGRAPH_MAX_ITERATIONS")
    langgraph_recursion_limit: int = Field(default=100, env="LANGGRAPH_RECURSION_LIMIT")
    
    # Thresholds Configuration
    confidence_high_threshold: float = Field(default=0.85, env="CONFIDENCE_HIGH_THRESHOLD")
    confidence_medium_threshold: float = Field(default=0.65, env="CONFIDENCE_MEDIUM_THRESHOLD")
    risk_low_threshold: float = Field(default=0.3, env="RISK_LOW_THRESHOLD")
    risk_high_threshold: float = Field(default=0.7, env="RISK_HIGH_THRESHOLD")
    coverage_ok_threshold: float = Field(default=0.8, env="COVERAGE_OK_THRESHOLD")
    anomaly_high_threshold: float = Field(default=0.8, env="ANOMALY_HIGH_THRESHOLD")
    
    # SLA Configuration
    default_sla_hours: int = Field(default=24, env="DEFAULT_SLA_HOURS")
    priority_high_sla_hours: int = Field(default=4, env="PRIORITY_HIGH_SLA_HOURS")
    priority_critical_sla_hours: int = Field(default=1, env="PRIORITY_CRITICAL_SLA_HOURS")
    
    # Audit Configuration
    audit_retention_days: int = Field(default=2555, env="AUDIT_RETENTION_DAYS")  # 7 years
    audit_export_enabled: bool = Field(default=True, env="AUDIT_EXPORT_ENABLED")
    audit_encryption_enabled: bool = Field(default=True, env="AUDIT_ENCRYPTION_ENABLED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
