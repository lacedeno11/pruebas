"""
API module for Policy Validation Copilot.

Provides FastAPI endpoints for the validation service.
"""

from policy_validation_copilot.api.main import app, run

__all__ = ["app", "run"]
