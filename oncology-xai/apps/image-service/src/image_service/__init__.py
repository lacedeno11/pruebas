# DERCAS-ONCO-XAI V1 - Image Service
# Medical image management and storage service

"""
Image Service for DERCAS-ONCO-XAI V1 platform.

This service provides:
- Image upload handling with multipart support
- Format validation for .png and .biff files with magic bytes
- MinIO integration for object storage
- Checksum calculation for data integrity
- Metadata persistence with SQLAlchemy
- Signed URL generation for secure image viewing
- Proper error handling for file operations
"""

__version__ = "1.0.0"
