# DERCAS-ONCO-XAI V1 - Image Service Events
# Event emission for image lifecycle events

from typing import Optional
from datetime import datetime
import structlog

from oncology_xai_event_contracts import EventPublisher, EventEnvelope
from oncology_xai_common.middleware import get_correlation_id

from .models import Image
from .schemas import ImageEventData
from .config import Settings, get_settings

logger = structlog.get_logger(__name__)


class ImageEventEmitter:
    """Event emitter for image-related events."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.publisher = EventPublisher(
            rabbitmq_url=settings.rabbitmq_url,
            exchange_name=settings.rabbitmq_exchange
        )
    
    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        await self.publisher.connect()
        logger.info("Event publisher connected")
    
    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        await self.publisher.disconnect()
        logger.info("Event publisher disconnected")
    
    async def emit_image_uploaded(
        self,
        image: Image,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit image uploaded event.
        
        Args:
            image: Uploaded image
            correlation_id: Request correlation ID
        """
        try:
            event_data = ImageEventData(
                image_id=image.id,
                case_id=image.case_id,
                original_filename=image.original_filename,
                file_format=image.file_format,
                file_size=image.file_size,
                processing_status=image.processing_status,
                uploaded_by=image.uploaded_by
            )
            
            envelope = EventEnvelope(
                event_type="image.uploaded",
                correlation_id=correlation_id or get_correlation_id(),
                producer="image-service",
                case_id=image.case_id,
                payload=event_data.dict()
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.image.uploaded"
            )
            
            logger.info(
                "Image uploaded event emitted",
                image_id=image.id,
                case_id=image.case_id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit image uploaded event",
                image_id=image.id,
                error=str(e)
            )
    
    async def emit_image_deleted(
        self,
        image: Image,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit image deleted event.
        
        Args:
            image: Deleted image
            correlation_id: Request correlation ID
        """
        try:
            event_data = ImageEventData(
                image_id=image.id,
                case_id=image.case_id,
                original_filename=image.original_filename,
                file_format=image.file_format,
                file_size=image.file_size,
                processing_status=image.processing_status,
                updated_by=image.updated_by
            )
            
            envelope = EventEnvelope(
                event_type="image.deleted",
                correlation_id=correlation_id or get_correlation_id(),
                producer="image-service",
                case_id=image.case_id,
                payload=event_data.dict()
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.image.deleted"
            )
            
            logger.info(
                "Image deleted event emitted",
                image_id=image.id,
                case_id=image.case_id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit image deleted event",
                image_id=image.id,
                error=str(e)
            )
    
    async def emit_image_processing_status_changed(
        self,
        image: Image,
        old_status: str,
        new_status: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit image processing status changed event.
        
        Args:
            image: Image with changed status
            old_status: Previous processing status
            new_status: New processing status
            correlation_id: Request correlation ID
        """
        try:
            event_data = {
                "image_id": image.id,
                "case_id": image.case_id,
                "original_filename": image.original_filename,
                "file_format": image.file_format,
                "old_processing_status": old_status,
                "new_processing_status": new_status,
                "processing_error": image.processing_error,
                "updated_by": image.updated_by
            }
            
            envelope = EventEnvelope(
                event_type="image.processing_status_changed",
                correlation_id=correlation_id or get_correlation_id(),
                producer="image-service",
                case_id=image.case_id,
                payload=event_data
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.image.processing_status_changed"
            )
            
            logger.info(
                "Image processing status changed event emitted",
                image_id=image.id,
                old_status=old_status,
                new_status=new_status,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit image processing status changed event",
                image_id=image.id,
                error=str(e)
            )
    
    async def emit_image_viewed(
        self,
        image: Image,
        viewer_user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit image viewed event.
        
        Args:
            image: Viewed image
            viewer_user_id: User who viewed the image
            correlation_id: Request correlation ID
        """
        try:
            event_data = {
                "image_id": image.id,
                "case_id": image.case_id,
                "original_filename": image.original_filename,
                "view_count": image.view_count,
                "viewer_user_id": viewer_user_id,
                "viewed_at": datetime.utcnow().isoformat()
            }
            
            envelope = EventEnvelope(
                event_type="image.viewed",
                correlation_id=correlation_id or get_correlation_id(),
                producer="image-service",
                case_id=image.case_id,
                payload=event_data
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.image.viewed"
            )
            
            logger.debug(
                "Image viewed event emitted",
                image_id=image.id,
                view_count=image.view_count,
                viewer_user_id=viewer_user_id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit image viewed event",
                image_id=image.id,
                error=str(e)
            )


# Global event emitter instance
_event_emitter: Optional[ImageEventEmitter] = None


async def get_event_emitter(settings: Settings = None) -> ImageEventEmitter:
    """Get event emitter instance."""
    global _event_emitter
    if _event_emitter is None:
        if settings is None:
            settings = get_settings()
        _event_emitter = ImageEventEmitter(settings)
        await _event_emitter.connect()
    return _event_emitter


async def cleanup_event_emitter() -> None:
    """Cleanup event emitter on shutdown."""
    global _event_emitter
    if _event_emitter is not None:
        await _event_emitter.disconnect()
        _event_emitter = None
    logger.info("Event emitter cleanup completed")
