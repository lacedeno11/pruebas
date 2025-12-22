"""
Configuration Management System

This module implements a comprehensive configuration management system
for the Policy Validation Copilot with environment-specific settings,
validation, and secure credential management.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import timedelta
import os
import logging
from pathlib import Path
from pydantic import BaseSettings, Field, validator, SecretStr
from pydantic.env_settings import SettingsSourceCallable
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    
    # Connection settings
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="policy_copilot", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: SecretStr = Field(default="postgres", description="Database password")
    
    # Connection pool settings
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    
    # SSL settings
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca_path: Optional[str] = Field(default=None, description="SSL CA path")
    
    # Performance settings
    echo_sql: bool = Field(default=False, description="Echo SQL queries")
    query_timeout: int = Field(default=30, description="Query timeout in seconds")
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False
    
    @property
    def connection_url(self) -> str:
        """Get database connection URL"""
        password = self.password.get_secret_value()
        return f"postgresql://{self.username}:{password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_connection_url(self) -> str:
        """Get async database connection URL"""
        password = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.username}:{password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration settings"""
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    database: int = Field(default=0, description="Redis database number")
    password: Optional[SecretStr] = Field(default=None, description="Redis password")
    username: Optional[str] = Field(default=None, description="Redis username")
    
    # Connection settings
    max_connections: int = Field(default=20, description="Maximum connections")
    connection_timeout: int = Field(default=10, description="Connection timeout in seconds")
    socket_timeout: int = Field(default=10, description="Socket timeout in seconds")
    
    # SSL settings
    ssl_enabled: bool = Field(default=False, description="Enable SSL")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca_path: Optional[str] = Field(default=None, description="SSL CA path")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False
    
    @property
    def connection_url(self) -> str:
        """Get Redis connection URL"""
        auth_part = ""
        if self.username and self.password:
            password = self.password.get_secret_value()
            auth_part = f"{self.username}:{password}@"
        elif self.password:
            password = self.password.get_secret_value()
            auth_part = f":{password}@"
        
        protocol = "rediss" if self.ssl_enabled else "redis"
        return f"{protocol}://{auth_part}{self.host}:{self.port}/{self.database}"


class MLServiceSettings(BaseSettings):
    """ML services configuration settings"""
    
    # Classification service
    classification_endpoint: Optional[str] = Field(default=None, description="Classification service endpoint")
    classification_timeout: int = Field(default=30, description="Classification timeout in seconds")
    classification_model_version: str = Field(default="latest", description="Classification model version")
    
    # Anomaly detection service
    anomaly_endpoint: Optional[str] = Field(default=None, description="Anomaly detection service endpoint")
    anomaly_timeout: int = Field(default=30, description="Anomaly detection timeout in seconds")
    anomaly_model_version: str = Field(default="latest", description="Anomaly model version")
    
    # ETA prediction service
    eta_endpoint: Optional[str] = Field(default=None, description="ETA prediction service endpoint")
    eta_timeout: int = Field(default=30, description="ETA prediction timeout in seconds")
    eta_model_version: str = Field(default="latest", description="ETA model version")
    
    # General ML settings
    use_mock_services: bool = Field(default=True, description="Use mock ML services")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, description="Retry delay in seconds")
    
    class Config:
        env_prefix = "ML_"
        case_sensitive = False


class StorageSettings(BaseSettings):
    """Object storage configuration settings"""
    
    # Storage backend
    backend: str = Field(default="local", description="Storage backend (s3, local, azure, gcs)")
    
    # S3 settings
    s3_bucket_name: Optional[str] = Field(default=None, description="S3 bucket name")
    s3_region: str = Field(default="us-east-1", description="S3 region")
    s3_access_key: Optional[SecretStr] = Field(default=None, description="S3 access key")
    s3_secret_key: Optional[SecretStr] = Field(default=None, description="S3 secret key")
    s3_endpoint_url: Optional[str] = Field(default=None, description="S3 endpoint URL")
    
    # Local storage settings
    local_path: str = Field(default="./storage", description="Local storage path")
    
    # General settings
    encryption_enabled: bool = Field(default=True, description="Enable encryption")
    versioning_enabled: bool = Field(default=True, description="Enable versioning")
    retention_days: int = Field(default=2555, description="Retention period in days")
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    
    class Config:
        env_prefix = "STORAGE_"
        case_sensitive = False


