"""
Repository Pattern Implementations for DERCAS 01 Policy Validation Copilot

Provides repository pattern implementations for each entity type, abstracting
database operations and providing a clean interface for data access.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from .database import (
    AuditTrailModel,
    CaseModel,
    ChecklistModel,
    DecisionRecordModel,
    EvidencePackModel,
    ExceptionRuleModel,
    ExternalQueryModel,
    GuardrailRecordModel,
    HITLRequestModel,
    MLScoreRecordModel,
    ModelVersionModel,
    NotificationModel,
    PolicyDocumentModel,
    SystemConfigModel,
)
from ..models.entities import (
    AuditTrail,
    Case,
    Checklist,
    DecisionRecord,
    EvidencePack,
    ExceptionRule,
    ExternalQuery,
    GuardrailRecord,
    HITLRequest,
    MLScoreRecord,
    PolicyDocument,
)
from ..models.enums import CaseStatus, DecisionStatus, ExceptionStatus, PolicyStatus

logger = logging.getLogger(__name__)

# Type variables for generic repository
T = TypeVar('T')
M = TypeVar('M')


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found."""
    pass


class DuplicateEntityError(RepositoryError):
    """Raised when attempting to create a duplicate entity."""
    pass


class BaseRepository(ABC):
    """Abstract base repository with common CRUD operations."""
    
    def __init__(self, session: Session, model_class: Type[M], entity_class: Type[T]):
        self.session = session
        self.model_class = model_class
        self.entity_class = entity_class
    
    def _model_to_entity(self, model: M) -> T:
        """Convert SQLAlchemy model to Pydantic entity."""
        # This is a simplified conversion - in practice, you might want
        # more sophisticated mapping logic
        model_dict = {}
        for column in self.model_class.__table__.columns:
            value = getattr(model, column.name)
            model_dict[column.name] = value
        
        return self.entity_class(**model_dict)
    
    def _entity_to_model(self, entity: T, model: Optional[M] = None) -> M:
        """Convert Pydantic entity to SQLAlchemy model."""
        if model is None:
            model = self.model_class()
        
        entity_dict = entity.dict() if hasattr(entity, 'dict') else entity.__dict__
        
        for key, value in entity_dict.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        return model
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        try:
            model = self._entity_to_model(entity)
            self.session.add(model)
            self.session.flush()  # Get the ID without committing
            return self._model_to_entity(model)
        except IntegrityError as e:
            self.session.rollback()
            raise DuplicateEntityError(f"Entity already exists: {e}")
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to create entity: {e}")
    
    def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.id == entity_id
            ).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get entity by ID: {e}")
    
    def update(self, entity_id: UUID, updates: Dict[str, Any]) -> Optional[T]:
        """Update an entity."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.id == entity_id
            ).first()
            
            if model is None:
                return None
            
            for key, value in updates.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            
            model.updated_at = datetime.utcnow()
            self.session.flush()
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to update entity: {e}")
    
    def delete(self, entity_id: UUID) -> bool:
        """Delete an entity."""
        try:
            result = self.session.query(self.model_class).filter(
                self.model_class.id == entity_id
            ).delete()
            
            return result > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to delete entity: {e}")
    
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """List all entities with optional pagination."""
        try:
            query = self.session.query(self.model_class)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list entities: {e}")


class CaseRepository(BaseRepository):
    """Repository for Case entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, CaseModel, Case)
    
    def get_by_case_id(self, case_id: str) -> Optional[Case]:
        """Get case by business case ID."""
        try:
            model = self.session.query(CaseModel).filter(
                CaseModel.case_id == case_id
            ).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get case by case_id: {e}")
    
    def get_by_crm_ticket_id(self, crm_ticket_id: str) -> Optional[Case]:
        """Get case by CRM ticket ID."""
        try:
            model = self.session.query(CaseModel).filter(
                CaseModel.crm_ticket_id == crm_ticket_id
            ).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get case by CRM ticket ID: {e}")
    
    def list_by_status(self, status: CaseStatus, limit: Optional[int] = None) -> List[Case]:
        """List cases by status."""
        try:
            query = self.session.query(CaseModel).filter(
                CaseModel.status == status.value
            ).order_by(desc(CaseModel.created_at))
            
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list cases by status: {e}")
    
    def list_by_insurer(self, insurer_id: str, limit: Optional[int] = None) -> List[Case]:
        """List cases by insurer."""
        try:
            query = self.session.query(CaseModel).filter(
                CaseModel.insurer_id == insurer_id
            ).order_by(desc(CaseModel.created_at))
            
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list cases by insurer: {e}")
    
    def list_sla_at_risk(self, threshold_minutes: int = 60) -> List[Case]:
        """List cases at risk of SLA breach."""
        try:
            now = datetime.utcnow()
            
            models = self.session.query(CaseModel).filter(
                and_(
                    CaseModel.sla_target.isnot(None),
                    CaseModel.sla_target <= now + timedelta(minutes=threshold_minutes),
                    CaseModel.status.in_([
                        CaseStatus.CREATED.value,
                        CaseStatus.INGESTED.value,
                        CaseStatus.ROUTING.value,
                        CaseStatus.RETRIEVING_POLICY.value,
                        CaseStatus.BUILDING_CHECKLIST.value,
                        CaseStatus.DECIDING.value,
                        CaseStatus.HITL_REVIEW.value,
                    ])
                )
            ).order_by(CaseModel.sla_target).all()
            
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list SLA at-risk cases: {e}")
    
    def update_status(self, case_id: str, status: CaseStatus, updated_by: Optional[str] = None) -> Optional[Case]:
        """Update case status."""
        try:
            model = self.session.query(CaseModel).filter(
                CaseModel.case_id == case_id
            ).first()
            
            if model is None:
                return None
            
            model.status = status.value
            model.updated_at = datetime.utcnow()
            model.last_activity_at = datetime.utcnow()
            
            if updated_by:
                model.updated_by = updated_by
            
            self.session.flush()
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to update case status: {e}")


