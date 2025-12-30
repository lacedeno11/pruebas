# API Gateway Service

FastAPI-based API Gateway for DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- JWT validation and RBAC routing
- Request proxying to internal services using httpx
- Correlation-ID propagation
- Rate limiting and request size limits
- Basic health checks

## Endpoints

- `GET /healthz` - Health check
- `GET /auth/me` - Token validation and user claims
- Proxy routes to all internal services

## Configuration

See `.env.example` for required environment variables.

## Development

```bash
cd apps/api-gateway
python -m uvicorn main:app --reload --port 8000
```
