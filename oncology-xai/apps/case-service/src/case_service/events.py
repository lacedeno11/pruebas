# DERCAS-ONCO-XAI V1 - Case Service Events
# Event emission for case lifecycle events

from typing import Optional
from datetime import datetime
import structlog

from oncology_xai_event_contracts import EventPublisher, EventEnvelope
from oncology_xai_common.middleware import get_correlation_id

from .models import Patient, Case
from .schemas import CaseEventData, PatientEventData
from .config import Settings, get_settings

logger = structlog.get_logger(__name__)


class CaseEventEmitter:
    """Event emitter for case-related events."""
    
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
    
    async def emit_patient_created(
        self,
        patient: Patient,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit patient created event.
        
        Args:
            patient: Created patient
            correlation_id: Request correlation ID
        """
        try:
            event_data = PatientEventData(
                patient_id=patient.id,
                full_name=patient.full_name,
                medical_record_number=patient.medical_record_number,
                created_by=patient.created_by
            )
            
            envelope = EventEnvelope(
                event_type="patient.created",
                correlation_id=correlation_id or get_correlation_id(),
                producer="case-service",
                case_id=None,  # No case associated yet
                payload=event_data.dict()
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.patient.created"
            )
            
            logger.info(
                "Patient created event emitted",
                patient_id=patient.id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit patient created event",
                patient_id=patient.id,
                error=str(e)
            )
    
    async def emit_patient_updated(
        self,
        patient: Patient,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit patient updated event.
        
        Args:
            patient: Updated patient
            correlation_id: Request correlation ID
        """
        try:
            event_data = PatientEventData(
                patient_id=patient.id,
                full_name=patient.full_name,
                medical_record_number=patient.medical_record_number,
                updated_by=patient.updated_by
            )
            
            envelope = EventEnvelope(
                event_type="patient.updated",
                correlation_id=correlation_id or get_correlation_id(),
                producer="case-service",
                case_id=None,
                payload=event_data.dict()
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.patient.updated"
            )
            
            logger.info(
                "Patient updated event emitted",
                patient_id=patient.id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit patient updated event",
                patient_id=patient.id,
                error=str(e)
            )
    
    async def emit_case_created(
        self,
        case: Case,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit case created event.
        
        Args:
            case: Created case
            correlation_id: Request correlation ID
        """
        try:
            event_data = CaseEventData(
                case_id=case.id,
                patient_id=case.patient_id,
                title=case.title,
                status=case.status,
                processing_status=case.processing_status,
                created_by=case.created_by
            )
            
            envelope = EventEnvelope(
                event_type="case.created",
                correlation_id=correlation_id or get_correlation_id(),
                producer="case-service",
                case_id=case.id,
                payload=event_data.dict()
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.case.created"
            )
            
            logger.info(
                "Case created event emitted",
                case_id=case.id,
                patient_id=case.patient_id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit case created event",
                case_id=case.id,
                error=str(e)
            )
    
    async def emit_case_updated(
        self,
        case: Case,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit case updated event.
        
        Args:
            case: Updated case
            correlation_id: Request correlation ID
        """
        try:
            event_data = CaseEventData(
                case_id=case.id,
                patient_id=case.patient_id,
                title=case.title,
                status=case.status,
                processing_status=case.processing_status,
                updated_by=case.updated_by
            )
            
            envelope = EventEnvelope(
                event_type="case.updated",
                correlation_id=correlation_id or get_correlation_id(),
                producer="case-service",
                case_id=case.id,
                payload=event_data.dict()
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.case.updated"
            )
            
            logger.info(
                "Case updated event emitted",
                case_id=case.id,
                patient_id=case.patient_id,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit case updated event",
                case_id=case.id,
                error=str(e)
            )
    
    async def emit_case_status_changed(
        self,
        case: Case,
        old_status: str,
        new_status: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit case status changed event.
        
        Args:
            case: Case with changed status
            old_status: Previous status
            new_status: New status
            correlation_id: Request correlation ID
        """
        try:
            event_data = {
                "case_id": case.id,
                "patient_id": case.patient_id,
                "title": case.title,
                "old_status": old_status,
                "new_status": new_status,
                "processing_status": case.processing_status,
                "updated_by": case.updated_by
            }
            
            envelope = EventEnvelope(
                event_type="case.status_changed",
                correlation_id=correlation_id or get_correlation_id(),
                producer="case-service",
                case_id=case.id,
                payload=event_data
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.case.status_changed"
            )
            
            logger.info(
                "Case status changed event emitted",
                case_id=case.id,
                old_status=old_status,
                new_status=new_status,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit case status changed event",
                case_id=case.id,
                error=str(e)
            )
    
    async def emit_case_processing_status_changed(
        self,
        case: Case,
        old_processing_status: str,
        new_processing_status: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit case processing status changed event.
        
        Args:
            case: Case with changed processing status
            old_processing_status: Previous processing status
            new_processing_status: New processing status
            correlation_id: Request correlation ID
        """
        try:
            event_data = {
                "case_id": case.id,
                "patient_id": case.patient_id,
                "title": case.title,
                "old_processing_status": old_processing_status,
                "new_processing_status": new_processing_status,
                "processing_progress": case.processing_progress,
                "processing_error": case.processing_error,
                "updated_by": case.updated_by
            }
            
            envelope = EventEnvelope(
                event_type="case.processing_status_changed",
                correlation_id=correlation_id or get_correlation_id(),
                producer="case-service",
                case_id=case.id,
                payload=event_data
            )
            
            await self.publisher.publish(
                envelope=envelope,
                routing_key=f"{self.settings.rabbitmq_routing_key_prefix}.case.processing_status_changed"
            )
            
            logger.info(
                "Case processing status changed event emitted",
                case_id=case.id,
                old_processing_status=old_processing_status,
                new_processing_status=new_processing_status,
                correlation_id=envelope.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to emit case processing status changed event",
                case_id=case.id,
                error=str(e)
            )


# Global event emitter instance
_event_emitter: Optional[CaseEventEmitter] = None


async def get_event_emitter(settings: Settings = None) -> CaseEventEmitter:
    """Get event emitter instance."""
    global _event_emitter
    if _event_emitter is None:
        if settings is None:
            settings = get_settings()
        _event_emitter = CaseEventEmitter(settings)
        await _event_emitter.connect()
    return _event_emitter


async def cleanup_event_emitter() -> None:
    """Cleanup event emitter on shutdown."""
    global _event_emitter
    if _event_emitter is not None:
        await _event_emitter.disconnect()
        _event_emitter = None
    logger.info("Event emitter cleanup completed")
