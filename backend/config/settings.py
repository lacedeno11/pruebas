"""
Application settings using Pydantic BaseSettings.
Configuration is loaded from environment variables and .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings for PEI Platform.
    Loads configuration from environment variables and .env file.
    """

    # Database Configuration
    database_url: str = "sqlite:///./pei_platform.db"

    # System Mode: 'MOCK' for development, 'PRODUCTION' for live
    system_mode: str = "PRODUCTION"

    # LLM Configuration (OpenAI)
    openai_api_key: str = ""

    # Telegram Bot Token for notifications
    telegram_bot_token: str = ""

    # SMTP Configuration for email notifications
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Mock API Latency (milliseconds) - simulates API response time
    mock_api_latency_ms: int = 500

    # Logging Level
    log_level: str = "INFO"

    class Config:
        """Configuration for BaseSettings."""

        env_file = ".env"
        case_sensitive = False

