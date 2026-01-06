# DERCAS-ONCO-XAI V1 - API Gateway Authentication
# JWT validation and RBAC implementation

import time
import httpx
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from jose.exceptions import JWKError
import structlog

from oncology_xai_common.auth import JWTValidator, UserContext
from oncology_xai_common.exceptions import AuthenticationError, AuthorizationError
from .config import Settings, get_settings

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer()


class APIGatewayAuth:
    """Authentication and authorization handler for API Gateway."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwt_validator = JWTValidator(
            jwks_url=settings.jwks_url,
            algorithm=settings.algorithm,
            cache_ttl=settings.jwks_cache_ttl
        )
        self._role_permissions = settings.get_role_permissions()
        
    async def validate_token(self, credentials: HTTPAuthorizationCredentials) -> UserContext:
        """
        Validate JWT token and return user context.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            UserContext with user information
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Validate JWT token
            payload = await self.jwt_validator.validate_token(credentials.credentials)
            
            # Extract user information
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Token missing subject")
            
            # Extract roles from token
            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            
            # Filter to only include our application roles
            app_roles = [role for role in roles if role in self._role_permissions]
            
            # Get permissions for user roles
            permissions = set()
            for role in app_roles:
                role_perms = self._role_permissions.get(role, [])
                permissions.update(role_perms)
            
            # Extract additional user information
            email = payload.get("email")
            name = payload.get("name", payload.get("preferred_username", user_id))
            session_id = payload.get("session_state")
            
            return UserContext(
                user_id=user_id,
                email=email,
                name=name,
                roles=app_roles,
                permissions=list(permissions),
                session_id=session_id,
                token_payload=payload
            )
            
        except JWTError as e:
            logger.warning("JWT validation failed", error=str(e))
            raise AuthenticationError(f"Invalid token: {e}")
        except Exception as e:
            logger.error("Token validation error", error=str(e))
            raise AuthenticationError("Token validation failed")
    
    def check_permission(self, user_context: UserContext, required_permission: str) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user_context: User context
            required_permission: Required permission string
            
        Returns:
            True if user has permission
        """
        return required_permission in user_context.permissions
    
    def check_role(self, user_context: UserContext, required_role: str) -> bool:
        """
        Check if user has required role.
        
        Args:
            user_context: User context
            required_role: Required role string
            
        Returns:
            True if user has role
        """
        return required_role in user_context.roles
    
    def require_permission(self, permission: str):
        """
        Decorator to require specific permission.
        
        Args:
            permission: Required permission
            
        Returns:
            Dependency function
        """
        async def permission_dependency(
            user_context: UserContext = Depends(self.get_current_user)
        ) -> UserContext:
            if not self.check_permission(user_context, permission):
                raise AuthorizationError(
                    f"Permission required: {permission}",
                    required_permission=permission,
                    user_permissions=user_context.permissions
                )
            return user_context
        
        return permission_dependency
    
    def require_role(self, role: str):
        """
        Decorator to require specific role.
        
        Args:
            role: Required role
            
        Returns:
            Dependency function
        """
        async def role_dependency(
            user_context: UserContext = Depends(self.get_current_user)
        ) -> UserContext:
            if not self.check_role(user_context, role):
                raise AuthorizationError(
                    f"Role required: {role}",
                    required_role=role,
                    user_roles=user_context.roles
                )
            return user_context
        
        return role_dependency
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> UserContext:
        """
        Get current authenticated user.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            UserContext for current user
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            return await self.validate_token(credentials)
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except AuthorizationError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )


# Global auth instance
_auth_instance: Optional[APIGatewayAuth] = None


def get_auth(settings: Settings = Depends(get_settings)) -> APIGatewayAuth:
    """Get authentication handler instance."""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = APIGatewayAuth(settings)
    return _auth_instance


