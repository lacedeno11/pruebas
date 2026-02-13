from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # System Configuration
    SYSTEM_MODE: str = "MOCK"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./pei.db"

    # OpenAI API Configuration
    OPENAI_API_KEY: str = ""

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = ""

    # SMTP Configuration (Email)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # JWT Security
    JWT_SECRET: str = "change_this_secret"

    # CORS Origins (comma-separated)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Create a singleton instance of settings
settings = Settings()

