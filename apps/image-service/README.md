# Image Service

Image upload, storage, and management service with MinIO integration.

## Features

- Image upload handling (multipart/form-data)
- Format validation (.png/.biff with magic byte verification)
- MinIO storage integration with checksum verification
- Signed URL generation for secure image viewing
- Database models for image metadata
- File size limits and streaming upload support
- Comprehensive error handling

## Endpoints

- `POST /api/v1/cases/{caseId}/images:upload` - Upload image
- `GET /api/v1/cases/{caseId}/images` - List images by case
- `GET /api/v1/images/{imageId}` - Get image details
- `GET /api/v1/images/{imageId}/viewer-url` - Get signed URL for viewing
- `DELETE /api/v1/images/{imageId}` - Delete image (if permitted)

## Development

```bash
cd apps/image-service
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8002
```
