"""
Configuration module for PEI Platform using Pydantic Settings.

This module loads environment variables and provides a singleton settings instance
for the entire application. It handles validation and provides convenient properties
for accessing configuration.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for automatic .env file loading and validation.
    """

    # System Mode Configuration
    system_mode: str = Field(
        default="MOCK",
        description="System mode: MOCK for development (simulated APIs), PROD for production",
        pattern="^(MOCK|PROD)$",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://pei_user:pei_pass@localhost:5432/pei_db",
        description="PostgreSQL async connection URL for SQLAlchemy",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LangChain LLM integration (GPT-4)",
    )

    # Telegram Configuration
    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token for sending notifications to technical teams",
    )

    # SMTP Configuration for Email Notifications
    smtp_host: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname for sending emails",
    )

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port number",
    )

    smtp_user: Optional[str] = Field(
        default=None,
        description="SMTP authentication username (optional)",
    )

    smtp_password: Optional[str] = Field(
        default=None,
        description="SMTP authentication password (optional)",
    )

    # Mock API Configuration
    mock_api_latency_ms: int = Field(
        default=500,
        ge=0,
        description="Simulated latency in milliseconds for mock API calls to test loading states",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Python logging level",
    )

    class Config:
        """Pydantic configuration for settings."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_mock_mode(self) -> bool:
        """
        Check if system is running in MOCK mode.
        
        Returns:
            bool: True if SYSTEM_MODE is 'MOCK', False otherwise
        """
        return self.system_mode.upper() == "MOCK"

    @property
    def is_prod_mode(self) -> bool:
        """
        Check if system is running in PROD mode.
        
        Returns:
            bool: True if SYSTEM_MODE is 'PROD', False otherwise
        """
        return self.system_mode.upper() == "PROD"

    @validator("system_mode", pre=True)
    def validate_system_mode(cls, v: str) -> str:
        """Ensure system_mode is uppercase and valid."""
        if not v:
            return "MOCK"
        return v.upper()

    @validator("openai_api_key", pre=True, always=True)
    def validate_openai_key(cls, v: str, values):
        """
        Validate OpenAI API key based on system mode.
        
        In PROD mode, the key is required and should start with 'sk-'.
        In MOCK mode, it can be empty.
        """
        system_mode = values.get("system_mode", "MOCK").upper()
        
        # In MOCK mode, key is optional
        if system_mode == "MOCK":
            return v or "mock-key-for-development"
        
        # In PROD mode, key is required
        if not v or not v.startswith("sk-"):
            raise ValueError(
                "OPENAI_API_KEY is required in PROD mode and should start with 'sk-'"
            )
        return v

    @validator("telegram_bot_token", pre=True, always=True)
    def validate_telegram_token(cls, v: str, values):
        """
        Validate Telegram bot token based on system mode.
        
        In PROD mode with notifications enabled, token is required.
        In MOCK mode, it can be empty.
        """
        system_mode = values.get("system_mode", "MOCK").upper()
        
        # In MOCK mode, token is optional
        if system_mode == "MOCK":
            return v or "mock-telegram-token"
        
        # In PROD mode, token should be provided
        if not v:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN should be provided in PROD mode for Telegram notifications"
            )
        return v

    @validator("database_url", pre=True)
    def validate_database_url(cls, v: str) -> str:
        """
        Validate database URL format.
        
        Must be a valid async PostgreSQL connection string using asyncpg driver.
        """
        if not v:
            raise ValueError("DATABASE_URL is required")
        
        if "postgresql+asyncpg" not in v and "asyncpg" not in v:
            raise ValueError(
                "DATABASE_URL must use async PostgreSQL driver (asyncpg). "
                "Format: postgresql+asyncpg://user:pass@host:port/dbname"
            )
        
        return v

    def get_db_echo(self) -> bool:
        """
        Determine whether SQLAlchemy should echo SQL statements.
        
        Returns:
            bool: True in MOCK mode for debugging, False in PROD mode
        """
        return self.is_mock_mode

    def get_cors_origins(self) -> list[str]:
        """
        Get allowed CORS origins based on system mode.
        
        Returns:
            list[str]: List of allowed origins
        """
        if self.is_mock_mode:
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        else:
            # In PROD mode, restrict to specific domains
            return [
                "https://pei.telconet.ec",
                "https://app.telconet.ec",
            ]


@lru_cache()
def get_settings() -> Settings:
    """
    Get the singleton settings instance.
    
    Uses @lru_cache to ensure only one instance is created and reused
    throughout the application lifetime.
    
    Returns:
        Settings: The application settings singleton
    """
    return Settings()


# Export singleton instance for easy import
settings = get_settings()

