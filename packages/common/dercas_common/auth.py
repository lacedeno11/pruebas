"""
DERCAS-ONCO-XAI Authentication and Authorization

JWT validation with Keycloak JWKS integration and RBAC utilities.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class UserInfo(BaseModel):
    """User information from JWT token."""
    user_id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = []
    groups: List[str] = []
    permissions: Set[str] = set()
    
    class Config:
        arbitrary_types_allowed = True


class JWTAuth:
    """JWT Authentication handler with Keycloak JWKS validation."""
    
    def __init__(
        self,
        jwks_url: str,
        issuer: str,
        audience: str,
        algorithm: str = "RS256",
        cache_ttl: int = 3600
    ):
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.cache_ttl = cache_ttl
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self.security = HTTPBearer()
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS from Keycloak with caching."""
        now = datetime.utcnow()
        
        # Check cache validity
        if (self._jwks_cache and self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self.cache_ttl):
            return self._jwks_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()
                
                # Cache the JWKS
                self._jwks_cache = jwks
                self._cache_timestamp = now
                
                logger.info("JWKS refreshed from Keycloak")
                return jwks
                
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            if self._jwks_cache:
                logger.warning("Using cached JWKS due to fetch failure")
                return self._jwks_cache
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    def _get_signing_key(self, jwks: Dict[str, Any], kid: str) -> str:
        """Get signing key from JWKS."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return json.dumps(key)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: signing key not found"
        )
    
    async def verify_token(self, token: str) -> UserInfo:
        """Verify JWT token and extract user information."""
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing key ID"
                )
            
            # Get JWKS and signing key
            jwks = await self._get_jwks()
            signing_key = self._get_signing_key(jwks, kid)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )
            
            # Extract user information
            user_info = UserInfo(
                user_id=payload.get("sub", ""),
                username=payload.get("preferred_username", ""),
                email=payload.get("email"),
                roles=payload.get("realm_access", {}).get("roles", []),
                groups=payload.get("groups", []),
                permissions=set(payload.get("permissions", []))
            )
            
            logger.debug(f"Token verified for user: {user_info.username}")
            return user_info
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )
    
    async def __call__(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> UserInfo:
        """FastAPI dependency for JWT authentication."""
        return await self.verify_token(credentials.credentials)


# Global JWT auth instance (to be initialized by each service)
jwt_auth: Optional[JWTAuth] = None


def init_jwt_auth(
    jwks_url: str,
    issuer: str,
    audience: str,
    algorithm: str = "RS256"
) -> JWTAuth:
    """Initialize global JWT auth instance."""
    global jwt_auth
    jwt_auth = JWTAuth(jwks_url, issuer, audience, algorithm)
    return jwt_auth


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> UserInfo:
    """Get current authenticated user."""
    if not jwt_auth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured"
        )
    return await jwt_auth.verify_token(credentials.credentials)


def require_roles(*required_roles: str):
    """Decorator to require specific roles."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs or dependencies
            user = None
            for arg in args:
                if isinstance(arg, UserInfo):
                    user = arg
                    break
            
            if not user:
                for value in kwargs.values():
                    if isinstance(value, UserInfo):
                        user = value
                        break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check roles
            user_roles = set(user.roles)
            required_roles_set = set(required_roles)
            
            if not user_roles.intersection(required_roles_set):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required roles: {', '.join(required_roles)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """FastAPI dependency to require a specific role."""
    def role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {role}"
            )
        return user
    return role_checker


def require_any_role(*roles: str):
    """FastAPI dependency to require any of the specified roles."""
    def role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        user_roles = set(user.roles)
        required_roles = set(roles)
        
        if not user_roles.intersection(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(roles)}"
            )
        return user
    return role_checker


# Predefined role dependencies
require_clinician = require_role("clinician")
require_admin = require_role("admin")
require_auditor = require_role("auditor")
require_clinical_access = require_any_role("clinician", "admin")


async def verify_jwt_token(token: str) -> UserInfo:
    """Standalone function to verify JWT token."""
    if not jwt_auth:
        raise ValueError("JWT authentication not initialized")
    return await jwt_auth.verify_token(token)


def extract_correlation_id(request: Request) -> Optional[str]:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-Id")


def extract_case_id(request: Request) -> Optional[str]:
    """Extract case ID from request headers."""
    return request.headers.get("X-Case-Id")


class RBACChecker:
    """Role-Based Access Control checker."""
    
    @staticmethod
    def can_access_case(user: UserInfo, case_id: str) -> bool:
        """Check if user can access a specific case."""
        # Admin can access all cases
        if "admin" in user.roles:
            return True
        
        # Clinicians can access cases they created or are assigned to
        if "clinician" in user.roles:
            # TODO: Implement case ownership/assignment logic
            return True
        
        # Auditors can read all cases
        if "auditor" in user.roles:
            return True
        
        return False
    
    @staticmethod
    def can_modify_case(user: UserInfo, case_id: str) -> bool:
        """Check if user can modify a specific case."""
        # Only admin and clinicians can modify cases
        if "admin" in user.roles:
            return True
        
        if "clinician" in user.roles:
            # TODO: Implement case ownership logic
            return True
        
        return False
    
    @staticmethod
    def can_access_admin_functions(user: UserInfo) -> bool:
        """Check if user can access admin functions."""
        return "admin" in user.roles
    
    @staticmethod
    def can_access_audit_data(user: UserInfo) -> bool:
        """Check if user can access audit data."""
        return "admin" in user.roles or "auditor" in user.roles


# ABAC (Attribute-Based Access Control) utilities
class ABACContext(BaseModel):
    """ABAC context for fine-grained access control."""
    user: UserInfo
    resource_type: str
    resource_id: str
    action: str
    environment: Dict[str, Any] = {}
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.user.permissions
    
    def is_resource_owner(self, owner_id: str) -> bool:
        """Check if user owns the resource."""
        return self.user.user_id == owner_id
    
    def evaluate_policy(self, policy: Dict[str, Any]) -> bool:
        """Evaluate ABAC policy."""
        # Simple policy evaluation - can be extended
        required_roles = policy.get("roles", [])
        required_permissions = policy.get("permissions", [])
        
        # Check roles
        if required_roles and not set(self.user.roles).intersection(set(required_roles)):
            return False
        
        # Check permissions
        if required_permissions and not set(self.user.permissions).intersection(set(required_permissions)):
            return False
        
        return True
