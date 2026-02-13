from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # System Mode
    SYSTEM_MODE: str = Field(default="MOCK", description="MOCK or PRODUCTION")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./pei.db",
        description="Database connection URL"
    )

    # OpenAI
    OPENAI_API_KEY: str = Field(
        default="sk-your-key-here",
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4",
        description="OpenAI model to use"
    )

    # External APIs
    TELCOS_API_BASE_URL: str = Field(
        default="https://api.telconet.ec",
        description="TELCOS API base URL"
    )
    TELCOS_API_KEY: str = Field(
        default="your-telcos-key",
        description="TELCOS API authentication key"
    )
    TELCODRIVE_API_URL: str = Field(
        default="https://drive.telconet.ec/api",
        description="TelcoDrive API URL for document management"
    )

    # Notifications
    TELEGRAM_BOT_TOKEN: str = Field(
        default="your-bot-token",
        description="Telegram bot token for notifications"
    )
    TELEGRAM_COORDINADOR_CHAT_ID: str = Field(
        default="123456789",
        description="Telegram chat ID for coordinator notifications"
    )
    SMTP_HOST: str = Field(
        default="smtp.gmail.com",
        description="SMTP server host"
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port"
    )
    SMTP_USER: str = Field(
        default="noreply@telconet.ec",
        description="SMTP user email"
    )
    SMTP_PASSWORD: str = Field(
        default="your-password",
        description="SMTP user password"
    )
    EMAIL_FROM: str = Field(
        default="PEI System <noreply@telconet.ec>",
        description="Default sender email address"
    )

    # Business Rules
    MAX_DISTANCE_KM: float = Field(
        default=10.0,
        description="Maximum distance in km for cuadrilla assignment"
    )
    AUTO_CANCEL_DAYS: int = Field(
        default=30,
        description="Days before auto-cancelling inactive OTs"
    )
    ALERT_DAYS: List[int] = Field(
        default=[20, 25, 29],
        description="Days to send alerts for inactive OTs"
    )
    INACTIVITY_ALERT_HOURS: int = Field(
        default=48,
        description="Hours of inactivity before PREPLANIFICADA alert"
    )
    MOCK_LATENCY_MS: int = Field(
        default=500,
        description="Simulated latency for mock API calls in milliseconds"
    )

    # Server
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    PORT: int = Field(
        default=8000,
        description="Server port"
    )
    WORKERS: int = Field(
        default=4,
        description="Number of worker processes"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @field_validator("ALERT_DAYS", mode="before")
    @classmethod
    def parse_alert_days(cls, v):
        """Parse ALERT_DAYS from comma-separated string or list"""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",")]
        return v

    @field_validator("SYSTEM_MODE")
    @classmethod
    def validate_system_mode(cls, v):
        """Validate SYSTEM_MODE is either MOCK or PRODUCTION"""
        if v not in ("MOCK", "PRODUCTION"):
            raise ValueError(f"SYSTEM_MODE must be 'MOCK' or 'PRODUCTION', got '{v}'")
        return v


# Global settings instance
settings = Settings()

