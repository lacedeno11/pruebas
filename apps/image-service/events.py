"""
DERCAS-ONCO-XAI V1 - Image Service Events

Event publishing for image operations.
"""

import logging
from typing import Optional

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.event_contracts.events import (
    EventType,
    create_audit_event,
    ImageEventPayload,
    EventEnvelope
)
from packages.event_contracts.messaging import EventBus

from .models import Image

logger = logging.getLogger(__name__)


class EventPublisher:
    """Event publisher for image service operations."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.service_name = "image-service"
        logger.info("Initialized event publisher for image service")
    
    async def publish_image_uploaded(
        self,
        image: Image,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish image uploaded event.
        
        Args:
            image: Uploaded image
            correlation_id: Request correlation ID
            user_id: User who uploaded the image
        """
        try:
            # Create image event payload
            payload = ImageEventPayload(
                image_id=image.image_id,
                case_id=image.case_id,
                filename=image.filename,
                file_size=image.file_size,
                file_format=image.file_format,
                storage_path=image.storage_path,
                checksum=image.checksum
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.IMAGE_UPLOADED,
                correlation_id=correlation_id,
                case_id=image.case_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump()
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published image uploaded event: {image.image_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish image uploaded event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id
                },
                exc_info=True
            )
    
    async def publish_image_validated(
        self,
        image: Image,
        validation_result: dict,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish image validated event.
        
        Args:
            image: Validated image
            validation_result: Validation result details
            correlation_id: Request correlation ID
            user_id: User who triggered validation
        """
        try:
            # Create image event payload
            payload = ImageEventPayload(
                image_id=image.image_id,
                case_id=image.case_id,
                filename=image.filename,
                file_size=image.file_size,
                file_format=image.file_format,
                storage_path=image.storage_path,
                checksum=image.checksum
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.IMAGE_VALIDATED,
                correlation_id=correlation_id,
                case_id=image.case_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump(),
                metadata={
                    "validation_result": validation_result,
                    "is_valid": validation_result.get("is_valid", False),
                    "validation_errors": validation_result.get("errors", [])
                }
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published image validated event: {image.image_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id,
                    "event_id": event.event_id,
                    "is_valid": validation_result.get("is_valid", False)
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish image validated event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id
                },
                exc_info=True
            )
    
    async def publish_image_processing_started(
        self,
        image: Image,
        processing_job_id: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish image processing started event.
        
        Args:
            image: Image being processed
            processing_job_id: Processing job ID
            correlation_id: Request correlation ID
            user_id: User who started processing
        """
        try:
            # Create image event payload
            payload = ImageEventPayload(
                image_id=image.image_id,
                case_id=image.case_id,
                filename=image.filename,
                processing_job_id=processing_job_id
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.IMAGE_PROCESSING_STARTED,
                correlation_id=correlation_id,
                case_id=image.case_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump()
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published image processing started event: {image.image_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id,
                    "processing_job_id": processing_job_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish image processing started event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id
                },
                exc_info=True
            )
    
    async def publish_image_processing_completed(
        self,
        image: Image,
        processing_job_id: str,
        processing_result: dict,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish image processing completed event.
        
        Args:
            image: Processed image
            processing_job_id: Processing job ID
            processing_result: Processing result details
            correlation_id: Request correlation ID
            user_id: User associated with processing
        """
        try:
            # Create image event payload
            payload = ImageEventPayload(
                image_id=image.image_id,
                case_id=image.case_id,
                filename=image.filename,
                processing_job_id=processing_job_id
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.IMAGE_PROCESSING_COMPLETED,
                correlation_id=correlation_id,
                case_id=image.case_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump(),
                metadata={
                    "processing_result": processing_result,
                    "processing_status": image.processing_status
                }
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published image processing completed event: {image.image_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id,
                    "processing_job_id": processing_job_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish image processing completed event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id
                },
                exc_info=True
            )
    
    async def publish_image_processing_failed(
        self,
        image: Image,
        processing_job_id: str,
        error_message: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish image processing failed event.
        
        Args:
            image: Image that failed processing
            processing_job_id: Processing job ID
            error_message: Error message
            correlation_id: Request correlation ID
            user_id: User associated with processing
        """
        try:
            # Create image event payload
            payload = ImageEventPayload(
                image_id=image.image_id,
                case_id=image.case_id,
                filename=image.filename,
                processing_job_id=processing_job_id
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.IMAGE_PROCESSING_FAILED,
                correlation_id=correlation_id,
                case_id=image.case_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump(),
                metadata={
                    "error_message": error_message,
                    "processing_status": "failed"
                }
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published image processing failed event: {image.image_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id,
                    "processing_job_id": processing_job_id,
                    "event_id": event.event_id,
                    "error": error_message
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish image processing failed event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id
                },
                exc_info=True
            )
    
    async def publish_image_deleted(
        self,
        image: Image,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish image deleted event.
        
        Args:
            image: Deleted image
            correlation_id: Request correlation ID
            user_id: User who deleted the image
        """
        try:
            # Create image event payload
            payload = ImageEventPayload(
                image_id=image.image_id,
                case_id=image.case_id,
                filename=image.filename,
                file_size=image.file_size,
                file_format=image.file_format,
                storage_path=image.storage_path,
                checksum=image.checksum
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.IMAGE_DELETED,
                correlation_id=correlation_id,
                case_id=image.case_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump()
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published image deleted event: {image.image_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish image deleted event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": image.case_id,
                    "image_id": image.image_id
                },
                exc_info=True
            )
    
    async def publish_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str = "success",
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_details: Optional[dict] = None
    ):
        """
        Publish audit event for image service operations.
        
        Args:
            action: Action performed
            resource_type: Type of resource (image, thumbnail)
            resource_id: Resource identifier
            outcome: Operation outcome (success, failure)
            correlation_id: Request correlation ID
            user_id: User who performed the action
            additional_details: Additional audit details
        """
        try:
            # Create audit event
            event = create_audit_event(
                event_category="image_management",
                action=action,
                outcome=outcome,
                producer=self.service_name,
                correlation_id=correlation_id,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                additional_details=additional_details or {}
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.debug(
                f"Published audit event: {action} on {resource_type}:{resource_id}",
                extra={
                    "correlation_id": correlation_id,
                    "event_id": event.event_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "outcome": outcome
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish audit event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id
                },
                exc_info=True
            )
