"""
DERCAS-ONCO-XAI V1 - Authentication Handler

Authentication and authorization handling for the API Gateway.
"""

import logging
from typing import Optional

from fastapi import Request, HTTPException, status

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.auth import JWTValidator, UserClaims
from packages.common.middleware import get_correlation_id
from packages.common.errors import (
    ErrorCode,
    AuthenticationError,
    AuthorizationError,
    create_http_exception
)

logger = logging.getLogger(__name__)


class AuthHandler:
    """Authentication handler for the API Gateway."""
    
    def __init__(self, jwt_validator: JWTValidator):
        self.jwt_validator = jwt_validator
        logger.info("Initialized authentication handler")
    
    async def authenticate_request(self, request: Request) -> UserClaims:
        """
        Authenticate a request and return user claims.
        
        Args:
            request: FastAPI request object
            
        Returns:
            UserClaims: Validated user claims
            
        Raises:
            AuthenticationError: If authentication fails
        """
        correlation_id = get_correlation_id(request)
        
        # Extract authorization header
        authorization = request.headers.get("authorization")
        if not authorization:
            logger.warning(
                "Missing authorization header",
                extra={"correlation_id": correlation_id}
            )
            raise AuthenticationError(
                message="Missing authorization header",
                correlation_id=correlation_id
            )
        
        # Extract bearer token
        token = self.jwt_validator.extract_bearer_token(authorization)
        if not token:
            logger.warning(
                "Invalid authorization header format",
                extra={"correlation_id": correlation_id}
            )
            raise AuthenticationError(
                message="Invalid authorization header format. Expected 'Bearer <token>'",
                correlation_id=correlation_id
            )
        
        try:
            # Validate token and extract claims
            user_claims = self.jwt_validator.validate_token(token)
            
            logger.debug(
                f"Successfully authenticated user: {user_claims.sub}",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": user_claims.sub,
                    "username": user_claims.preferred_username
                }
            )
            
            return user_claims
            
        except Exception as e:
            logger.warning(
                f"Token validation failed: {e}",
                extra={"correlation_id": correlation_id}
            )
            raise AuthenticationError(
                message=f"Token validation failed: {str(e)}",
                correlation_id=correlation_id
            )
    
    def check_permissions(
        self,
        user_claims: UserClaims,
        required_roles: Optional[list] = None,
        required_permissions: Optional[list] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Check if user has required permissions.
        
        Args:
            user_claims: User claims from JWT
            required_roles: List of required roles (any one is sufficient)
            required_permissions: List of required permissions
            correlation_id: Request correlation ID
            
        Raises:
            AuthorizationError: If user lacks required permissions
        """
        # Check roles if specified
        if required_roles:
            user_roles = set()
            if user_claims.realm_access and user_claims.realm_access.get("roles"):
                user_roles.update(user_claims.realm_access["roles"])
            
            required_roles_set = set(required_roles)
            if not user_roles.intersection(required_roles_set):
                logger.warning(
                    f"User {user_claims.sub} lacks required roles: {required_roles}",
                    extra={
                        "correlation_id": correlation_id,
                        "user_id": user_claims.sub,
                        "user_roles": list(user_roles),
                        "required_roles": required_roles
                    }
                )
                raise AuthorizationError(
                    message=f"Insufficient permissions. Required roles: {required_roles}",
                    correlation_id=correlation_id
                )
        
        # Check custom permissions if specified
        if required_permissions:
            # This is where you would implement custom permission logic
            # For now, we'll use a simple role-based approach
            logger.debug(
                f"Checking permissions for user {user_claims.sub}: {required_permissions}",
                extra={"correlation_id": correlation_id}
            )
        
        logger.debug(
            f"Permission check passed for user {user_claims.sub}",
            extra={"correlation_id": correlation_id}
        )
    
    async def authenticate_and_authorize(
        self,
        request: Request,
        required_roles: Optional[list] = None,
        required_permissions: Optional[list] = None
    ) -> UserClaims:
        """
        Authenticate request and check authorization.
        
        Args:
            request: FastAPI request object
            required_roles: List of required roles
            required_permissions: List of required permissions
            
        Returns:
            UserClaims: Validated user claims
            
        Raises:
            AuthenticationError: If authentication fails
            AuthorizationError: If authorization fails
        """
        correlation_id = get_correlation_id(request)
        
        # Authenticate
        user_claims = await self.authenticate_request(request)
        
        # Authorize
        self.check_permissions(
            user_claims=user_claims,
            required_roles=required_roles,
            required_permissions=required_permissions,
            correlation_id=correlation_id
        )
        
        return user_claims
    
    def is_admin(self, user_claims: UserClaims) -> bool:
        """Check if user has admin role."""
        if not user_claims.realm_access:
            return False
        
        admin_roles = {"admin", "system-admin"}
        user_roles = set(user_claims.realm_access.get("roles", []))
        
        return bool(admin_roles.intersection(user_roles))
    
    def is_clinician(self, user_claims: UserClaims) -> bool:
        """Check if user has clinician role."""
        if not user_claims.realm_access:
            return False
        
        clinician_roles = {"clinician", "radiologist", "pathologist", "oncologist"}
        user_roles = set(user_claims.realm_access.get("roles", []))
        
        return bool(clinician_roles.intersection(user_roles))
    
    def is_auditor(self, user_claims: UserClaims) -> bool:
        """Check if user has auditor role."""
        if not user_claims.realm_access:
            return False
        
        auditor_roles = {"auditor", "compliance-officer"}
        user_roles = set(user_claims.realm_access.get("roles", []))
        
        return bool(auditor_roles.intersection(user_roles))
    
    def can_access_case(self, user_claims: UserClaims, case_id: str) -> bool:
        """
        Check if user can access a specific case.
        
        Args:
            user_claims: User claims
            case_id: Case ID to check access for
            
        Returns:
            bool: True if user can access the case
        """
        # Admins can access all cases
        if self.is_admin(user_claims):
            return True
        
        # Clinicians can access cases (in real implementation, check assignment)
        if self.is_clinician(user_claims):
            return True
        
        # Auditors can read all cases
        if self.is_auditor(user_claims):
            return True
        
        return False
    
    def can_modify_case(self, user_claims: UserClaims, case_id: str) -> bool:
        """
        Check if user can modify a specific case.
        
        Args:
            user_claims: User claims
            case_id: Case ID to check modification rights for
            
        Returns:
            bool: True if user can modify the case
        """
        # Admins can modify all cases
        if self.is_admin(user_claims):
            return True
        
        # Clinicians can modify assigned cases (in real implementation, check assignment)
        if self.is_clinician(user_claims):
            return True
        
        # Auditors cannot modify cases
        return False
    
    def get_user_context(self, user_claims: UserClaims) -> dict:
        """
        Get user context information for logging and headers.
        
        Args:
            user_claims: User claims
            
        Returns:
            dict: User context information
        """
        return {
            "user_id": user_claims.sub,
            "username": user_claims.preferred_username,
            "email": user_claims.email,
            "name": user_claims.name,
            "roles": user_claims.realm_access.get("roles", []) if user_claims.realm_access else [],
            "groups": user_claims.groups or [],
            "is_admin": self.is_admin(user_claims),
            "is_clinician": self.is_clinician(user_claims),
            "is_auditor": self.is_auditor(user_claims)
        }


# Utility functions for route-level authentication
async def require_authentication(request: Request, auth_handler: AuthHandler) -> UserClaims:
    """Require authentication for a route."""
    return await auth_handler.authenticate_request(request)


async def require_admin(request: Request, auth_handler: AuthHandler) -> UserClaims:
    """Require admin role for a route."""
    return await auth_handler.authenticate_and_authorize(
        request=request,
        required_roles=["admin", "system-admin"]
    )


async def require_clinician(request: Request, auth_handler: AuthHandler) -> UserClaims:
    """Require clinician role for a route."""
    return await auth_handler.authenticate_and_authorize(
        request=request,
        required_roles=["clinician", "radiologist", "pathologist", "oncologist"]
    )


async def require_auditor(request: Request, auth_handler: AuthHandler) -> UserClaims:
    """Require auditor role for a route."""
    return await auth_handler.authenticate_and_authorize(
        request=request,
        required_roles=["auditor", "compliance-officer"]
    )


# Development mode authentication bypass
class DevAuthHandler(AuthHandler):
    """Development authentication handler that bypasses JWT validation."""
    
    def __init__(self, jwt_validator: JWTValidator):
        super().__init__(jwt_validator)
        logger.warning("Using development authentication handler - JWT validation bypassed!")
    
    async def authenticate_request(self, request: Request) -> UserClaims:
        """Return mock user claims for development."""
        correlation_id = get_correlation_id(request)
        
        logger.info(
            "Development mode: bypassing JWT validation",
            extra={"correlation_id": correlation_id}
        )
        
        # Create mock user claims
        mock_claims = UserClaims(
            sub="dev-user-123",
            email="dev@example.com",
            preferred_username="dev-user",
            given_name="Dev",
            family_name="User",
            name="Dev User",
            realm_access={
                "roles": ["admin", "clinician", "auditor"]  # Grant all roles in dev mode
            },
            groups=["developers"],
            iss="http://localhost:8080/realms/oncology",
            aud="oncology-api",
            exp=9999999999,  # Far future expiration
            iat=1000000000,
            jti="dev-token-123"
        )
        
        return mock_claims


def create_auth_handler(jwt_validator: JWTValidator, development_mode: bool = False) -> AuthHandler:
    """
    Create authentication handler.
    
    Args:
        jwt_validator: JWT validator instance
        development_mode: Whether to use development mode (bypasses JWT validation)
        
    Returns:
        AuthHandler: Configured authentication handler
    """
    if development_mode:
        logger.warning("Creating development authentication handler")
        return DevAuthHandler(jwt_validator)
    else:
        return AuthHandler(jwt_validator)
