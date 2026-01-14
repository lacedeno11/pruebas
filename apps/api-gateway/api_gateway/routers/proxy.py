"""
DERCAS-ONCO-XAI API Gateway Proxy Router

Request routing to internal services with authentication and authorization.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
import httpx

from dercas_common.auth import get_current_user, require_clinician, require_admin, require_auditor, UserInfo
from dercas_common.middleware import get_correlation_id

from ..services import ServiceRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


def get_service_registry(request: Request) -> ServiceRegistry:
    """Get service registry from app state."""
    return request.app.state.service_registry


async def proxy_to_service(
    service_name: str,
    request: Request,
    service_registry: ServiceRegistry,
    path_override: Optional[str] = None,
    require_auth: bool = True,
    current_user: Optional[UserInfo] = None
) -> Response:
    """Generic proxy function to route requests to internal services."""
    
    # Extract path for the target service
    if path_override:
        service_path = path_override
    else:
        # Remove /api/v1/{service} prefix
        path_parts = request.url.path.split('/')
        if len(path_parts) >= 4:
            service_path = '/' + '/'.join(path_parts[4:])
        else:
            service_path = '/'
    
    # Prepare headers
    headers = dict(request.headers)
    
    # Add authentication headers if user is authenticated
    if current_user:
        headers['X-User-ID'] = current_user.user_id
        headers['X-User-Roles'] = ','.join(current_user.roles)
        headers['X-User-Permissions'] = ','.join(current_user.permissions)
    
    # Add correlation ID
    correlation_id = get_correlation_id(request)
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id
    
    # Remove hop-by-hop headers
    hop_by_hop_headers = {
        'connection', 'keep-alive', 'proxy-authenticate',
        'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
    }
    headers = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop_headers}
    
    # Get request body
    body = None
    if request.method in ['POST', 'PUT', 'PATCH']:
        body = await request.body()
    
    try:
        # Proxy the request
        response = await service_registry.proxy_request(
            service_name=service_name,
            method=request.method,
            path=service_path,
            headers=headers,
            params=dict(request.query_params),
            content=body if body else None
        )
        
        # Prepare response headers
        response_headers = dict(response.headers)
        
        # Remove hop-by-hop headers from response
        response_headers = {k: v for k, v in response_headers.items() if k.lower() not in hop_by_hop_headers}
        
        # Add correlation ID to response
        if correlation_id:
            response_headers['X-Correlation-ID'] = correlation_id
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get('content-type')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proxy error for {service_name}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Service {service_name} error: {str(e)}"
        )


# =============================================================================
# CASE SERVICE ROUTES
# =============================================================================

@router.api_route("/cases/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_cases(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Proxy requests to case service (requires clinician role)."""
    return await proxy_to_service(
        service_name="cases",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# IMAGE SERVICE ROUTES
# =============================================================================

@router.api_route("/images/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_images(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Proxy requests to image service (requires clinician role)."""
    return await proxy_to_service(
        service_name="images",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# INFERENCE SERVICE ROUTES
# =============================================================================

@router.api_route("/inference/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_inference(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Proxy requests to inference service (requires clinician role)."""
    return await proxy_to_service(
        service_name="inference",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# EHR SERVICE ROUTES
# =============================================================================

@router.api_route("/ehr/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_ehr(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Proxy requests to EHR service (requires clinician role)."""
    return await proxy_to_service(
        service_name="ehr",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# GRAPH SERVICE ROUTES
# =============================================================================

@router.api_route("/graph/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_graph(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Proxy requests to graph service (requires clinician role)."""
    return await proxy_to_service(
        service_name="graph",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# ONTOLOGY ADMIN SERVICE ROUTES
# =============================================================================

@router.api_route("/ontology/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_ontology(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_admin)
):
    """Proxy requests to ontology admin service (requires admin role)."""
    return await proxy_to_service(
        service_name="ontology",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# AUDIT SERVICE ROUTES
# =============================================================================

@router.api_route("/audit/{path:path}", methods=["GET"])
async def proxy_audit(
    path: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_auditor)
):
    """Proxy requests to audit service (requires auditor role, read-only)."""
    # Audit service is read-only through the gateway
    if request.method != "GET":
        raise HTTPException(
            status_code=405,
            detail="Only GET requests are allowed for audit service"
        )
    
    return await proxy_to_service(
        service_name="audit",
        request=request,
        service_registry=service_registry,
        path_override=f"/{path}",
        current_user=current_user
    )


# =============================================================================
# SPECIAL UPLOAD ENDPOINTS
# =============================================================================

@router.post("/images/upload")
async def upload_image(
    request: Request,
    case_id: str = Form(...),
    file: UploadFile = File(...),
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Special endpoint for image uploads with enhanced handling."""
    
    # Validate file size (already handled by middleware, but double-check)
    if hasattr(file, 'size') and file.size and file.size > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(
            status_code=413,
            detail="File size exceeds 100MB limit"
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="Only image files are allowed"
        )
    
    # Prepare headers
    headers = {
        'X-User-ID': current_user.user_id,
        'X-User-Roles': ','.join(current_user.roles),
        'X-Correlation-ID': get_correlation_id(request)
    }
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Prepare multipart form data
        files = {'file': (file.filename, file_content, file.content_type)}
        data = {'case_id': case_id}
        
        # Use httpx to send multipart request
        service_url = service_registry.get_service_url("images")
        if not service_url:
            raise HTTPException(status_code=503, detail="Image service unavailable")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for uploads
            response = await client.post(
                f"{service_url}/upload",
                headers=headers,
                files=files,
                data=data
            )
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get('content-type')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

@router.post("/batch/inference")
async def batch_inference(
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Batch inference endpoint for multiple images."""
    return await proxy_to_service(
        service_name="inference",
        request=request,
        service_registry=service_registry,
        path_override="/batch",
        current_user=current_user
    )


@router.get("/batch/status/{batch_id}")
async def batch_status(
    batch_id: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Get batch operation status."""
    return await proxy_to_service(
        service_name="inference",
        request=request,
        service_registry=service_registry,
        path_override=f"/batch/{batch_id}/status",
        current_user=current_user
    )


# =============================================================================
# STREAMING ENDPOINTS
# =============================================================================

@router.get("/inference/stream/{job_id}")
async def stream_inference_progress(
    job_id: str,
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_clinician)
):
    """Stream inference job progress."""
    
    # Get service URL
    service_url = service_registry.get_service_url("inference")
    if not service_url:
        raise HTTPException(status_code=503, detail="Inference service unavailable")
    
    # Prepare headers
    headers = {
        'X-User-ID': current_user.user_id,
        'X-Correlation-ID': get_correlation_id(request),
        'Accept': 'text/event-stream'
    }
    
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                'GET',
                f"{service_url}/stream/{job_id}",
                headers=headers
            ) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to stream inference progress"
                    )
                
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Correlation-ID": get_correlation_id(request)
                    }
                )
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Streaming failed: {str(e)}"
        )


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/services/status")
async def admin_services_status(
    request: Request,
    service_registry: ServiceRegistry = Depends(get_service_registry),
    current_user: UserInfo = Depends(require_admin)
):
    """Get detailed status of all services (admin only)."""
    try:
        health_summary = await service_registry.get_service_health_summary()
        
        return {
            "services": health_summary,
            "gateway_info": {
                "version": "0.1.0",
                "uptime": "unknown",  # Would track actual uptime
                "requests_processed": "unknown",  # Would track metrics
                "rate_limit_hits": "unknown"  # Would track rate limiting
            },
            "requested_by": current_user.user_id,
            "correlation_id": get_correlation_id(request)
        }
    except Exception as e:
        logger.error(f"Admin status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get services status: {str(e)}"
        )


@router.post("/admin/services/{service_name}/restart")
async def admin_restart_service(
    service_name: str,
    request: Request,
    current_user: UserInfo = Depends(require_admin)
):
    """Restart a service (placeholder - would integrate with orchestrator)."""
    # This would integrate with Kubernetes or Docker Compose to restart services
    # For now, it's a placeholder
    
    logger.info(
        f"Service restart requested by admin: {service_name}",
        extra={
            'service': service_name,
            'admin_user': current_user.user_id,
            'correlation_id': get_correlation_id(request)
        }
    )
    
    return {
        "message": f"Service restart requested: {service_name}",
        "note": "This is a placeholder - would integrate with orchestrator",
        "requested_by": current_user.user_id,
        "service": service_name
    }
