"""
Application entry point for PEI Platform.
Loads settings, configures logging, and starts the FastAPI server.
"""

import uvicorn

from backend.config import Settings
from backend.utils.logging_helper import setup_logging

if __name__ == "__main__":
    # Load settings from environment
    settings = Settings()

    # Setup logging
    setup_logging(settings.log_level)

    # Determine if reload should be enabled (useful for MOCK mode development)
    reload = settings.system_mode.upper() == "MOCK"

    # Run the application
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        log_level=settings.log_level.lower(),
    )

