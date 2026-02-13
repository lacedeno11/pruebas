"""
Application Configuration Module

This module defines centralized configuration management using Pydantic Settings.
All configuration is loaded from environment variables, allowing seamless switching
between development (MOCK mode) and production (PRODUCTION mode) environments.

Environment Variables:
    SYSTEM_MODE: 'MOCK' for development with mock services, 'PRODUCTION' for live APIs
    DATABASE_URL: PostgreSQL async connection string
    OPENAI_API_KEY: OpenAI API key for LLM-powered agents
    TELEGRAM_BOT_TOKEN: Telegram Bot API token for field team notifications
    SMTP_HOST: SMTP server hostname for email notifications
    SMTP_PORT: SMTP server port (usually 587 or 465)
    SMTP_USER: SMTP authentication username
    SMTP_PASSWORD: SMTP authentication password
    FRONTEND_URL: Frontend application URL (for CORS)
    BACKEND_URL: Backend API URL (for generating links in responses)
    PROJECT_NAME: Application display name (default: 'DERCAS PEI')
    API_V1_STR: API version prefix (default: '/api/v1')

Usage:
    from app.core.config import settings
    
    # Access configuration
    if settings.SYSTEM_MODE == 'MOCK':
        api_service = MockApiService()
    else:
        api_service = TelcosApiService()
    
    # Use in FastAPI
    app = FastAPI(title=settings.PROJECT_NAME)
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application Settings using Pydantic BaseSettings.
    
    All configuration is loaded from environment variables with optional .env file support.
    This enables different configurations for development, testing, and production
    without changing code.
    
    Model Config:
        env_file: '.env' - Load configuration from .env file in working directory
        env_file_encoding: 'utf-8' - UTF-8 encoding for .env file
        case_sensitive: True - Environment variable names are case-sensitive
    """

    # ========================================================================
    # System Configuration
    # ========================================================================

    SYSTEM_MODE: str = Field(
        default="MOCK",
        description="System mode: 'MOCK' for development, 'PRODUCTION' for live APIs",
        examples=["MOCK", "PRODUCTION"],
    )

    PROJECT_NAME: str = Field(
        default="DERCAS PEI",
        description="Application display name",
    )

    API_V1_STR: str = Field(
        default="/api/v1",
        description="API version prefix for all endpoints",
    )

    # ========================================================================
    # Database Configuration
    # ========================================================================

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/pei_db",
        description="PostgreSQL async connection string",
        examples=["postgresql+asyncpg://user:password@localhost:5432/dercas"],
    )

    # ========================================================================
    # LLM Configuration
    # ========================================================================

    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key for LLM-powered agents",
        examples=["sk-..."],
    )

    # ========================================================================
    # Notification Configuration - Telegram
    # ========================================================================

    TELEGRAM_BOT_TOKEN: Optional[str] = Field(
        default=None,
        description="Telegram Bot API token for field team notifications",
        examples=["123456789:ABCdefGHIjklmnoPQRstuvWXYZ"],
    )

    # ========================================================================
    # Notification Configuration - SMTP (Email)
    # ========================================================================

    SMTP_HOST: Optional[str] = Field(
        default=None,
        description="SMTP server hostname for email notifications",
        examples=["smtp.gmail.com", "mail.company.com"],
    )

    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port (587 for TLS, 465 for SSL)",
        examples=[587, 465],
    )

    SMTP_USER: Optional[str] = Field(
        default=None,
        description="SMTP authentication username",
        examples=["noreply@company.com"],
    )

    SMTP_PASSWORD: Optional[str] = Field(
        default=None,
        description="SMTP authentication password",
    )

    COORDINADOR_EMAIL: Optional[str] = Field(
        default=None,
        description="Email address for OPU Coordinador to receive critical alerts",
        examples=["coordinador@company.com"],
    )

    # ========================================================================
    # URL Configuration
    # ========================================================================

    FRONTEND_URL: str = Field(
        default="http://localhost:5173",
        description="Frontend application URL (for CORS)",
        examples=["http://localhost:5173", "https://app.dercas.com"],
    )

    BACKEND_URL: str = Field(
        default="http://localhost:8000",
        description="Backend API URL (for generating links in responses)",
        examples=["http://localhost:8000", "https://api.dercas.com"],
    )

    # ========================================================================
    # Configuration Class Settings
    # ========================================================================

    class Config:
        """Pydantic configuration for Settings class."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Allow extra fields from environment
        extra = "allow"


# ============================================================================
# Global Settings Instance
# ============================================================================

settings = Settings()

"""
Global singleton instance of Settings.

This instance is created once at module import time and should be used
throughout the application for configuration access.

Example:
    from app.core.config import settings
    
    mode = settings.SYSTEM_MODE
    db_url = settings.DATABASE_URL
"""


# ============================================================================
# Configuration Validation & Documentation
# ============================================================================

def get_config_summary() -> dict:
    """
    Get a summary of current configuration (excluding sensitive data).
    
    Returns:
        Dict with configuration summary and masked sensitive values
    """
    return {
        "system_mode": settings.SYSTEM_MODE,
        "project_name": settings.PROJECT_NAME,
        "api_version": settings.API_V1_STR,
        "database": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "configured",
        "frontend_url": settings.FRONTEND_URL,
        "backend_url": settings.BACKEND_URL,
        "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN),
        "smtp_configured": bool(settings.SMTP_HOST and settings.SMTP_USER),
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


if __name__ == "__main__":
    """
    Print configuration summary when module is run directly.
    
    Usage: python -m app.core.config
    """
    import json
    
    print("=" * 80)
    print("DERCAS PEI - Configuration Summary")
    print("=" * 80)
    print(json.dumps(get_config_summary(), indent=2))
    print("=" * 80)

