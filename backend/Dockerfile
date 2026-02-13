# Use official Python 3.13 runtime as base image
FROM python:3.13-slim

# Set environment variables
# PYTHONUNBUFFERED: Ensures Python output is sent straight to logs without buffering
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory inside container
WORKDIR /app

# Install system dependencies required by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy application code
# Copy entire app directory (includes all models, services, agents, etc.)
COPY app/ ./app/

# Copy alembic directory and configuration for database migrations
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create a non-root user for security (optional but recommended)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 8000 for FastAPI application
EXPOSE 8000

# Health check to ensure application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command to run the application
# Can be overridden when running the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

