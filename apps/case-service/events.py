"""
DERCAS-ONCO-XAI V1 - Case Service Events

Event publishing for case and patient operations.
"""

import logging
from typing import Optional

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.event_contracts.events import (
    EventType,
    create_case_event,
    create_audit_event,
    CaseEventPayload,
    PatientEventPayload,
    EventEnvelope
)
from packages.event_contracts.messaging import EventBus

from .models import Patient, Case

logger = logging.getLogger(__name__)


class EventPublisher:
    """Event publisher for case service operations."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.service_name = "case-service"
        logger.info("Initialized event publisher for case service")
    
    async def publish_patient_created(
        self,
        patient: Patient,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish patient created event.
        
        Args:
            patient: Created patient
            correlation_id: Request correlation ID
            user_id: User who created the patient
        """
        try:
            # Create patient event payload
            payload = PatientEventPayload(
                patient_id=patient.patient_id,
                medical_record_number=patient.medical_record_number,
                age=patient.age,
                gender=patient.gender
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.PATIENT_CREATED,
                correlation_id=correlation_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump()
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published patient created event: {patient.patient_id}",
                extra={
                    "correlation_id": correlation_id,
                    "patient_id": patient.patient_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish patient created event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "patient_id": patient.patient_id
                },
                exc_info=True
            )
    
    async def publish_patient_updated(
        self,
        patient: Patient,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        changes: Optional[dict] = None
    ):
        """
        Publish patient updated event.
        
        Args:
            patient: Updated patient
            correlation_id: Request correlation ID
            user_id: User who updated the patient
            changes: Dictionary of changed fields
        """
        try:
            # Create patient event payload
            payload = PatientEventPayload(
                patient_id=patient.patient_id,
                medical_record_number=patient.medical_record_number,
                age=patient.age,
                gender=patient.gender,
                changes=changes
            )
            
            # Create event envelope
            event = EventEnvelope(
                event_type=EventType.PATIENT_UPDATED,
                correlation_id=correlation_id,
                user_id=user_id,
                producer=self.service_name,
                payload=payload.model_dump()
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published patient updated event: {patient.patient_id}",
                extra={
                    "correlation_id": correlation_id,
                    "patient_id": patient.patient_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish patient updated event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "patient_id": patient.patient_id
                },
                exc_info=True
            )
    
    async def publish_case_created(
        self,
        case: Case,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish case created event.
        
        Args:
            case: Created case
            correlation_id: Request correlation ID
            user_id: User who created the case
        """
        try:
            # Create case event
            event = create_case_event(
                event_type=EventType.CASE_CREATED,
                case_id=case.case_id,
                patient_id=str(case.patient_id),
                producer=self.service_name,
                correlation_id=correlation_id,
                user_id=user_id,
                status=case.status.value,
                title=case.title,
                priority=case.priority,
                assigned_to=case.assigned_to
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published case created event: {case.case_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id,
                    "event_id": event.event_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish case created event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id
                },
                exc_info=True
            )
    
    async def publish_case_updated(
        self,
        case: Case,
        previous_case: Optional[Case] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish case updated event.
        
        Args:
            case: Updated case
            previous_case: Previous case state for change tracking
            correlation_id: Request correlation ID
            user_id: User who updated the case
        """
        try:
            # Determine changes
            changes = {}
            previous_status = None
            
            if previous_case:
                if previous_case.status != case.status:
                    changes["status"] = {
                        "from": previous_case.status.value,
                        "to": case.status.value
                    }
                    previous_status = previous_case.status.value
                
                if previous_case.title != case.title:
                    changes["title"] = {
                        "from": previous_case.title,
                        "to": case.title
                    }
                
                if previous_case.assigned_to != case.assigned_to:
                    changes["assigned_to"] = {
                        "from": previous_case.assigned_to,
                        "to": case.assigned_to
                    }
                
                if previous_case.priority != case.priority:
                    changes["priority"] = {
                        "from": previous_case.priority,
                        "to": case.priority
                    }
            
            # Create case event
            event = create_case_event(
                event_type=EventType.CASE_UPDATED,
                case_id=case.case_id,
                patient_id=str(case.patient_id),
                producer=self.service_name,
                correlation_id=correlation_id,
                user_id=user_id,
                status=case.status.value,
                previous_status=previous_status,
                title=case.title,
                priority=case.priority,
                assigned_to=case.assigned_to,
                changes=changes
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published case updated event: {case.case_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id,
                    "event_id": event.event_id,
                    "changes": changes
                }
            )
            
            # Publish specific status change event if status changed
            if previous_case and previous_case.status != case.status:
                await self.publish_case_status_changed(
                    case=case,
                    previous_status=previous_case.status.value,
                    correlation_id=correlation_id,
                    user_id=user_id
                )
            
        except Exception as e:
            logger.error(
                f"Failed to publish case updated event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id
                },
                exc_info=True
            )
    
    async def publish_case_status_changed(
        self,
        case: Case,
        previous_status: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish case status changed event.
        
        Args:
            case: Case with new status
            previous_status: Previous status value
            correlation_id: Request correlation ID
            user_id: User who changed the status
        """
        try:
            # Create case event
            event = create_case_event(
                event_type=EventType.CASE_STATUS_CHANGED,
                case_id=case.case_id,
                patient_id=str(case.patient_id),
                producer=self.service_name,
                correlation_id=correlation_id,
                user_id=user_id,
                status=case.status.value,
                previous_status=previous_status
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published case status changed event: {case.case_id} ({previous_status} → {case.status.value})",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id,
                    "event_id": event.event_id,
                    "previous_status": previous_status,
                    "new_status": case.status.value
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish case status changed event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id
                },
                exc_info=True
            )
    
    async def publish_case_assigned(
        self,
        case: Case,
        previous_assignee: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish case assigned event.
        
        Args:
            case: Assigned case
            previous_assignee: Previous assignee
            correlation_id: Request correlation ID
            user_id: User who assigned the case
        """
        try:
            # Create case event
            event = create_case_event(
                event_type=EventType.CASE_ASSIGNED,
                case_id=case.case_id,
                patient_id=str(case.patient_id),
                producer=self.service_name,
                correlation_id=correlation_id,
                user_id=user_id,
                assigned_to=case.assigned_to,
                changes={
                    "assigned_to": {
                        "from": previous_assignee,
                        "to": case.assigned_to
                    }
                }
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published case assigned event: {case.case_id} → {case.assigned_to}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id,
                    "event_id": event.event_id,
                    "assigned_to": case.assigned_to
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish case assigned event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id
                },
                exc_info=True
            )
    
    async def publish_case_closed(
        self,
        case: Case,
        reason: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Publish case closed event.
        
        Args:
            case: Closed case
            reason: Reason for closing
            correlation_id: Request correlation ID
            user_id: User who closed the case
        """
        try:
            # Create case event
            event = create_case_event(
                event_type=EventType.CASE_CLOSED,
                case_id=case.case_id,
                patient_id=str(case.patient_id),
                producer=self.service_name,
                correlation_id=correlation_id,
                user_id=user_id,
                status=case.status.value,
                changes={
                    "closure_reason": reason,
                    "processing_duration_seconds": case.get_processing_duration()
                }
            )
            
            # Publish event
            await self.event_bus.publish(event)
            
            logger.info(
                f"Published case closed event: {case.case_id}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id,
                    "event_id": event.event_id,
                    "reason": reason
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to publish case closed event: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "case_id": case.case_id
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
        Publish audit event for case service operations.
        
        Args:
            action: Action performed
            resource_type: Type of resource (patient, case)
            resource_id: Resource identifier
            outcome: Operation outcome (success, failure)
            correlation_id: Request correlation ID
            user_id: User who performed the action
            additional_details: Additional audit details
        """
        try:
            # Create audit event
            event = create_audit_event(
                event_category="case_management",
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
