# DERCAS-ONCO-XAI V1 - Image Service Validation
# Image format validation with magic bytes and content verification

import hashlib
import mimetypes
from typing import Optional, Dict, Any, Tuple, BinaryIO
from pathlib import Path
import filetype
import magic
from PIL import Image as PILImage
import structlog

logger = structlog.get_logger(__name__)


class ImageValidator:
    """Image validation with format checking and magic bytes verification."""
    
    # Magic bytes for supported formats
    MAGIC_BYTES = {
        'png': [
            b'\x89PNG\r\n\x1a\n',  # PNG signature
        ],
        'biff': [
            b'II*\x00',  # TIFF little-endian
            b'MM\x00*',  # TIFF big-endian
            b'II+\x00',  # BigTIFF little-endian
            b'MM\x00+',  # BigTIFF big-endian
        ]
    }
    
    # MIME types for supported formats
    MIME_TYPES = {
        'png': 'image/png',
        'biff': 'image/tiff',
        'tiff': 'image/tiff',
        'tif': 'image/tiff'
    }
    
    # Maximum dimensions for safety
    MAX_DIMENSIONS = (50000, 50000)  # 50k x 50k pixels
    
    def __init__(self, allowed_formats: list = None, validate_magic_bytes: bool = True):
        """
        Initialize image validator.
        
        Args:
            allowed_formats: List of allowed formats (default: ['png', 'biff'])
            validate_magic_bytes: Whether to validate magic bytes
        """
        self.allowed_formats = allowed_formats or ['png', 'biff']
        self.validate_magic_bytes = validate_magic_bytes
        
        # Normalize format names
        self.allowed_formats = [fmt.lower() for fmt in self.allowed_formats]
        
        logger.info(
            "Image validator initialized",
            allowed_formats=self.allowed_formats,
            validate_magic_bytes=validate_magic_bytes
        )
    
    def validate_file(self, file_path: str, original_filename: str = None) -> Dict[str, Any]:
        """
        Validate image file comprehensively.
        
        Args:
            file_path: Path to the file to validate
            original_filename: Original filename for additional validation
            
        Returns:
            Validation result dictionary
            
        Raises:
            ValueError: If validation fails
        """
        result = {
            'is_valid': False,
            'format': None,
            'mime_type': None,
            'file_size': 0,
            'width': None,
            'height': None,
            'color_mode': None,
            'bit_depth': None,
            'md5_hash': None,
            'sha256_hash': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                result['errors'].append("File does not exist")
                return result
            
            # Get file size
            result['file_size'] = file_path.stat().st_size
            
            # Check file size (not empty, not too large)
            if result['file_size'] == 0:
                result['errors'].append("File is empty")
                return result
            
            if result['file_size'] > 1024 * 1024 * 1024:  # 1GB limit
                result['errors'].append("File is too large (>1GB)")
                return result
            
            # Calculate checksums
            result['md5_hash'] = self._calculate_md5(file_path)
            result['sha256_hash'] = self._calculate_sha256(file_path)
            
            # Detect format using multiple methods
            format_detection = self._detect_format(file_path, original_filename)
            result['format'] = format_detection['format']
            result['mime_type'] = format_detection['mime_type']
            
            if not result['format']:
                result['errors'].append("Could not detect image format")
                return result
            
            # Check if format is allowed
            if result['format'] not in self.allowed_formats:
                result['errors'].append(f"Format '{result['format']}' is not allowed")
                return result
            
            # Validate magic bytes if enabled
            if self.validate_magic_bytes:
                magic_validation = self._validate_magic_bytes(file_path, result['format'])
                if not magic_validation['is_valid']:
                    result['errors'].extend(magic_validation['errors'])
                    return result
            
            # Try to open and analyze image
            try:
                image_info = self._analyze_image(file_path)
                result.update(image_info)
                
                # Validate dimensions
                if result['width'] and result['height']:
                    if (result['width'] > self.MAX_DIMENSIONS[0] or 
                        result['height'] > self.MAX_DIMENSIONS[1]):
                        result['errors'].append(
                            f"Image dimensions too large: {result['width']}x{result['height']} "
                            f"(max: {self.MAX_DIMENSIONS[0]}x{self.MAX_DIMENSIONS[1]})"
                        )
                        return result
                
            except Exception as e:
                result['errors'].append(f"Failed to analyze image: {str(e)}")
                return result
            
            # Additional format-specific validation
            format_validation = self._validate_format_specific(file_path, result['format'])
            if format_validation['errors']:
                result['errors'].extend(format_validation['errors'])
                return result
            
            if format_validation['warnings']:
                result['warnings'].extend(format_validation['warnings'])
            
            # If we get here, validation passed
            result['is_valid'] = True
            
            logger.info(
                "Image validation successful",
                format=result['format'],
                dimensions=f"{result['width']}x{result['height']}" if result['width'] else None,
                file_size_mb=round(result['file_size'] / (1024 * 1024), 2)
            )
            
        except Exception as e:
            logger.error("Image validation failed", error=str(e))
            result['errors'].append(f"Validation error: {str(e)}")
        
        return result
    
    def _detect_format(self, file_path: Path, original_filename: str = None) -> Dict[str, Any]:
        """
        Detect image format using multiple methods.
        
        Args:
            file_path: Path to the file
            original_filename: Original filename
            
        Returns:
            Format detection result
        """
        result = {'format': None, 'mime_type': None, 'detection_method': None}
        
        try:
            # Method 1: Use filetype library (magic bytes)
            kind = filetype.guess(str(file_path))
            if kind:
                detected_format = kind.extension.lower()
                if detected_format in ['tiff', 'tif']:
                    detected_format = 'biff'  # Normalize TIFF to BIFF
                
                if detected_format in self.allowed_formats:
                    result['format'] = detected_format
                    result['mime_type'] = kind.mime
                    result['detection_method'] = 'filetype'
                    return result
            
            # Method 2: Use python-magic
            try:
                mime_type = magic.from_file(str(file_path), mime=True)
                if mime_type:
                    if mime_type == 'image/png':
                        result['format'] = 'png'
                        result['mime_type'] = mime_type
                        result['detection_method'] = 'magic'
                        return result
                    elif mime_type in ['image/tiff', 'image/tif']:
                        result['format'] = 'biff'
                        result['mime_type'] = 'image/tiff'
                        result['detection_method'] = 'magic'
                        return result
            except Exception:
                pass
            
            # Method 3: File extension fallback
            if original_filename:
                ext = Path(original_filename).suffix.lower().lstrip('.')
                if ext in ['tiff', 'tif']:
                    ext = 'biff'
                
                if ext in self.allowed_formats:
                    result['format'] = ext
                    result['mime_type'] = self.MIME_TYPES.get(ext)
                    result['detection_method'] = 'extension'
                    return result
            
            # Method 4: MIME type from filename
            if original_filename:
                mime_type, _ = mimetypes.guess_type(original_filename)
                if mime_type:
                    if mime_type == 'image/png':
                        result['format'] = 'png'
                        result['mime_type'] = mime_type
                        result['detection_method'] = 'mimetypes'
                        return result
                    elif mime_type in ['image/tiff', 'image/tif']:
                        result['format'] = 'biff'
                        result['mime_type'] = 'image/tiff'
                        result['detection_method'] = 'mimetypes'
                        return result
            
        except Exception as e:
            logger.warning("Format detection error", error=str(e))
        
        return result
    
    def _validate_magic_bytes(self, file_path: Path, format_name: str) -> Dict[str, Any]:
        """
        Validate magic bytes for the detected format.
        
        Args:
            file_path: Path to the file
            format_name: Detected format name
            
        Returns:
            Magic bytes validation result
        """
        result = {'is_valid': False, 'errors': []}
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes
            
            if format_name in self.MAGIC_BYTES:
                magic_signatures = self.MAGIC_BYTES[format_name]
                
                for signature in magic_signatures:
                    if header.startswith(signature):
                        result['is_valid'] = True
                        return result
                
                result['errors'].append(
                    f"Magic bytes validation failed for format '{format_name}'"
                )
            else:
                # Format not in our magic bytes list, assume valid
                result['is_valid'] = True
        
        except Exception as e:
            result['errors'].append(f"Magic bytes validation error: {str(e)}")
        
        return result
    
    def _analyze_image(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze image using PIL to extract metadata.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Image analysis result
        """
        result = {
            'width': None,
            'height': None,
            'color_mode': None,
            'bit_depth': None,
            'has_transparency': False
        }
        
        try:
            with PILImage.open(file_path) as img:
                result['width'] = img.width
                result['height'] = img.height
                result['color_mode'] = img.mode
                
                # Estimate bit depth
                if img.mode in ['1']:
                    result['bit_depth'] = 1
                elif img.mode in ['L', 'P']:
                    result['bit_depth'] = 8
                elif img.mode in ['RGB', 'YCbCr', 'LAB', 'HSV']:
                    result['bit_depth'] = 24
                elif img.mode in ['RGBA', 'CMYK']:
                    result['bit_depth'] = 32
                elif img.mode in ['I', 'F']:
                    result['bit_depth'] = 32
                
                # Check for transparency
                result['has_transparency'] = (
                    img.mode in ['RGBA', 'LA'] or 
                    'transparency' in img.info
                )
                
        except Exception as e:
            logger.warning("Image analysis failed", error=str(e))
            # Don't raise exception, just log warning
        
        return result
    
    def _validate_format_specific(self, file_path: Path, format_name: str) -> Dict[str, Any]:
        """
        Perform format-specific validation.
        
        Args:
            file_path: Path to the file
            format_name: Format name
            
        Returns:
            Format-specific validation result
        """
        result = {'errors': [], 'warnings': []}
        
        try:
            if format_name == 'png':
                result.update(self._validate_png(file_path))
            elif format_name == 'biff':
                result.update(self._validate_biff(file_path))
        
        except Exception as e:
            result['warnings'].append(f"Format-specific validation error: {str(e)}")
        
        return result
    
    def _validate_png(self, file_path: Path) -> Dict[str, Any]:
        """Validate PNG-specific requirements."""
        result = {'errors': [], 'warnings': []}
        
        try:
            with PILImage.open(file_path) as img:
                # PNG-specific checks
                if img.format != 'PNG':
                    result['errors'].append("File is not a valid PNG")
                
                # Check for common PNG issues
                if img.mode not in ['RGB', 'RGBA', 'L', 'LA', 'P']:
                    result['warnings'].append(f"Unusual PNG color mode: {img.mode}")
        
        except Exception as e:
            result['errors'].append(f"PNG validation failed: {str(e)}")
        
        return result
    
    def _validate_biff(self, file_path: Path) -> Dict[str, Any]:
        """Validate BIFF/TIFF-specific requirements."""
        result = {'errors': [], 'warnings': []}
        
        try:
            with PILImage.open(file_path) as img:
                # TIFF-specific checks
                if img.format != 'TIFF':
                    result['errors'].append("File is not a valid TIFF/BIFF")
                
                # Check for multi-page TIFF
                try:
                    img.seek(1)
                    result['warnings'].append("Multi-page TIFF detected, only first page will be processed")
                    img.seek(0)
                except EOFError:
                    pass  # Single page, which is fine
        
        except Exception as e:
            result['errors'].append(f"BIFF/TIFF validation failed: {str(e)}")
        
        return result
    
    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def validate_stream(self, file_stream: BinaryIO, filename: str, max_size: int = None) -> Dict[str, Any]:
        """
        Validate image from a stream (for upload handling).
        
        Args:
            file_stream: File stream to validate
            filename: Original filename
            max_size: Maximum allowed file size
            
        Returns:
            Validation result dictionary
        """
        import tempfile
        import os
        
        result = {
            'is_valid': False,
            'format': None,
            'mime_type': None,
            'file_size': 0,
            'errors': [],
            'warnings': []
        }
        
        temp_file = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                # Read and write stream to temp file
                total_size = 0
                while True:
                    chunk = file_stream.read(8192)
                    if not chunk:
                        break
                    
                    total_size += len(chunk)
                    
                    # Check size limit during upload
                    if max_size and total_size > max_size:
                        result['errors'].append(f"File too large (>{max_size} bytes)")
                        return result
                    
                    temp_file.write(chunk)
                
                temp_file.flush()
                result['file_size'] = total_size
                
                # Validate the temporary file
                validation_result = self.validate_file(temp_file.name, filename)
                result.update(validation_result)
        
        except Exception as e:
            result['errors'].append(f"Stream validation error: {str(e)}")
        
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass
        
        return result


def create_image_validator(allowed_formats: list = None, validate_magic_bytes: bool = True) -> ImageValidator:
    """
    Create an image validator instance.
    
    Args:
        allowed_formats: List of allowed formats
        validate_magic_bytes: Whether to validate magic bytes
        
    Returns:
        ImageValidator instance
    """
    return ImageValidator(allowed_formats, validate_magic_bytes)
