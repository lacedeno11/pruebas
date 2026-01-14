"""
DERCAS-ONCO-XAI API Gateway Auth Router

Authentication endpoints for JWT validation and user information.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from dercas_common.auth import (
    verify_jwt_token,
    get_current_user,
    require_clinician,
    require_admin,
    require_auditor,
    UserInfo
)
from dercas_common.models import UserInfoResponse

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


@router.get("/me", response_model=UserInfoResponse)
async def get_user_info(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get current user information from JWT token."""
    try:
        return UserInfoResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            roles=current_user.roles,
            permissions=list(current_user.permissions),
            is_active=current_user.is_active,
            metadata=current_user.metadata
        )
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user information"
        )


@router.post("/validate")
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Validate JWT token and return token information."""
    try:
        # Verify the token
        payload = await verify_jwt_token(credentials.credentials)
        
        return {
            "valid": True,
            "token_type": "Bearer",
            "subject": payload.get("sub"),
            "issuer": payload.get("iss"),
            "audience": payload.get("aud"),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat"),
            "roles": payload.get("realm_access", {}).get("roles", []),
            "permissions": payload.get("resource_access", {}).get("dercas-api", {}).get("roles", [])
        }
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


@router.get("/roles")
async def get_user_roles(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get current user's roles and permissions."""
    return {
        "user_id": current_user.user_id,
        "roles": current_user.roles,
        "permissions": list(current_user.permissions),
        "is_clinician": "clinician" in current_user.roles,
        "is_admin": "admin" in current_user.roles,
        "is_auditor": "auditor" in current_user.roles
    }


@router.get("/check/clinician")
async def check_clinician_access(
    current_user: UserInfo = Depends(require_clinician)
):
    """Check if user has clinician access."""
    return {
        "access": "granted",
        "role": "clinician",
        "user_id": current_user.user_id
    }


@router.get("/check/admin")
async def check_admin_access(
    current_user: UserInfo = Depends(require_admin)
):
    """Check if user has admin access."""
    return {
        "access": "granted",
        "role": "admin",
        "user_id": current_user.user_id
    }


@router.get("/check/auditor")
async def check_auditor_access(
    current_user: UserInfo = Depends(require_auditor)
):
    """Check if user has auditor access."""
    return {
        "access": "granted",
        "role": "auditor",
        "user_id": current_user.user_id
    }


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Refresh JWT token (placeholder for future implementation)."""
    # Note: Token refresh would typically be handled by Keycloak directly
    # This endpoint is a placeholder for future refresh token implementation
    
    try:
        # Verify current token is valid
        payload = await verify_jwt_token(credentials.credentials)
        
        return {
            "message": "Token refresh not implemented",
            "note": "Please use Keycloak token endpoint for refresh",
            "current_token_valid": True,
            "expires_at": payload.get("exp")
        }
    except Exception as e:
        logger.warning(f"Token refresh validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token for refresh"
        )


@router.get("/permissions")
async def get_permissions(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get detailed permissions for current user."""
    # Define permission mappings based on roles
    role_permissions = {
        "clinician": [
            "cases:read",
            "cases:create",
            "cases:update",
            "images:read",
            "images:upload",
            "inference:read",
            "inference:create",
            "ehr:read",
            "ehr:create",
            "graph:read",
            "explanations:read",
            "explanations:create"
        ],
        "admin": [
            "cases:*",
            "images:*",
            "inference:*",
            "ehr:*",
            "graph:*",
            "ontology:*",
            "explanations:*",
            "users:read",
            "audit:read"
        ],
        "auditor": [
            "cases:read",
            "images:read",
            "inference:read",
            "ehr:read",
            "graph:read",
            "explanations:read",
            "audit:read",
            "audit:export"
        ]
    }
    
    # Collect permissions based on user roles
    user_permissions = set()
    for role in current_user.roles:
        if role in role_permissions:
            user_permissions.update(role_permissions[role])
    
    return {
        "user_id": current_user.user_id,
        "roles": current_user.roles,
        "permissions": sorted(list(user_permissions)),
        "permission_summary": {
            "can_create_cases": "cases:create" in user_permissions or "cases:*" in user_permissions,
            "can_upload_images": "images:upload" in user_permissions or "images:*" in user_permissions,
            "can_run_inference": "inference:create" in user_permissions or "inference:*" in user_permissions,
            "can_manage_ontology": "ontology:*" in user_permissions,
            "can_view_audit": "audit:read" in user_permissions,
            "is_admin": "admin" in current_user.roles
        }
    }


@router.get("/session")
async def get_session_info(
    request: Request,
    current_user: UserInfo = Depends(get_current_user)
):
    """Get current session information."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "session_id": correlation_id,
        "roles": current_user.roles,
        "is_active": current_user.is_active,
        "login_time": current_user.metadata.get("login_time"),
        "last_activity": current_user.metadata.get("last_activity"),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    }
