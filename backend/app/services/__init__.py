"""
Services module for PEI Agentic Platform.
Provides background job scheduling and management.

Exported components:
- start_scheduler: Initialize and start background scheduler
- shutdown_scheduler: Gracefully stop background scheduler
- get_scheduler: Get singleton scheduler instance
"""

from app.services.scheduler import (
    get_scheduler,
    shutdown_scheduler,
    start_scheduler,
)

__all__ = [
    "start_scheduler",
    "shutdown_scheduler",
    "get_scheduler",
]

