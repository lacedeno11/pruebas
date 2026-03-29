"""
API Factory: Provides mode-based selection between Mock and Production TELCOS APIs.

This factory pattern enables seamless switching between:
- MockApiService: For development and testing (SYSTEM_MODE='MOCK')
- TelcosApiService: For production with real external APIs (SYSTEM_MODE='PRODUCTION')

Both services implement the same interface, allowing transparent switching
without modifying client code.
"""

from typing import Union

from app.services.mock_api_service import MockApiService
from app.services.telcos_api_service import TelcosApiService


# Lazy-loaded singletons to avoid unnecessary instantiation
_mock_service_instance: MockApiService | None = None
_telcos_service_instance: TelcosApiService | None = None


def get_api_service(system_mode: str = "MOCK") -> Union[MockApiService, TelcosApiService]:
    """
    Factory function to get the appropriate API service based on system mode.
    
    Implements lazy initialization and singleton pattern to avoid
    creating multiple instances of the same service.
    
    Args:
        system_mode: System mode from configuration ('MOCK' or 'PRODUCTION')
                    Defaults to 'MOCK' for development
    
    Returns:
        MockApiService instance if system_mode == 'MOCK'
        TelcosApiService instance otherwise
        
    Example:
        >>> from app.core.config import settings
        >>> api_service = get_api_service(settings.SYSTEM_MODE)
        >>> ots = await api_service.get_ots_from_telcos()
    """
    global _mock_service_instance, _telcos_service_instance

    if system_mode == "MOCK":
        # Lazy initialization of MockApiService singleton
        if _mock_service_instance is None:
            _mock_service_instance = MockApiService()
        return _mock_service_instance

    else:
        # Production mode: return TelcosApiService
        # Lazy initialization of TelcosApiService singleton
        if _telcos_service_instance is None:
            _telcos_service_instance = TelcosApiService()
        return _telcos_service_instance


async def get_api_service_async(
    system_mode: str = "MOCK",
) -> Union[MockApiService, TelcosApiService]:
    """
    Async factory function to get the appropriate API service.
    
    Provides async context for potential future async initialization
    requirements (e.g., database connection pooling for TelcosApiService).
    
    Args:
        system_mode: System mode from configuration ('MOCK' or 'PRODUCTION')
        
    Returns:
        Union[MockApiService, TelcosApiService]
    """
    # Currently same as synchronous version, but provides
    # forward compatibility for async initialization
    return get_api_service(system_mode)


def reset_singletons() -> None:
    """
    Reset service singletons.
    
    Useful for testing to ensure clean state between test cases.
    This function should be called during test teardown.
    
    Example:
        >>> # In pytest fixture
        >>> @pytest.fixture(autouse=True)
        >>> def cleanup():
        >>>     yield
        >>>     reset_singletons()
    """
    global _mock_service_instance, _telcos_service_instance
    _mock_service_instance = None
    _telcos_service_instance = None

