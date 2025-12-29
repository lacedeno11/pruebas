#!/bin/bash

# Audit Service Runner Script

set -e

echo "========================================="
echo "Audit Service Setup and Runner"
echo "========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please update .env with your configuration"
fi

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service to be ready..."
    while ! nc -z $host $port; do
        if [ $attempt -eq $max_attempts ]; then
            echo "Error: $service not available after $max_attempts attempts"
            exit 1
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "$service is ready!"
}

# Parse command line arguments
case "${1:-dev}" in
    install)
        echo "Installing dependencies..."
        poetry install
        ;;

    setup)
        echo "Setting up development environment..."
        docker-compose up -d postgres rabbitmq
        wait_for_service localhost 5432 "PostgreSQL"
        wait_for_service localhost 5672 "RabbitMQ"
        echo "Running migrations..."
        poetry run alembic upgrade head
        echo "Setup complete!"
        ;;

    dev)
        echo "Starting development server..."
        poetry run uvicorn app.main:app --host 0.0.0.0 --port 8007 --reload
        ;;

    docker)
        echo "Starting all services with Docker Compose..."
        docker-compose up --build
        ;;

    migrate)
        echo "Running database migrations..."
        poetry run alembic upgrade head
        ;;

    test)
        echo "Running tests..."
        poetry run pytest
        ;;

    lint)
        echo "Running linters..."
        poetry run ruff check app/
        poetry run mypy app/
        ;;

    format)
        echo "Formatting code..."
        poetry run black app/
        poetry run ruff check --fix app/
        ;;

    clean)
        echo "Cleaning up..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        find . -type f -name "*.pyo" -delete
        rm -rf .pytest_cache htmlcov .coverage
        echo "Cleanup complete!"
        ;;

    *)
        echo "Usage: $0 {install|setup|dev|docker|migrate|test|lint|format|clean}"
        echo ""
        echo "Commands:"
        echo "  install - Install dependencies with Poetry"
        echo "  setup   - Setup development environment (DB + RabbitMQ)"
        echo "  dev     - Run development server"
        echo "  docker  - Run with Docker Compose"
        echo "  migrate - Run database migrations"
        echo "  test    - Run tests"
        echo "  lint    - Run linters"
        echo "  format  - Format code"
        echo "  clean   - Clean cache files"
        exit 1
        ;;
esac
