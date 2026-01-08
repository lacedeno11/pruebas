"""
Repository Pattern Implementations

This module provides repository pattern implementations for data access
in the Policy Validation Copilot system, offering a clean abstraction
layer over SQLAlchemy models.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type, TypeVar, Generic
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import and_, or_, desc, asc, func
from datetime import datetime, timedelta
import logging

from .models import (
    Case, CaseAttachment, Policy, PolicyException, EvidencePack, EvidenceItem,
    Decision, AuditLog, MLPrediction, GuardrailEvent, SystemConfiguration
)
from .base import get_db_session

logger = logging.getLogger(__name__)

# Generic type for model classes
ModelType = TypeVar('ModelType')


class BaseRepository(Generic[ModelType], ABC):
    """
    Abstract base repository providing common CRUD operations.
    
    Implements the Repository pattern for clean data access abstraction.
    """
    
    def __init__(self, model_class: Type[ModelType], session: Session = None):
        self.model_class = model_class
        self._session = session
    
    @property
    def session(self) -> Session:
        """Get database session"""
        if self._session:
            return self._session
        # This should be injected in production
        return next(get_db_session())
    
    def create(self, **kwargs) -> ModelType:
        """Create a new entity"""
        try:
            entity = self.model_class(**kwargs)
            self.session.add(entity)
            self.session.commit()
            self.session.refresh(entity)
            logger.info(f"Created {self.model_class.__name__} with id: {entity.id}")
            return entity
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Failed to create {self.model_class.__name__}: {e}")
            raise
    
    def get_by_id(self, entity_id: str) -> Optional[ModelType]:
        """Get entity by ID"""
        return self.session.query(self.model_class).filter(
            self.model_class.id == entity_id
        ).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all entities with pagination"""
        return self.session.query(self.model_class).offset(offset).limit(limit).all()
    
    def update(self, entity_id: str, **kwargs) -> Optional[ModelType]:
        """Update entity by ID"""
        try:
            entity = self.get_by_id(entity_id)
            if not entity:
                return None
            
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            # Update version for optimistic locking if available
            if hasattr(entity, 'version'):
                entity.version += 1
            
            # Update timestamp if available
            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.utcnow()
            
            self.session.commit()
            self.session.refresh(entity)
            logger.info(f"Updated {self.model_class.__name__} with id: {entity_id}")
            return entity
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Failed to update {self.model_class.__name__}: {e}")
            raise
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        try:
            entity = self.get_by_id(entity_id)
            if not entity:
                return False
            
            self.session.delete(entity)
            self.session.commit()
            logger.info(f"Deleted {self.model_class.__name__} with id: {entity_id}")
            return True
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Failed to delete {self.model_class.__name__}: {e}")
            raise
    
    def count(self) -> int:
        """Count total entities"""
        return self.session.query(self.model_class).count()
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        return self.session.query(
            self.session.query(self.model_class).filter(
                self.model_class.id == entity_id
            ).exists()
        ).scalar()


