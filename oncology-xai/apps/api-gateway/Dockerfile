FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared packages first
COPY packages/common /packages/common
COPY packages/event-contracts /packages/event-contracts

# Install shared packages
RUN pip install --no-cache-dir /packages/common /packages/event-contracts

# Copy application
COPY apps/api-gateway/pyproject.toml apps/api-gateway/README.md* ./
COPY apps/api-gateway/src ./src

# Install application
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
