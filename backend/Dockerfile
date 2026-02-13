# PEI Agentic Platform - Backend Dockerfile
# Multi-stage build for optimized production image

# ============================================================================
# Stage 1: Base - Install Dependencies
# ============================================================================

FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================================================
# Stage 2: Application - Copy Code and Setup
# ============================================================================

FROM base as application

# Set environment variables for Python path
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy application code from builder stage
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application source code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Build Arguments and Labels
# ============================================================================

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.authors="PEI Development Team" \
      org.opencontainers.image.url="https://github.com/lacedeno11/pruebas" \
      org.opencontainers.image.documentation="https://github.com/lacedeno11/pruebas/blob/main/backend/README.md" \
      org.opencontainers.image.source="https://github.com/lacedeno11/pruebas" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.vendor="TELCONET" \
      org.opencontainers.image.title="PEI Agentic Platform - Backend" \
      org.opencontainers.image.description="AI-powered order planning and governance platform"

