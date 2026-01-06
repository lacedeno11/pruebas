# Common Package

Shared utilities and models for DERCAS-ONCO-XAI V1 platform.

## Contents

### Pydantic v2 Models
- `Patient` - Patient demographic and clinical data
- `Case` - Clinical case information and status
- `Image` - Histopathological image metadata
- `ResultBundle` - ML inference results and XAI artifacts
- `EHRDocument` - Electronic health record document
- `OntologyMapping` - Entity to ontology concept mappings

### Authentication Utilities
- JWT validation with Keycloak JWKS
- Role-based access control (RBAC) helpers
- User context and permissions management

### Middleware
- Correlation-ID propagation
- Request/response logging
- Error handling and standardization

### Error Schemas
- Standardized error response format
- Clinical error codes and messages
- Validation error handling

## Usage

```python
from packages.common.models import Patient, Case, Image
from packages.common.auth import validate_jwt, get_user_context
from packages.common.middleware import correlation_id_middleware
from packages.common.errors import StandardError, ErrorCode
```

## Development

This package is shared across all services in the platform.
