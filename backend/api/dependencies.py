"""Dependency Injection Functions for FastAPI"""

from fastapi import Depends
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.database.session import get_db as get_db_session
from backend.services.telcos_service import TelcosService
from backend.services.notification_service import NotificationService
from backend.config.settings import settings


# Re-export get_db from session.py for convenience
def get_db() -> Session:
    """
    Get database session.

    Yields:
        SQLAlchemy database session
    """
    return get_db_session()


def get_telcos_service(db: Session = Depends(get_db)) -> TelcosService:
    """
    Get TELCOS API service instance.

    Args:
        db: Database session from dependency injection

    Returns:
        TelcosService instance
    """
    return TelcosService()


def get_notification_service() -> NotificationService:
    """
    Get notification service instance.

    Returns:
        NotificationService instance
    """
    return NotificationService()


def get_llm_client() -> ChatOpenAI:
    """
    Get LLM (ChatOpenAI) client instance.

    Returns:
        ChatOpenAI instance configured with settings
    """
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        max_tokens=2048,
    )


def get_current_user():
    """
    Get current authenticated user (placeholder for future authentication).

    Returns:
        Mock user object for development
    """
    return {
        "user_id": "dev-user-001",
        "username": "developer",
        "role": "admin",
        "email": "dev@example.com",
    }

