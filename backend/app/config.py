from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuration management for PEI platform"""
    
    # System Configuration
    SYSTEM_MODE: str = Field(default="MOCK", description="MOCK or PRODUCTION")
    
    # Database Configuration
    DATABASE_URL: str = Field(default="sqlite:///./pei.db", description="Database URL")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram bot token")
    
    # External API Configuration
    TELCOS_API_BASE_URL: str = Field(default="https://api.telcos.example.com", description="TELCOS API base URL")
    TELCODRIVE_API_BASE_URL: str = Field(default="https://telcodrive.example.com", description="TelcoDrive API base URL")
    
    # Email Configuration
    EMAIL_SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP host")
    EMAIL_SMTP_PORT: int = Field(default=587, description="SMTP port")
    EMAIL_FROM: str = Field(default="noreply@telconet.com", description="Email from address")
    
    # Governance Configuration
    ALERT_DETENTION_DAYS: List[int] = Field(default=[20, 25, 29], description="Days to alert for detained OTs")
    AUTO_CANCEL_DAYS: int = Field(default=30, description="Days before auto-cancelling detained OTs")
    PREPLANNED_ALERT_HOURS: int = Field(default=48, description="Hours before alerting for preplanificada timeout")
    PROXIMITY_RADIUS_KM: float = Field(default=10.0, description="Proximity radius in kilometers for crew assignment")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return singleton Settings instance"""
    return Settings()

