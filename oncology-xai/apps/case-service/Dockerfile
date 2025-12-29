FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/common /packages/common
COPY packages/event-contracts /packages/event-contracts

RUN pip install --no-cache-dir /packages/common /packages/event-contracts

COPY apps/case-service/pyproject.toml apps/case-service/README.md* ./
COPY apps/case-service/src ./src
COPY apps/case-service/alembic ./alembic
COPY apps/case-service/alembic.ini ./

RUN pip install --no-cache-dir -e .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["uvicorn", "case_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