class PolicyDocumentRepository(BaseRepository):
    """Repository for PolicyDocument entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, PolicyDocumentModel, PolicyDocument)
    
    def get_by_doc_id_version(self, doc_id: str, version: str) -> Optional[PolicyDocument]:
        """Get policy document by doc_id and version."""
        try:
            model = self.session.query(PolicyDocumentModel).filter(
                and_(
                    PolicyDocumentModel.doc_id == doc_id,
                    PolicyDocumentModel.version == version
                )
            ).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get policy document: {e}")
    
    def list_active_policies(self, insurer_id: Optional[str] = None) -> List[PolicyDocument]:
        """List active policy documents."""
        try:
            query = self.session.query(PolicyDocumentModel).filter(
                PolicyDocumentModel.status == PolicyStatus.ACTIVE.value
            )
            
            if insurer_id:
                query = query.filter(PolicyDocumentModel.insurer_id == insurer_id)
            
            query = query.order_by(desc(PolicyDocumentModel.effective_date))
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list active policies: {e}")
    
    def find_applicable_policies(
        self,
        insurer_id: str,
        plan_id: str,
        service_code: Optional[str] = None,
        effective_date: Optional[datetime] = None
    ) -> List[PolicyDocument]:
        """Find applicable policy documents for a case."""
        try:
            if effective_date is None:
                effective_date = datetime.utcnow()
            
            query = self.session.query(PolicyDocumentModel).filter(
                and_(
                    PolicyDocumentModel.insurer_id == insurer_id,
                    PolicyDocumentModel.status == PolicyStatus.ACTIVE.value,
                    PolicyDocumentModel.effective_date <= effective_date,
                    or_(
                        PolicyDocumentModel.expiration_date.is_(None),
                        PolicyDocumentModel.expiration_date > effective_date
                    )
                )
            )
            
            # Filter by plan_id (stored as JSON array)
            query = query.filter(
                func.json_contains(PolicyDocumentModel.plan_ids, f'"{plan_id}"')
            )
            
            # Filter by service_code if provided
            if service_code:
                query = query.filter(
                    func.json_contains(PolicyDocumentModel.service_codes, f'"{service_code}"')
                )
            
            # Order by priority (higher priority first) and effective date (newer first)
            query = query.order_by(
                desc(PolicyDocumentModel.priority),
                desc(PolicyDocumentModel.effective_date)
            )
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find applicable policies: {e}")


class ExceptionRuleRepository(BaseRepository):
    """Repository for ExceptionRule entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, ExceptionRuleModel, ExceptionRule)
    
    def get_by_rule_id(self, rule_id: str) -> Optional[ExceptionRule]:
        """Get exception rule by rule ID."""
        try:
            model = self.session.query(ExceptionRuleModel).filter(
                ExceptionRuleModel.rule_id == rule_id
            ).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get exception rule: {e}")
    
    def list_active_exceptions(self, insurer_id: Optional[str] = None) -> List[ExceptionRule]:
        """List active exception rules."""
        try:
            now = datetime.utcnow()
            
            query = self.session.query(ExceptionRuleModel).filter(
                and_(
                    ExceptionRuleModel.status == ExceptionStatus.APPROVED.value,
                    ExceptionRuleModel.effective_date <= now,
                    or_(
                        ExceptionRuleModel.expiration_date.is_(None),
                        ExceptionRuleModel.expiration_date > now
                    )
                )
            )
            
            if insurer_id:
                query = query.filter(ExceptionRuleModel.insurer_id == insurer_id)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list active exceptions: {e}")
    
    def find_applicable_exceptions(
        self,
        insurer_id: str,
        customer_id: Optional[str] = None,
        contract_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        service_code: Optional[str] = None,
    ) -> List[ExceptionRule]:
        """Find applicable exception rules for a case."""
        try:
            now = datetime.utcnow()
            
            # Base query for active exceptions
            query = self.session.query(ExceptionRuleModel).filter(
                and_(
                    ExceptionRuleModel.insurer_id == insurer_id,
                    ExceptionRuleModel.status == ExceptionStatus.APPROVED.value,
                    ExceptionRuleModel.effective_date <= now,
                    or_(
                        ExceptionRuleModel.expiration_date.is_(None),
                        ExceptionRuleModel.expiration_date > now
                    )
                )
            )
            
            # Apply scope filters
            scope_conditions = []
            
            # Customer-specific exceptions
            if customer_id:
                scope_conditions.append(
                    ExceptionRuleModel.customer_id == customer_id
                )
            
            # Contract-specific exceptions
            if contract_id:
                scope_conditions.append(
                    ExceptionRuleModel.contract_id == contract_id
                )
            
            # Plan-specific exceptions
            if plan_id:
                scope_conditions.append(
                    ExceptionRuleModel.plan_id == plan_id
                )
            
            # Service-specific exceptions
            if service_code:
                scope_conditions.append(
                    func.json_contains(ExceptionRuleModel.service_codes, f'"{service_code}"')
                )
            
            # General exceptions (no specific scope)
            scope_conditions.append(
                and_(
                    ExceptionRuleModel.customer_id.is_(None),
                    ExceptionRuleModel.contract_id.is_(None),
                    ExceptionRuleModel.plan_id.is_(None),
                    func.json_length(ExceptionRuleModel.service_codes) == 0
                )
            )
            
            if scope_conditions:
                query = query.filter(or_(*scope_conditions))
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find applicable exceptions: {e}")
    
    def increment_usage(self, rule_id: str) -> bool:
        """Increment usage count for an exception rule."""
        try:
            model = self.session.query(ExceptionRuleModel).filter(
                ExceptionRuleModel.rule_id == rule_id
            ).first()
            
            if model is None:
                return False
            
            model.usage_count += 1
            model.last_used_at = datetime.utcnow()
            self.session.flush()
            
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to increment exception usage: {e}")


