"""
DERCAS-ONCO-XAI V1 - Image Service

FastAPI service for medical image upload, storage, and management with MinIO S3 integration.
"""

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.middleware import (
    CorrelationIdMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    get_correlation_id,
    get_user_id,
    get_case_id
)
from packages.common.models import HealthCheckResponse
from packages.common.errors import (
    ErrorCode,
    create_http_exception,
    create_image_not_found_error,
    create_case_not_found_error,
    create_file_format_error,
    platform_exception_to_http_exception
)
from packages.event_contracts.messaging import EventBus

from .config import get_settings
from .database import get_db, init_db
from .models import Image
from .schemas import (
    ImageResponse,
    ImageUploadResponse,
    ImageListResponse,
    ViewerUrlResponse
)
from .services import ImageService, StorageService
from .events import EventPublisher
from .validation import FileValidator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Image Service...")
    
    settings = get_settings()
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize storage service
    app.state.storage_service = StorageService(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket_name=settings.s3_bucket,
        region=settings.s3_region
    )
    await app.state.storage_service.initialize()
    logger.info("Storage service initialized")
    
    # Initialize event bus
    app.state.event_bus = EventBus(
        connection_url=settings.rabbitmq_url,
        service_name="image-service"
    )
    await app.state.event_bus.start()
    logger.info("Event bus initialized")
    
    # Initialize event publisher
    app.state.event_publisher = EventPublisher(app.state.event_bus)
    
    # Initialize file validator
    app.state.file_validator = FileValidator(
        max_file_size=settings.max_file_size,
        allowed_formats=settings.allowed_formats
    )
    
    logger.info("Image Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Image Service...")
    await app.state.event_bus.stop()
    await app.state.storage_service.close()
    logger.info("Image Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DERCAS-ONCO-XAI Image Service",
    description="Medical Image Upload and Management Service for the Explainable AI Oncology Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware, enable_cors=True)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CorrelationIdMiddleware)


# Health check endpoint
@app.get("/healthz", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    # Check storage connectivity
    storage_healthy = await app.state.storage_service.health_check()
    
    return HealthCheckResponse(
        status="healthy" if storage_healthy else "degraded",
        version="1.0.0",
        dependencies={
            "database": "healthy",  # TODO: Add actual health checks
            "storage": "healthy" if storage_healthy else "unhealthy",
            "rabbitmq": "healthy"
        }
    )


# Image upload endpoint
@app.post("/api/v1/cases/{case_id}/images:upload", response_model=ImageUploadResponse, status_code=201)
async def upload_image(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload an image for a case."""
    correlation_id = get_correlation_id(request)
    user_id = get_user_id(request)
    
    logger.info(
        f"Uploading image for case: {case_id}, filename: {file.filename}",
        extra={"correlation_id": correlation_id, "case_id": case_id}
    )
    
    try:
        # Validate file
        await app.state.file_validator.validate_file(file)
        
        # Initialize services
        image_service = ImageService(db, app.state.storage_service)
        
        # Upload image
        image = await image_service.upload_image(
            case_id=case_id,
            file=file,
            description=description,
            uploaded_by=user_id
        )
        
        # Publish image uploaded event
        await app.state.event_publisher.publish_image_uploaded(
            image=image,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        logger.info(
            f"Image uploaded successfully: {image.id}",
            extra={"correlation_id": correlation_id, "case_id": case_id, "image_id": str(image.id)}
        )
        
        return ImageUploadResponse.from_orm(image)
        
    except Exception as e:
        logger.error(
            f"Failed to upload image for case {case_id}: {e}",
            extra={"correlation_id": correlation_id, "case_id": case_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


# List images for a case
@app.get("/api/v1/cases/{case_id}/images", response_model=ImageListResponse)
async def list_case_images(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """List all images for a case."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Listing images for case: {case_id}",
        extra={"correlation_id": correlation_id, "case_id": case_id}
    )
    
    try:
        image_service = ImageService(db, app.state.storage_service)
        images = await image_service.list_case_images(case_id)
        
        image_responses = [ImageResponse.from_orm(img) for img in images]
        
        return ImageListResponse(
            images=image_responses,
            total=len(image_responses),
            case_id=case_id
        )
        
    except Exception as e:
        logger.error(
            f"Failed to list images for case {case_id}: {e}",
            extra={"correlation_id": correlation_id, "case_id": case_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


# Get image by ID
@app.get("/api/v1/images/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get an image by ID."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Getting image: {image_id}",
        extra={"correlation_id": correlation_id, "image_id": image_id}
    )
    
    try:
        image_service = ImageService(db, app.state.storage_service)
        image = await image_service.get_image_by_id(image_id)
        
        if not image:
            raise create_image_not_found_error(image_id, correlation_id)
        
        return ImageResponse.from_orm(image)
        
    except Exception as e:
        logger.error(
            f"Failed to get image {image_id}: {e}",
            extra={"correlation_id": correlation_id, "image_id": image_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


# Get viewer URL for image
@app.get("/api/v1/images/{image_id}/viewer-url", response_model=ViewerUrlResponse)
async def get_image_viewer_url(
    image_id: str,
    request: Request,
    expires_in: int = 3600,  # 1 hour default
    db: AsyncSession = Depends(get_db)
):
    """Get a signed URL for viewing an image."""
    correlation_id = get_correlation_id(request)
    
    logger.info(
        f"Getting viewer URL for image: {image_id}",
        extra={"correlation_id": correlation_id, "image_id": image_id}
    )
    
    try:
        image_service = ImageService(db, app.state.storage_service)
        image = await image_service.get_image_by_id(image_id)
        
        if not image:
            raise create_image_not_found_error(image_id, correlation_id)
        
        # Generate signed URL
        signed_url = await app.state.storage_service.generate_presigned_url(
            object_key=image.storage_path,
            expires_in=expires_in
        )
        
        return ViewerUrlResponse(
            image_id=image.image_id,
            viewer_url=signed_url,
            expires_in=expires_in
        )
        
    except Exception as e:
        logger.error(
            f"Failed to get viewer URL for image {image_id}: {e}",
            extra={"correlation_id": correlation_id, "image_id": image_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


# Delete image
@app.delete("/api/v1/images/{image_id}", status_code=204)
async def delete_image(
    image_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete an image."""
    correlation_id = get_correlation_id(request)
    user_id = get_user_id(request)
    
    logger.info(
        f"Deleting image: {image_id}",
        extra={"correlation_id": correlation_id, "image_id": image_id}
    )
    
    try:
        image_service = ImageService(db, app.state.storage_service)
        
        # Get image before deletion for event
        image = await image_service.get_image_by_id(image_id)
        if not image:
            raise create_image_not_found_error(image_id, correlation_id)
        
        # Delete image
        await image_service.delete_image(image_id)
        
        # Publish image deleted event
        await app.state.event_publisher.publish_image_deleted(
            image=image,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        logger.info(
            f"Image deleted successfully: {image_id}",
            extra={"correlation_id": correlation_id, "image_id": image_id}
        )
        
    except Exception as e:
        logger.error(
            f"Failed to delete image {image_id}: {e}",
            extra={"correlation_id": correlation_id, "image_id": image_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


# Direct image access (redirect to signed URL)
@app.get("/api/v1/images/{image_id}/download")
async def download_image(
    image_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Download an image (redirects to signed URL)."""
    correlation_id = get_correlation_id(request)
    
    try:
        image_service = ImageService(db, app.state.storage_service)
        image = await image_service.get_image_by_id(image_id)
        
        if not image:
            raise create_image_not_found_error(image_id, correlation_id)
        
        # Generate signed URL for download
        signed_url = await app.state.storage_service.generate_presigned_url(
            object_key=image.storage_path,
            expires_in=300  # 5 minutes for download
        )
        
        return RedirectResponse(url=signed_url, status_code=302)
        
    except Exception as e:
        logger.error(
            f"Failed to download image {image_id}: {e}",
            extra={"correlation_id": correlation_id, "image_id": image_id},
            exc_info=True
        )
        raise platform_exception_to_http_exception(e)


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
