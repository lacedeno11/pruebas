"""
Configuration module for PEI Agentic Platform.
Uses Pydantic Settings for environment-based configuration with type validation.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults for development mode.
    Production environments should override via .env file or environment variables.
    """

    # ============================================================================
    # SYSTEM CONFIGURATION
    # ============================================================================
    
    SYSTEM_MODE: str = "MOCK"
    """
    System operation mode.
    - MOCK: Uses simulated data and mock APIs for development/testing
    - PRODUCTION: Uses real APIs and database connections
    """

    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    
    DATABASE_URL: str = "sqlite:///./pei.db"
    """
    Database connection URL.
    SQLite format: sqlite:///./pei.db
    PostgreSQL format: postgresql+asyncpg://user:password@localhost:5432/pei
    """

    # ============================================================================
    # API & LLM CONFIGURATION
    # ============================================================================
    
    OPENAI_API_KEY: str = "sk-test-key"
    """OpenAI API key for LLM access (GPT-4/GPT-5.2)"""

    OPENAI_MODEL: str = "gpt-4"
    """OpenAI model to use for agent reasoning"""

    LLM_TEMPERATURE: float = 0.1
    """LLM temperature for deterministic decision-making (0.0-1.0)"""

    LLM_MAX_TOKENS: int = 2000
    """Maximum tokens per LLM response"""

    # ============================================================================
    # JWT & AUTHENTICATION
    # ============================================================================
    
    JWT_SECRET: str = "test-secret-key-change-in-production"
    """Secret key for JWT token signing"""

    JWT_ALGORITHM: str = "HS256"
    """Algorithm for JWT token encoding"""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    """JWT token expiration time in minutes"""

    # ============================================================================
    # NOTIFICATION CONFIGURATION
    # ============================================================================
    
    TELEGRAM_BOT_TOKEN: str = "test-telegram-token"
    """Telegram bot token for crew notifications"""

    EMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    """SMTP server for email notifications"""

    EMAIL_SMTP_PORT: int = 587
    """SMTP port (usually 587 for TLS, 465 for SSL)"""

    EMAIL_USERNAME: str = "noreply@telconet.ec"
    """Email account for sending notifications"""

    EMAIL_PASSWORD: str = "test-email-password"
    """Email account password"""

    EMAIL_FROM_NAME: str = "PEI Agentic Platform"
    """Sender name for emails"""

    # ============================================================================
    # LOGGING CONFIGURATION
    # ============================================================================
    
    LOG_LEVEL: str = "INFO"
    """
    Logging level.
    Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """

    LOG_DIR: str = "logs"
    """Directory for log files"""

    # ============================================================================
    # MOCK SERVICE CONFIGURATION
    # ============================================================================
    
    MOCK_API_LATENCY_MS: int = 500
    """Simulated API latency in milliseconds (for testing loading states)"""

    # ============================================================================
    # BUSINESS RULES & CONSTRAINTS
    # ============================================================================
    
    MAX_DAILY_CAPACITY: int = 10
    """Default maximum daily capacity per crew"""

    CENTROID_RADIUS_KM: float = 10.0
    """
    Geospatial constraint: maximum distance (km) from crew centroid
    for OT assignment in Phase 2 of planning algorithm
    """

    # ============================================================================
    # GOVERNANCE & AUTOMATION
    # ============================================================================
    
    INACTIVITY_ALERT_DAYS: List[int] = [20, 25, 29]
    """Days at which inactivity alerts are sent for DETENIDA orders"""

    AUTO_CANCEL_DAYS: int = 30
    """Days after which DETENIDA orders are automatically ANULADA"""

    # ============================================================================
    # CORS & API CONFIGURATION
    # ============================================================================
    
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    """Allowed CORS origins for frontend requests"""

    API_TITLE: str = "PEI Agentic Platform"
    """API title for OpenAPI documentation"""

    API_VERSION: str = "1.0.0"
    """API version"""

    API_DOCS_URL: str = "/api/docs"
    """URL path for Swagger OpenAPI documentation"""

    # ============================================================================
    # SCHEDULER CONFIGURATION
    # ============================================================================
    
    SCHEDULER_TIMEZONE: str = "America/Guayaquil"
    """Timezone for scheduled jobs (Ecuador)"""

    SCHEDULER_NIGHTLY_HOUR: int = 0
    """Hour (0-23) for nightly normalization job"""

    SCHEDULER_DOCUMENT_CHECK_HOUR: int = 8
    """Hour (0-23) for daily document validation job"""

    # ============================================================================
    # MONITORING & PERFORMANCE
    # ============================================================================
    
    DB_POOL_SIZE: int = 20
    """SQLAlchemy connection pool size"""

    DB_MAX_OVERFLOW: int = 10
    """SQLAlchemy max overflow connections"""

    REQUEST_TIMEOUT_SECONDS: int = 30
    """HTTP request timeout in seconds"""

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get singleton Settings instance.
    
    Uses @lru_cache to ensure only one Settings instance is created,
    loading environment variables once and caching the result.
    
    Returns:
        Settings: Configured settings object
        
    Example:
        >>> settings = get_settings()
        >>> print(settings.SYSTEM_MODE)
        "MOCK"
    """
    return Settings()

