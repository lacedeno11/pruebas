# API Gateway Service

FastAPI-based API Gateway for the DERCAS-ONCO-XAI V1 platform.

## Overview

The API Gateway serves as the single entry point for all client requests to the oncology platform. It provides:

- **JWT Authentication**: Token validation with Keycloak JWKS
- **Role-Based Access Control (RBAC)**: Permission-based routing
- **Request Proxying**: Intelligent routing to internal microservices
- **Rate Limiting**: Configurable rate limits per user/role
- **Health Monitoring**: Service health checks and status endpoints
- **Correlation ID Propagation**: Distributed tracing support
- **OpenAPI Documentation**: Auto-generated API documentation

## Features

### Authentication & Authorization
- JWT token validation with Keycloak JWKS
- Role-based permissions (clinician, admin, auditor)
- Route-specific permission requirements
- User context propagation to downstream services

### Request Routing
- Intelligent proxy to internal services
- Service health checking with circuit breaker pattern
- Automatic retry with exponential backoff
- Header propagation and transformation

### Rate Limiting
- Per-user and per-role rate limits
- Endpoint-specific limits
- Burst protection
- Rate limit headers in responses

### Monitoring & Health
- `/healthz` - Basic health check
- `/health` - Detailed service status
- `/api/v1/auth/me` - Current user info
- Service dependency health monitoring

## Configuration

The gateway is configured via environment variables:

```bash
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=RS256

# Keycloak
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=oncology-xai
KEYCLOAK_CLIENT_ID=api-gateway

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Service URLs
CASE_SERVICE_URL=http://case-service:8001
IMAGE_SERVICE_URL=http://image-service:8002
INFERENCE_SERVICE_URL=http://inference-service:8003
EHR_SERVICE_URL=http://ehr-service:8004
GRAPH_SERVICE_URL=http://graph-service:8005
ONTOLOGY_ADMIN_SERVICE_URL=http://ontology-admin-service:8006
AUDIT_SERVICE_URL=http://audit-service:8007

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## API Routes

### Health Endpoints
- `GET /healthz` - Basic health check
- `GET /health` - Detailed health with service status
- `GET /api/v1/health` - Authenticated health endpoint
- `GET /api/v1/auth/me` - Current user information
- `GET /api/v1/auth/health` - Authentication system health

### Proxied Routes
All `/api/v1/*` routes are proxied to appropriate services:

- `/api/v1/patients/*` → Case Service
- `/api/v1/cases/*` → Case Service
- `/api/v1/images/*` → Image Service
- `/api/v1/inference/*` → Inference Service
- `/api/v1/jobs/*` → Inference Service
- `/api/v1/ehr/*` → EHR Service
- `/api/v1/graph/*` → Graph Service
- `/api/v1/ontology/*` → Ontology Admin Service
- `/api/v1/audit/*` → Audit Service

## Development

### Running Locally

```bash
# Install dependencies
pip install -e .

# Run with uvicorn
uvicorn src.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# Or use the Makefile from project root
make gateway-dev
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src/api_gateway tests/

# Lint code
ruff check src/ tests/
black src/ tests/
mypy src/
```

### Docker

```bash
# Build image
docker build -t oncology-xai-api-gateway .

# Run container
docker run -p 8000:8000 --env-file .env oncology-xai-api-gateway
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │  Mobile Client  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────────┐
          │    API Gateway      │
          │  - Authentication   │
          │  - Authorization    │
          │  - Rate Limiting    │
          │  - Request Routing  │
          └─────────┬───────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼───┐    ┌─────▼─────┐    ┌───▼───┐
│ Case  │    │   Image   │    │  EHR  │
│Service│    │  Service  │    │Service│
└───────┘    └───────────┘    └───────┘
```

## Security

### JWT Validation
- Validates JWT tokens against Keycloak JWKS endpoint
- Caches JWKS keys with configurable TTL
- Supports RS256 algorithm
- Extracts user roles and permissions

### RBAC Implementation
- **Clinician**: Read/write access to patients, cases, images, EHR
- **Admin**: Full access including ontology management
- **Auditor**: Read access to all data plus audit write access

### Rate Limiting
- Anonymous users: 50 requests/minute
- Authenticated users: 200 requests/minute
- Clinicians: 300 requests/minute
- Admins: 500 requests/minute
- Auditors: 100 requests/minute

### Security Headers
- CORS configuration
- Correlation ID propagation
- User context headers for downstream services

## Monitoring

### Health Checks
The gateway monitors all downstream services and provides health status:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "services": [
    {
      "name": "case",
      "url": "http://case-service:8001",
      "status": "healthy",
      "response_time_ms": 45.2,
      "last_check": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### Logging
Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "info",
  "message": "Request completed",
  "method": "GET",
  "path": "/api/v1/cases",
  "status_code": 200,
  "duration_ms": 123.45,
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef",
  "user_id": "user123"
}
```

### Metrics
- Request count and duration
- Rate limit violations
- Service health status
- Error rates by endpoint

## Error Handling

The gateway provides consistent error responses:

```json
{
  "error": "Authentication failed",
  "message": "Invalid token: Token has expired",
  "correlation_id": "01234567-89ab-cdef-0123-456789abcdef"
}
```

Error types:
- `401 Unauthorized` - Authentication failures
- `403 Forbidden` - Authorization failures
- `422 Unprocessable Entity` - Validation errors
- `429 Too Many Requests` - Rate limit exceeded
- `502 Bad Gateway` - Service unavailable
- `504 Gateway Timeout` - Service timeout

## Production Deployment

### Environment Variables
Set all required environment variables in production:

```bash
# Security
SECRET_KEY=<strong-secret-key>
KEYCLOAK_URL=https://auth.yourdomain.com
JWKS_URL=https://auth.yourdomain.com/realms/oncology-xai/protocol/openid_connect/certs

# Services
CASE_SERVICE_URL=http://case-service:8001
# ... other service URLs

# CORS
CORS_ORIGINS=https://app.yourdomain.com

# Rate limiting
RATE_LIMIT_ENABLED=true
```

### Health Checks
Configure load balancer health checks:
- Path: `/healthz`
- Expected status: `200`
- Timeout: `5s`
- Interval: `30s`

### Scaling
The gateway is stateless and can be horizontally scaled:
- Use Redis for rate limiting state (if needed)
- Configure load balancer with session affinity (if needed)
- Monitor response times and error rates

## Troubleshooting

### Common Issues

1. **Authentication failures**
   - Check Keycloak connectivity
   - Verify JWKS endpoint accessibility
   - Validate JWT token format

2. **Service unavailable errors**
   - Check downstream service health
   - Verify service URLs in configuration
   - Check network connectivity

3. **Rate limit issues**
   - Review rate limit configuration
   - Check user roles and permissions
   - Monitor rate limit metrics

### Debug Mode
Enable debug mode for development:

```bash
DEBUG=true
```

This enables:
- Detailed error messages
- OpenAPI documentation at `/docs`
- Request/response logging
- Relaxed CORS settings
