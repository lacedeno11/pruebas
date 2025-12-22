"""
Case Ingest Node (UC-OP-05) for Policy Validation Copilot

This module implements the case_ingest_node function that serves as the entry point
for the policy validation workflow. It handles:

- Payload validation and sanitization
- Field normalization against catalogs
- Deduplication logic by ticket_id and hash
- Idempotency checks
- Case persistence with attachments and hashes
- SLA calculation and queue assignment
- State updates with normalized data and audit logging

The node ensures data integrity, prevents duplicate processing, and establishes
the foundation for downstream workflow processing.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import ValidationError

from src.schemas.state import (
    PolicyValidationState,
    CaseData,
    AttachmentInfo,
    Priority,
    CaseState,
    update_state_audit
)


# ============================================================================
# Configuration and Constants
# ============================================================================

# Field validation catalogs (would be loaded from database/config in production)
VALID_INSURERS = {
    "INS001", "INS002", "INS003", "INS004", "INS005"
}

VALID_SERVICE_CODES = {
    "SRV001", "SRV002", "SRV003", "SRV004", "SRV005",
    "MED001", "MED002", "MED003", "DEN001", "DEN002"
}

VALID_PROVIDERS = {
    "PRV001", "PRV002", "PRV003", "PRV004", "PRV005"
}

VALID_QUEUES = {
    "high_priority_queue",
    "medium_priority_queue", 
    "low_priority_queue",
    "specialist_review_queue",
    "fraud_investigation_queue"
}

# SLA targets by priority (in hours)
SLA_TARGETS = {
    Priority.HIGH: 1,
    Priority.MEDIUM: 4,
    Priority.LOW: 24
}

# Maximum file size for attachments (in bytes)
MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024  # 50MB

# Supported file types
SUPPORTED_FILE_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "image/jpeg",
    "image/png",
    "text/plain"
}


# ============================================================================
# In-Memory Storage for Deduplication (Production: Use Redis/Database)
# ============================================================================

class CaseRegistry:
    """In-memory registry for case deduplication and idempotency."""
    
    def __init__(self):
        self._processed_tickets: Set[str] = set()
        self._case_hashes: Dict[str, str] = {}  # hash -> case_id
        self._case_data: Dict[str, Dict[str, Any]] = {}  # case_id -> case_data
    
    def is_ticket_processed(self, ticket_id: str) -> bool:
        """Check if ticket has already been processed."""
        return ticket_id in self._processed_tickets
    
    def get_case_by_hash(self, case_hash: str) -> Optional[str]:
        """Get case_id by content hash."""
        return self._case_hashes.get(case_hash)
    
    def register_case(self, case_id: str, ticket_id: str, case_hash: str, case_data: Dict[str, Any]):
        """Register a new case in the registry."""
        self._processed_tickets.add(ticket_id)
        self._case_hashes[case_hash] = case_id
        self._case_data[case_id] = case_data
    
    def get_case_data(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case data by case_id."""
        return self._case_data.get(case_id)


# Global registry instance (Production: Replace with Redis/Database)
case_registry = CaseRegistry()


# ============================================================================
# Validation Functions
# ============================================================================

