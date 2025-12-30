# DERCAS-ONCO-XAI V1 - Image Service Main Application
# FastAPI application for medical image management and storage

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Request, Response, HTTPException, status, Depends, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from oncology_xai_common.middleware import CorrelationIdMiddleware, get_correlation_id
from oncology_xai_common.exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    ValidationError
)
from oncology_xai_common.auth import get_user_context, UserContext

from .config import Settings, get_settings
from .database import init_database, cleanup_database, get_db_session
from .storage import get_storage, cleanup_storage
from .validation import create_image_validator
from .upload import get_upload_handler, cleanup_upload_handler
from .events import get_event_emitter, cleanup_event_emitter
from .crud import ImageCRUD
from .schemas import (
    ImageResponse, ImageSummary, ImageUpload, ImageUpdate, ImageUploadResponse,
    SignedUrlResponse, ViewerUrlResponse, ImageStatistics, ValidationResult,
    PaginationParams, PaginatedImages, ImageFilters, HealthCheck,
    ProcessingStatusEnum, ImageFormatEnum, ModalityEnum
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Image Service")
    
    settings = app.state.settings
    
    # Initialize database
    await init_database(settings)
    
    # Initialize storage
    await get_storage(settings)
    
    # Initialize upload handler
    await get_upload_handler(settings)
    
    # Initialize event emitter
    await get_event_emitter(settings)
    
    # Store startup time
    app.state.start_time = time.time()
    
    logger.info("Image Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Image Service")
    
    # Cleanup resources
    await cleanup_event_emitter()
    await cleanup_upload_handler()
    await cleanup_storage()
    await cleanup_database()
    
    logger.info("Image Service shutdown complete")


def create_app(settings: Settings = None) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Medical image management and storage service for DERCAS-ONCO-XAI V1 platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Store settings in app state
    app.state.settings = settings
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add correlation ID middleware
    app.add_middleware(CorrelationIdMiddleware)
    
    # Add custom exception handlers
    add_exception_handlers(app)
    
    # Add middleware for request/response logging
    app.middleware("http")(request_logging_middleware)
    
    # Add API endpoints
    add_api_endpoints(app)
    
    return app


def add_exception_handlers(app: FastAPI):
    """Add custom exception handlers."""
    
    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.warning(
            "Authentication error",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication failed",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        """Handle authorization errors."""
        logger.warning(
            "Authorization error",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "Access denied",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handle validation errors."""
        logger.warning(
            "Validation error",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id()
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation failed",
                "message": str(exc),
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "message": exc.detail,
                "correlation_id": get_correlation_id()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
            correlation_id=get_correlation_id(),
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "correlation_id": get_correlation_id()
            }
        )


async def request_logging_middleware(request: Request, call_next):
    """Middleware for request/response logging."""
    start_time = time.time()
    correlation_id = get_correlation_id()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        query=str(request.url.query) if request.url.query else None,
        correlation_id=correlation_id,
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
        correlation_id=correlation_id
    )
    
    return response


