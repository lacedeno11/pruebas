"""
API Service Factory for PEI Platform.

This module provides a factory function to return the appropriate API service
based on system mode (MOCK or PROD). This allows agents to work with either
the mock service (for development/testing) or the real Telcos API (production).

Factory Pattern: Provides abstraction layer for API integration.
"""

import logging

from src.config.settings import settings
from src.services.mock_api_service import MockApiService
from src.services.telcos_api_service import TelcosApiService

logger = logging.getLogger(__name__)


def get_api_service() -> MockApiService | TelcosApiService:
    """
    Factory function to get the appropriate API service instance.

    Returns the correct API service based on SYSTEM_MODE setting:
    - MOCK mode: Returns MockApiService for development/testing
    - PROD mode: Returns TelcosApiService for production (real API calls)

    Both services implement the same interface:
    - async get_ots() -> list[dict]
    - async update_status(ot_external_id: str, new_status: str) -> dict
    - async get_telcodrive_documents(ot_external_id: str) -> dict
    - async health_check() -> dict

    This design allows agents to work transparently with either service
    without code changes.

    Returns:
        MockApiService | TelcosApiService: The appropriate service instance
            based on settings.system_mode

    Example usage in agents:
        from src.services.api_factory import get_api_service

        async def fetch_ots():
            api_service = get_api_service()
            ots = await api_service.get_ots()
            # Works with both mock and real API
            return ots

    Logging:
        - INFO: When service is initialized with mode
        - DEBUG: Service method calls and responses
    """
    if settings.is_mock_mode:
        logger.info("Initializing MockApiService (SYSTEM_MODE=MOCK)")
        return MockApiService()
    else:
        logger.info("Initializing TelcosApiService (SYSTEM_MODE=PROD)")
        return TelcosApiService()


# Convenience function to check current mode
def is_mock_mode() -> bool:
    """
    Check if the system is running in MOCK mode.

    Returns:
        bool: True if SYSTEM_MODE is MOCK, False otherwise
    """
    return settings.is_mock_mode


# Convenience function to get mode name
def get_current_mode() -> str:
    """
    Get the current system mode.

    Returns:
        str: The current SYSTEM_MODE setting (MOCK or PROD)
    """
    return settings.system_mode