def validate_payload_structure(payload: Dict[str, Any]) -> List[str]:
    """
    Validate the basic structure and required fields of the input payload.
    
    Args:
        payload: Raw input payload
        
    Returns:
        List[str]: List of validation errors
    """
    errors = []
    
    # Required fields
    required_fields = [
        "crm_ticket_id", "customer_id", "contract_id", "insurer_id",
        "plan_id", "service_code", "service_date", "provider_id"
    ]
    
    for field in required_fields:
        if field not in payload:
            errors.append(f"Missing required field: {field}")
        elif not payload[field] or str(payload[field]).strip() == "":
            errors.append(f"Empty value for required field: {field}")
    
    # Field type validations
    if "service_date" in payload:
        try:
            if isinstance(payload["service_date"], str):
                datetime.fromisoformat(payload["service_date"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            errors.append("Invalid service_date format. Expected ISO format.")
    
    if "priority" in payload:
        if payload["priority"] not in ["HIGH", "MEDIUM", "LOW"]:
            errors.append("Invalid priority. Must be HIGH, MEDIUM, or LOW.")
    
    # Validate attachments structure
    if "attachments" in payload:
        if not isinstance(payload["attachments"], list):
            errors.append("Attachments must be a list.")
        else:
            for i, attachment in enumerate(payload["attachments"]):
                if not isinstance(attachment, dict):
                    errors.append(f"Attachment {i} must be an object.")
                    continue
                
                required_attachment_fields = ["filename", "content_type", "size_bytes"]
                for field in required_attachment_fields:
                    if field not in attachment:
                        errors.append(f"Attachment {i} missing required field: {field}")
    
    return errors


def normalize_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and validate fields against catalogs.
    
    Args:
        payload: Raw payload data
        
    Returns:
        Dict[str, Any]: Normalized payload
    """
    normalized = payload.copy()
    
    # Normalize string fields
    string_fields = [
        "crm_ticket_id", "customer_id", "contract_id", "insurer_id",
        "plan_id", "service_code", "provider_id"
    ]
    
    for field in string_fields:
        if field in normalized:
            normalized[field] = str(normalized[field]).strip().upper()
    
    # Normalize service_date
    if "service_date" in normalized:
        if isinstance(normalized["service_date"], str):
            try:
                normalized["service_date"] = datetime.fromisoformat(
                    normalized["service_date"].replace("Z", "+00:00")
                )
            except ValueError:
                # Keep original value for error handling downstream
                pass
    
    # Normalize priority
    if "priority" in normalized:
        normalized["priority"] = normalized["priority"].upper()
    else:
        normalized["priority"] = "MEDIUM"  # Default priority
    
    # Normalize assigned_queue if not provided
    if "assigned_queue" not in normalized:
        priority_queue_map = {
            "HIGH": "high_priority_queue",
            "MEDIUM": "medium_priority_queue",
            "LOW": "low_priority_queue"
        }
        normalized["assigned_queue"] = priority_queue_map.get(
            normalized.get("priority", "MEDIUM"),
            "medium_priority_queue"
        )
    
    return normalized


def validate_against_catalogs(normalized_payload: Dict[str, Any]) -> List[str]:
    """
    Validate normalized fields against business catalogs.
    
    Args:
        normalized_payload: Normalized payload data
        
    Returns:
        List[str]: List of validation errors
    """
    errors = []
    
    # Validate insurer_id
    if normalized_payload.get("insurer_id") not in VALID_INSURERS:
        errors.append(f"Invalid insurer_id: {normalized_payload.get('insurer_id')}")
    
    # Validate service_code
    if normalized_payload.get("service_code") not in VALID_SERVICE_CODES:
        errors.append(f"Invalid service_code: {normalized_payload.get('service_code')}")
    
    # Validate provider_id
    if normalized_payload.get("provider_id") not in VALID_PROVIDERS:
        errors.append(f"Invalid provider_id: {normalized_payload.get('provider_id')}")
    
    # Validate assigned_queue
    if normalized_payload.get("assigned_queue") not in VALID_QUEUES:
        errors.append(f"Invalid assigned_queue: {normalized_payload.get('assigned_queue')}")
    
    return errors


def validate_attachments(attachments: List[Dict[str, Any]]) -> List[str]:
    """
    Validate attachment metadata and constraints.
    
    Args:
        attachments: List of attachment metadata
        
    Returns:
        List[str]: List of validation errors
    """
    errors = []
    
    for i, attachment in enumerate(attachments):
        # Validate file size
        size_bytes = attachment.get("size_bytes", 0)
        if size_bytes > MAX_ATTACHMENT_SIZE:
            errors.append(f"Attachment {i} exceeds maximum size limit ({MAX_ATTACHMENT_SIZE} bytes)")
        
        # Validate content type
        content_type = attachment.get("content_type", "")
        if content_type not in SUPPORTED_FILE_TYPES:
            errors.append(f"Attachment {i} has unsupported content type: {content_type}")
        
        # Validate filename
        filename = attachment.get("filename", "")
        if not filename or len(filename) > 255:
            errors.append(f"Attachment {i} has invalid filename")
        
        # Check for required checksum
        if "checksum" not in attachment:
            errors.append(f"Attachment {i} missing checksum")
    
    return errors


# ============================================================================
# Deduplication and Idempotency
# ============================================================================

def calculate_case_hash(normalized_payload: Dict[str, Any]) -> str:
    """
    Calculate a hash for case deduplication based on key fields.
    
    Args:
        normalized_payload: Normalized case data
        
    Returns:
        str: SHA-256 hash of key case fields
    """
    # Key fields for deduplication
    key_fields = [
        "customer_id", "contract_id", "service_code", 
        "service_date", "provider_id"
    ]
    
    # Create deterministic string for hashing
    hash_data = {}
    for field in key_fields:
        value = normalized_payload.get(field)
        if isinstance(value, datetime):
            hash_data[field] = value.isoformat()
        else:
            hash_data[field] = str(value) if value is not None else ""
    
    # Sort keys for deterministic hash
    hash_string = json.dumps(hash_data, sort_keys=True)
    return hashlib.sha256(hash_string.encode()).hexdigest()


def check_idempotency(ticket_id: str, case_hash: str) -> Optional[str]:
    """
    Check for duplicate processing and return existing case_id if found.
    
    Args:
        ticket_id: CRM ticket identifier
        case_hash: Calculated case hash
        
    Returns:
        Optional[str]: Existing case_id if duplicate found, None otherwise
    """
    # Check if ticket was already processed
    if case_registry.is_ticket_processed(ticket_id):
        return "DUPLICATE_TICKET"
    
    # Check if same case content was already processed
    existing_case_id = case_registry.get_case_by_hash(case_hash)
    if existing_case_id:
        return existing_case_id
    
    return None


# ============================================================================
# SLA and Queue Assignment
# ============================================================================

def calculate_sla_target(priority: Priority, service_date: datetime) -> datetime:
    """
    Calculate SLA target based on priority and service date.
    
    Args:
        priority: Case priority level
        service_date: Date of service
        
    Returns:
        datetime: SLA target timestamp
    """
    now = datetime.utcnow()
    sla_hours = SLA_TARGETS.get(priority, 24)
    
    # For urgent cases, SLA starts from now
    # For routine cases, consider service date recency
    if priority == Priority.HIGH:
        return now + timedelta(hours=sla_hours)
    
    # If service is recent (within 7 days), use standard SLA
    days_since_service = (now.date() - service_date.date()).days
    if days_since_service <= 7:
        return now + timedelta(hours=sla_hours)
    
    # For older services, extend SLA slightly
    extended_hours = min(sla_hours * 1.5, 48)  # Cap at 48 hours
    return now + timedelta(hours=extended_hours)


def assign_processing_queue(
    priority: Priority,
    service_code: str,
    insurer_id: str,
    case_hash: str
) -> str:
    """
    Assign case to appropriate processing queue.
    
    Args:
        priority: Case priority level
        service_code: Medical/service code
        insurer_id: Insurance company identifier
        case_hash: Case content hash
        
    Returns:
        str: Assigned queue name
    """
    # High priority cases go to high priority queue
    if priority == Priority.HIGH:
        return "high_priority_queue"
    
    # Check for fraud indicators (simple heuristic)
    fraud_indicators = [
        service_code.startswith("SRV"),  # Certain service codes
        case_hash.startswith("a"),  # Hash-based routing (example)
    ]
    
    if any(fraud_indicators) and priority != Priority.LOW:
        return "fraud_investigation_queue"
    
    # Specialist review for certain insurers
    specialist_insurers = {"INS001", "INS002"}
    if insurer_id in specialist_insurers:
        return "specialist_review_queue"
    
    # Default priority-based assignment
    priority_queue_map = {
        Priority.HIGH: "high_priority_queue",
        Priority.MEDIUM: "medium_priority_queue",
        Priority.LOW: "low_priority_queue"
    }
    
    return priority_queue_map.get(priority, "medium_priority_queue")


# ============================================================================
# Attachment Processing
# ============================================================================

def process_attachments(attachments_data: List[Dict[str, Any]]) -> List[AttachmentInfo]:
    """
    Process and validate attachment metadata.
    
    Args:
        attachments_data: Raw attachment data
        
    Returns:
        List[AttachmentInfo]: Processed attachment info objects
    """
    processed_attachments = []
    
    for attachment_data in attachments_data:
        # Generate file_id if not provided
        file_id = attachment_data.get("file_id", str(uuid4()))
        
        # Generate storage path
        storage_path = f"attachments/{file_id}/{attachment_data['filename']}"
        
        # Create AttachmentInfo object
        attachment_info = AttachmentInfo(
            file_id=file_id,
            filename=attachment_data["filename"],
            content_type=attachment_data["content_type"],
            size_bytes=attachment_data["size_bytes"],
            checksum=attachment_data.get("checksum", ""),
            upload_timestamp=datetime.utcnow(),
            storage_path=storage_path
        )
        
        processed_attachments.append(attachment_info)
    
    return processed_attachments


# ============================================================================
# Main Case Ingest Node Function
# ============================================================================

async def case_ingest_node(state: PolicyValidationState) -> PolicyValidationState:
    """
    Case Ingest Node (UC-OP-05) - Entry point for policy validation workflow.
    
    Implements:
    - Payload validation and sanitization
    - Field normalization against catalogs
    - Deduplication logic by ticket_id and hash
    - Idempotency checks
    - Case persistence with attachments and hashes
    - SLA calculation and queue assignment
    - State updates with normalized data and audit logging
    
    Args:
        state: Current PolicyValidationState
        
    Returns:
        PolicyValidationState: Updated state with case data and audit log
    """
    start_time = datetime.utcnow()
    node_name = "case_ingest"
    
    # Update audit trail - node started
    state = update_state_audit(
        state,
        node_name=node_name,
        status="started",
        input_hash=str(hash(str(state["case"])))
    )
    
    try:
        # Extract case data from state (assuming it was populated by API layer)
        case_data = state["case"]
        
        # Convert CaseData to dict for processing
        payload = {
            "crm_ticket_id": case_data.crm_ticket_id,
            "customer_id": case_data.customer_id,
            "contract_id": case_data.contract_id,
            "insurer_id": case_data.insurer_id,
            "plan_id": case_data.plan_id,
            "service_code": case_data.service_code,
            "service_date": case_data.service_date,
            "provider_id": case_data.provider_id,
            "priority": case_data.priority.value,
            "attachments": [
                {
                    "file_id": att.file_id,
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "size_bytes": att.size_bytes,
                    "checksum": att.checksum
                }
                for att in case_data.attachments
            ]
        }
        
        # Step 1: Validate payload structure
        validation_errors = validate_payload_structure(payload)
        if validation_errors:
            error_msg = f"Payload validation failed: {'; '.join(validation_errors)}"
            state = update_state_audit(
                state,
                node_name=node_name,
                status="failed",
                input_hash=str(hash(str(state["case"]))),
                error_message=error_msg
            )
            raise ValueError(error_msg)
        
        # Step 2: Normalize fields
        normalized_payload = normalize_fields(payload)
        
        # Step 3: Validate against catalogs
        catalog_errors = validate_against_catalogs(normalized_payload)
        if catalog_errors:
            error_msg = f"Catalog validation failed: {'; '.join(catalog_errors)}"
            state = update_state_audit(
                state,
                node_name=node_name,
                status="failed",
                input_hash=str(hash(str(state["case"]))),
                error_message=error_msg
            )
            raise ValueError(error_msg)
        
        # Step 4: Validate attachments
        if normalized_payload.get("attachments"):
            attachment_errors = validate_attachments(normalized_payload["attachments"])
            if attachment_errors:
                error_msg = f"Attachment validation failed: {'; '.join(attachment_errors)}"
                state = update_state_audit(
                    state,
                    node_name=node_name,
                    status="failed",
                    input_hash=str(hash(str(state["case"]))),
                    error_message=error_msg
                )
                raise ValueError(error_msg)
        
        # Step 5: Calculate case hash for deduplication
        case_hash = calculate_case_hash(normalized_payload)
        
        # Step 6: Check idempotency
        existing_case_id = check_idempotency(
            normalized_payload["crm_ticket_id"],
            case_hash
        )
        
        if existing_case_id:
            if existing_case_id == "DUPLICATE_TICKET":
                error_msg = f"Duplicate ticket processing detected: {normalized_payload['crm_ticket_id']}"
            else:
                error_msg = f"Duplicate case content detected. Existing case_id: {existing_case_id}"
            
            state = update_state_audit(
                state,
                node_name=node_name,
                status="failed",
                input_hash=str(hash(str(state["case"]))),
                error_message=error_msg
            )
            raise ValueError(error_msg)
        
        # Step 7: Process attachments
        processed_attachments = []
        if normalized_payload.get("attachments"):
            processed_attachments = process_attachments(normalized_payload["attachments"])
        
        # Step 8: Calculate SLA target
        priority = Priority(normalized_payload["priority"])
        service_date = normalized_payload["service_date"]
        sla_target = calculate_sla_target(priority, service_date)
        
        # Step 9: Assign processing queue
        assigned_queue = assign_processing_queue(
            priority,
            normalized_payload["service_code"],
            normalized_payload["insurer_id"],
            case_hash
        )
        
        # Step 10: Create normalized CaseData object
        normalized_case = CaseData(
            case_id=case_data.case_id,  # Keep existing case_id
            crm_ticket_id=normalized_payload["crm_ticket_id"],
            customer_id=normalized_payload["customer_id"],
            contract_id=normalized_payload["contract_id"],
            insurer_id=normalized_payload["insurer_id"],
            plan_id=normalized_payload["plan_id"],
            service_code=normalized_payload["service_code"],
            service_date=service_date,
            provider_id=normalized_payload["provider_id"],
            attachments=processed_attachments,
            priority=priority,
            sla_target=sla_target,
            state=CaseState.PROCESSING,
            assigned_queue=assigned_queue,
            created_at=case_data.created_at,
            updated_at=datetime.utcnow()
        )
        
        # Step 11: Register case in registry (for deduplication)
        case_registry.register_case(
            normalized_case.case_id,
            normalized_case.crm_ticket_id,
            case_hash,
            normalized_case.dict()
        )
        
        # Step 12: Update state with normalized case data
        state["case"] = normalized_case
        
        # Step 13: Update audit timestamps
        state["audit"].timestamps.processing_started = datetime.utcnow()
        
        # Step 14: Add processing log entry
        processing_log = f"Case ingested successfully. Hash: {case_hash[:8]}..., Queue: {assigned_queue}, SLA: {sla_target.isoformat()}"
        state["audit"].node_execution_log.append(
            type(state["audit"].node_execution_log[0])(
                node_name=node_name,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="completed",
                input_hash=str(hash(str(payload))),
                output_hash=str(hash(str(normalized_case.dict()))),
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
        )
        
        # Update audit trail - node completed
        state = update_state_audit(
            state,
            node_name=node_name,
            status="completed",
            input_hash=str(hash(str(payload))),
            output_hash=str(hash(str(normalized_case.dict()))),
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
        )
        
        return state
        
    except Exception as e:
        # Update audit trail - node failed
        state = update_state_audit(
            state,
            node_name=node_name,
            status="failed",
            input_hash=str(hash(str(state["case"]))),
            error_message=str(e),
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
        )
        
        # Update case state to indicate failure
        state["case"].state = CaseState.RECEIVED  # Reset to received state
        state["case"].updated_at = datetime.utcnow()
        
        raise


# ============================================================================
# Utility Functions for Testing and Monitoring
# ============================================================================

def get_case_registry_stats() -> Dict[str, Any]:
    """Get statistics about the case registry."""
    return {
        "processed_tickets_count": len(case_registry._processed_tickets),
        "unique_cases_count": len(case_registry._case_hashes),
        "registry_size": len(case_registry._case_data)
    }


def clear_case_registry():
    """Clear the case registry (for testing purposes)."""
    global case_registry
    case_registry = CaseRegistry()


def validate_case_data_integrity(case_data: CaseData) -> List[str]:
    """
    Validate the integrity of processed case data.
    
    Args:
        case_data: Processed case data
        
    Returns:
        List[str]: List of integrity issues
    """
    issues = []
    
    # Check required fields are not empty
    if not case_data.case_id:
        issues.append("Missing case_id")
    
    if not case_data.crm_ticket_id:
        issues.append("Missing crm_ticket_id")
    
    # Check SLA target is in the future
    if case_data.sla_target <= datetime.utcnow():
        issues.append("SLA target is in the past")
    
    # Check state consistency
    if case_data.state == CaseState.PROCESSING and not case_data.assigned_queue:
        issues.append("Processing case without assigned queue")
    
    # Check attachment integrity
    for i, attachment in enumerate(case_data.attachments):
        if not attachment.checksum:
            issues.append(f"Attachment {i} missing checksum")
        
        if not attachment.storage_path:
            issues.append(f"Attachment {i} missing storage path")
    
    return issues