def add_api_endpoints(app: FastAPI):
    """Add all API endpoints to the application."""
    
    # Health check endpoint
    @app.get("/healthz", response_model=HealthCheck)
    async def health_check():
        """Health check endpoint."""
        return HealthCheck(
            status="healthy",
            timestamp=datetime.utcnow(),
            service="image-service",
            version=app.state.settings.app_version,
            database="connected",
            storage="connected"
        )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "DERCAS-ONCO-XAI Image Service",
            "version": app.state.settings.app_version,
            "status": "running",
            "timestamp": time.time()
        }
    
    # Service info endpoint
    @app.get("/api/v1/info")
    async def service_info(
        settings: Settings = Depends(get_settings),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Get service information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime_seconds": time.time() - app.state.start_time,
            "max_file_size_mb": settings.get_max_file_size_mb(),
            "allowed_formats": settings.allowed_formats,
            "user": {
                "user_id": user_context.user_id,
                "roles": user_context.roles
            }
        }
    
    # Image upload endpoint
    @app.post("/api/v1/images", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
    async def upload_image(
        file: UploadFile = File(..., description="Image file to upload"),
        case_id: Optional[str] = Form(None, description="Case ID to associate with image"),
        modality: Optional[ModalityEnum] = Form(None, description="Imaging modality"),
        acquisition_date: Optional[str] = Form(None, description="Acquisition date (ISO format)"),
        patient_position: Optional[str] = Form(None, description="Patient position"),
        slice_thickness: Optional[float] = Form(None, description="Slice thickness in mm"),
        pixel_spacing: Optional[str] = Form(None, description="Pixel spacing"),
        tags: Optional[str] = Form(None, description="Comma-separated tags"),
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Upload a new image."""
        try:
            # Parse optional fields
            acquisition_date_dt = None
            if acquisition_date:
                try:
                    acquisition_date_dt = datetime.fromisoformat(acquisition_date.replace('Z', '+00:00'))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid acquisition_date format. Use ISO format."
                    )
            
            tags_list = None
            if tags:
                tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            
            # Prepare metadata
            metadata = {}
            if modality:
                metadata["modality"] = modality
            if acquisition_date_dt:
                metadata["acquisition_date"] = acquisition_date_dt.isoformat()
            if patient_position:
                metadata["patient_position"] = patient_position
            if slice_thickness:
                metadata["slice_thickness"] = slice_thickness
            if pixel_spacing:
                metadata["pixel_spacing"] = pixel_spacing
            if tags_list:
                metadata["tags"] = tags_list
            
            # Handle upload
            upload_handler = await get_upload_handler()
            upload_result = await upload_handler.handle_upload(
                file, case_id, user_context.user_id, metadata
            )
            
            # Create database record
            image_data = upload_result["image_data"]
            if modality:
                image_data["modality"] = modality
            if acquisition_date_dt:
                image_data["acquisition_date"] = acquisition_date_dt
            if patient_position:
                image_data["patient_position"] = patient_position
            if slice_thickness:
                image_data["slice_thickness"] = slice_thickness
            if pixel_spacing:
                image_data["pixel_spacing"] = pixel_spacing
            if tags_list:
                image_data["tags"] = tags_list
            
            image = await ImageCRUD.create(db, image_data, user_context.user_id)
            await db.commit()
            
            # Emit event
            event_emitter = await get_event_emitter()
            await event_emitter.emit_image_uploaded(image, get_correlation_id())
            
            # Prepare response
            validation_result = upload_result["validation_result"]
            response = ImageUploadResponse(
                image_id=image.id,
                original_filename=image.original_filename,
                file_format=image.file_format,
                file_size=image.file_size,
                file_size_mb=image.file_size_mb,
                dimensions=image.dimensions,
                storage_key=image.storage_key,
                md5_hash=image.md5_hash,
                sha256_hash=image.sha256_hash,
                processing_status=image.processing_status,
                validation_warnings=validation_result.get("warnings"),
                upload_timestamp=image.created_at
            )
            
            logger.info(
                "Image uploaded successfully",
                image_id=image.id,
                filename=image.original_filename,
                case_id=case_id,
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Image upload failed",
                filename=file.filename if file else "unknown",
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image upload failed"
            )
    
    # List images endpoint
    @app.get("/api/v1/images", response_model=PaginatedImages)
    async def list_images(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size"),
        case_id: Optional[str] = Query(None, description="Filter by case ID"),
        file_format: Optional[ImageFormatEnum] = Query(None, description="Filter by format"),
        modality: Optional[ModalityEnum] = Query(None, description="Filter by modality"),
        processing_status: Optional[ProcessingStatusEnum] = Query(None, description="Filter by processing status"),
        has_thumbnail: Optional[bool] = Query(None, description="Filter by thumbnail availability"),
        search: Optional[str] = Query(None, description="Search in filename"),
        order_by: str = Query("created_at", description="Field to order by"),
        order_desc: bool = Query(True, description="Order descending"),
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """List images with pagination and filtering."""
        try:
            # Create filters
            filters = ImageFilters(
                case_id=case_id,
                file_format=file_format,
                modality=modality,
                processing_status=processing_status,
                has_thumbnail=has_thumbnail,
                search=search
            )
            
            pagination = PaginationParams(page=page, size=size)
            
            # Get images
            images, total_count = await ImageCRUD.list_images(
                db, pagination, filters, order_by, order_desc
            )
            
            # Convert to summary format
            image_summaries = []
            for image in images:
                summary = ImageSummary(
                    id=image.id,
                    original_filename=image.original_filename,
                    file_format=image.file_format,
                    file_size_mb=image.file_size_mb,
                    dimensions=image.dimensions,
                    modality=image.modality,
                    processing_status=image.processing_status,
                    has_thumbnail=image.has_thumbnail,
                    view_count=image.view_count,
                    created_at=image.created_at,
                    case_id=image.case_id
                )
                image_summaries.append(summary)
            
            return PaginatedImages(
                items=image_summaries,
                total=total_count,
                page=page,
                size=size
            )
            
        except Exception as e:
            logger.error(
                "Failed to list images",
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list images"
            )
    
    # Get image endpoint
    @app.get("/api/v1/images/{image_id}", response_model=ImageResponse)
    async def get_image(
        image_id: str,
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Get image by ID."""
        try:
            image = await ImageCRUD.get_by_id(db, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image not found"
                )
            
            return image
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get image",
                image_id=image_id,
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get image"
            )
    
    # Update image endpoint
    @app.patch("/api/v1/images/{image_id}", response_model=ImageResponse)
    async def update_image(
        image_id: str,
        image_data: ImageUpdate,
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Update image metadata."""
        try:
            # Get existing image
            image = await ImageCRUD.get_by_id(db, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image not found"
                )
            
            # Store old processing status for event emission
            old_processing_status = image.processing_status
            
            # Update image
            update_data = image_data.dict(exclude_unset=True)
            updated_image = await ImageCRUD.update(db, image, update_data, user_context.user_id)
            await db.commit()
            
            # Emit processing status change event if changed
            if (image_data.processing_status and 
                image_data.processing_status != old_processing_status):
                event_emitter = await get_event_emitter()
                await event_emitter.emit_image_processing_status_changed(
                    updated_image, old_processing_status, image_data.processing_status, get_correlation_id()
                )
            
            logger.info(
                "Image updated successfully",
                image_id=image_id,
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            
            return updated_image
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to update image",
                image_id=image_id,
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update image"
            )
    
    # Delete image endpoint
    @app.delete("/api/v1/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_image(
        image_id: str,
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Delete image (soft delete)."""
        try:
            # Get existing image
            image = await ImageCRUD.get_by_id(db, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image not found"
                )
            
            # Delete image
            await ImageCRUD.delete(db, image, user_context.user_id)
            await db.commit()
            
            # Emit event
            event_emitter = await get_event_emitter()
            await event_emitter.emit_image_deleted(image, get_correlation_id())
            
            logger.info(
                "Image deleted successfully",
                image_id=image_id,
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete image",
                image_id=image_id,
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete image"
            )
    
    # Generate signed URL endpoint
    @app.post("/api/v1/images/{image_id}/signed-url", response_model=SignedUrlResponse)
    async def generate_signed_url(
        image_id: str,
        expiry_seconds: Optional[int] = Query(None, description="URL expiry in seconds"),
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Generate signed URL for image access."""
        try:
            # Get image
            image = await ImageCRUD.get_by_id(db, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image not found"
                )
            
            # Generate signed URL
            storage = await get_storage()
            signed_url = await storage.generate_presigned_url(
                image.storage_key,
                expiry=expiry_seconds
            )
            
            # Calculate expiry
            expiry = expiry_seconds or app.state.settings.signed_url_expiry
            expires_at = datetime.utcnow() + timedelta(seconds=expiry)
            
            logger.info(
                "Signed URL generated",
                image_id=image_id,
                expiry_seconds=expiry,
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            
            return SignedUrlResponse(
                image_id=image_id,
                signed_url=signed_url,
                expires_at=expires_at,
                expires_in_seconds=expiry
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to generate signed URL",
                image_id=image_id,
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate signed URL"
            )
    
    # Generate viewer URL endpoint
    @app.post("/api/v1/images/{image_id}/viewer-url", response_model=ViewerUrlResponse)
    async def generate_viewer_url(
        image_id: str,
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Generate viewer URL for image viewing."""
        try:
            # Get image
            image = await ImageCRUD.get_by_id(db, image_id)
            if not image:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image not found"
                )
            
            # Generate viewer URL
            storage = await get_storage()
            viewer_url = await storage.generate_viewer_url(image.storage_key)
            
            # Generate thumbnail URL if available
            thumbnail_url = None
            if image.has_thumbnail and image.thumbnail_path:
                thumbnail_url = await storage.generate_viewer_url(image.thumbnail_path)
            
            # Increment view count
            await ImageCRUD.increment_view_count(db, image)
            await db.commit()
            
            # Emit view event
            event_emitter = await get_event_emitter()
            await event_emitter.emit_image_viewed(image, user_context.user_id, get_correlation_id())
            
            # Calculate expiry
            expiry = app.state.settings.viewer_url_expiry
            expires_at = datetime.utcnow() + timedelta(seconds=expiry)
            
            logger.info(
                "Viewer URL generated",
                image_id=image_id,
                view_count=image.view_count,
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            
            return ViewerUrlResponse(
                image_id=image_id,
                viewer_url=viewer_url,
                thumbnail_url=thumbnail_url,
                expires_at=expires_at,
                expires_in_seconds=expiry
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to generate viewer URL",
                image_id=image_id,
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate viewer URL"
            )
    
    # Get image statistics endpoint
    @app.get("/api/v1/images/statistics", response_model=ImageStatistics)
    async def get_image_statistics(
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """Get image statistics."""
        try:
            statistics = await ImageCRUD.get_image_statistics(db)
            
            logger.info(
                "Image statistics retrieved",
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            
            return ImageStatistics(**statistics)
            
        except Exception as e:
            logger.error(
                "Failed to get image statistics",
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get image statistics"
            )
    
    # List images by case endpoint
    @app.get("/api/v1/cases/{case_id}/images", response_model=PaginatedImages)
    async def list_images_by_case(
        case_id: str,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size"),
        order_by: str = Query("created_at", description="Field to order by"),
        order_desc: bool = Query(True, description="Order descending"),
        db: AsyncSession = Depends(get_db_session),
        user_context: UserContext = Depends(get_user_context)
    ):
        """List images for a specific case."""
        try:
            pagination = PaginationParams(page=page, size=size)
            
            # Get images for case
            images, total_count = await ImageCRUD.list_images_by_case(
                db, case_id, pagination, order_by, order_desc
            )
            
            # Convert to summary format
            image_summaries = []
            for image in images:
                summary = ImageSummary(
                    id=image.id,
                    original_filename=image.original_filename,
                    file_format=image.file_format,
                    file_size_mb=image.file_size_mb,
                    dimensions=image.dimensions,
                    modality=image.modality,
                    processing_status=image.processing_status,
                    has_thumbnail=image.has_thumbnail,
                    view_count=image.view_count,
                    created_at=image.created_at,
                    case_id=image.case_id
                )
                image_summaries.append(summary)
            
            return PaginatedImages(
                items=image_summaries,
                total=total_count,
                page=page,
                size=size
            )
            
        except Exception as e:
            logger.error(
                "Failed to list images by case",
                case_id=case_id,
                error=str(e),
                user_id=user_context.user_id,
                correlation_id=get_correlation_id()
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list images by case"
            )


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )
