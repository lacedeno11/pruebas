"""
FastAPI dependency injection functions.
Provides database session, settings, and service instances to route handlers.
"""

from fastapi import Depends

from backend.config import Settings
from backend.config.database import get_db
from backend.services import TelcosClient


def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings instance with environment configuration
    """
    return Settings()


async def get_telcos_client(
    settings: Settings = Depends(get_settings),
) -> TelcosClient:
    """
    Get TelcosClient instance for API integration.

    Args:
        settings: Application settings

    Returns:
        TelcosClient instance configured for mock or production mode
    """
    return TelcosClient(settings)


__all__ = ["get_db", "get_settings", "get_telcos_client"]

