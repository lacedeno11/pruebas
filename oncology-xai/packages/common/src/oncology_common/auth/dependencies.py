"""FastAPI authentication dependencies."""

from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from oncology_common.auth.jwt import JWTValidator, TokenPayload


# Security scheme
security = HTTPBearer(auto_error=False)


def create_jwt_validator(
    jwks_url: str,
    audience: str | None = None,
    issuer: str | None = None,
) -> JWTValidator:
    """Create a JWT validator instance."""
    return JWTValidator(jwks_url=jwks_url, audience=audience, issuer=issuer)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> TokenPayload:
    """Get current user from JWT token.

    Requires jwt_validator to be set on app.state.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_validator: JWTValidator | None = getattr(request.app.state, "jwt_validator", None)

    if not jwt_validator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT validator not configured",
        )

    try:
        token_payload = await jwt_validator.validate_token(credentials.credentials)

        if token_payload.is_expired:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token_payload

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(*required_roles: str) -> Callable:
    """Dependency factory for role-based access control.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
        async def admin_endpoint(): ...
    """
    async def role_checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        user_roles = set(current_user.roles)
        required = set(required_roles)

        if not required.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )

        return current_user

    return role_checker


def optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> TokenPayload | None:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    jwt_validator: JWTValidator | None = getattr(request.app.state, "jwt_validator", None)

    if not jwt_validator:
        return None

    try:
        import asyncio
        token_payload = asyncio.get_event_loop().run_until_complete(
            jwt_validator.validate_token(credentials.credentials)
        )
        return token_payload if not token_payload.is_expired else None
    except Exception:
        return None
