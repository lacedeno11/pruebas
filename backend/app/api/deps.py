"""
FastAPI Dependencies Module

This module provides dependency injection functions for FastAPI endpoints.
Dependencies are reusable components that can be injected into route handlers
to reduce code duplication and enable consistent configuration.

Available Dependencies:
    - get_db_session: Provides AsyncSession for database operations
    - get_api_client: Provides appropriate API service (Mock or Production)

Usage in Route Handlers:
    @router.get("/items")
    async def get_items(
        db: AsyncSession = Depends(get_db_session),
        api_client = Depends(get_api_client)
    ):
        # Use db and api_client in handler
        ...

Benefits:
    - Single point of configuration for database sessions
    - Seamless switching between Mock and Production APIs
    - Automatic resource cleanup via FastAPI's dependency system
    - Type-safe dependency injection
    - Easy to mock in tests
"""

from typing import AsyncGenerator, Union

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.api_factory import get_api_service
from app.services.mock_api_service import MockApiService
from app.services.telcos_api_service import TelcosApiService


# ============================================================================
# Database Session Dependency
# ============================================================================


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides database session for route handlers.
    
    This is an alias/wrapper around app.core.database.get_db() that provides
    a consistent AsyncSession for all database operations in endpoints.
    
    The session is automatically:
    - Created at the start of the request
    - Committed on success
    - Rolled back on error
    - Closed at the end of the request
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Yields:
        AsyncSession: Database session for the request
        
    Raises:
        Exception: Any database operation error
    """
    async for session in get_db():
        yield session


# ============================================================================
# API Service Client Dependency
# ============================================================================


def get_api_client() -> Union[MockApiService, TelcosApiService]:
    """
    FastAPI dependency that provides appropriate API service client.
    
    Returns the correct API service based on SYSTEM_MODE configuration:
    - 'MOCK': Returns MockApiService for development/testing
    - 'PRODUCTION': Returns TelcosApiService for live APIs
    
    This enables seamless switching between mock and production without
    changing endpoint code. All endpoints use the same interface.
    
    Configuration:
        settings.SYSTEM_MODE: 'MOCK' or 'PRODUCTION' (from environment)
    
    Usage:
        @router.post("/sync-ots")
        async def sync_ots(api_client = Depends(get_api_client)):
            # api_client automatically selected based on SYSTEM_MODE
            ots = await api_client.get_ots_from_telcos()
            return {"ingested": len(ots)}
    
    Returns:
        MockApiService: If settings.SYSTEM_MODE == 'MOCK'
        TelcosApiService: Otherwise
        
    Example:
        # In development (SYSTEM_MODE=MOCK)
        api_client = get_api_client()  # Returns MockApiService instance
        
        # In production (SYSTEM_MODE=PRODUCTION)
        api_client = get_api_client()  # Returns TelcosApiService instance
        
        # Same code works in both modes!
    """
    return get_api_service(settings.SYSTEM_MODE)


# ============================================================================
# Combined Dependency for Common Use Case
# ============================================================================


async def get_db_and_api(
    db: AsyncSession = Depends(get_db_session),
    api_client: Union[MockApiService, TelcosApiService] = Depends(get_api_client),
) -> tuple[AsyncSession, Union[MockApiService, TelcosApiService]]:
    """
    Combined dependency providing both database session and API client.
    
    This is a convenience dependency for handlers that need both database
    access and external API access in a single function.
    
    Usage:
        @router.post("/ingest-ots")
        async def ingest_ots(
            deps: tuple[AsyncSession, Union[MockApiService, TelcosApiService]]
            = Depends(get_db_and_api)
        ):
            db, api_client = deps
            # Use both db and api_client
            ots = await api_client.get_ots_from_telcos()
            # Save to database...
            await db.commit()
    
    Args:
        db: Database session (from get_db_session)
        api_client: API service client (from get_api_client)
    
    Returns:
        Tuple of (AsyncSession, API service client)
    """
    return (db, api_client)


# ============================================================================
# Configuration Info Dependency
# ============================================================================


def get_system_info() -> dict:
    """
    FastAPI dependency providing system configuration information.
    
    Useful for endpoints that need to know current system configuration
    (e.g., health check endpoints that report MOCK vs PRODUCTION mode).
    
    Usage:
        @router.get("/health")
        async def health_check(info: dict = Depends(get_system_info)):
            return {
                "status": "ok",
                "mode": info.get("system_mode"),
                "database": info.get("database_configured")
            }
    
    Returns:
        Dict with system configuration details:
        - system_mode: 'MOCK' or 'PRODUCTION'
        - database_configured: Whether DATABASE_URL is set
        - frontend_url: Frontend application URL
        - backend_url: Backend API URL
    """
    return {
        "system_mode": settings.SYSTEM_MODE,
        "database_configured": bool(settings.DATABASE_URL),
        "frontend_url": settings.FRONTEND_URL,
        "backend_url": settings.BACKEND_URL,
        "project_name": settings.PROJECT_NAME,
    }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "get_db_session",
    "get_api_client",
    "get_db_and_api",
    "get_system_info",
]

