"""Main application runner for PEI Agéntico platform."""

import uvicorn
import os
import sys
import logging
import signal
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """Handle graceful shutdown on SIGINT (Ctrl+C)."""
    logger.info("Shutdown signal received, shutting down gracefully...")
    sys.exit(0)


def start_scheduler():
    """Start the governance scheduler in a background thread."""
    try:
        from backend.scheduler.governance_scheduler import run_scheduler
        logger.info("Starting governance scheduler...")
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Governance scheduler started in background thread")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def main():
    """Main entry point for the application."""
    # Log startup information
    logger.info(f"Python version: {sys.version}")
    system_mode = os.getenv("SYSTEM_MODE", "MOCK")
    logger.info(f"System mode: {system_mode}")
    logger.info(f"Database URL: {os.getenv('DATABASE_URL', 'sqlite:///./pei.db')}")
    logger.info(f"LLM Model: {os.getenv('LLM_MODEL', 'gpt-4')}")
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start scheduler if enabled (optional based on configuration)
    # Uncomment to enable scheduler:
    # start_scheduler()
    
    # Run FastAPI application with uvicorn
    logger.info("Starting FastAPI application on http://0.0.0.0:8000")
    uvicorn.run(
        app="backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable hot-reload for development
        log_level="info",
    )


if __name__ == "__main__":
    main()