class VectorDBSettings(BaseSettings):
    """Vector database configuration settings"""
    
    # Backend selection
    backend: str = Field(default="chromadb", description="Vector DB backend (chromadb, pinecone)")
    
    # ChromaDB settings
    chromadb_host: str = Field(default="localhost", description="ChromaDB host")
    chromadb_port: int = Field(default=8000, description="ChromaDB port")
    chromadb_collection: str = Field(default="policy_documents", description="ChromaDB collection name")
    
    # Pinecone settings
    pinecone_api_key: Optional[SecretStr] = Field(default=None, description="Pinecone API key")
    pinecone_environment: Optional[str] = Field(default=None, description="Pinecone environment")
    pinecone_index_name: Optional[str] = Field(default=None, description="Pinecone index name")
    
    # Embedding settings
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model")
    embedding_dimension: int = Field(default=384, description="Embedding dimension")
    similarity_metric: str = Field(default="cosine", description="Similarity metric")
    
    class Config:
        env_prefix = "VECTORDB_"
        case_sensitive = False


class NotificationSettings(BaseSettings):
    """Notification service configuration settings"""
    
    # Email settings
    smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[SecretStr] = Field(default=None, description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")
    from_email: Optional[str] = Field(default=None, description="From email address")
    
    # Slack settings
    slack_webhook_url: Optional[SecretStr] = Field(default=None, description="Slack webhook URL")
    slack_bot_token: Optional[SecretStr] = Field(default=None, description="Slack bot token")
    slack_channel: Optional[str] = Field(default=None, description="Default Slack channel")
    
    # SMS settings
    sms_provider: Optional[str] = Field(default=None, description="SMS provider (twilio, aws_sns)")
    sms_api_key: Optional[SecretStr] = Field(default=None, description="SMS API key")
    sms_from_number: Optional[str] = Field(default=None, description="SMS from number")
    
    # General settings
    retry_attempts: int = Field(default=3, description="Retry attempts")
    retry_delay_seconds: int = Field(default=60, description="Retry delay in seconds")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    
    class Config:
        env_prefix = "NOTIFICATION_"
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    
    # JWT settings
    jwt_secret_key: SecretStr = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")
    
    # API security
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    cors_headers: List[str] = Field(default=["*"], description="CORS allowed headers")
    
    # Encryption settings
    encryption_key: Optional[SecretStr] = Field(default=None, description="Data encryption key")
    hash_salt: SecretStr = Field(default="policy-copilot-salt", description="Hash salt")
    
    # Session settings
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(default=15, description="Account lockout duration")
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration settings"""
    
    # Prometheus settings
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=8000, description="Prometheus metrics port")
    prometheus_path: str = Field(default="/metrics", description="Prometheus metrics path")
    
    # Grafana settings
    grafana_enabled: bool = Field(default=True, description="Enable Grafana dashboards")
    grafana_host: str = Field(default="localhost", description="Grafana host")
    grafana_port: int = Field(default=3000, description="Grafana port")
    
    # Jaeger settings
    jaeger_enabled: bool = Field(default=False, description="Enable Jaeger tracing")
    jaeger_host: str = Field(default="localhost", description="Jaeger host")
    jaeger_port: int = Field(default=14268, description="Jaeger port")
    
    # Health check settings
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, description="Health check timeout in seconds")
    
    # Alerting settings
    alert_webhook_url: Optional[str] = Field(default=None, description="Alert webhook URL")
    alert_email: Optional[str] = Field(default=None, description="Alert email address")
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False


class WorkflowSettings(BaseSettings):
    """Workflow configuration settings"""
    
    # LangGraph settings
    checkpoint_enabled: bool = Field(default=True, description="Enable workflow checkpoints")
    max_workflow_duration_hours: int = Field(default=48, description="Maximum workflow duration")
    
    # HITL settings
    hitl_enabled: bool = Field(default=True, description="Enable human-in-the-loop")
    hitl_timeout_hours: int = Field(default=24, description="HITL timeout in hours")
    
    # Auto-closure settings
    auto_closure_enabled: bool = Field(default=True, description="Enable auto-closure")
    confidence_threshold: float = Field(default=0.8, description="Confidence threshold for auto-closure")
    risk_threshold: float = Field(default=0.3, description="Risk threshold for auto-closure")
    
    # External query settings
    external_queries_enabled: bool = Field(default=True, description="Enable external queries")
    external_query_timeout_minutes: int = Field(default=30, description="External query timeout")
    
    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_minutes: int = Field(default=5, description="Retry delay in minutes")
    
    class Config:
        env_prefix = "WORKFLOW_"
        case_sensitive = False


class ApplicationSettings(BaseSettings):
    """Main application configuration settings"""
    
    # Application metadata
    app_name: str = Field(default="Policy Validation Copilot", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(default="DERCAS 01 Policy Validation Copilot", description="Application description")
    
    # Environment settings
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=True, description="Debug mode")
    testing: bool = Field(default=False, description="Testing mode")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")
    
    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_format: str = Field(default="json", description="Log format (json, text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    docs_url: str = Field(default="/docs", description="API documentation URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI schema URL")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ml_services: MLServiceSettings = Field(default_factory=MLServiceSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    vectordb: VectorDBSettings = Field(default_factory=VectorDBSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    workflow: WorkflowSettings = Field(default_factory=WorkflowSettings)
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("environment", pre=True)
    def validate_environment(cls, v):
        """Validate environment setting"""
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @validator("log_level", pre=True)
    def validate_log_level(cls, v):
        """Validate log level setting"""
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v
    
    @validator("debug")
    def validate_debug_in_production(cls, v, values):
        """Ensure debug is disabled in production"""
        if values.get("environment") == Environment.PRODUCTION and v:
            raise ValueError("Debug mode must be disabled in production")
        return v
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION
    
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment == Environment.TESTING or self.testing


class ConfigManager:
    """
    Configuration manager for loading and managing application settings.
    
    Provides environment-specific configuration loading, validation,
    and runtime configuration updates.
    """
    
    def __init__(self, env_file: Optional[str] = None, config_dir: Optional[str] = None):
        self.env_file = env_file or ".env"
        self.config_dir = Path(config_dir or "config")
        self._settings: Optional[ApplicationSettings] = None
        self._config_cache: Dict[str, Any] = {}
    
    def load_settings(self, environment: Optional[Environment] = None) -> ApplicationSettings:
        """Load application settings for specified environment"""
        
        if self._settings is not None:
            return self._settings
        
        # Determine environment
        if environment is None:
            environment = Environment(os.getenv("APP_ENVIRONMENT", "development").lower())
        
        # Load environment-specific configuration
        env_files = self._get_env_files(environment)
        
        # Create settings with environment files
        self._settings = ApplicationSettings(
            _env_file=env_files,
            environment=environment
        )
        
        # Apply environment-specific overrides
        self._apply_environment_overrides(environment)
        
        # Validate configuration
        self._validate_configuration()
        
        logger.info(f"Configuration loaded for environment: {environment.value}")
        
        return self._settings
    
    def _get_env_files(self, environment: Environment) -> List[str]:
        """Get list of environment files to load"""
        
        env_files = []
        
        # Base environment file
        base_env = self.config_dir / ".env"
        if base_env.exists():
            env_files.append(str(base_env))
        
        # Environment-specific file
        env_specific = self.config_dir / f".env.{environment.value}"
        if env_specific.exists():
            env_files.append(str(env_specific))
        
        # Local override file
        local_env = self.config_dir / ".env.local"
        if local_env.exists():
            env_files.append(str(local_env))
        
        # Root .env file
        if Path(self.env_file).exists():
            env_files.append(self.env_file)
        
        return env_files
    
    def _apply_environment_overrides(self, environment: Environment) -> None:
        """Apply environment-specific configuration overrides"""
        
        if environment == Environment.PRODUCTION:
            # Production overrides
            self._settings.debug = False
            self._settings.testing = False
            self._settings.log_level = LogLevel.INFO
            self._settings.ml_services.use_mock_services = False
            
        elif environment == Environment.TESTING:
            # Testing overrides
            self._settings.testing = True
            self._settings.database.name = "policy_copilot_test"
            self._settings.redis.database = 1
            self._settings.ml_services.use_mock_services = True
            
        elif environment == Environment.DEVELOPMENT:
            # Development overrides
            self._settings.debug = True
            self._settings.log_level = LogLevel.DEBUG
            self._settings.ml_services.use_mock_services = True
    
    def _validate_configuration(self) -> None:
        """Validate configuration settings"""
        
        if not self._settings:
            raise ValueError("Settings not loaded")
        
        # Validate production requirements
        if self._settings.is_production():
            self._validate_production_config()
        
        # Validate database configuration
        self._validate_database_config()
        
        # Validate security configuration
        self._validate_security_config()
    
    def _validate_production_config(self) -> None:
        """Validate production-specific configuration"""
        
        # Check for default passwords
        if self._settings.database.password.get_secret_value() == "postgres":
            raise ValueError("Default database password not allowed in production")
        
        if self._settings.security.jwt_secret_key.get_secret_value() == "your-secret-key-change-in-production":
            raise ValueError("Default JWT secret key not allowed in production")
        
        # Check SSL configuration
        if not self._settings.database.ssl_mode or self._settings.database.ssl_mode == "disable":
            logger.warning("SSL disabled for database in production")
    
    def _validate_database_config(self) -> None:
        """Validate database configuration"""
        
        if not self._settings.database.host:
            raise ValueError("Database host is required")
        
        if not self._settings.database.name:
            raise ValueError("Database name is required")
    
    def _validate_security_config(self) -> None:
        """Validate security configuration"""
        
        if self._settings.is_production():
            if "*" in self._settings.security.cors_origins:
                logger.warning("Wildcard CORS origins not recommended in production")
    
    def get_settings(self) -> ApplicationSettings:
        """Get current application settings"""
        
        if self._settings is None:
            return self.load_settings()
        
        return self._settings
    
    def reload_settings(self, environment: Optional[Environment] = None) -> ApplicationSettings:
        """Reload application settings"""
        
        self._settings = None
        self._config_cache.clear()
        
        return self.load_settings(environment)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        
        if key in self._config_cache:
            return self._config_cache[key]
        
        settings = self.get_settings()
        
        # Navigate nested configuration
        keys = key.split(".")
        value = settings
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        
        self._config_cache[key] = value
        return value
    
    def update_config_value(self, key: str, value: Any) -> None:
        """Update configuration value at runtime"""
        
        settings = self.get_settings()
        
        # Navigate to parent and set value
        keys = key.split(".")
        parent = settings
        
        for k in keys[:-1]:
            if hasattr(parent, k):
                parent = getattr(parent, k)
            else:
                raise ValueError(f"Configuration key not found: {key}")
        
        setattr(parent, keys[-1], value)
        
        # Update cache
        self._config_cache[key] = value
        
        logger.info(f"Configuration updated: {key} = {value}")


# Global configuration manager instance
config_manager = ConfigManager()


def get_settings() -> ApplicationSettings:
    """Get application settings"""
    return config_manager.get_settings()


def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value by key"""
    return config_manager.get_config_value(key, default)


def reload_config(environment: Optional[Environment] = None) -> ApplicationSettings:
    """Reload configuration"""
    return config_manager.reload_settings(environment)
