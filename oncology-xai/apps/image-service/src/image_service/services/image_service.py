"""Image service."""
import hashlib
from io import BytesIO
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from oncology_common.clients.storage import StorageClient
from image_service.models.image import Image, ImageFormat
from image_service.config import settings

# PNG magic bytes
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

class ImageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageClient(
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
        )

    def _validate_format(self, data: bytes, filename: str) -> ImageFormat:
        """Validate image format by extension and magic bytes."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if ext == 'png':
            if data[:8] != PNG_MAGIC:
                raise ValueError("Invalid PNG file: magic bytes don't match")
            return ImageFormat.PNG
        elif ext == 'biff':
            return ImageFormat.BIFF
        else:
            raise ValueError(f"Unsupported format: {ext}")

    async def upload(
        self,
        case_id: UUID,
        file_data: bytes,
        filename: str,
        stain: str | None = None,
        magnification: str | None = None,
        notes: str | None = None,
        uploaded_by: str | None = None,
    ) -> Image:
        """Upload an image."""
        if len(file_data) > settings.max_file_size:
            raise ValueError(f"File too large: {len(file_data)} > {settings.max_file_size}")

        img_format = self._validate_format(file_data, filename)
        image_id = uuid4()
        key = f"images/{case_id}/{image_id}.{img_format.value}"

        file_obj = BytesIO(file_data)
        content_type = "image/png" if img_format == ImageFormat.PNG else "application/octet-stream"
        storage_uri, checksum = self.storage.upload_file(file_obj, key, content_type)

        image = Image(
            image_id=image_id,
            case_id=case_id,
            format=img_format,
            storage_uri=storage_uri,
            checksum=checksum,
            size_bytes=len(file_data),
            stain=stain,
            magnification=magnification,
            notes=notes,
            uploaded_by=uploaded_by,
        )
        self.db.add(image)
        await self.db.flush()
        return image

    async def get_by_id(self, image_id: UUID) -> Image | None:
        result = await self.db.execute(select(Image).where(Image.image_id == image_id))
        return result.scalar_one_or_none()

    async def list_by_case(self, case_id: UUID) -> list[Image]:
        result = await self.db.execute(
            select(Image).where(Image.case_id == case_id).order_by(Image.uploaded_at.desc())
        )
        return list(result.scalars().all())

    def get_viewer_url(self, image: Image, expires_in: int = 3600) -> str:
        """Get signed URL for image viewing."""
        key = self.storage.key_from_uri(image.storage_uri)
        return self.storage.get_signed_url(key, expires_in)

    async def delete(self, image_id: UUID) -> bool:
        image = await self.get_by_id(image_id)
        if not image:
            return False
        key = self.storage.key_from_uri(image.storage_uri)
        self.storage.delete_file(key)
        await self.db.delete(image)
        await self.db.flush()
        return True
