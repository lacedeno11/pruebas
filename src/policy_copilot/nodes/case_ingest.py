"""
Case Ingest Node (UC-OP-05)

This module implements the Case Ingest Node for the Policy Validation Copilot system,
providing payload validation/normalization, deduplication logic, idempotency handling,
attachment processing, SLA calculation, and error handling.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
import json
import hashlib
import uuid
from dataclasses import dataclass
from enum import Enum

from ..state import PolicyValidationState, create_case_from_crm_payload, create_initial_state
from ..database import (
    CaseRepository, CaseAttachmentRepository, AuditLogRepository,
    get_repository_factory
)
from ..guardrails import create_security_context, evaluate_payload_security

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class DeduplicationError(Exception):
    """Custom exception for deduplication errors"""
    pass


class AttachmentError(Exception):
    """Custom exception for attachment processing errors"""
    pass


class Priority(str, Enum):
    """Case priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SLAConfig:
    """SLA configuration for different priority levels"""
    priority: Priority
    target_hours: int
    escalation_hours: int
    critical_hours: int


@dataclass
class AttachmentMetadata:
    """Attachment metadata for processing"""
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    storage_path: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class ValidationResult:
    """Result of payload validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_payload: Optional[Dict[str, Any]] = None


@dataclass
class DeduplicationResult:
    """Result of deduplication check"""
    is_duplicate: bool
    existing_case_id: Optional[str] = None
    similarity_score: float = 0.0
    duplicate_fields: List[str] = None


class CaseIngestNode:
    """
    Case Ingest Node implementing UC-OP-05.
    
    Handles the initial ingestion of cases from CRM systems with comprehensive
    validation, deduplication, attachment processing, and SLA calculation.
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.repo_factory = get_repository_factory()
        
        # SLA configurations
        self.sla_configs = self._initialize_sla_configs()
        
        # Validation rules
        self.validation_rules = self._initialize_validation_rules()
        
        # Deduplication settings
        self.deduplication_enabled = True
        self.deduplication_window_hours = 24
        self.similarity_threshold = 0.8
        
        # Attachment settings
        self.max_attachment_size = 50 * 1024 * 1024  # 50MB
        self.allowed_file_types = {
            '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', 
            '.tiff', '.xls', '.xlsx', '.csv', '.xml', '.json'
        }
        
        # Statistics
        self.ingest_stats = {
            "total_ingested": 0,
            "validation_failures": 0,
            "duplicates_detected": 0,
            "attachments_processed": 0,
            "sla_violations": 0
        }
    
    def _initialize_sla_configs(self) -> Dict[Priority, SLAConfig]:
        """Initialize SLA configurations for different priorities"""
        return {
            Priority.CRITICAL: SLAConfig(Priority.CRITICAL, 2, 1, 0.5),
            Priority.HIGH: SLAConfig(Priority.HIGH, 8, 4, 2),
            Priority.MEDIUM: SLAConfig(Priority.MEDIUM, 24, 12, 6),
            Priority.LOW: SLAConfig(Priority.LOW, 72, 48, 24)
        }
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules for case payloads"""
        return {
            "required_fields": [
                "crm_ticket_id",
                "customer_id",
                "insurer_id",
                "plan_id",
                "service_code",
                "service_date"
            ],
            "optional_fields": [
                "contract_id",
                "provider_id",
                "service_amount",
                "service_currency",
                "service_description",
                "diagnosis_codes",
                "procedure_codes",
                "priority",
                "attachments"
            ],
            "field_formats": {
                "crm_ticket_id": r"^[A-Z0-9-]{6,20}$",
                "customer_id": r"^[A-Z0-9]{6,15}$",
                "insurer_id": r"^INS[0-9]{3}$",
                "plan_id": r"^[A-Z0-9_]{3,20}$",
                "service_code": r"^[A-Z0-9_]{3,15}$",
                "service_amount": r"^\d+(\.\d{2})?$"
            },
            "field_constraints": {
                "service_amount": {"min": 0, "max": 1000000},
                "priority": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "service_currency": ["USD", "EUR", "GBP", "CAD"]
            }
        }
    
    async def ingest_case(
        self, 
        crm_payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> PolicyValidationState:
        """
        Main entry point for case ingestion.
        
        Args:
            crm_payload: Raw payload from CRM system
            correlation_id: Optional correlation ID for tracking
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            Initial policy validation state
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting case ingestion with correlation_id: {correlation_id}")
            
            # Step 1: Validate and normalize payload
            validation_result = await self._validate_and_normalize_payload(crm_payload)
            if not validation_result.is_valid:
                raise ValidationError(f"Payload validation failed: {validation_result.errors}")
            
            normalized_payload = validation_result.normalized_payload
            
            # Step 2: Check idempotency
            if idempotency_key:
                existing_case = await self._check_idempotency(idempotency_key)
                if existing_case:
                    logger.info(f"Idempotent request detected, returning existing case: {existing_case['case_id']}")
                    return await self._load_existing_state(existing_case["case_id"])
            
            # Step 3: Deduplication check
            if self.deduplication_enabled:
                dedup_result = await self._check_deduplication(normalized_payload)
                if dedup_result.is_duplicate:
                    logger.warning(f"Duplicate case detected: {dedup_result.existing_case_id}")
                    await self._handle_duplicate_case(normalized_payload, dedup_result)
                    return await self._load_existing_state(dedup_result.existing_case_id)
            
            # Step 4: Calculate SLA
            sla_info = await self._calculate_sla(normalized_payload)
            
            # Step 5: Process attachments
            attachment_results = await self._process_attachments(
                normalized_payload.get("attachments", [])
            )
            
            # Step 6: Create case record
            case_data = await self._prepare_case_data(
                normalized_payload, sla_info, attachment_results, correlation_id
            )
            
            # Step 7: Apply security guardrails
            security_context = create_security_context(
                user_id="SYSTEM",
                resource_type="case",
                action="create"
            )
            
            guardrail_result = await evaluate_payload_security(case_data, security_context)
            
            if guardrail_result.decision == "BLOCK":
                raise ValidationError(f"Security validation failed: {guardrail_result.flags}")
            
            # Step 8: Persist case
            case_id = await self._persist_case(case_data, attachment_results, idempotency_key)
            
            # Step 9: Create initial state
            initial_state = create_initial_state(case_data)
            
            # Step 10: Log ingestion audit
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._log_ingestion_audit(
                case_id, normalized_payload, processing_time, correlation_id
            )
            
            # Step 11: Update statistics
            await self._update_ingestion_statistics(validation_result, attachment_results)
            
            logger.info(
                f"Case ingestion completed: case_id={case_id}, "
                f"processing_time={processing_time}ms, "
                f"attachments={len(attachment_results)}"
            )
            
            return initial_state
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"Case ingestion failed: {e}")
            
            # Log error audit
            await self._log_error_audit(crm_payload, str(e), processing_time, correlation_id)
            
            # Update error statistics
            self.ingest_stats["validation_failures"] += 1
            
            raise
    
    async def _validate_and_normalize_payload(self, payload: Dict[str, Any]) -> ValidationResult:
        """Validate and normalize CRM payload"""
        
        errors = []
        warnings = []
        normalized = payload.copy()
        
        # Check required fields
        for field in self.validation_rules["required_fields"]:
            if field not in payload or payload[field] is None:
                errors.append(f"Missing required field: {field}")
            elif not str(payload[field]).strip():
                errors.append(f"Empty required field: {field}")
        
        # Validate field formats
        for field, pattern in self.validation_rules["field_formats"].items():
            if field in payload and payload[field] is not None:
                import re
                if not re.match(pattern, str(payload[field])):
                    errors.append(f"Invalid format for field {field}: {payload[field]}")
        
        # Validate field constraints
        for field, constraints in self.validation_rules["field_constraints"].items():
            if field in payload and payload[field] is not None:
                value = payload[field]
                
                if isinstance(constraints, dict):
                    # Numeric constraints
                    if "min" in constraints and float(value) < constraints["min"]:
                        errors.append(f"Field {field} below minimum: {value} < {constraints['min']}")
                    if "max" in constraints and float(value) > constraints["max"]:
                        errors.append(f"Field {field} above maximum: {value} > {constraints['max']}")
                
                elif isinstance(constraints, list):
                    # Enum constraints
                    if value not in constraints:
                        errors.append(f"Invalid value for field {field}: {value} not in {constraints}")
        
        # Normalize data types
        normalized = await self._normalize_data_types(normalized)
        
        # Add default values
        normalized = await self._add_default_values(normalized)
        
        # Validate business logic
        business_errors = await self._validate_business_logic(normalized)
        errors.extend(business_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_payload=normalized if len(errors) == 0 else None
        )
    
    async def _normalize_data_types(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data types in payload"""
        
        normalized = payload.copy()
        
        # Convert service_date to datetime
        if "service_date" in normalized:
            service_date = normalized["service_date"]
            if isinstance(service_date, str):
                try:
                    normalized["service_date"] = datetime.fromisoformat(service_date.replace('Z', '+00:00'))
                except ValueError:
                    # Try other common formats
                    from dateutil import parser
                    normalized["service_date"] = parser.parse(service_date)
        
        # Convert service_amount to float
        if "service_amount" in normalized and normalized["service_amount"] is not None:
            normalized["service_amount"] = float(normalized["service_amount"])
        
        # Ensure lists for codes
        for field in ["diagnosis_codes", "procedure_codes"]:
            if field in normalized:
                if isinstance(normalized[field], str):
                    normalized[field] = [normalized[field]]
                elif not isinstance(normalized[field], list):
                    normalized[field] = []
        
        return normalized
    
    async def _add_default_values(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add default values to payload"""
        
        defaults = {
            "priority": "MEDIUM",
            "service_currency": "USD",
            "service_urgency": "NORMAL",
            "diagnosis_codes": [],
            "procedure_codes": [],
            "attachments": []
        }
        
        for field, default_value in defaults.items():
            if field not in payload or payload[field] is None:
                payload[field] = default_value
        
        return payload
    
    async def _validate_business_logic(self, payload: Dict[str, Any]) -> List[str]:
        """Validate business logic rules"""
        
        errors = []
        
        # Service date should not be in the future
        service_date = payload.get("service_date")
        if service_date and service_date > datetime.utcnow():
            errors.append("Service date cannot be in the future")
        
        # Service date should not be too old (more than 2 years)
        if service_date and service_date < datetime.utcnow() - timedelta(days=730):
            errors.append("Service date is too old (more than 2 years)")
        
        # High priority cases should have service amount
        if payload.get("priority") in ["HIGH", "CRITICAL"] and not payload.get("service_amount"):
            errors.append("High priority cases must have service amount")
        
        # Emergency services should have high priority
        service_code = payload.get("service_code", "").upper()
        if "EMERGENCY" in service_code and payload.get("priority") not in ["HIGH", "CRITICAL"]:
            errors.append("Emergency services should have HIGH or CRITICAL priority")
        
        return errors
    
    async def _check_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Check for existing case with same idempotency key"""
        
        case_repo = self.repo_factory.case_repository()
        
        # In production, would store idempotency keys in database
        # For now, use a simple approach with case metadata
        
        # Search for cases with this idempotency key in metadata
        # This is a simplified implementation
        return None
    
    async def _check_deduplication(self, payload: Dict[str, Any]) -> DeduplicationResult:
        """Check for duplicate cases"""
        
        if not self.deduplication_enabled:
            return DeduplicationResult(is_duplicate=False)
        
        case_repo = self.repo_factory.case_repository()
        
        # Define deduplication window
        window_start = datetime.utcnow() - timedelta(hours=self.deduplication_window_hours)
        
        # Search for similar cases
        similar_cases = case_repo.search_cases(
            customer_id=payload.get("customer_id"),
            service_code=payload.get("service_code"),
            date_from=window_start
        )
        
        for case in similar_cases:
            similarity_score = await self._calculate_similarity(payload, case)
            
            if similarity_score >= self.similarity_threshold:
                duplicate_fields = await self._identify_duplicate_fields(payload, case)
                
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_case_id=case.id,
                    similarity_score=similarity_score,
                    duplicate_fields=duplicate_fields
                )
        
        return DeduplicationResult(is_duplicate=False)
    
    async def _calculate_similarity(self, payload1: Dict[str, Any], case2: Any) -> float:
        """Calculate similarity score between payload and existing case"""
        
        # Key fields for similarity comparison
        key_fields = [
            "customer_id", "service_code", "service_date", "service_amount",
            "provider_id", "diagnosis_codes", "procedure_codes"
        ]
        
        matches = 0
        total_fields = 0
        
        for field in key_fields:
            total_fields += 1
            
            payload_value = payload.get(field)
            case_value = getattr(case2, field, None)
            
            if payload_value == case_value:
                matches += 1
            elif field == "service_date":
                # Allow small time differences for service date
                if (payload_value and case_value and 
                    abs((payload_value - case_value).total_seconds()) < 3600):  # 1 hour
                    matches += 0.8
            elif field == "service_amount":
                # Allow small amount differences
                if (payload_value and case_value and 
                    abs(float(payload_value) - float(case_value)) < 10.0):
                    matches += 0.8
        
        return matches / total_fields if total_fields > 0 else 0.0
    
    async def _identify_duplicate_fields(self, payload: Dict[str, Any], case: Any) -> List[str]:
        """Identify which fields are duplicated"""
        
        duplicate_fields = []
        
        comparison_fields = [
            "customer_id", "service_code", "service_date", "service_amount",
            "provider_id", "crm_ticket_id"
        ]
        
        for field in comparison_fields:
            payload_value = payload.get(field)
            case_value = getattr(case, field, None)
            
            if payload_value == case_value:
                duplicate_fields.append(field)
        
        return duplicate_fields
    
    async def _handle_duplicate_case(
        self, 
        payload: Dict[str, Any], 
        dedup_result: DeduplicationResult
    ) -> None:
        """Handle duplicate case detection"""
        
        logger.warning(
            f"Duplicate case detected: existing_case_id={dedup_result.existing_case_id}, "
            f"similarity={dedup_result.similarity_score:.3f}, "
            f"duplicate_fields={dedup_result.duplicate_fields}"
        )
        
        # Update statistics
        self.ingest_stats["duplicates_detected"] += 1
        
        # Could implement additional logic here:
        # - Update existing case with new information
        # - Merge attachments
        # - Create audit trail for duplicate attempt
    
    async def _calculate_sla(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate SLA information for the case"""
        
        priority = Priority(payload.get("priority", "MEDIUM"))
        sla_config = self.sla_configs[priority]
        
        current_time = datetime.utcnow()
        
        sla_info = {
            "priority": priority.value,
            "sla_hours": sla_config.target_hours,
            "sla_target_date": current_time + timedelta(hours=sla_config.target_hours),
            "escalation_date": current_time + timedelta(hours=sla_config.escalation_hours),
            "critical_date": current_time + timedelta(hours=sla_config.critical_hours),
            "sla_config_version": "v1.0"
        }
        
        # Adjust SLA for emergency cases
        service_code = payload.get("service_code", "").upper()
        if "EMERGENCY" in service_code:
            sla_info["sla_hours"] = min(sla_info["sla_hours"], 4)  # Max 4 hours for emergency
            sla_info["sla_target_date"] = current_time + timedelta(hours=sla_info["sla_hours"])
        
        # Adjust SLA for high-value cases
        service_amount = payload.get("service_amount", 0)
        if service_amount > 10000:
            sla_info["sla_hours"] = min(sla_info["sla_hours"], 12)  # Max 12 hours for high-value
            sla_info["sla_target_date"] = current_time + timedelta(hours=sla_info["sla_hours"])
        
        return sla_info
    
    async def _process_attachments(self, attachments: List[Dict[str, Any]]) -> List[AttachmentMetadata]:
        """Process case attachments"""
        
        processed_attachments = []
        
        for i, attachment in enumerate(attachments):
            try:
                # Validate attachment
                await self._validate_attachment(attachment)
                
                # Process attachment
                metadata = await self._process_single_attachment(attachment, i)
                processed_attachments.append(metadata)
                
            except AttachmentError as e:
                logger.error(f"Attachment processing failed for attachment {i}: {e}")
                # Continue processing other attachments
        
        self.ingest_stats["attachments_processed"] += len(processed_attachments)
        
        return processed_attachments
    
    async def _validate_attachment(self, attachment: Dict[str, Any]) -> None:
        """Validate individual attachment"""
        
        # Check required fields
        required_fields = ["filename", "content", "content_type"]
        for field in required_fields:
            if field not in attachment:
                raise AttachmentError(f"Missing required attachment field: {field}")
        
        # Check file size
        content = attachment.get("content", "")
        size_bytes = len(content.encode('utf-8')) if isinstance(content, str) else len(content)
        
        if size_bytes > self.max_attachment_size:
            raise AttachmentError(f"Attachment too large: {size_bytes} bytes > {self.max_attachment_size}")
        
        # Check file type
        filename = attachment.get("filename", "")
        file_extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_extension not in self.allowed_file_types:
            raise AttachmentError(f"File type not allowed: {file_extension}")
        
        # Check for malicious content (simplified)
        if isinstance(content, str) and any(keyword in content.lower() for keyword in ["<script", "javascript:", "vbscript:"]):
            raise AttachmentError("Potentially malicious content detected")
    
    async def _process_single_attachment(self, attachment: Dict[str, Any], index: int) -> AttachmentMetadata:
        """Process a single attachment"""
        
        filename = attachment["filename"]
        content = attachment["content"]
        content_type = attachment["content_type"]
        
        # Calculate size and checksum
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        size_bytes = len(content_bytes)
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Generate storage path (in production, would upload to object storage)
        storage_path = f"attachments/{datetime.utcnow().strftime('%Y/%m/%d')}/{checksum}_{filename}"
        
        # Extract metadata
        description = attachment.get("description")
        tags = attachment.get("tags", [])
        
        return AttachmentMetadata(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum=checksum,
            storage_path=storage_path,
            description=description,
            tags=tags
        )
    
    async def _prepare_case_data(
        self,
        payload: Dict[str, Any],
        sla_info: Dict[str, Any],
        attachments: List[AttachmentMetadata],
        correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare case data for persistence"""
        
        case_data = {
            # Case identification
            "case_id": str(uuid.uuid4()),
            "crm_ticket_id": payload["crm_ticket_id"],
            "customer_id": payload["customer_id"],
            "contract_id": payload.get("contract_id"),
            
            # Service information
            "insurer_id": payload["insurer_id"],
            "plan_id": payload["plan_id"],
            "service_code": payload["service_code"],
            "service_date": payload["service_date"],
            "provider_id": payload.get("provider_id"),
            
            # Service details
            "service_amount": payload.get("service_amount"),
            "service_currency": payload.get("service_currency", "USD"),
            "service_description": payload.get("service_description"),
            "diagnosis_codes": payload.get("diagnosis_codes", []),
            "procedure_codes": payload.get("procedure_codes", []),
            
            # Case management
            "priority": payload.get("priority", "MEDIUM"),
            "status": "PENDIENTE",
            "queue": self._determine_queue(payload),
            "assigned_to": None,
            
            # SLA information
            "sla_target_date": sla_info["sla_target_date"],
            "sla_priority_hours": sla_info["sla_hours"],
            
            # Metadata
            "source_system": "CRM",
            "correlation_id": correlation_id,
            "tags": payload.get("tags", []),
            "metadata": {
                "ingestion_timestamp": datetime.utcnow(),
                "sla_config": sla_info,
                "attachment_count": len(attachments),
                "validation_passed": True
            }
        }
        
        return case_data
    
    def _determine_queue(self, payload: Dict[str, Any]) -> str:
        """Determine processing queue for the case"""
        
        priority = payload.get("priority", "MEDIUM")
        service_code = payload.get("service_code", "").upper()
        service_amount = payload.get("service_amount", 0)
        
        # Emergency queue
        if "EMERGENCY" in service_code or priority == "CRITICAL":
            return "EMERGENCY"
        
        # High-value queue
        if service_amount > 10000 or priority == "HIGH":
            return "HIGH_VALUE"
        
        # Specialized queues
        if "DENTAL" in service_code:
            return "DENTAL"
        elif "SURGERY" in service_code:
            return "SURGICAL"
        elif "MENTAL" in service_code:
            return "MENTAL_HEALTH"
        
        # Default queue
        return "STANDARD"
    
    async def _persist_case(
        self,
        case_data: Dict[str, Any],
        attachments: List[AttachmentMetadata],
        idempotency_key: Optional[str]
    ) -> str:
        """Persist case and attachments to database"""
        
        case_repo = self.repo_factory.case_repository()
        
        # Create case record
        case = case_repo.create(**case_data)
        case_id = case.id
        
        # Create attachment records
        if attachments:
            attachment_repo = self.repo_factory.case_attachment_repository()
            
            for attachment in attachments:
                attachment_data = {
                    "case_id": case_id,
                    "filename": attachment.filename,
                    "content_type": attachment.content_type,
                    "size_bytes": attachment.size_bytes,
                    "checksum": attachment.checksum,
                    "storage_path": attachment.storage_path,
                    "description": attachment.description,
                    "tags": attachment.tags
                }
                
                attachment_repo.create(**attachment_data)
        
        # Store idempotency key if provided
        if idempotency_key:
            # In production, would store in dedicated idempotency table
            pass
        
        return case_id
    
    async def _load_existing_state(self, case_id: str) -> PolicyValidationState:
        """Load existing case state"""
        
        case_repo = self.repo_factory.case_repository()
        case = case_repo.get_by_id(case_id)
        
        if not case:
            raise Exception(f"Case not found: {case_id}")
        
        # Convert case to state format
        case_data = {
            "case_id": case.id,
            "crm_ticket_id": case.crm_ticket_id,
            "customer_id": case.customer_id,
            "contract_id": case.contract_id,
            "insurer_id": case.insurer_id,
            "plan_id": case.plan_id,
            "service_code": case.service_code,
            "service_date": case.service_date,
            "provider_id": case.provider_id,
            "service_amount": case.service_amount,
            "service_currency": case.service_currency,
            "service_description": case.service_description,
            "diagnosis_codes": case.diagnosis_codes,
            "procedure_codes": case.procedure_codes,
            "priority": case.priority,
            "status": case.status,
            "queue": case.queue,
            "assigned_to": case.assigned_to,
            "sla_target_date": case.sla_target_date,
            "sla_priority_hours": case.sla_priority_hours,
            "source_system": case.source_system,
            "correlation_id": case.correlation_id,
            "tags": case.tags,
            "metadata": case.metadata
        }
        
        return create_initial_state(case_data)
    
    async def _log_ingestion_audit(
        self,
        case_id: str,
        payload: Dict[str, Any],
        processing_time_ms: int,
        correlation_id: Optional[str]
    ) -> None:
        """Log case ingestion audit trail"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        audit_data = {
            "case_id": case_id,
            "event_type": "CASE_INGESTED",
            "event_category": "CASE",
            "event_description": f"Case ingested from CRM: {payload.get('crm_ticket_id')}",
            "user_id": "SYSTEM",
            "correlation_id": correlation_id,
            "event_data": {
                "crm_ticket_id": payload.get("crm_ticket_id"),
                "customer_id": payload.get("customer_id"),
                "service_code": payload.get("service_code"),
                "priority": payload.get("priority"),
                "queue": self._determine_queue(payload),
                "attachment_count": len(payload.get("attachments", [])),
                "processing_time_ms": processing_time_ms
            },
            "processing_time_ms": processing_time_ms
        }
        
        try:
            audit_repo.create(**audit_data)
        except Exception as e:
            logger.error(f"Failed to log ingestion audit: {e}")
    
    async def _log_error_audit(
        self,
        payload: Dict[str, Any],
        error_message: str,
        processing_time_ms: int,
        correlation_id: Optional[str]
    ) -> None:
        """Log ingestion error audit trail"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        audit_data = {
            "event_type": "CASE_INGESTION_FAILED",
            "event_category": "CASE",
            "event_description": f"Case ingestion failed: {error_message}",
            "user_id": "SYSTEM",
            "correlation_id": correlation_id,
            "security_level": "HIGH",
            "event_data": {
                "crm_ticket_id": payload.get("crm_ticket_id"),
                "error_message": error_message,
                "payload_size": len(str(payload)),
                "processing_time_ms": processing_time_ms
            },
            "processing_time_ms": processing_time_ms
        }
        
        try:
            audit_repo.create(**audit_data)
        except Exception as e:
            logger.error(f"Failed to log error audit: {e}")
    
    async def _update_ingestion_statistics(
        self,
        validation_result: ValidationResult,
        attachments: List[AttachmentMetadata]
    ) -> None:
        """Update ingestion statistics"""
        
        self.ingest_stats["total_ingested"] += 1
        
        if not validation_result.is_valid:
            self.ingest_stats["validation_failures"] += 1
        
        self.ingest_stats["attachments_processed"] += len(attachments)
    
    def get_ingestion_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        stats = self.ingest_stats.copy()
        
        if stats["total_ingested"] > 0:
            stats["validation_success_rate"] = 1 - (stats["validation_failures"] / stats["total_ingested"])
            stats["duplicate_rate"] = stats["duplicates_detected"] / stats["total_ingested"]
            stats["avg_attachments_per_case"] = stats["attachments_processed"] / stats["total_ingested"]
        
        return stats
    
    def update_validation_rules(self, new_rules: Dict[str, Any]) -> None:
        """Update validation rules"""
        self.validation_rules.update(new_rules)
        logger.info("Validation rules updated")
    
    def update_sla_config(self, priority: Priority, config: SLAConfig) -> None:
        """Update SLA configuration"""
        self.sla_configs[priority] = config
        logger.info(f"SLA configuration updated for priority {priority.value}")


# Factory function for creating case ingest node
def create_case_ingest_node(use_mock: bool = False) -> CaseIngestNode:
    """
    Factory function to create case ingest node.
    
    Args:
        use_mock: Whether to use mock implementations
        
    Returns:
        Configured case ingest node
    """
    return CaseIngestNode(use_mock=use_mock)
