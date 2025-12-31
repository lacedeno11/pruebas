"""
DERCAS-ONCO-XAI API Gateway Services

Service registry and HTTP client for routing requests to internal services.
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException

from .config import Settings

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for managing internal service connections and health checks."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.services = {
            "cases": settings.CASE_SERVICE_URL,
            "images": settings.IMAGE_SERVICE_URL,
            "inference": settings.INFERENCE_SERVICE_URL,
            "ehr": settings.EHR_SERVICE_URL,
            "graph": settings.GRAPH_SERVICE_URL,
            "ontology": settings.ONTOLOGY_ADMIN_SERVICE_URL,
            "audit": settings.AUDIT_SERVICE_URL,
        }
        self.health_status: Dict[str, bool] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def initialize(self):
        """Initialize HTTP client and perform initial health checks."""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=self.settings.SERVICE_TIMEOUT_SECONDS,
                write=self.settings.SERVICE_TIMEOUT_SECONDS,
                pool=self.settings.SERVICE_TIMEOUT_SECONDS
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            ),
            follow_redirects=True
        )
        
        # Initialize health status
        for service_name in self.services:
            self.health_status[service_name] = False
        
        logger.info("Service registry initialized")
    
    async def close(self):
        """Close HTTP client and cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        logger.info("Service registry closed")
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get service URL by name."""
        return self.services.get(service_name)
    
    async def is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        return self.health_status.get(service_name, False)
    
    async def health_check_service(self, service_name: str) -> bool:
        """Perform health check for a specific service."""
        service_url = self.get_service_url(service_name)
        if not service_url:
            logger.warning(f"Unknown service: {service_name}")
            return False
        
        if not self.http_client:
            logger.error("HTTP client not initialized")
            return False
        
        try:
            health_url = urljoin(service_url, "/healthz")
            response = await self.http_client.get(
                health_url,
                timeout=self.settings.HEALTH_CHECK_TIMEOUT
            )
            
            is_healthy = response.status_code == 200
            self.health_status[service_name] = is_healthy
            
            if is_healthy:
                logger.debug(f"Service {service_name} is healthy")
            else:
                logger.warning(f"Service {service_name} health check failed: {response.status_code}")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            self.health_status[service_name] = False
            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks for all services."""
        tasks = [
            self.health_check_service(service_name)
            for service_name in self.services
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = {}
        for service_name, result in zip(self.services.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Health check error for {service_name}: {result}")
                health_results[service_name] = False
            else:
                health_results[service_name] = result
        
        return health_results
    
    async def proxy_request(
        self,
        service_name: str,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """Proxy request to internal service."""
        service_url = self.get_service_url(service_name)
        if not service_url:
            raise HTTPException(
                status_code=404,
                detail=f"Service '{service_name}' not found"
            )
        
        if not self.http_client:
            raise HTTPException(
                status_code=503,
                detail="Service registry not initialized"
            )
        
        # Build full URL
        full_url = urljoin(service_url, path)
        
        # Prepare headers
        request_headers = headers or {}
        
        # Set timeout
        request_timeout = timeout or self.settings.SERVICE_TIMEOUT_SECONDS
        if path.startswith('/upload') or 'upload' in path:
            request_timeout = self.settings.UPLOAD_TIMEOUT_SECONDS
        
        try:
            logger.debug(
                f"Proxying {method} request to {service_name}: {full_url}",
                extra={
                    'service': service_name,
                    'method': method,
                    'path': path,
                    'timeout': request_timeout
                }
            )
            
            response = await self.http_client.request(
                method=method,
                url=full_url,
                headers=request_headers,
                params=params,
                json=json_data,
                content=content,
                timeout=request_timeout
            )
            
            logger.debug(
                f"Service {service_name} responded: {response.status_code}",
                extra={
                    'service': service_name,
                    'status_code': response.status_code,
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
            )
            
            return response
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling {service_name}: {e}")
            raise HTTPException(
                status_code=504,
                detail=f"Service '{service_name}' timeout"
            )
        except httpx.ConnectError as e:
            logger.error(f"Connection error to {service_name}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Service '{service_name}' unavailable"
            )
        except Exception as e:
            logger.error(f"Error calling {service_name}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Service '{service_name}' error"
            )
    
    async def get_service_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all services."""
        health_results = await self.health_check_all()
        
        healthy_count = sum(1 for status in health_results.values() if status)
        total_count = len(health_results)
        
        return {
            "services": health_results,
            "summary": {
                "healthy": healthy_count,
                "total": total_count,
                "overall_healthy": healthy_count == total_count
            }
        }
