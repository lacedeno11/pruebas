# DERCAS-ONCO-XAI V1 - Authentication Utilities
# JWT verification with JWKS and role-based access control

import os
from typing import List, Optional, Dict, Any
from functools import wraps
import httpx
from jose import JWTError, jwt
from jose.exceptions import JWKError
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# Configuration from environment variables
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "oncology-xai")
JWKS_URL = os.getenv("JWKS_URL", f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "oncology-xai-client")
JWT_ISSUER = os.getenv("JWT_ISSUER", f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}")


class UserInfo(BaseModel):
    """User information extracted from JWT token."""
    user_id: str
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = []
    groups: List[str] = []
    correlation_id: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)


class JWTAuth:
    """JWT Authentication handler with JWKS support."""
    
    def __init__(self):
        self.jwks_cache: Optional[Dict[str, Any]] = None
        self.security = HTTPBearer()
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak with caching."""
        if self.jwks_cache is None:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(JWKS_URL, timeout=10.0)
                    response.raise_for_status()
                    self.jwks_cache = response.json()
                    logger.info("JWKS fetched and cached successfully")
            except Exception as e:
                logger.error(f"Failed to fetch JWKS from {JWKS_URL}: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Authentication service unavailable"
                )
        return self.jwks_cache
    
    def clear_jwks_cache(self):
        """Clear JWKS cache to force refresh."""
        self.jwks_cache = None
        logger.info("JWKS cache cleared")
    
    async def verify_token(self, token: str) -> UserInfo:
        """Verify JWT token and extract user information."""
        try:
            # Get JWKS for token verification
            jwks = await self.get_jwks()
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(
                    status_code=401,
                    detail="Token missing key ID"
                )
            
            # Find the correct key in JWKS
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise HTTPException(
                    status_code=401,
                    detail="Token key not found in JWKS"
                )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=[JWT_ALGORITHM],
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True}
            )
            
            # Extract user information from token payload
            user_info = UserInfo(
                user_id=payload.get("sub", ""),
                username=payload.get("preferred_username", ""),
                email=payload.get("email"),
                first_name=payload.get("given_name"),
                last_name=payload.get("family_name"),
                roles=payload.get("roles", []),
                groups=payload.get("groups", []),
                correlation_id=payload.get("correlation_id")
            )
            
            logger.debug(f"Token verified for user: {user_info.username}")
            return user_info
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        except JWKError as e:
            logger.error(f"JWK error: {e}")
            raise HTTPException(
                status_code=401,
                detail="Token verification failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            raise HTTPException(
                status_code=500,
                detail="Authentication error"
            )
    
    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> UserInfo:
        """FastAPI dependency for JWT authentication."""
        return await self.verify_token(credentials.credentials)


# Global JWT auth instance
jwt_auth = JWTAuth()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> UserInfo:
    """FastAPI dependency to get current authenticated user."""
    return await jwt_auth.verify_token(credentials.credentials)


def require_roles(required_roles: List[str], require_all: bool = False):
    """
    Decorator to require specific roles for endpoint access.
    
    Args:
        required_roles: List of required roles
        require_all: If True, user must have ALL roles. If False, user must have ANY role.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by FastAPI dependency)
            user = None
            for arg in args:
                if isinstance(arg, UserInfo):
                    user = arg
                    break
            
            if not user:
                # Try to find user in kwargs
                for key, value in kwargs.items():
                    if isinstance(value, UserInfo):
                        user = value
                        break
            
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Check role requirements
            if require_all:
                has_access = user.has_all_roles(required_roles)
            else:
                has_access = user.has_any_role(required_roles)
            
            if not has_access:
                logger.warning(
                    f"User {user.username} denied access. Required roles: {required_roles}, "
                    f"User roles: {user.roles}, Require all: {require_all}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required roles: {required_roles}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_clinician(func):
    """Decorator to require clinician role."""
    return require_roles(["clinician"])(func)


def require_admin(func):
    """Decorator to require admin role."""
    return require_roles(["admin"])(func)


def require_auditor(func):
    """Decorator to require auditor role."""
    return require_roles(["auditor"])(func)


def require_clinical_access(func):
    """Decorator to require clinical access (clinician or admin)."""
    return require_roles(["clinician", "admin"], require_all=False)(func)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[UserInfo]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        return await jwt_auth.verify_token(credentials.credentials)
    except HTTPException:
        return None


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions."""
    pass
