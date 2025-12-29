FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY packages/common /packages/common
COPY packages/event-contracts /packages/event-contracts
RUN pip install --no-cache-dir /packages/common /packages/event-contracts

COPY apps/image-service/pyproject.toml apps/image-service/README.md* ./
COPY apps/image-service/src ./src
COPY apps/image-service/alembic ./alembic
COPY apps/image-service/alembic.ini ./

RUN pip install --no-cache-dir -e .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8002

CMD ["uvicorn", "image_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
