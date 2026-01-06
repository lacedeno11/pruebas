# Image Service

FastAPI service for histopathological image management in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- Image upload handling for .png/.biff files
- MinIO S3 integration for storage
- Checksum validation and metadata persistence
- Signed URL generation for image viewing
- File format validation using magic bytes

## Endpoints

- `POST /api/v1/cases/{caseId}/images:upload` - Upload image (multipart)
- `GET /api/v1/cases/{caseId}/images` - List case images
- `GET /api/v1/images/{imageId}` - Get image metadata
- `GET /api/v1/images/{imageId}/viewer-url` - Get signed viewing URL
- `DELETE /api/v1/images/{imageId}` - Delete image (if permitted)

## Development

```bash
cd apps/image-service
python -m uvicorn main:app --reload --port 8002
```
