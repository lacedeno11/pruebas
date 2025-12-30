"""
DERCAS-ONCO-XAI V1 - Image Service Validation

File format validation using magic bytes and content validation.
"""

import hashlib
import logging
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from PIL import Image as PILImage
from PIL.ExifTags import TAGS

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.errors import (
    ErrorCode,
    FileError,
    ValidationError,
    create_file_format_error
)

from .config import get_settings

logger = logging.getLogger(__name__)


class FileValidator:
    """File validation service with magic byte detection and content validation."""
    
    def __init__(self, max_file_size: int, allowed_formats: List[str]):
        self.max_file_size = max_file_size
        self.allowed_formats = allowed_formats
        self.settings = get_settings()
        
        # Magic bytes for file format detection
        self.magic_bytes = {
            "png": [b"\x89PNG\r\n\x1a\n"],
            "tiff": [b"II*\x00", b"MM\x00*"],  # Little-endian and big-endian TIFF
            "tif": [b"II*\x00", b"MM\x00*"],   # Same as TIFF
            "jpeg": [b"\xff\xd8\xff"],
            "jpg": [b"\xff\xd8\xff"]
        }
        
        logger.info(f"Initialized file validator with max size: {max_file_size} bytes")
    
    async def validate_file(self, file: UploadFile) -> dict:
        """
        Validate uploaded file format, size, and content.
        
        Args:
            file: Uploaded file to validate
            
        Returns:
            dict: Validation result with metadata
            
        Raises:
            FileError: If file validation fails
        """
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Reset file position for subsequent reads
        await file.seek(0)
        
        # Validate file size
        if file_size > self.max_file_size:
            raise FileError(
                error_code=ErrorCode.FILE_TOO_LARGE,
                message=f"File size {file_size} bytes exceeds maximum allowed size {self.max_file_size} bytes"
            )
        
        if file_size == 0:
            raise FileError(
                error_code=ErrorCode.INVALID_FILE_FORMAT,
                message="File is empty"
            )
        
        # Detect file format using magic bytes
        detected_format = self._detect_format_by_magic_bytes(file_content)
        
        # Validate against filename extension
        filename_format = self._get_format_from_filename(file.filename or "")
        
        # Check if detected format is allowed
        if detected_format not in self.allowed_formats:
            raise create_file_format_error(
                filename=file.filename or "unknown",
                allowed_formats=self.allowed_formats
            )
        
        # Warn if filename extension doesn't match detected format
        if filename_format and filename_format != detected_format:
            logger.warning(
                f"Filename extension '{filename_format}' doesn't match detected format '{detected_format}' "
                f"for file: {file.filename}"
            )
        
        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Validate image content and extract metadata
        try:
            image_metadata = await self._validate_image_content(file_content, detected_format)
        except Exception as e:
            raise FileError(
                error_code=ErrorCode.FILE_CORRUPTED,
                message=f"Image content validation failed: {str(e)}"
            )
        
        # Validate image dimensions and properties
        self._validate_image_properties(image_metadata)
        
        validation_result = {
            "is_valid": True,
            "file_format": detected_format,
            "file_size": file_size,
            "checksum": checksum,
            "filename_format": filename_format,
            "format_mismatch": filename_format != detected_format if filename_format else False,
            "image_metadata": image_metadata,
            "errors": [],
            "warnings": []
        }
        
        if validation_result["format_mismatch"]:
            validation_result["warnings"].append(
                f"Filename extension '{filename_format}' doesn't match detected format '{detected_format}'"
            )
        
        logger.info(
            f"File validation successful: {file.filename} ({detected_format}, {file_size} bytes)"
        )
        
        return validation_result
    
    def _detect_format_by_magic_bytes(self, file_content: bytes) -> str:
        """
        Detect file format using magic bytes.
        
        Args:
            file_content: File content as bytes
            
        Returns:
            str: Detected file format
            
        Raises:
            FileError: If format cannot be detected or is not supported
        """
        if len(file_content) < 8:
            raise FileError(
                error_code=ErrorCode.INVALID_FILE_FORMAT,
                message="File too small to determine format"
            )
        
        # Check magic bytes for each supported format
        for format_name, magic_list in self.magic_bytes.items():
            for magic in magic_list:
                if file_content.startswith(magic):
                    logger.debug(f"Detected format '{format_name}' by magic bytes")
                    return format_name
        
        # Additional checks for formats that might have variable headers
        if self._is_tiff_format(file_content):
            return "tiff"
        
        raise FileError(
            error_code=ErrorCode.INVALID_FILE_FORMAT,
            message="Unsupported file format or corrupted file"
        )
    
    def _is_tiff_format(self, file_content: bytes) -> bool:
        """Check if file is TIFF format with additional validation."""
        if len(file_content) < 8:
            return False
        
        # Check for TIFF magic numbers
        # Little-endian: II*\x00
        # Big-endian: MM\x00*
        if file_content[:4] == b"II*\x00":
            return True
        elif file_content[:4] == b"MM\x00*":
            return True
        
        return False
    
    def _get_format_from_filename(self, filename: str) -> Optional[str]:
        """Extract format from filename extension."""
        if not filename:
            return None
        
        # Get extension without the dot
        ext = filename.lower().split('.')[-1] if '.' in filename else ""
        
        # Normalize TIFF extensions
        if ext in ["tif", "tiff"]:
            return "tiff"
        
        return ext if ext in self.allowed_formats else None
    
    async def _validate_image_content(self, file_content: bytes, file_format: str) -> dict:
        """
        Validate image content and extract metadata using PIL.
        
        Args:
            file_content: Image file content
            file_format: Detected file format
            
        Returns:
            dict: Image metadata
        """
        try:
            # Create PIL Image from bytes
            from io import BytesIO
            image_stream = BytesIO(file_content)
            
            with PILImage.open(image_stream) as img:
                # Basic image properties
                metadata = {
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "format": img.format,
                    "channels": len(img.getbands()) if hasattr(img, 'getbands') else None,
                    "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                }
                
                # Calculate additional properties
                metadata["pixel_count"] = img.width * img.height
                metadata["aspect_ratio"] = img.width / img.height if img.height > 0 else None
                
                # Extract EXIF data if available
                exif_data = self._extract_exif_data(img)
                if exif_data:
                    metadata["exif"] = exif_data
                
                # Format-specific validation
                if file_format in ["tiff", "tif"]:
                    metadata.update(self._validate_tiff_specific(img))
                elif file_format == "png":
                    metadata.update(self._validate_png_specific(img))
                
                return metadata
                
        except Exception as e:
            logger.error(f"Failed to validate image content: {e}")
            raise FileError(
                error_code=ErrorCode.FILE_CORRUPTED,
                message=f"Invalid or corrupted image file: {str(e)}"
            )
    
    def _extract_exif_data(self, img: PILImage.Image) -> Optional[dict]:
        """Extract EXIF data from image."""
        try:
            exif_dict = {}
            
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    # Convert bytes to string for JSON serialization
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)
                    exif_dict[tag] = value
            
            return exif_dict if exif_dict else None
            
        except Exception as e:
            logger.warning(f"Failed to extract EXIF data: {e}")
            return None
    
    def _validate_tiff_specific(self, img: PILImage.Image) -> dict:
        """TIFF-specific validation and metadata extraction."""
        metadata = {}
        
        # Check for multi-page TIFF
        try:
            img.seek(1)
            metadata["is_multipage"] = True
            metadata["page_count"] = img.n_frames
            img.seek(0)  # Reset to first page
        except:
            metadata["is_multipage"] = False
            metadata["page_count"] = 1
        
        # TIFF compression info
        if hasattr(img, 'tag') and img.tag:
            compression = img.tag.get(259)  # Compression tag
            if compression:
                metadata["compression"] = compression[0] if isinstance(compression, tuple) else compression
        
        return metadata
    
    def _validate_png_specific(self, img: PILImage.Image) -> dict:
        """PNG-specific validation and metadata extraction."""
        metadata = {}
        
        # PNG info
        if img.info:
            # DPI information
            if "dpi" in img.info:
                metadata["dpi"] = img.info["dpi"]
            
            # Gamma information
            if "gamma" in img.info:
                metadata["gamma"] = img.info["gamma"]
            
            # Text chunks
            text_info = {}
            for key, value in img.info.items():
                if isinstance(key, str) and isinstance(value, str):
                    text_info[key] = value
            
            if text_info:
                metadata["text_chunks"] = text_info
        
        return metadata
    
    def _validate_image_properties(self, metadata: dict):
        """
        Validate image properties against business rules.
        
        Args:
            metadata: Image metadata dictionary
            
        Raises:
            ValidationError: If image properties are invalid
        """
        width = metadata.get("width", 0)
        height = metadata.get("height", 0)
        
        # Minimum dimensions
        min_dimension = 32
        if width < min_dimension or height < min_dimension:
            raise ValidationError(
                message=f"Image dimensions too small: {width}x{height}. "
                       f"Minimum required: {min_dimension}x{min_dimension}"
            )
        
        # Maximum dimensions (to prevent memory issues)
        max_dimension = 50000
        if width > max_dimension or height > max_dimension:
            raise ValidationError(
                message=f"Image dimensions too large: {width}x{height}. "
                       f"Maximum allowed: {max_dimension}x{max_dimension}"
            )
        
        # Maximum pixel count (to prevent memory issues)
        pixel_count = metadata.get("pixel_count", 0)
        max_pixels = 500_000_000  # 500 megapixels
        if pixel_count > max_pixels:
            raise ValidationError(
                message=f"Image has too many pixels: {pixel_count:,}. "
                       f"Maximum allowed: {max_pixels:,}"
            )
        
        # Validate aspect ratio (prevent extremely narrow images)
        aspect_ratio = metadata.get("aspect_ratio")
        if aspect_ratio:
            min_aspect = 0.01  # 1:100
            max_aspect = 100.0  # 100:1
            if aspect_ratio < min_aspect or aspect_ratio > max_aspect:
                raise ValidationError(
                    message=f"Invalid aspect ratio: {aspect_ratio:.3f}. "
                           f"Must be between {min_aspect} and {max_aspect}"
                )
    
    def validate_checksum(self, file_content: bytes, expected_checksum: str) -> bool:
        """
        Validate file checksum.
        
        Args:
            file_content: File content as bytes
            expected_checksum: Expected SHA-256 checksum
            
        Returns:
            bool: True if checksum matches
        """
        actual_checksum = hashlib.sha256(file_content).hexdigest()
        return actual_checksum.lower() == expected_checksum.lower()
    
    def get_file_info(self, file_content: bytes) -> dict:
        """
        Get basic file information without full validation.
        
        Args:
            file_content: File content as bytes
            
        Returns:
            dict: Basic file information
        """
        return {
            "size": len(file_content),
            "checksum": hashlib.sha256(file_content).hexdigest(),
            "detected_format": self._detect_format_by_magic_bytes(file_content) if len(file_content) >= 8 else None
        }


