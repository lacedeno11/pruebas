"""
DERCAS-ONCO-XAI V1 - Authentication Utilities

JWT validation with Keycloak JWKS integration and RBAC utilities.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import jwt
import requests
from jwt import PyJWKClient
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserClaims(BaseModel):
    """User claims extracted from JWT token."""
    sub: str = Field(..., description="Subject (user ID)")
    email: Optional[str] = Field(None, description="User email")
    preferred_username: Optional[str] = Field(None, description="Preferred username")
    given_name: Optional[str] = Field(None, description="Given name")
    family_name: Optional[str] = Field(None, description="Family name")
    name: Optional[str] = Field(None, description="Full name")
    
    # Keycloak specific claims
    realm_access: Optional[Dict[str, List[str]]] = Field(None, description="Realm access roles")
    resource_access: Optional[Dict[str, Dict[str, List[str]]]] = Field(None, description="Resource access roles")
    groups: Optional[List[str]] = Field(None, description="User groups")
    
    # Token metadata
    iss: str = Field(..., description="Token issuer")
    aud: str = Field(..., description="Token audience")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: Optional[str] = Field(None, description="JWT ID")


class AuthConfig:
    """Authentication configuration."""
    
    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        jwks_cache_ttl: int = 300,
        verify_signature: bool = True,
        verify_exp: bool = True,
        verify_aud: bool = True
    ):
        self.keycloak_url = keycloak_url.rstrip('/')
        self.realm = realm
        self.client_id = client_id
        self.jwks_cache_ttl = jwks_cache_ttl
        self.verify_signature = verify_signature
        self.verify_exp = verify_exp
        self.verify_aud = verify_aud
        
        # Construct JWKS URL
        self.jwks_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        
        # Initialize JWKS client
        self.jwks_client = PyJWKClient(
            self.jwks_url,
            cache_ttl=self.jwks_cache_ttl,
            cache_jwks=True
        ) if self.verify_signature else None
        
        logger.info(f"Initialized auth config for realm '{realm}' at {self.keycloak_url}")


class JWTValidator:
    """JWT token validator with Keycloak JWKS support."""
    
    def __init__(self, config: AuthConfig):
        self.config = config
    
    def validate_token(self, token: str) -> UserClaims:
        """
        Validate JWT token and extract user claims.
        
        Args:
            token: JWT token string
            
        Returns:
            UserClaims: Validated user claims
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
            jwt.InvalidAudienceError: If audience is invalid
        """
        try:
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            
            # Get signing key from JWKS
            if self.config.verify_signature and self.config.jwks_client:
                signing_key = self.config.jwks_client.get_signing_key_from_jwt(token)
                key = signing_key.key
            else:
                key = None
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                key=key,
                algorithms=["RS256", "HS256"] if key else None,
                audience=self.config.client_id if self.config.verify_aud else None,
                options={
                    "verify_signature": self.config.verify_signature,
                    "verify_exp": self.config.verify_exp,
                    "verify_aud": self.config.verify_aud,
                    "verify_iss": True
                }
            )
            
            # Validate issuer
            expected_issuer = f"{self.config.keycloak_url}/realms/{self.config.realm}"
            if payload.get("iss") != expected_issuer:
                raise jwt.InvalidIssuerError(f"Invalid issuer: {payload.get('iss')}")
            
            # Create user claims
            return UserClaims(**payload)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise jwt.InvalidTokenError(f"Token validation failed: {e}")
    
    def extract_bearer_token(self, authorization_header: Optional[str]) -> Optional[str]:
        """
        Extract bearer token from Authorization header.
        
        Args:
            authorization_header: Authorization header value
            
        Returns:
            str: Bearer token or None if not found
        """
        if not authorization_header:
            return None
        
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]


class RoleChecker:
    """Role-based access control utilities."""
    
    @staticmethod
    def has_realm_role(claims: UserClaims, role: str) -> bool:
        """
        Check if user has a specific realm role.
        
        Args:
            claims: User claims
            role: Role name to check
            
        Returns:
            bool: True if user has the role
        """
        if not claims.realm_access:
            return False
        
        roles = claims.realm_access.get("roles", [])
        return role in roles
    
    @staticmethod
    def has_client_role(claims: UserClaims, client_id: str, role: str) -> bool:
        """
        Check if user has a specific client role.
        
        Args:
            claims: User claims
            client_id: Client ID
            role: Role name to check
            
        Returns:
            bool: True if user has the role
        """
        if not claims.resource_access:
            return False
        
        client_access = claims.resource_access.get(client_id, {})
        roles = client_access.get("roles", [])
        return role in roles
    
    @staticmethod
    def has_any_role(claims: UserClaims, roles: List[str]) -> bool:
        """
        Check if user has any of the specified realm roles.
        
        Args:
            claims: User claims
            roles: List of role names to check
            
        Returns:
            bool: True if user has any of the roles
        """
        if not claims.realm_access:
            return False
        
        user_roles = set(claims.realm_access.get("roles", []))
        required_roles = set(roles)
        return bool(user_roles.intersection(required_roles))
    
    @staticmethod
    def has_all_roles(claims: UserClaims, roles: List[str]) -> bool:
        """
        Check if user has all of the specified realm roles.
        
        Args:
            claims: User claims
            roles: List of role names to check
            
        Returns:
            bool: True if user has all of the roles
        """
        if not claims.realm_access:
            return False
        
        user_roles = set(claims.realm_access.get("roles", []))
        required_roles = set(roles)
        return required_roles.issubset(user_roles)
    
    @staticmethod
    def is_in_group(claims: UserClaims, group: str) -> bool:
        """
        Check if user is in a specific group.
        
        Args:
            claims: User claims
            group: Group name to check
            
        Returns:
            bool: True if user is in the group
        """
        if not claims.groups:
            return False
        
        return group in claims.groups


class PermissionChecker:
    """Permission-based access control for clinical data."""
    
    # Define role hierarchy
    ADMIN_ROLES = {"admin", "system-admin"}
    CLINICIAN_ROLES = {"clinician", "radiologist", "pathologist", "oncologist"}
    AUDITOR_ROLES = {"auditor", "compliance-officer"}
    
    @classmethod
    def can_access_case(cls, claims: UserClaims, case_id: str) -> bool:
        """
        Check if user can access a specific case.
        
        Args:
            claims: User claims
            case_id: Case ID to check access for
            
        Returns:
            bool: True if user can access the case
        """
        # Admins can access all cases
        if cls._has_admin_role(claims):
            return True
        
        # Clinicians can access cases (in real implementation, check assignment)
        if cls._has_clinician_role(claims):
            return True
        
        # Auditors can read all cases
        if cls._has_auditor_role(claims):
            return True
        
        return False
    
    @classmethod
    def can_modify_case(cls, claims: UserClaims, case_id: str) -> bool:
        """
        Check if user can modify a specific case.
        
        Args:
            claims: User claims
            case_id: Case ID to check modification rights for
            
        Returns:
            bool: True if user can modify the case
        """
        # Admins can modify all cases
        if cls._has_admin_role(claims):
            return True
        
        # Clinicians can modify assigned cases (in real implementation, check assignment)
        if cls._has_clinician_role(claims):
            return True
        
        # Auditors cannot modify cases
        return False
    
    @classmethod
    def can_access_admin_functions(cls, claims: UserClaims) -> bool:
        """
        Check if user can access administrative functions.
        
        Args:
            claims: User claims
            
        Returns:
            bool: True if user can access admin functions
        """
        return cls._has_admin_role(claims)
    
    @classmethod
    def can_manage_ontologies(cls, claims: UserClaims) -> bool:
        """
        Check if user can manage ontologies.
        
        Args:
            claims: User claims
            
        Returns:
            bool: True if user can manage ontologies
        """
        # Only admins can manage ontologies
        return cls._has_admin_role(claims)
    
    @classmethod
    def can_view_audit_logs(cls, claims: UserClaims) -> bool:
        """
        Check if user can view audit logs.
        
        Args:
            claims: User claims
            
        Returns:
            bool: True if user can view audit logs
        """
        # Admins and auditors can view audit logs
        return cls._has_admin_role(claims) or cls._has_auditor_role(claims)
    
    @classmethod
    def _has_admin_role(cls, claims: UserClaims) -> bool:
        """Check if user has admin role."""
        return RoleChecker.has_any_role(claims, list(cls.ADMIN_ROLES))
    
    @classmethod
    def _has_clinician_role(cls, claims: UserClaims) -> bool:
        """Check if user has clinician role."""
        return RoleChecker.has_any_role(claims, list(cls.CLINICIAN_ROLES))
    
    @classmethod
    def _has_auditor_role(cls, claims: UserClaims) -> bool:
        """Check if user has auditor role."""
        return RoleChecker.has_any_role(claims, list(cls.AUDITOR_ROLES))


# Utility functions for FastAPI integration
def create_jwt_validator(
    keycloak_url: str,
    realm: str,
    client_id: str,
    **kwargs
) -> JWTValidator:
    """
    Create JWT validator with configuration.
    
    Args:
        keycloak_url: Keycloak server URL
        realm: Keycloak realm name
        client_id: Client ID for audience validation
        **kwargs: Additional configuration options
        
    Returns:
        JWTValidator: Configured JWT validator
    """
    config = AuthConfig(
        keycloak_url=keycloak_url,
        realm=realm,
        client_id=client_id,
        **kwargs
    )
    return JWTValidator(config)


def validate_token_string(validator: JWTValidator, token: str) -> UserClaims:
    """
    Validate token string and return claims.
    
    Args:
        validator: JWT validator instance
        token: JWT token string
        
    Returns:
        UserClaims: Validated user claims
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    return validator.validate_token(token)


def extract_user_info(claims: UserClaims) -> Dict[str, Any]:
    """
    Extract user information for API responses.
    
    Args:
        claims: User claims
        
    Returns:
        Dict: User information
    """
    return {
        "user_id": claims.sub,
        "username": claims.preferred_username,
        "email": claims.email,
        "name": claims.name,
        "given_name": claims.given_name,
        "family_name": claims.family_name,
        "roles": claims.realm_access.get("roles", []) if claims.realm_access else [],
        "groups": claims.groups or []
    }
