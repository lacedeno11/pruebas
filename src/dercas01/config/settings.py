"""
Configuration Settings for DERCAS 01 Policy Validation Copilot

This module contains all application settings using Pydantic Settings for
environment variable management and validation.
"""

from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from pydantic_settings import BaseSettings as PydanticBaseSettings


class Settings(PydanticBaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    """
    
    # Application
    app_name: str = Field(default="DERCAS 01 Policy Validation Copilot", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Database
    database_url: str = Field(
        default="postgresql://dercas01:password@localhost:5432/dercas01_db",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # ChromaDB
    chromadb_host: str = Field(default="localhost", env="CHROMADB_HOST")
    chromadb_port: int = Field(default=8001, env="CHROMADB_PORT")
    chromadb_collection_name: str = Field(default="policy_documents", env="CHROMADB_COLLECTION_NAME")
    chromadb_persist_directory: str = Field(default="./data/chromadb", env="CHROMADB_PERSIST_DIRECTORY")
    
    # Embeddings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL"
    )
    embedding_device: str = Field(default="cpu", env="EMBEDDING_DEVICE")
    
    # Object Storage
    object_storage_type: str = Field(default="local", env="OBJECT_STORAGE_TYPE")
    object_storage_path: str = Field(default="./data/documents", env="OBJECT_STORAGE_PATH")
    
    # ML Services
    ml_classify_url: str = Field(default="http://localhost:8001/classify", env="ML_CLASSIFY_URL")
    ml_anomaly_url: str = Field(default="http://localhost:8002/anomaly", env="ML_ANOMALY_URL")
    ml_eta_url: str = Field(default="http://localhost:8003/eta", env="ML_ETA_URL")
    
    # Model Versions
    default_classify_model_version: str = Field(default="v1.0.0", env="DEFAULT_CLASSIFY_MODEL_VERSION")
    default_anomaly_model_version: str = Field(default="v1.0.0", env="DEFAULT_ANOMALY_MODEL_VERSION")
    default_eta_model_version: str = Field(default="v1.0.0", env="DEFAULT_ETA_MODEL_VERSION")
    
    # LangGraph
    langgraph_max_iterations: int = Field(default=50, env="LANGGRAPH_MAX_ITERATIONS")
    langgraph_timeout_seconds: int = Field(default=300, env="LANGGRAPH_TIMEOUT_SECONDS")
    langgraph_checkpoint_enabled: bool = Field(default=True, env="LANGGRAPH_CHECKPOINT_ENABLED")
    
    # Guardrails
    enable_rbac: bool = Field(default=True, env="ENABLE_RBAC")
    enable_pii_masking: bool = Field(default=True, env="ENABLE_PII_MASKING")
    enable_source_validation: bool = Field(default=True, env="ENABLE_SOURCE_VALIDATION")
    enable_anti_hallucination: bool = Field(default=True, env="ENABLE_ANTI_HALLUCINATION")
    
    # Decision Thresholds
    confidence_high_threshold: float = Field(default=0.85, env="CONFIDENCE_HIGH_THRESHOLD")
    confidence_medium_threshold: float = Field(default=0.65, env="CONFIDENCE_MEDIUM_THRESHOLD")
    risk_low_threshold: float = Field(default=0.3, env="RISK_LOW_THRESHOLD")
    risk_high_threshold: float = Field(default=0.7, env="RISK_HIGH_THRESHOLD")
    coverage_ok_threshold: float = Field(default=0.8, env="COVERAGE_OK_THRESHOLD")
    anomaly_high_threshold: float = Field(default=0.8, env="ANOMALY_HIGH_THRESHOLD")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(default=10, env="HEALTH_CHECK_TIMEOUT")
    
    # Logging
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_path: str = Field(default="./logs/dercas01.log", env="LOG_FILE_PATH")
    log_rotation_size: str = Field(default="100MB", env="LOG_ROTATION_SIZE")
    log_retention_days: int = Field(default=30, env="LOG_RETENTION_DAYS")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level setting."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()
    
    @validator("object_storage_type")
    def validate_storage_type(cls, v):
        """Validate object storage type."""
        allowed_types = ["local", "s3", "azure", "gcp"]
        if v not in allowed_types:
            raise ValueError(f"Storage type must be one of: {allowed_types}")
        return v
    
    @validator("embedding_device")
    def validate_embedding_device(cls, v):
        """Validate embedding device."""
        allowed_devices = ["cpu", "cuda", "mps"]
        if v not in allowed_devices:
            raise ValueError(f"Embedding device must be one of: {allowed_devices}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
