"""
CRM/Ticketing Webhook Handlers

This module implements webhook handlers for CRM and ticketing systems,
providing case ingestion and status update capabilities.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
import logging
import asyncio
import json
import hashlib
import hmac
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from ..state import create_case_from_crm_payload, create_initial_state
from ..workflow.policy_validation import execute_policy_validation
from ..database import get_repository_factory

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Webhook event types"""
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_CLOSED = "case.closed"
    ATTACHMENT_ADDED = "attachment.added"
    PRIORITY_CHANGED = "priority.changed"
    STATUS_UPDATE = "status.update"


class WebhookStatus(str, Enum):
    """Webhook processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


@dataclass
class WebhookEvent:
    """Webhook event data structure"""
    event_id: str
    event_type: WebhookEventType
    source_system: str
    timestamp: datetime
    payload: Dict[str, Any]
    signature: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


@dataclass
class WebhookProcessingResult:
    """Result of webhook processing"""
    success: bool
    case_id: Optional[str] = None
    workflow_id: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: int = 0
    retry_count: int = 0


class WebhookProcessor(ABC):
    """Abstract base class for webhook processors"""
    
    def __init__(self, source_system: str):
        self.source_system = source_system
        self.secret_key: Optional[str] = None
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0
        }
    
    @abstractmethod
    async def process_webhook(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Process webhook event"""
        pass
    
    @abstractmethod
    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature"""
        pass
    
    def set_secret_key(self, secret_key: str) -> None:
        """Set webhook secret key for signature validation"""
        self.secret_key = secret_key
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get webhook processing statistics"""
        stats = self.processing_stats.copy()
        if stats["total_processed"] > 0:
            stats["success_rate"] = stats["successful"] / stats["total_processed"]
            stats["failure_rate"] = stats["failed"] / stats["total_processed"]
        return stats


