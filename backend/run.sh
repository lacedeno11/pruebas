#!/bin/bash

# DERCAS PEI Backend - Development Server Startup Script
#
# This script starts the DERCAS PEI backend server with database migrations.
#
# Prerequisites:
# - Python 3.11+ installed
# - Dependencies installed via: pip install -r requirements.txt
# - Environment variables configured in .env file
#
# Required Environment Variables:
# - SYSTEM_MODE: 'MOCK' for development, 'PRODUCTION' for live APIs
# - DATABASE_URL: PostgreSQL connection string
# - OPENAI_API_KEY: OpenAI API key for LLM features
# - TELEGRAM_BOT_TOKEN: Telegram bot token for notifications
# - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD: Email configuration
# - FRONTEND_URL: Frontend application URL (for CORS)
#
# Usage:
#   ./run.sh                    # Start with environment from .env
#   SYSTEM_MODE=MOCK ./run.sh   # Override SYSTEM_MODE for development
#   SYSTEM_MODE=PRODUCTION ./run.sh  # Start in production mode
#
# Notes:
# - The script automatically runs pending database migrations
# - Development server runs with --reload for hot reloading
# - Logs are sent to stdout with 'info' level
# - Press Ctrl+C to stop the server
#

set -e  # Exit on any error

echo "================================================================================"
echo "🚀 Starting DERCAS PEI Backend"
echo "================================================================================"

# Display current environment settings
echo ""
echo "Configuration:"
echo "  System Mode: ${SYSTEM_MODE:-MOCK}"
echo "  Database: ${DATABASE_URL:-not configured}"
echo "  Frontend URL: ${FRONTEND_URL:-http://localhost:5173}"
echo ""

# Check if we're in the backend directory, if not, navigate there
if [ ! -f "app/main.py" ]; then
    echo "⚠️  app/main.py not found in current directory"
    echo "Attempting to navigate to backend directory..."
    cd backend
    if [ ! -f "app/main.py" ]; then
        echo "❌ Error: Could not find backend/app/main.py"
        echo "Please run this script from the backend directory or repository root"
        exit 1
    fi
fi

# Run database migrations
echo "📦 Running database migrations..."
python -m alembic upgrade head
echo "✓ Database migrations completed"
echo ""

# Start the development server
echo "🔧 Starting DERCAS PEI Backend Server..."
echo "   Host: 0.0.0.0"
echo "   Port: 8000"
echo "   Documentation: http://localhost:8000/api/v1/docs"
echo "   ReDoc: http://localhost:8000/api/v1/redoc"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================================================"
echo ""

# Start Uvicorn with development settings
python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info

# This line is only reached if the server stops
echo ""
echo "================================================================================"
echo "🛑 DERCAS PEI Backend Server Stopped"
echo "================================================================================"

