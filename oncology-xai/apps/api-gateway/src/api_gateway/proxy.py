# DERCAS-ONCO-XAI V1 - API Gateway Proxy
# HTTP proxy functionality for routing requests to internal services

import asyncio
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import httpx
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse
import structlog

from oncology_xai_common.middleware import get_correlation_id
from oncology_xai_common.auth import UserContext
from .config import Settings

logger = structlog.get_logger(__name__)


class ServiceProxy:
    """HTTP proxy for routing requests to internal services."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.service_routes = settings.get_service_routes()
        
        # Create HTTP client with proper configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=settings.proxy_timeout,
                write=settings.proxy_timeout,
                pool=settings.proxy_timeout
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            ),
            follow_redirects=False,
            verify=False  # For development with self-signed certs
        )
        
        # Service health status cache
        self._service_health: Dict[str, bool] = {}
        self._health_check_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def get_target_service(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get target service configuration for a path.
        
        Args:
            path: Request path
            
        Returns:
            Service configuration or None
        """
        # Find matching route
        for route_prefix, service_config in self.service_routes.items():
            if path.startswith(route_prefix):
                return service_config
        
        return None
    
    def build_target_url(self, service_config: Dict[str, Any], path: str, query_string: str = "") -> str:
        """
        Build target URL for proxying.
        
        Args:
            service_config: Service configuration
            path: Request path
            query_string: Query string
            
        Returns:
            Target URL
        """
        base_url = service_config["url"]
        
        # Handle prefix stripping if configured
        if service_config.get("strip_prefix", False):
            # Find the route prefix that matched
            for route_prefix in self.service_routes:
                if path.startswith(route_prefix):
                    path = path[len(route_prefix):]
                    break
        
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        
        # Build full URL
        target_url = urljoin(base_url, path)
        
        if query_string:
            target_url += "?" + query_string
        
        return target_url
    
    async def check_service_health(self, service_url: str) -> bool:
        """
        Check if a service is healthy.
        
        Args:
            service_url: Service base URL
            
        Returns:
            True if service is healthy
        """
        try:
            health_url = urljoin(service_url, "/healthz")
            response = await self.client.get(
                health_url,
                timeout=self.settings.health_check_timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Service health check failed", service_url=service_url, error=str(e))
            return False
    
    async def get_service_health_status(self, service_url: str) -> bool:
        """
        Get cached service health status with periodic updates.
        
        Args:
            service_url: Service base URL
            
        Returns:
            True if service is healthy
        """
        async with self._health_check_lock:
            # Check if we have recent health status
            if service_url not in self._service_health:
                self._service_health[service_url] = await self.check_service_health(service_url)
        
        return self._service_health.get(service_url, False)
    
    def prepare_headers(self, request: Request, user_context: Optional[UserContext] = None) -> Dict[str, str]:
        """
        Prepare headers for proxying.
        
        Args:
            request: Original request
            user_context: User context if authenticated
            
        Returns:
            Headers dictionary
        """
        headers = {}
        
        # Copy relevant headers from original request
        headers_to_copy = [
            "content-type",
            "content-length",
            "accept",
            "accept-encoding",
            "accept-language",
            "user-agent",
        ]
        
        for header_name in headers_to_copy:
            if header_name in request.headers:
                headers[header_name] = request.headers[header_name]
        
        # Add correlation ID
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id
        
        # Add user context headers if authenticated
        if user_context:
            headers["X-User-Id"] = user_context.user_id
            headers["X-User-Roles"] = ",".join(user_context.roles)
            headers["X-User-Permissions"] = ",".join(user_context.permissions)
            
            if user_context.session_id:
                headers["X-Session-Id"] = user_context.session_id
        
        # Add case context if available
        case_id = request.headers.get("X-Case-Id")
        if case_id:
            headers["X-Case-Id"] = case_id
        
        # Remove hop-by-hop headers
        hop_by_hop_headers = [
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade"
        ]
        
        for header in hop_by_hop_headers:
            headers.pop(header, None)
        
        return headers
    
    async def proxy_request(
        self,
        request: Request,
        user_context: Optional[UserContext] = None
    ) -> Response:
        """
        Proxy request to target service.
        
        Args:
            request: Original request
            user_context: User context if authenticated
            
        Returns:
            Response from target service
            
        Raises:
            HTTPException: If proxying fails
        """
        path = request.url.path
        query_string = str(request.url.query) if request.url.query else ""
        
        # Find target service
        service_config = self.get_target_service(path)
        if not service_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No service configured for path: {path}"
            )
        
        # Check service health
        service_url = service_config["url"]
        is_healthy = await self.get_service_health_status(service_url)
        if not is_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable: {service_config['service']}"
            )
        
        # Build target URL
        target_url = self.build_target_url(service_config, path, query_string)
        
        # Prepare headers
        headers = self.prepare_headers(request, user_context)
        
        # Get request body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        logger.info(
            "Proxying request",
            method=request.method,
            path=path,
            target_url=target_url,
            service=service_config["service"],
            correlation_id=get_correlation_id()
        )
        
        try:
            # Make request to target service with retries
            for attempt in range(self.settings.proxy_retries + 1):
                try:
                    response = await self.client.request(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        content=body,
                        timeout=self.settings.proxy_timeout
                    )
                    break
                except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                    if attempt == self.settings.proxy_retries:
                        logger.error(
                            "Proxy request timeout after retries",
                            target_url=target_url,
                            attempt=attempt + 1,
                            error=str(e)
                        )
                        raise HTTPException(
                            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                            detail="Service request timeout"
                        )
                    
                    # Wait before retry
                    await asyncio.sleep(self.settings.proxy_backoff_factor * (2 ** attempt))
                    continue
                except httpx.ConnectError as e:
                    logger.error(
                        "Proxy connection error",
                        target_url=target_url,
                        error=str(e)
                    )
                    # Mark service as unhealthy
                    self._service_health[service_url] = False
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Service connection failed"
                    )
            
            # Prepare response headers
            response_headers = {}
            headers_to_copy = [
                "content-type",
                "content-length",
                "cache-control",
                "expires",
                "last-modified",
                "etag",
                "location",
            ]
            
            for header_name in headers_to_copy:
                if header_name in response.headers:
                    response_headers[header_name] = response.headers[header_name]
            
            # Add correlation ID to response
            correlation_id = get_correlation_id()
            if correlation_id:
                response_headers["X-Correlation-Id"] = correlation_id
            
            logger.info(
                "Proxy response",
                status_code=response.status_code,
                target_url=target_url,
                correlation_id=correlation_id
            )
            
            # Handle streaming responses
            if response.headers.get("transfer-encoding") == "chunked":
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
            else:
                # Regular response
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Proxy request failed",
                target_url=target_url,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Proxy request failed"
            )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all configured services.
        
        Returns:
            Service status dictionary
        """
        status_info = {}
        
        for route_prefix, service_config in self.service_routes.items():
            service_name = service_config["service"]
            service_url = service_config["url"]
            
            if service_name not in status_info:
                is_healthy = await self.check_service_health(service_url)
                status_info[service_name] = {
                    "url": service_url,
                    "healthy": is_healthy,
                    "routes": [route_prefix]
                }
            else:
                status_info[service_name]["routes"].append(route_prefix)
        
        return status_info


# Global proxy instance
_proxy_instance: Optional[ServiceProxy] = None


async def get_proxy(settings: Settings) -> ServiceProxy:
    """Get service proxy instance."""
    global _proxy_instance
    if _proxy_instance is None:
        _proxy_instance = ServiceProxy(settings)
    return _proxy_instance


async def cleanup_proxy():
    """Cleanup proxy resources."""
    global _proxy_instance
    if _proxy_instance is not None:
        await _proxy_instance.client.aclose()
        _proxy_instance = None
