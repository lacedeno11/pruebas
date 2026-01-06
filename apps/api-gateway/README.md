# API Gateway Service

FastAPI-based API Gateway with JWT validation, RBAC enforcement, and request routing.

## Features

- JWT validation with Keycloak JWKS
- RBAC enforcement (clinician/admin/auditor roles)
- Request routing to internal services using httpx
- Correlation-id propagation
- Rate limiting and request size limits
- OpenAPI documentation
- Security middleware for OWASP protection

## Endpoints

- `GET /healthz` - Health check
- `GET /auth/me` - Token validation and user claims

## Development

```bash
cd apps/api-gateway
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8080
```