class CaseRepository(BaseRepository[Case]):
    """Repository for Case entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(Case, session)
    
    def get_by_crm_ticket_id(self, crm_ticket_id: str) -> Optional[Case]:
        """Get case by CRM ticket ID"""
        return self.session.query(Case).filter(
            Case.crm_ticket_id == crm_ticket_id
        ).first()
    
    def get_by_customer_id(self, customer_id: str, limit: int = 50) -> List[Case]:
        """Get cases by customer ID"""
        return self.session.query(Case).filter(
            Case.customer_id == customer_id
        ).order_by(desc(Case.created_at)).limit(limit).all()
    
    def get_by_status(self, status: str, limit: int = 100) -> List[Case]:
        """Get cases by status"""
        return self.session.query(Case).filter(
            Case.status == status
        ).order_by(desc(Case.created_at)).limit(limit).all()
    
    def get_pending_cases(self, limit: int = 100) -> List[Case]:
        """Get pending cases"""
        pending_statuses = ['PENDIENTE', 'EN_REVISION']
        return self.session.query(Case).filter(
            Case.status.in_(pending_statuses)
        ).order_by(asc(Case.created_at)).limit(limit).all()
    
    def get_overdue_cases(self) -> List[Case]:
        """Get cases that are overdue based on SLA"""
        now = datetime.utcnow()
        return self.session.query(Case).filter(
            and_(
                Case.sla_target_date < now,
                Case.status.in_(['PENDIENTE', 'EN_REVISION'])
            )
        ).order_by(asc(Case.sla_target_date)).all()
    
    def get_by_queue(self, queue: str, limit: int = 100) -> List[Case]:
        """Get cases by processing queue"""
        return self.session.query(Case).filter(
            Case.queue == queue
        ).order_by(desc(Case.created_at)).limit(limit).all()
    
    def get_assigned_to_user(self, user_id: str, limit: int = 100) -> List[Case]:
        """Get cases assigned to a specific user"""
        return self.session.query(Case).filter(
            Case.assigned_to == user_id
        ).order_by(desc(Case.created_at)).limit(limit).all()
    
    def search_cases(
        self,
        customer_id: str = None,
        service_code: str = None,
        status: str = None,
        priority: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        limit: int = 100
    ) -> List[Case]:
        """Search cases with multiple criteria"""
        query = self.session.query(Case)
        
        if customer_id:
            query = query.filter(Case.customer_id == customer_id)
        if service_code:
            query = query.filter(Case.service_code == service_code)
        if status:
            query = query.filter(Case.status == status)
        if priority:
            query = query.filter(Case.priority == priority)
        if date_from:
            query = query.filter(Case.created_at >= date_from)
        if date_to:
            query = query.filter(Case.created_at <= date_to)
        
        return query.order_by(desc(Case.created_at)).limit(limit).all()
    
    def get_case_statistics(self) -> Dict[str, Any]:
        """Get case statistics"""
        total_cases = self.session.query(Case).count()
        
        status_counts = self.session.query(
            Case.status, func.count(Case.id)
        ).group_by(Case.status).all()
        
        priority_counts = self.session.query(
            Case.priority, func.count(Case.id)
        ).group_by(Case.priority).all()
        
        overdue_count = len(self.get_overdue_cases())
        
        return {
            "total_cases": total_cases,
            "status_distribution": dict(status_counts),
            "priority_distribution": dict(priority_counts),
            "overdue_cases": overdue_count
        }


class PolicyRepository(BaseRepository[Policy]):
    """Repository for Policy entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(Policy, session)
    
    def get_by_policy_id(self, policy_id: str, version: str = None) -> Optional[Policy]:
        """Get policy by policy ID and optional version"""
        query = self.session.query(Policy).filter(Policy.policy_id == policy_id)
        
        if version:
            query = query.filter(Policy.version == version)
        else:
            # Get latest version
            query = query.order_by(desc(Policy.created_at))
        
        return query.first()
    
    def get_active_policies(self, policy_type: str = None) -> List[Policy]:
        """Get active policies"""
        query = self.session.query(Policy).filter(Policy.status == 'ACTIVE')
        
        if policy_type:
            query = query.filter(Policy.policy_type == policy_type)
        
        return query.order_by(Policy.policy_id, desc(Policy.version)).all()
    
    def get_policy_versions(self, policy_id: str) -> List[Policy]:
        """Get all versions of a policy"""
        return self.session.query(Policy).filter(
            Policy.policy_id == policy_id
        ).order_by(desc(Policy.version)).all()
    
    def search_policies(
        self,
        policy_type: str = None,
        category: str = None,
        status: str = None,
        effective_date_from: datetime = None,
        effective_date_to: datetime = None
    ) -> List[Policy]:
        """Search policies with criteria"""
        query = self.session.query(Policy)
        
        if policy_type:
            query = query.filter(Policy.policy_type == policy_type)
        if category:
            query = query.filter(Policy.category == category)
        if status:
            query = query.filter(Policy.status == status)
        if effective_date_from:
            query = query.filter(Policy.effective_date >= effective_date_from)
        if effective_date_to:
            query = query.filter(Policy.effective_date <= effective_date_to)
        
        return query.order_by(Policy.policy_id, desc(Policy.version)).all()


class PolicyExceptionRepository(BaseRepository[PolicyException]):
    """Repository for PolicyException entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(PolicyException, session)
    
    def get_active_exceptions(self, policy_id: str = None) -> List[PolicyException]:
        """Get active policy exceptions"""
        now = datetime.utcnow()
        query = self.session.query(PolicyException).filter(
            and_(
                PolicyException.status == 'ACTIVE',
                PolicyException.effective_date <= now,
                or_(
                    PolicyException.expiry_date.is_(None),
                    PolicyException.expiry_date > now
                )
            )
        )
        
        if policy_id:
            query = query.join(Policy).filter(Policy.policy_id == policy_id)
        
        return query.order_by(PolicyException.effective_date).all()
    
    def get_by_exception_id(self, exception_id: str) -> Optional[PolicyException]:
        """Get exception by exception ID"""
        return self.session.query(PolicyException).filter(
            PolicyException.exception_id == exception_id
        ).first()
    
    def increment_usage(self, exception_id: str) -> bool:
        """Increment usage count for an exception"""
        try:
            exception = self.get_by_exception_id(exception_id)
            if not exception:
                return False
            
            exception.usage_count += 1
            exception.last_used_at = datetime.utcnow()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to increment usage for exception {exception_id}: {e}")
            return False


class EvidencePackRepository(BaseRepository[EvidencePack]):
    """Repository for EvidencePack entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(EvidencePack, session)
    
    def get_by_case_id(self, case_id: str) -> List[EvidencePack]:
        """Get evidence packs by case ID"""
        return self.session.query(EvidencePack).filter(
            EvidencePack.case_id == case_id
        ).order_by(desc(EvidencePack.created_at)).all()
    
    def get_latest_by_case_id(self, case_id: str) -> Optional[EvidencePack]:
        """Get latest evidence pack for a case"""
        return self.session.query(EvidencePack).filter(
            EvidencePack.case_id == case_id
        ).order_by(desc(EvidencePack.created_at)).first()


