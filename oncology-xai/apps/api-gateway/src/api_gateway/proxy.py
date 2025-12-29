"""Proxy router for downstream services."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse

from oncology_common.auth.dependencies import get_current_user, require_roles
from oncology_common.auth.jwt import TokenPayload

from api_gateway.config import Settings


class ProxyRouter:
    """Proxy router for downstream services."""

    # Service routing configuration
    SERVICE_ROUTES = {
        "patients": "case_service_url",
        "cases": "case_service_url",
        "images": "image_service_url",
        "jobs": "inference_service_url",
        "results": "inference_service_url",
        "ehr": "ehr_service_url",
        "graphs": "graph_service_url",
        "graph": "graph_service_url",
        "admin/ontologies": "ontology_admin_service_url",
        "audit": "audit_service_url",
        "explanations": "ehr_service_url",
    }

    # Role requirements for routes
    ROLE_REQUIREMENTS = {
        "admin/ontologies": ["admin"],
        "audit": ["admin", "auditor"],
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.router = APIRouter()
        self._setup_routes()

    def _get_service_url(self, path: str) -> str | None:
        """Get service URL for a path."""
        for prefix, service_attr in self.SERVICE_ROUTES.items():
            if path.startswith(prefix):
                return getattr(self.settings, service_attr)
        return None

    def _check_role_requirements(self, path: str, roles: list[str]) -> bool:
        """Check if user has required roles for path."""
        for prefix, required_roles in self.ROLE_REQUIREMENTS.items():
            if path.startswith(prefix):
                return any(role in roles for role in required_roles)
        return True  # No role requirement

    def _setup_routes(self):
        """Setup proxy routes."""

        @self.router.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        async def proxy_request(
            request: Request,
            path: str,
            current_user: Annotated[TokenPayload, Depends(get_current_user)],
        ) -> Response:
            """Proxy request to downstream service."""
            # Get service URL
            service_url = self._get_service_url(path)

            if not service_url:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No service found for path: {path}",
                )

            # Check role requirements
            if not self._check_role_requirements(path, current_user.roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            # Build target URL
            target_url = f"{service_url}/api/v1/{path}"
            if request.url.query:
                target_url = f"{target_url}?{request.url.query}"

            # Forward headers
            headers = dict(request.headers)
            headers["X-User-Id"] = current_user.user_id
            headers["X-User-Roles"] = ",".join(current_user.roles)

            # Remove hop-by-hop headers
            for header in ["host", "connection", "keep-alive", "transfer-encoding"]:
                headers.pop(header, None)

            # Get request body
            body = await request.body()

            # Make request to downstream service
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        content=body,
                    )

                    # Return response
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.headers.get("content-type"),
                    )

                except httpx.TimeoutException:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Downstream service timeout",
                    )
                except httpx.ConnectError:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Downstream service unavailable",
                    )