# Convenience dependency functions
async def get_current_user(
    auth: APIGatewayAuth = Depends(get_auth),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserContext:
    """Get current authenticated user."""
    return await auth.get_current_user(credentials)


def require_permission(permission: str):
    """Require specific permission."""
    async def permission_dependency(
        auth: APIGatewayAuth = Depends(get_auth),
        user_context: UserContext = Depends(get_current_user)
    ) -> UserContext:
        if not auth.check_permission(user_context, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return user_context
    
    return permission_dependency


def require_role(role: str):
    """Require specific role."""
    async def role_dependency(
        auth: APIGatewayAuth = Depends(get_auth),
        user_context: UserContext = Depends(get_current_user)
    ) -> UserContext:
        if not auth.check_role(user_context, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        return user_context
    
    return role_dependency


# Route-specific permission requirements
ROUTE_PERMISSIONS = {
    # Patient endpoints
    "GET /api/v1/patients": "patients:read",
    "POST /api/v1/patients": "patients:write",
    "GET /api/v1/patients/{patient_id}": "patients:read",
    "PUT /api/v1/patients/{patient_id}": "patients:write",
    "DELETE /api/v1/patients/{patient_id}": "patients:write",
    
    # Case endpoints
    "GET /api/v1/cases": "cases:read",
    "POST /api/v1/cases": "cases:write",
    "GET /api/v1/cases/{case_id}": "cases:read",
    "PATCH /api/v1/cases/{case_id}": "cases:write",
    "DELETE /api/v1/cases/{case_id}": "cases:write",
    
    # Image endpoints
    "GET /api/v1/images": "images:read",
    "POST /api/v1/images": "images:write",
    "GET /api/v1/images/{image_id}": "images:read",
    "DELETE /api/v1/images/{image_id}": "images:write",
    
    # Inference endpoints
    "GET /api/v1/inference": "inference:read",
    "POST /api/v1/inference": "inference:write",
    "GET /api/v1/jobs": "inference:read",
    "GET /api/v1/jobs/{job_id}": "inference:read",
    
    # EHR endpoints
    "GET /api/v1/ehr": "ehr:read",
    "POST /api/v1/ehr": "ehr:write",
    "GET /api/v1/ehr/{ehr_id}": "ehr:read",
    "PUT /api/v1/ehr/{ehr_id}": "ehr:write",
    
    # Graph endpoints
    "GET /api/v1/graph": "graph:read",
    "POST /api/v1/graph": "graph:write",
    "GET /api/v1/graph/{graph_id}": "graph:read",
    
    # Ontology endpoints
    "GET /api/v1/ontology": "ontology:read",
    "POST /api/v1/ontology": "ontology:write",
    "GET /api/v1/ontology/{ontology_id}": "ontology:read",
    "PUT /api/v1/ontology/{ontology_id}": "ontology:write",
    
    # Audit endpoints
    "GET /api/v1/audit": "audit:read",
    "POST /api/v1/audit": "audit:write",
}


def get_required_permission(method: str, path: str) -> Optional[str]:
    """
    Get required permission for a route.
    
    Args:
        method: HTTP method
        path: Request path
        
    Returns:
        Required permission or None
    """
    # Try exact match first
    route_key = f"{method} {path}"
    permission = ROUTE_PERMISSIONS.get(route_key)
    
    if permission:
        return permission
    
    # Try pattern matching for parameterized routes
    for route_pattern, route_permission in ROUTE_PERMISSIONS.items():
        pattern_method, pattern_path = route_pattern.split(" ", 1)
        
        if method != pattern_method:
            continue
        
        # Simple pattern matching for {param} style parameters
        if "{" in pattern_path and "}" in pattern_path:
            # Convert pattern to regex-like matching
            pattern_parts = pattern_path.split("/")
            path_parts = path.split("/")
            
            if len(pattern_parts) != len(path_parts):
                continue
            
            match = True
            for pattern_part, path_part in zip(pattern_parts, path_parts):
                if pattern_part.startswith("{") and pattern_part.endswith("}"):
                    # This is a parameter, skip validation
                    continue
                elif pattern_part != path_part:
                    match = False
                    break
            
            if match:
                return route_permission
    
    return None


async def check_route_permission(
    method: str,
    path: str,
    user_context: UserContext
) -> bool:
    """
    Check if user has permission for a specific route.
    
    Args:
        method: HTTP method
        path: Request path
        user_context: User context
        
    Returns:
        True if user has permission
    """
    required_permission = get_required_permission(method, path)
    
    if not required_permission:
        # No specific permission required
        return True
    
    return required_permission in user_context.permissions