class DecisionRepository(BaseRepository[Decision]):
    """Repository for Decision entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(Decision, session)
    
    def get_by_case_id(self, case_id: str) -> List[Decision]:
        """Get decisions by case ID"""
        return self.session.query(Decision).filter(
            Decision.case_id == case_id
        ).order_by(desc(Decision.created_at)).all()
    
    def get_final_decision(self, case_id: str) -> Optional[Decision]:
        """Get final decision for a case"""
        return self.session.query(Decision).filter(
            and_(
                Decision.case_id == case_id,
                Decision.is_final == True
            )
        ).first()
    
    def get_pending_hitl_decisions(self, assigned_to: str = None) -> List[Decision]:
        """Get decisions pending HITL review"""
        query = self.session.query(Decision).filter(
            and_(
                Decision.requires_hitl == True,
                Decision.hitl_completed_at.is_(None)
            )
        )
        
        if assigned_to:
            query = query.filter(Decision.hitl_assigned_to == assigned_to)
        
        return query.order_by(asc(Decision.created_at)).all()
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get decision statistics"""
        total_decisions = self.session.query(Decision).count()
        
        status_counts = self.session.query(
            Decision.status, func.count(Decision.id)
        ).group_by(Decision.status).all()
        
        hitl_pending = self.session.query(Decision).filter(
            and_(
                Decision.requires_hitl == True,
                Decision.hitl_completed_at.is_(None)
            )
        ).count()
        
        avg_confidence = self.session.query(
            func.avg(Decision.confidence_score)
        ).filter(Decision.confidence_score.isnot(None)).scalar()
        
        avg_risk = self.session.query(
            func.avg(Decision.risk_score)
        ).filter(Decision.risk_score.isnot(None)).scalar()
        
        return {
            "total_decisions": total_decisions,
            "status_distribution": dict(status_counts),
            "pending_hitl": hitl_pending,
            "average_confidence": float(avg_confidence) if avg_confidence else None,
            "average_risk": float(avg_risk) if avg_risk else None
        }


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(AuditLog, session)
    
    def get_by_case_id(self, case_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by case ID"""
        return self.session.query(AuditLog).filter(
            AuditLog.case_id == case_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_by_user_id(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by user ID"""
        return self.session.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_by_event_type(self, event_type: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by event type"""
        return self.session.query(AuditLog).filter(
            AuditLog.event_type == event_type
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_security_events(self, severity: str = None, limit: int = 100) -> List[AuditLog]:
        """Get security-related audit logs"""
        query = self.session.query(AuditLog).filter(
            AuditLog.event_category == 'SECURITY'
        )
        
        if severity:
            query = query.filter(AuditLog.security_level == severity)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def search_audit_logs(
        self,
        case_id: str = None,
        user_id: str = None,
        event_type: str = None,
        event_category: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Search audit logs with criteria"""
        query = self.session.query(AuditLog)
        
        if case_id:
            query = query.filter(AuditLog.case_id == case_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if event_category:
            query = query.filter(AuditLog.event_category == event_category)
        if date_from:
            query = query.filter(AuditLog.created_at >= date_from)
        if date_to:
            query = query.filter(AuditLog.created_at <= date_to)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()


class MLPredictionRepository(BaseRepository[MLPrediction]):
    """Repository for MLPrediction entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(MLPrediction, session)
    
    def get_by_case_id(self, case_id: str) -> List[MLPrediction]:
        """Get ML predictions by case ID"""
        return self.session.query(MLPrediction).filter(
            MLPrediction.case_id == case_id
        ).order_by(desc(MLPrediction.created_at)).all()
    
    def get_by_service_and_type(
        self, 
        service_name: str, 
        prediction_type: str,
        limit: int = 100
    ) -> List[MLPrediction]:
        """Get predictions by service and type"""
        return self.session.query(MLPrediction).filter(
            and_(
                MLPrediction.service_name == service_name,
                MLPrediction.prediction_type == prediction_type
            )
        ).order_by(desc(MLPrediction.created_at)).limit(limit).all()
    
    def get_model_performance_stats(self, model_version: str) -> Dict[str, Any]:
        """Get performance statistics for a model version"""
        predictions = self.session.query(MLPrediction).filter(
            MLPrediction.model_version == model_version
        ).all()
        
        if not predictions:
            return {}
        
        processing_times = [p.processing_time_ms for p in predictions if p.processing_time_ms]
        confidence_scores = [p.confidence_score for p in predictions if p.confidence_score]
        
        return {
            "total_predictions": len(predictions),
            "avg_processing_time_ms": sum(processing_times) / len(processing_times) if processing_times else None,
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else None,
            "min_processing_time_ms": min(processing_times) if processing_times else None,
            "max_processing_time_ms": max(processing_times) if processing_times else None
        }


class GuardrailEventRepository(BaseRepository[GuardrailEvent]):
    """Repository for GuardrailEvent entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(GuardrailEvent, session)
    
    def get_by_severity(self, severity: str, limit: int = 100) -> List[GuardrailEvent]:
        """Get guardrail events by severity"""
        return self.session.query(GuardrailEvent).filter(
            GuardrailEvent.severity == severity
        ).order_by(desc(GuardrailEvent.created_at)).limit(limit).all()
    
    def get_security_incidents(self, limit: int = 100) -> List[GuardrailEvent]:
        """Get high-severity security incidents"""
        return self.session.query(GuardrailEvent).filter(
            GuardrailEvent.severity.in_(['HIGH', 'CRITICAL'])
        ).order_by(desc(GuardrailEvent.created_at)).limit(limit).all()
    
    def get_blocked_requests(self, limit: int = 100) -> List[GuardrailEvent]:
        """Get blocked requests"""
        return self.session.query(GuardrailEvent).filter(
            GuardrailEvent.decision == 'BLOCK'
        ).order_by(desc(GuardrailEvent.created_at)).limit(limit).all()


class SystemConfigurationRepository(BaseRepository[SystemConfiguration]):
    """Repository for SystemConfiguration entities"""
    
    def __init__(self, session: Session = None):
        super().__init__(SystemConfiguration, session)
    
    def get_by_key(self, config_key: str) -> Optional[SystemConfiguration]:
        """Get configuration by key"""
        return self.session.query(SystemConfiguration).filter(
            and_(
                SystemConfiguration.config_key == config_key,
                SystemConfiguration.is_active == True
            )
        ).first()
    
    def get_by_category(self, category: str) -> List[SystemConfiguration]:
        """Get configurations by category"""
        return self.session.query(SystemConfiguration).filter(
            and_(
                SystemConfiguration.config_category == category,
                SystemConfiguration.is_active == True
            )
        ).order_by(SystemConfiguration.config_key).all()
    
    def get_all_active(self) -> List[SystemConfiguration]:
        """Get all active configurations"""
        return self.session.query(SystemConfiguration).filter(
            SystemConfiguration.is_active == True
        ).order_by(
            SystemConfiguration.config_category,
            SystemConfiguration.config_key
        ).all()


# Repository factory for dependency injection
class RepositoryFactory:
    """Factory for creating repository instances"""
    
    def __init__(self, session: Session = None):
        self.session = session
    
    def case_repository(self) -> CaseRepository:
        return CaseRepository(self.session)
    
    def policy_repository(self) -> PolicyRepository:
        return PolicyRepository(self.session)
    
    def policy_exception_repository(self) -> PolicyExceptionRepository:
        return PolicyExceptionRepository(self.session)
    
    def evidence_pack_repository(self) -> EvidencePackRepository:
        return EvidencePackRepository(self.session)
    
    def decision_repository(self) -> DecisionRepository:
        return DecisionRepository(self.session)
    
    def audit_log_repository(self) -> AuditLogRepository:
        return AuditLogRepository(self.session)
    
    def ml_prediction_repository(self) -> MLPredictionRepository:
        return MLPredictionRepository(self.session)
    
    def guardrail_event_repository(self) -> GuardrailEventRepository:
        return GuardrailEventRepository(self.session)
    
    def system_configuration_repository(self) -> SystemConfigurationRepository:
        return SystemConfigurationRepository(self.session)


# Global repository factory
repository_factory = RepositoryFactory()
