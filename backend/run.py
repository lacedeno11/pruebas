"""
Uvicorn runner script for PEI Platform backend.
Entry point for running the FastAPI application development server.

Usage:
    python backend/run.py

This script starts the FastAPI application with uvicorn using:
    - Host: 0.0.0.0 (accessible from all network interfaces)
    - Port: 8000 (default FastAPI port)
    - Reload: True (auto-reload on code changes for development)
"""

import uvicorn
from backend.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    # Run the FastAPI application with uvicorn
    uvicorn.run(
        "backend.api.main:app",  # Path to FastAPI app
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,  # Default FastAPI port
        reload=True,  # Auto-reload on code changes (development)
        log_level="info",  # Log level: debug, info, warning, error, critical
    )