class CRMWebhookHandler(WebhookProcessor):
    """
    CRM webhook handler for case management integration.
    
    Handles webhooks from CRM systems for case creation, updates,
    and status changes.
    """
    
    def __init__(self, crm_system: str = "CRM"):
        super().__init__(crm_system)
        self.repo_factory = get_repository_factory()
        self.event_handlers = {
            WebhookEventType.CASE_CREATED: self._handle_case_created,
            WebhookEventType.CASE_UPDATED: self._handle_case_updated,
            WebhookEventType.ATTACHMENT_ADDED: self._handle_attachment_added,
            WebhookEventType.PRIORITY_CHANGED: self._handle_priority_changed
        }
    
    async def process_webhook(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Process CRM webhook event"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Processing CRM webhook: {event.event_type} from {event.source_system}")
            
            # Validate signature if secret key is set
            if self.secret_key and event.signature:
                payload_bytes = json.dumps(event.payload, sort_keys=True).encode('utf-8')
                if not self.validate_signature(payload_bytes, event.signature):
                    raise ValueError("Invalid webhook signature")
            
            # Get event handler
            handler = self.event_handlers.get(event.event_type)
            if not handler:
                raise ValueError(f"Unsupported event type: {event.event_type}")
            
            # Process event
            result = await handler(event)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.processing_time_ms = int(processing_time)
            
            self.processing_stats["total_processed"] += 1
            if result.success:
                self.processing_stats["successful"] += 1
            else:
                self.processing_stats["failed"] += 1
            
            # Log webhook processing
            await self._log_webhook_processing(event, result)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"CRM webhook processing failed: {e}")
            
            result = WebhookProcessingResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
            
            self.processing_stats["total_processed"] += 1
            self.processing_stats["failed"] += 1
            
            await self._log_webhook_processing(event, result)
            
            return result
    
    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate HMAC signature"""
        if not self.secret_key:
            return True
        
        try:
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            return False
    
    async def _handle_case_created(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Handle case creation webhook"""
        try:
            # Extract case data from payload
            case_data = event.payload
            
            # Validate required fields
            required_fields = ["crm_ticket_id", "customer_id", "insurer_id", "service_code"]
            for field in required_fields:
                if field not in case_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Execute policy validation workflow
            final_state = await execute_policy_validation(case_data)
            
            case_id = final_state.get("case", {}).get("case_id")
            workflow_status = final_state.get("case", {}).get("state", "UNKNOWN")
            
            logger.info(f"Case created and processed: {case_id}, status: {workflow_status}")
            
            return WebhookProcessingResult(
                success=True,
                case_id=case_id,
                workflow_id=case_id  # Using case_id as workflow_id for simplicity
            )
            
        except Exception as e:
            logger.error(f"Case creation handling failed: {e}")
            return WebhookProcessingResult(
                success=False,
                error_message=str(e)
            )
    
    async def _handle_case_updated(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Handle case update webhook"""
        try:
            case_data = event.payload
            crm_ticket_id = case_data.get("crm_ticket_id")
            
            if not crm_ticket_id:
                raise ValueError("Missing crm_ticket_id in update payload")
            
            # Find existing case
            case_repo = self.repo_factory.case_repository()
            existing_case = case_repo.get_by_crm_ticket_id(crm_ticket_id)
            
            if not existing_case:
                # If case doesn't exist, treat as new case creation
                return await self._handle_case_created(event)
            
            # Update case data
            update_fields = {}
            if "priority" in case_data:
                update_fields["priority"] = case_data["priority"]
            if "service_amount" in case_data:
                update_fields["service_amount"] = case_data["service_amount"]
            if "status" in case_data:
                update_fields["status"] = case_data["status"]
            
            if update_fields:
                case_repo.update(existing_case.id, **update_fields)
            
            logger.info(f"Case updated: {existing_case.id}")
            
            return WebhookProcessingResult(
                success=True,
                case_id=existing_case.id
            )
            
        except Exception as e:
            logger.error(f"Case update handling failed: {e}")
            return WebhookProcessingResult(
                success=False,
                error_message=str(e)
            )
    
    async def _handle_attachment_added(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Handle attachment addition webhook"""
        try:
            attachment_data = event.payload
            crm_ticket_id = attachment_data.get("crm_ticket_id")
            
            if not crm_ticket_id:
                raise ValueError("Missing crm_ticket_id in attachment payload")
            
            # Find existing case
            case_repo = self.repo_factory.case_repository()
            existing_case = case_repo.get_by_crm_ticket_id(crm_ticket_id)
            
            if not existing_case:
                raise ValueError(f"Case not found for CRM ticket: {crm_ticket_id}")
            
            # Process attachment (simplified - would integrate with object storage)
            attachment_info = {
                "filename": attachment_data.get("filename"),
                "content_type": attachment_data.get("content_type"),
                "size": attachment_data.get("size"),
                "url": attachment_data.get("url"),
                "added_at": datetime.utcnow()
            }
            
            # Update case with new attachment
            # In production, would store attachment metadata properly
            
            logger.info(f"Attachment added to case: {existing_case.id}")
            
            return WebhookProcessingResult(
                success=True,
                case_id=existing_case.id
            )
            
        except Exception as e:
            logger.error(f"Attachment handling failed: {e}")
            return WebhookProcessingResult(
                success=False,
                error_message=str(e)
            )
    
    async def _handle_priority_changed(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Handle priority change webhook"""
        try:
            priority_data = event.payload
            crm_ticket_id = priority_data.get("crm_ticket_id")
            new_priority = priority_data.get("priority")
            
            if not crm_ticket_id or not new_priority:
                raise ValueError("Missing crm_ticket_id or priority in payload")
            
            # Find existing case
            case_repo = self.repo_factory.case_repository()
            existing_case = case_repo.get_by_crm_ticket_id(crm_ticket_id)
            
            if not existing_case:
                raise ValueError(f"Case not found for CRM ticket: {crm_ticket_id}")
            
            # Update case priority
            case_repo.update(existing_case.id, priority=new_priority)
            
            # If priority is now CRITICAL, might need to re-route
            if new_priority == "CRITICAL":
                # Could trigger workflow re-evaluation here
                pass
            
            logger.info(f"Priority changed for case: {existing_case.id} to {new_priority}")
            
            return WebhookProcessingResult(
                success=True,
                case_id=existing_case.id
            )
            
        except Exception as e:
            logger.error(f"Priority change handling failed: {e}")
            return WebhookProcessingResult(
                success=False,
                error_message=str(e)
            )
    
    async def _log_webhook_processing(
        self, 
        event: WebhookEvent, 
        result: WebhookProcessingResult
    ) -> None:
        """Log webhook processing for audit"""
        
        audit_repo = self.repo_factory.audit_log_repository()
        
        audit_data = {
            "case_id": result.case_id,
            "event_type": "WEBHOOK_PROCESSED",
            "event_category": "INTEGRATION",
            "event_description": f"CRM webhook processed: {event.event_type}",
            "user_id": "SYSTEM",
            "event_data": {
                "webhook_event_id": event.event_id,
                "webhook_event_type": event.event_type,
                "source_system": event.source_system,
                "success": result.success,
                "error_message": result.error_message,
                "processing_time_ms": result.processing_time_ms
            },
            "processing_time_ms": result.processing_time_ms,
            "security_level": "NORMAL"
        }
        
        try:
            audit_repo.create(**audit_data)
        except Exception as e:
            logger.error(f"Failed to log webhook processing: {e}")


class TicketingWebhookHandler(WebhookProcessor):
    """
    Ticketing system webhook handler.
    
    Handles webhooks from ticketing systems for case status updates
    and workflow state synchronization.
    """
    
    def __init__(self, ticketing_system: str = "TICKETING"):
        super().__init__(ticketing_system)
        self.repo_factory = get_repository_factory()
        self.status_mapping = {
            "NEW": "NUEVO",
            "IN_PROGRESS": "EN_PROCESO",
            "PENDING_REVIEW": "REQUIERE_REVISION",
            "RESOLVED": "CERRADO",
            "CLOSED": "CERRADO"
        }
    
    async def process_webhook(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Process ticketing webhook event"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Processing ticketing webhook: {event.event_type}")
            
            # Validate signature
            if self.secret_key and event.signature:
                payload_bytes = json.dumps(event.payload, sort_keys=True).encode('utf-8')
                if not self.validate_signature(payload_bytes, event.signature):
                    raise ValueError("Invalid webhook signature")
            
            # Process status update
            result = await self._handle_status_update(event)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.processing_time_ms = int(processing_time)
            
            self.processing_stats["total_processed"] += 1
            if result.success:
                self.processing_stats["successful"] += 1
            else:
                self.processing_stats["failed"] += 1
            
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"Ticketing webhook processing failed: {e}")
            
            result = WebhookProcessingResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
            
            self.processing_stats["total_processed"] += 1
            self.processing_stats["failed"] += 1
            
            return result
    
    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature"""
        # Similar to CRM handler
        if not self.secret_key:
            return True
        
        try:
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            return False
    
    async def _handle_status_update(self, event: WebhookEvent) -> WebhookProcessingResult:
        """Handle ticket status update"""
        try:
            status_data = event.payload
            ticket_id = status_data.get("ticket_id")
            new_status = status_data.get("status")
            
            if not ticket_id or not new_status:
                raise ValueError("Missing ticket_id or status in payload")
            
            # Find case by ticket ID
            case_repo = self.repo_factory.case_repository()
            existing_case = case_repo.get_by_crm_ticket_id(ticket_id)
            
            if not existing_case:
                logger.warning(f"Case not found for ticket: {ticket_id}")
                return WebhookProcessingResult(
                    success=True,  # Not an error, just no action needed
                    error_message=f"Case not found for ticket: {ticket_id}"
                )
            
            # Map external status to internal status
            internal_status = self.status_mapping.get(new_status, new_status)
            
            # Update case status
            case_repo.update(existing_case.id, status=internal_status)
            
            logger.info(f"Status updated for case: {existing_case.id} to {internal_status}")
            
            return WebhookProcessingResult(
                success=True,
                case_id=existing_case.id
            )
            
        except Exception as e:
            logger.error(f"Status update handling failed: {e}")
            return WebhookProcessingResult(
                success=False,
                error_message=str(e)
            )


class WebhookRetryManager:
    """
    Manages webhook retry logic for failed processing.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay_seconds: int = 60):
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_queue: List[Dict[str, Any]] = []
    
    async def add_for_retry(
        self, 
        event: WebhookEvent, 
        processor: WebhookProcessor,
        retry_count: int = 0
    ) -> None:
        """Add failed webhook for retry"""
        
        if retry_count >= self.max_retries:
            logger.error(f"Max retries exceeded for webhook: {event.event_id}")
            return
        
        retry_item = {
            "event": event,
            "processor": processor,
            "retry_count": retry_count + 1,
            "retry_at": datetime.utcnow().timestamp() + self.retry_delay_seconds
        }
        
        self.retry_queue.append(retry_item)
        logger.info(f"Added webhook for retry: {event.event_id}, attempt {retry_count + 1}")
    
    async def process_retries(self) -> None:
        """Process pending retries"""
        
        current_time = datetime.utcnow().timestamp()
        items_to_retry = []
        
        # Find items ready for retry
        for item in self.retry_queue:
            if item["retry_at"] <= current_time:
                items_to_retry.append(item)
        
        # Remove from queue
        for item in items_to_retry:
            self.retry_queue.remove(item)
        
        # Process retries
        for item in items_to_retry:
            try:
                result = await item["processor"].process_webhook(item["event"])
                
                if not result.success:
                    # Add for another retry if not at max
                    await self.add_for_retry(
                        item["event"], 
                        item["processor"], 
                        item["retry_count"]
                    )
                else:
                    logger.info(f"Webhook retry successful: {item['event'].event_id}")
                
            except Exception as e:
                logger.error(f"Webhook retry failed: {e}")
                await self.add_for_retry(
                    item["event"], 
                    item["processor"], 
                    item["retry_count"]
                )


# Factory functions

def create_crm_webhook_handler(
    crm_system: str = "CRM",
    secret_key: Optional[str] = None
) -> CRMWebhookHandler:
    """Create CRM webhook handler"""
    handler = CRMWebhookHandler(crm_system)
    if secret_key:
        handler.set_secret_key(secret_key)
    return handler


def create_ticketing_webhook_handler(
    ticketing_system: str = "TICKETING",
    secret_key: Optional[str] = None
) -> TicketingWebhookHandler:
    """Create ticketing webhook handler"""
    handler = TicketingWebhookHandler(ticketing_system)
    if secret_key:
        handler.set_secret_key(secret_key)
    return handler


def create_webhook_retry_manager(
    max_retries: int = 3,
    retry_delay_seconds: int = 60
) -> WebhookRetryManager:
    """Create webhook retry manager"""
    return WebhookRetryManager(max_retries, retry_delay_seconds)
