# Policy Validation Copilot - Multi-stage Production Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -r app && useradd -r -g app app

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY pyproject.toml .
COPY README.md .

# Install the package
RUN pip install -e .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/storage /app/data /app/tmp && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default expose port
EXPOSE 8000

# API Server Stage
FROM base as api-server
LABEL service="policy-copilot-api"
EXPOSE 8000
CMD ["uvicorn", "policy_copilot.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Worker Stage
FROM base as worker
LABEL service="policy-copilot-worker"
CMD ["python", "-m", "policy_copilot.worker.main"]

# Scheduler Stage  
FROM base as scheduler
LABEL service="policy-copilot-scheduler"
CMD ["python", "-m", "policy_copilot.scheduler.main"]

# ML Services Stage
FROM base as ml-services
LABEL service="policy-copilot-ml"
EXPOSE 8001
CMD ["uvicorn", "policy_copilot.ml_services.api:app", "--host", "0.0.0.0", "--port", "8001"]

# Default stage (API Server)
FROM api-server as default

