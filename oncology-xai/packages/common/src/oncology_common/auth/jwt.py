"""JWT validation utilities with JWKS support."""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.backends import RSAKey
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str
    exp: int
    iat: int
    iss: str | None = None
    aud: str | list[str] | None = None
    realm_roles: list[str] = Field(default_factory=list)
    client_roles: list[str] = Field(default_factory=list)
    email: str | None = None
    preferred_username: str | None = None
    name: str | None = None

    @property
    def user_id(self) -> str:
        return self.sub

    @property
    def roles(self) -> list[str]:
        return list(set(self.realm_roles + self.client_roles))

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc).timestamp() > self.exp


class JWTValidator:
    """JWT validator with JWKS caching."""

    def __init__(
        self,
        jwks_url: str,
        audience: str | None = None,
        issuer: str | None = None,
        cache_ttl: int = 3600,
    ):
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self.cache_ttl = cache_ttl
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at: float = 0
        self._lock = asyncio.Lock()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from the issuer."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            return response.json()

    async def get_jwks(self) -> dict[str, Any]:
        """Get JWKS with caching."""
        now = datetime.now(timezone.utc).timestamp()

        async with self._lock:
            if self._jwks is None or (now - self._jwks_fetched_at) > self.cache_ttl:
                self._jwks = await self._fetch_jwks()
                self._jwks_fetched_at = now

            return self._jwks

    def _get_signing_key(self, jwks: dict[str, Any], kid: str) -> RSAKey | None:
        """Get signing key from JWKS by key ID."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None

    async def validate_token(self, token: str) -> TokenPayload:
        """Validate JWT token and return payload."""
        try:
            # Get unverified header to find key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise JWTError("Token missing key ID")

            # Get JWKS and find signing key
            jwks = await self.get_jwks()
            signing_key = self._get_signing_key(jwks, kid)

            if not signing_key:
                # Refresh JWKS and try again
                self._jwks = None
                jwks = await self.get_jwks()
                signing_key = self._get_signing_key(jwks, kid)

                if not signing_key:
                    raise JWTError(f"Signing key not found for kid: {kid}")

            # Verify and decode token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_aud": self.audience is not None,
                    "verify_iss": self.issuer is not None,
                },
            )

            # Extract roles from Keycloak token structure
            realm_roles = payload.get("realm_access", {}).get("roles", [])
            client_roles = payload.get("resource_access", {}).get(
                "oncology-api", {}
            ).get("roles", [])

            # Also check direct claims
            if "realm_roles" in payload:
                realm_roles = payload["realm_roles"]
            if "client_roles" in payload:
                client_roles = payload["client_roles"]

            return TokenPayload(
                sub=payload["sub"],
                exp=payload["exp"],
                iat=payload.get("iat", 0),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                realm_roles=realm_roles,
                client_roles=client_roles,
                email=payload.get("email"),
                preferred_username=payload.get("preferred_username"),
                name=payload.get("name"),
            )

        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")
        except Exception as e:
            raise ValueError(f"Token validation failed: {e}")

    def validate_token_sync(self, token: str) -> TokenPayload:
        """Synchronous wrapper for token validation."""
        return asyncio.get_event_loop().run_until_complete(
            self.validate_token(token)
        )
