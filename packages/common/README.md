# Common Package

Shared utilities, models, and middleware for the DERCAS-ONCO-XAI platform.

## Features

- JWT authentication utilities (JWKS verification with Keycloak)
- Correlation-id middleware
- Standardized error schemas
- Shared Pydantic models (Patient, Case, Image, ResultBundle, EHRDocument, etc.)
- Common database utilities
- Logging configuration
- Security utilities

## Components

### Authentication
- JWT token validation
- JWKS key retrieval and caching
- Role-based access control utilities
- User context management

### Models
- Patient and Case models
- Image and ResultBundle models
- EHR document models
- Audit event models
- Error response models

### Middleware
- Correlation ID propagation
- Request/response logging
- Error handling
- Security headers

### Utilities
- Database connection management
- Configuration loading
- Validation helpers
- Date/time utilities

## Usage

```python
from packages.common.auth import verify_jwt_token
from packages.common.models import Patient, Case
from packages.common.middleware import correlation_id_middleware
```
