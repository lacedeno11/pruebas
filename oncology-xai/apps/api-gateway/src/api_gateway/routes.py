"""API Gateway routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from oncology_common.auth.dependencies import get_current_user
from oncology_common.auth.jwt import TokenPayload


router = APIRouter(tags=["Auth"])


@router.get("/auth/me")
async def get_current_user_info(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
) -> dict:
    """Get current authenticated user information."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "name": current_user.name,
        "username": current_user.preferred_username,
        "roles": current_user.roles,
        "realm_roles": current_user.realm_roles,
        "client_roles": current_user.client_roles,
    }
