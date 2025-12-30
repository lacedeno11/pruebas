"""
DERCAS-ONCO-XAI V1 - Service Proxy

Request proxying to internal services using httpx.
"""

import logging
from typing import Dict, Optional

import httpx
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.middleware import get_correlation_id, get_case_id, get_user_id
from packages.common.errors import ErrorCode, create_http_exception

logger = logging.getLogger(__name__)


class ServiceProxy:
    """Proxy for forwarding requests to internal services."""
    
    def __init__(self, service_urls: Dict[str, str]):
        self.service_urls = service_urls
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        logger.info(f"Initialized service proxy with services: {list(service_urls.keys())}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Service proxy client closed")
    
    async def proxy_request(
        self,
        request: Request,
        service_name: str,
        path: str,
        auth_handler,
        rate_limiter,
        max_content_length: Optional[int] = None
    ) -> Response:
        """
        Proxy a request to an internal service.
        
        Args:
            request: Incoming FastAPI request
            service_name: Target service name
            path: Target path on the service
            auth_handler: Authentication handler
            rate_limiter: Rate limiter instance
            max_content_length: Maximum content length for the request
            
        Returns:
            Response: Proxied response from the service
        """
        # Get service URL
        service_url = self.service_urls.get(service_name)
        if not service_url:
            raise create_http_exception(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Service not available: {service_name}",
                correlation_id=get_correlation_id(request)
            )
        
        # Authenticate request
        user_claims = await auth_handler.authenticate_request(request)
        
        # Check rate limits
        rate_limit_key = f"{service_name}:{user_claims.sub}"
        await rate_limiter.check_rate_limit(rate_limit_key)
        
        # Check content length if specified
        if max_content_length and request.headers.get("content-length"):
            content_length = int(request.headers.get("content-length", 0))
            if content_length > max_content_length:
                raise create_http_exception(
                    error_code=ErrorCode.FILE_TOO_LARGE,
                    message=f"Request too large: {content_length} bytes (max: {max_content_length})",
                    correlation_id=get_correlation_id(request)
                )
        
        # Prepare target URL
        target_url = f"{service_url.rstrip('/')}/{path.lstrip('/')}"
        
        # Prepare headers for forwarding
        forward_headers = self._prepare_forward_headers(request, user_claims)
        
        try:
            # Get request body
            body = await self._get_request_body(request)
            
            # Make the proxied request
            logger.info(
                f"Proxying {request.method} request to {service_name}",
                extra={
                    "correlation_id": get_correlation_id(request),
                    "target_url": target_url,
                    "user_id": user_claims.sub
                }
            )
            
            response = await self.client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                params=dict(request.query_params),
                content=body,
                follow_redirects=False
            )
            
            # Handle the response
            return await self._create_response(response, request)
            
        except httpx.TimeoutException:
            logger.error(
                f"Timeout proxying request to {service_name}",
                extra={"correlation_id": get_correlation_id(request)}
            )
            raise create_http_exception(
                error_code=ErrorCode.PROCESSING_TIMEOUT,
                message=f"Service timeout: {service_name}",
                correlation_id=get_correlation_id(request)
            )
            
        except httpx.ConnectError:
            logger.error(
                f"Connection error proxying request to {service_name}",
                extra={"correlation_id": get_correlation_id(request)}
            )
            raise create_http_exception(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Service unavailable: {service_name}",
                correlation_id=get_correlation_id(request)
            )
            
        except Exception as e:
            logger.error(
                f"Error proxying request to {service_name}: {e}",
                extra={"correlation_id": get_correlation_id(request)},
                exc_info=True
            )
            raise create_http_exception(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=f"Service error: {service_name}",
                correlation_id=get_correlation_id(request)
            )
    
    def _prepare_forward_headers(self, request: Request, user_claims) -> Dict[str, str]:
        """Prepare headers for forwarding to internal services."""
        # Start with essential headers
        forward_headers = {
            "Content-Type": request.headers.get("content-type", "application/json"),
            "Accept": request.headers.get("accept", "application/json"),
            "User-Agent": "api-gateway/1.0.0",
        }
        
        # Add correlation tracking headers
        correlation_id = get_correlation_id(request)
        if correlation_id:
            forward_headers["X-Correlation-Id"] = correlation_id
        
        case_id = get_case_id(request)
        if case_id:
            forward_headers["X-Case-Id"] = case_id
        
        # Add user context headers
        forward_headers["X-User-Id"] = user_claims.sub
        if user_claims.preferred_username:
            forward_headers["X-Username"] = user_claims.preferred_username
        if user_claims.email:
            forward_headers["X-User-Email"] = user_claims.email
        
        # Add user roles
        if user_claims.realm_access and user_claims.realm_access.get("roles"):
            forward_headers["X-User-Roles"] = ",".join(user_claims.realm_access["roles"])
        
        # Add service identification
        forward_headers["X-Service-Name"] = "api-gateway"
        forward_headers["X-Service-Version"] = "1.0.0"
        
        # Forward specific headers that services might need
        headers_to_forward = [
            "authorization",  # In case services need the original token
            "x-request-id",
            "x-trace-id",
            "x-span-id",
            "content-encoding",
            "content-disposition"
        ]
        
        for header in headers_to_forward:
            value = request.headers.get(header)
            if value:
                forward_headers[header] = value
        
        return forward_headers
    
    async def _get_request_body(self, request: Request) -> Optional[bytes]:
        """Get request body for forwarding."""
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                return await request.body()
            return None
        except Exception as e:
            logger.warning(f"Error reading request body: {e}")
            return None
    
    async def _create_response(self, upstream_response: httpx.Response, original_request: Request) -> Response:
        """Create FastAPI response from upstream service response."""
        # Prepare response headers
        response_headers = {}
        
        # Forward specific headers from upstream
        headers_to_forward = [
            "content-type",
            "content-disposition",
            "content-encoding",
            "cache-control",
            "etag",
            "last-modified",
            "location"
        ]
        
        for header in headers_to_forward:
            value = upstream_response.headers.get(header)
            if value:
                response_headers[header] = value
        
        # Add correlation headers
        correlation_id = get_correlation_id(original_request)
        if correlation_id:
            response_headers["X-Correlation-Id"] = correlation_id
        
        case_id = get_case_id(original_request)
        if case_id:
            response_headers["X-Case-Id"] = case_id
        
        # Handle different response types
        content_type = upstream_response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # JSON response
            try:
                content = upstream_response.json()
            except Exception:
                content = upstream_response.text
            
            return Response(
                content=upstream_response.content,
                status_code=upstream_response.status_code,
                headers=response_headers,
                media_type="application/json"
            )
        
        elif content_type.startswith("text/"):
            # Text response
            return Response(
                content=upstream_response.text,
                status_code=upstream_response.status_code,
                headers=response_headers,
                media_type=content_type
            )
        
        elif "stream" in content_type or upstream_response.headers.get("transfer-encoding") == "chunked":
            # Streaming response
            async def stream_generator():
                async for chunk in upstream_response.aiter_bytes():
                    yield chunk
            
            return StreamingResponse(
                stream_generator(),
                status_code=upstream_response.status_code,
                headers=response_headers,
                media_type=content_type
            )
        
        else:
            # Binary response
            return Response(
                content=upstream_response.content,
                status_code=upstream_response.status_code,
                headers=response_headers,
                media_type=content_type or "application/octet-stream"
            )
    
    async def health_check_service(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        service_url = self.service_urls.get(service_name)
        if not service_url:
            return False
        
        try:
            response = await self.client.get(
                f"{service_url}/healthz",
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {service_name}: {e}")
            return False
    
    async def get_service_health_status(self) -> Dict[str, bool]:
        """Get health status for all services."""
        health_status = {}
        
        for service_name in self.service_urls.keys():
            health_status[service_name] = await self.health_check_service(service_name)
        
        return health_status
