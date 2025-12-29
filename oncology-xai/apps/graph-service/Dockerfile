FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/common /packages/common
COPY packages/event-contracts /packages/event-contracts
COPY packages/langgraph-workflows /packages/langgraph-workflows

RUN pip install --no-cache-dir /packages/common /packages/event-contracts /packages/langgraph-workflows

COPY apps/graph-service/pyproject.toml apps/graph-service/README.md* ./
COPY apps/graph-service/src ./src
COPY apps/graph-service/alembic ./alembic
COPY apps/graph-service/alembic.ini ./

RUN pip install --no-cache-dir -e .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8005

CMD ["uvicorn", "graph_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