class DecisionRecordRepository(BaseRepository):
    """Repository for DecisionRecord entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, DecisionRecordModel, DecisionRecord)
    
    def get_by_case_id(self, case_id: str) -> Optional[DecisionRecord]:
        """Get decision record by case ID."""
        try:
            model = self.session.query(DecisionRecordModel).filter(
                DecisionRecordModel.case_id == case_id
            ).order_by(desc(DecisionRecordModel.created_at)).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get decision record: {e}")
    
    def list_by_status(self, status: DecisionStatus, limit: Optional[int] = None) -> List[DecisionRecord]:
        """List decision records by status."""
        try:
            query = self.session.query(DecisionRecordModel).filter(
                DecisionRecordModel.status == status.value
            ).order_by(desc(DecisionRecordModel.created_at))
            
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list decisions by status: {e}")
    
    def list_requiring_hitl(self, limit: Optional[int] = None) -> List[DecisionRecord]:
        """List decisions requiring HITL review."""
        try:
            query = self.session.query(DecisionRecordModel).filter(
                DecisionRecordModel.requires_hitl == True
            ).order_by(desc(DecisionRecordModel.created_at))
            
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list HITL decisions: {e}")


class AuditTrailRepository(BaseRepository):
    """Repository for AuditTrail entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, AuditTrailModel, AuditTrail)
    
    def list_by_case_id(self, case_id: str, limit: Optional[int] = None) -> List[AuditTrail]:
        """List audit trails by case ID."""
        try:
            query = self.session.query(AuditTrailModel).filter(
                AuditTrailModel.case_id == case_id
            ).order_by(AuditTrailModel.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list audit trails: {e}")
    
    def list_by_correlation_id(self, correlation_id: str) -> List[AuditTrail]:
        """List audit trails by correlation ID."""
        try:
            models = self.session.query(AuditTrailModel).filter(
                AuditTrailModel.correlation_id == correlation_id
            ).order_by(AuditTrailModel.timestamp).all()
            
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list audit trails by correlation: {e}")
    
    def search_audit_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[AuditTrail]:
        """Search audit events with filters."""
        try:
            query = self.session.query(AuditTrailModel)
            
            if event_type:
                query = query.filter(AuditTrailModel.event_type == event_type)
            
            if user_id:
                query = query.filter(AuditTrailModel.user_id == user_id)
            
            if start_date:
                query = query.filter(AuditTrailModel.timestamp >= start_date)
            
            if end_date:
                query = query.filter(AuditTrailModel.timestamp <= end_date)
            
            query = query.order_by(desc(AuditTrailModel.timestamp))
            
            if limit:
                query = query.limit(limit)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to search audit events: {e}")


class MLScoreRecordRepository(BaseRepository):
    """Repository for MLScoreRecord entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, MLScoreRecordModel, MLScoreRecord)
    
    def list_by_case_id(self, case_id: str) -> List[MLScoreRecord]:
        """List ML score records by case ID."""
        try:
            models = self.session.query(MLScoreRecordModel).filter(
                MLScoreRecordModel.case_id == case_id
            ).order_by(desc(MLScoreRecordModel.inference_timestamp)).all()
            
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list ML scores: {e}")
    
    def get_latest_by_model_type(self, case_id: str, model_type: str) -> Optional[MLScoreRecord]:
        """Get latest ML score record by model type."""
        try:
            model = self.session.query(MLScoreRecordModel).filter(
                and_(
                    MLScoreRecordModel.case_id == case_id,
                    MLScoreRecordModel.model_type == model_type
                )
            ).order_by(desc(MLScoreRecordModel.inference_timestamp)).first()
            
            if model is None:
                return None
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get latest ML score: {e}")


class HITLRequestRepository(BaseRepository):
    """Repository for HITLRequest entities."""
    
    def __init__(self, session: Session):
        super().__init__(session, HITLRequestModel, HITLRequest)
    
    def list_pending_requests(self, assigned_to_role: Optional[str] = None) -> List[HITLRequest]:
        """List pending HITL requests."""
        try:
            query = self.session.query(HITLRequestModel).filter(
                HITLRequestModel.responded_at.is_(None)
            )
            
            if assigned_to_role:
                query = query.filter(HITLRequestModel.assigned_to_role == assigned_to_role)
            
            query = query.order_by(HITLRequestModel.requested_at)
            
            models = query.all()
            return [self._model_to_entity(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list pending HITL requests: {e}")
    
    def assign_to_user(self, request_id: UUID, user_id: str) -> Optional[HITLRequest]:
        """Assign HITL request to a specific user."""
        try:
            model = self.session.query(HITLRequestModel).filter(
                HITLRequestModel.id == request_id
            ).first()
            
            if model is None:
                return None
            
            model.assigned_to_user = user_id
            model.assigned_at = datetime.utcnow()
            self.session.flush()
            
            return self._model_to_entity(model)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to assign HITL request: {e}")


class SystemConfigRepository(BaseRepository):
    """Repository for system configuration."""
    
    def __init__(self, session: Session):
        super().__init__(session, SystemConfigModel, dict)  # Using dict as entity type
    
    def get_config(self, key: str) -> Optional[Any]:
        """Get configuration value by key."""
        try:
            model = self.session.query(SystemConfigModel).filter(
                SystemConfigModel.key == key
            ).first()
            
            if model is None:
                return None
            
            return model.value
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get config: {e}")
    
    def set_config(self, key: str, value: Any, description: Optional[str] = None) -> bool:
        """Set configuration value."""
        try:
            model = self.session.query(SystemConfigModel).filter(
                SystemConfigModel.key == key
            ).first()
            
            if model is None:
                model = SystemConfigModel(
                    key=key,
                    value=value,
                    description=description
                )
                self.session.add(model)
            else:
                model.value = value
                if description:
                    model.description = description
                model.updated_at = datetime.utcnow()
            
            self.session.flush()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to set config: {e}")
    
    def list_configs(self, config_type: Optional[str] = None) -> Dict[str, Any]:
        """List all configuration values."""
        try:
            query = self.session.query(SystemConfigModel)
            
            if config_type:
                query = query.filter(SystemConfigModel.config_type == config_type)
            
            models = query.all()
            return {model.key: model.value for model in models}
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to list configs: {e}")


class RepositoryManager:
    """Manager class for all repositories."""
    
    def __init__(self, session: Session):
        self.session = session
        
        # Initialize repositories
        self.cases = CaseRepository(session)
        self.policies = PolicyDocumentRepository(session)
        self.exceptions = ExceptionRuleRepository(session)
        self.decisions = DecisionRecordRepository(session)
        self.audit_trails = AuditTrailRepository(session)
        self.ml_scores = MLScoreRecordRepository(session)
        self.hitl_requests = HITLRequestRepository(session)
        self.system_config = SystemConfigRepository(session)
    
    def commit(self):
        """Commit the current transaction."""
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to commit transaction: {e}")
    
    def rollback(self):
        """Rollback the current transaction."""
        self.session.rollback()
    
    def close(self):
        """Close the session."""
        self.session.close()


# Utility functions

def create_repository_manager(session: Session) -> RepositoryManager:
    """Create a repository manager with the given session."""
    return RepositoryManager(session)


def with_transaction(session_factory: sessionmaker):
    """Decorator for repository operations that need transaction management."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            session = session_factory()
            try:
                repo_manager = create_repository_manager(session)
                result = func(repo_manager, *args, **kwargs)
                repo_manager.commit()
                return result
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
        return wrapper
    return decorator


# Example usage patterns

class CaseService:
    """Example service using repositories."""
    
    def __init__(self, repo_manager: RepositoryManager):
        self.repo_manager = repo_manager
    
    def create_case_with_audit(self, case: Case, created_by: str) -> Case:
        """Create a case and log audit event."""
        try:
            # Create the case
            created_case = self.repo_manager.cases.create(case)
            
            # Create audit trail
            audit_trail = AuditTrail(
                case_id=created_case.case_id,
                event_type="CASE_CREATED",
                event_data={"case_id": created_case.case_id},
                user_id=created_by,
                timestamp=datetime.utcnow(),
            )
            self.repo_manager.audit_trails.create(audit_trail)
            
            return created_case
        except Exception as e:
            self.repo_manager.rollback()
            raise e
    
    def get_case_with_history(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case with its complete audit history."""
        case = self.repo_manager.cases.get_by_case_id(case_id)
        if case is None:
            return None
        
        audit_history = self.repo_manager.audit_trails.list_by_case_id(case_id)
        
        return {
            "case": case,
            "audit_history": audit_history,
        }
