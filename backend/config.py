"""
Configuration management for PEI Platform backend.
Uses pydantic-settings to load configuration from environment variables.
"""

from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Default values are provided for development, but all critical
    values should be configured via .env file for production.
    """
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./pei.db"
    
    # System Mode
    SYSTEM_MODE: str = "MOCK"  # MOCK or PRODUCTION
    
    # LLM Configuration
    OPENAI_API_KEY: str = ""
    
    # Geographic Constraints
    MAX_DISTANCE_KM: float = 10.0
    
    # Cuadrilla Configuration
    CUADRILLA_DAILY_CAPACITY: int = 5
    
    # Governance Configuration
    INACTIVITY_THRESHOLD_HOURS: int = 48
    CANCELLATION_THRESHOLD_DAYS: int = 30
    ALERT_DAYS: List[int] = [20, 25, 29]
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Email Configuration
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of Settings.
    
    This function is cached to ensure only one Settings instance
    is created and reused throughout the application lifetime.
    """
    return Settings()

