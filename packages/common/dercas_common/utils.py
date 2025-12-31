"""
DERCAS-ONCO-XAI Utilities

Common utility functions for the DERCAS-ONCO-XAI platform.
"""

import hashlib
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier with optional prefix."""
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id


def get_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


def hash_content(content: Union[str, bytes]) -> str:
    """Generate SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def sanitize_phi(text: str, replacement: str = "[REDACTED]") -> str:
    """Sanitize potential PHI from text."""
    # Common PHI patterns
    phi_patterns = [
        (r'\b\d{3}-\d{2}-\d{4}\b', replacement),  # SSN
        (r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b', replacement),  # Credit card
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', replacement),  # Email
        (r'\b\d{3}-\d{3}-\d{4}\b', replacement),  # Phone number
        (r'\b\d{5}(-\d{4})?\b', replacement),  # ZIP code
    ]
    
    sanitized_text = text
    for pattern, repl in phi_patterns:
        sanitized_text = re.sub(pattern, repl, sanitized_text)
    
    return sanitized_text


def validate_file_format(filename: str, allowed_formats: List[str]) -> bool:
    """Validate file format based on extension."""
    if not filename:
        return False
    
    extension = filename.lower().split('.')[-1]
    return extension in [fmt.lower() for fmt in allowed_formats]


def calculate_file_checksum(file_content: bytes) -> str:
    """Calculate SHA256 checksum of file content."""
    return hashlib.sha256(file_content).hexdigest()


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID string format."""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def extract_case_id_from_path(path: str) -> Optional[str]:
    """Extract case ID from URL path."""
    # Pattern: /api/v1/cases/{caseId}/...
    match = re.search(r'/cases/([a-f0-9-]{36})', path)
    return match.group(1) if match else None


def extract_patient_id_from_path(path: str) -> Optional[str]:
    """Extract patient ID from URL path."""
    # Pattern: /api/v1/patients/{patientId}/...
    match = re.search(r'/patients/([a-f0-9-]{36})', path)
    return match.group(1) if match else None


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """Mask sensitive data in dictionary."""
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'secret', 'token', 'key', 'credential',
            'ssn', 'social_security', 'credit_card', 'phone', 'email'
        ]
    
    masked_data = data.copy()
    
    def mask_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                    obj[key] = "[MASKED]"
                else:
                    mask_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                mask_recursive(item)
    
    mask_recursive(masked_data)
    return masked_data


def validate_confidence_score(score: float) -> bool:
    """Validate confidence score is between 0.0 and 1.0."""
    return 0.0 <= score <= 1.0


def normalize_text(text: str) -> str:
    """Normalize text for processing."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def extract_version_from_string(version_string: str) -> Optional[str]:
    """Extract semantic version from string."""
    # Pattern: v1.2.3 or 1.2.3
    match = re.search(r'v?(\d+\.\d+\.\d+)', version_string)
    return match.group(1) if match else None


def is_valid_iri(iri: str) -> bool:
    """Validate IRI format."""
    # Basic IRI validation
    iri_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(iri_pattern, iri))


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_correlation_id(correlation_id: str) -> Dict[str, str]:
    """Parse correlation ID to extract components."""
    # Expected format: corr_{uuid}
    if correlation_id.startswith('corr_'):
        return {
            'prefix': 'corr',
            'uuid': correlation_id[5:],
            'full': correlation_id
        }
    return {'full': correlation_id}


def generate_event_id() -> str:
    """Generate event ID for audit events."""
    return f"evt_{uuid.uuid4()}"


def generate_job_id() -> str:
    """Generate job ID for ML jobs."""
    return f"job_{uuid.uuid4()}"


def generate_correlation_id() -> str:
    """Generate correlation ID for request tracing."""
    return f"corr_{uuid.uuid4()}"


class Timer:
    """Simple timer utility for performance measurement."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the timer."""
        self.start_time = datetime.utcnow()
        return self
    
    def stop(self):
        """Stop the timer."""
        self.end_time = datetime.utcnow()
        return self
    
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return 0.0
        
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()
    
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed_seconds() * 1000
    
    def __enter__(self):
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
):
    """Retry function with exponential backoff."""
    import time
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            time.sleep(delay)


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: Dict[str, Any], sep: str = '.') -> Dict[str, Any]:
    """Unflatten dictionary with dot notation keys."""
    result = {}
    for key, value in d.items():
        keys = key.split(sep)
        current = result
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    return result


class ConfigValidator:
    """Configuration validation utility."""
    
    @staticmethod
    def validate_required_env_vars(required_vars: List[str]) -> Dict[str, str]:
        """Validate required environment variables are set."""
        import os
        
        missing_vars = []
        config = {}
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            else:
                config[var] = value
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return config
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, url))
    
    @staticmethod
    def validate_port(port: Union[str, int]) -> bool:
        """Validate port number."""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False


def create_response_metadata(
    total_items: int = 0,
    page: int = 1,
    page_size: int = 20,
    processing_time_ms: float = 0.0
) -> Dict[str, Any]:
    """Create response metadata for API responses."""
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    
    return {
        "total_items": total_items,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "processing_time_ms": processing_time_ms,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def validate_clinical_guardrails(text: str) -> List[str]:
    """Validate text against clinical guardrails."""
    violations = []
    
    # Patterns that indicate definitive diagnosis language
    definitive_patterns = [
        r'\bis\s+diagnosed\s+with\b',
        r'\bhas\s+been\s+diagnosed\b',
        r'\bconfirms?\s+diagnosis\b',
        r'\bdefinitive\s+diagnosis\b',
        r'\bcertain\s+that\b',
        r'\bguaranteed?\s+to\s+have\b',
        r'\bwill\s+definitely\b',
        r'\bmust\s+have\b',
        r'\bwithout\s+doubt\b',
    ]
    
    for pattern in definitive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Definitive diagnosis language detected: {pattern}")
    
    # Check for required disclaimers
    required_disclaimers = [
        r'limitation',
        r'research\s+use',
        r'not\s+for\s+diagnostic',
        r'clinical\s+correlation',
        r'further\s+evaluation'
    ]
    
    has_disclaimer = any(
        re.search(disclaimer, text, re.IGNORECASE) 
        for disclaimer in required_disclaimers
    )
    
    if not has_disclaimer:
        violations.append("Missing required clinical disclaimer")
    
    return violations