# Utility functions
def is_medical_image_format(file_format: str) -> bool:
    """Check if format is commonly used for medical images."""
    medical_formats = ["tiff", "tif", "png", "dicom", "dcm"]
    return file_format.lower() in medical_formats


def estimate_processing_time(file_size: int, image_dimensions: Tuple[int, int]) -> float:
    """
    Estimate processing time based on file size and dimensions.
    
    Args:
        file_size: File size in bytes
        image_dimensions: (width, height) tuple
        
    Returns:
        float: Estimated processing time in seconds
    """
    width, height = image_dimensions
    pixel_count = width * height
    
    # Base time estimates (in seconds)
    base_time = 1.0
    size_factor = file_size / (10 * 1024 * 1024)  # Per 10MB
    pixel_factor = pixel_count / (1024 * 1024)    # Per megapixel
    
    estimated_time = base_time + (size_factor * 0.5) + (pixel_factor * 0.2)
    
    # Cap at reasonable maximum
    return min(estimated_time, 300.0)  # Max 5 minutes


def get_recommended_thumbnail_sizes(width: int, height: int) -> List[int]:
    """
    Get recommended thumbnail sizes based on original dimensions.
    
    Args:
        width: Original image width
        height: Original image height
        
    Returns:
        List[int]: Recommended thumbnail sizes
    """
    max_dimension = max(width, height)
    
    sizes = []
    
    # Always include small thumbnail
    sizes.append(150)
    
    # Medium thumbnail
    if max_dimension > 600:
        sizes.append(300)
    
    # Large thumbnail
    if max_dimension > 1200:
        sizes.append(600)
    
    # Extra large for very high resolution images
    if max_dimension > 4000:
        sizes.append(1200)
    
    return sizes
