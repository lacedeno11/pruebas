"""Image routes."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from oncology_common.models import Image as ImageSchema, ImageFormat
from oncology_common.clients.rabbitmq import create_event_publisher
from event_contracts import EventType
from image_service.database import get_db
from image_service.services.image_service import ImageService
from image_service.config import settings

router = APIRouter(tags=["Images"])

def get_event_publisher():
    return create_event_publisher(settings.rabbitmq_url, settings.service_name)

@router.post("/cases/{case_id}/images:upload", response_model=ImageSchema, status_code=status.HTTP_201_CREATED)
async def upload_image(
    case_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    stain: str | None = Form(None),
    magnification: str | None = Form(None),
    notes: str | None = Form(None),
) -> ImageSchema:
    """Upload an image for a case."""
    user_id = request.headers.get("X-User-Id")
    service = ImageService(db)
    file_data = await file.read()

    try:
        image = await service.upload(
            case_id=case_id,
            file_data=file_data,
            filename=file.filename or "unknown.png",
            stain=stain,
            magnification=magnification,
            notes=notes,
            uploaded_by=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        publisher = get_event_publisher()
        publisher.publish(
            event_type=EventType.IMAGE_UPLOADED,
            payload={
                "image_id": str(image.image_id),
                "case_id": str(image.case_id),
                "format": image.format.value,
                "storage_uri": image.storage_uri,
                "checksum": image.checksum,
                "size_bytes": image.size_bytes,
            },
            case_id=str(case_id),
        )
    except Exception:
        pass

    return ImageSchema(
        image_id=image.image_id,
        case_id=image.case_id,
        format=ImageFormat(image.format.value),
        storage_uri=image.storage_uri,
        checksum=image.checksum,
        size_bytes=image.size_bytes,
        stain=image.stain,
        magnification=image.magnification,
        notes=image.notes,
        uploaded_by=image.uploaded_by,
        uploaded_at=image.uploaded_at,
    )

@router.get("/cases/{case_id}/images", response_model=list[ImageSchema])
async def list_case_images(
    case_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ImageSchema]:
    """List images for a case."""
    service = ImageService(db)
    images = await service.list_by_case(case_id)
    return [
        ImageSchema(
            image_id=img.image_id,
            case_id=img.case_id,
            format=ImageFormat(img.format.value),
            storage_uri=img.storage_uri,
            checksum=img.checksum,
            size_bytes=img.size_bytes,
            stain=img.stain,
            magnification=img.magnification,
            notes=img.notes,
            uploaded_by=img.uploaded_by,
            uploaded_at=img.uploaded_at,
        )
        for img in images
    ]

@router.get("/images/{image_id}", response_model=ImageSchema)
async def get_image(
    image_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImageSchema:
    """Get image by ID."""
    service = ImageService(db)
    image = await service.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image {image_id} not found")
    return ImageSchema(
        image_id=image.image_id,
        case_id=image.case_id,
        format=ImageFormat(image.format.value),
        storage_uri=image.storage_uri,
        checksum=image.checksum,
        size_bytes=image.size_bytes,
        stain=image.stain,
        magnification=image.magnification,
        notes=image.notes,
        uploaded_by=image.uploaded_by,
        uploaded_at=image.uploaded_at,
    )

@router.get("/images/{image_id}/viewer-url")
async def get_viewer_url(
    image_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get signed URL for image viewing."""
    service = ImageService(db)
    image = await service.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image {image_id} not found")
    url = service.get_viewer_url(image)
    return {"viewer_url": url, "expires_in": 3600}

@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an image."""
    service = ImageService(db)
    if not await service.delete(image_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image {image_id} not found")
