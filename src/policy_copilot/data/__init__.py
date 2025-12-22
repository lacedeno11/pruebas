"""
Data Layer for Policy Validation Copilot

This module provides data access layer components including database connection management,
ORM models, repository pattern implementation, and migration management.
"""

# Database connection management
from .database import (
    DatabaseConfig,
    DatabaseManager,
    initialize_database,
    get_database_manager,
    get_session,
    get_transaction,
    DatabaseError,
    ConnectionError,
    TransactionError,
    Base,
    handle_database_error,
    execute_in_transaction,
    execute_with_session,
    MigrationManager as DBMigrationManager,
    get_migration_manager
)

# ORM Models
from .models import (
    CaseORM,
    EvidencePackORM,
    EvidenceItemORM,
    ChecklistORM,
    ChecklistItemORM,
    MLOutputsORM,
    DecisionORM,
    GuardrailsResultORM,
    HITLStateORM,
    HITLQuestionORM,
    HITLApprovalORM,
    AuditTrailORM,
    NodeExecutionORM
)

# Repository classes
from .repositories import (
    BaseRepository,
    CaseRepository,
    EvidencePackRepository,
    EvidenceItemRepository,
    ChecklistRepository,
    ChecklistItemRepository,
    MLOutputsRepository,
    DecisionRepository,
    GuardrailsResultRepository,
    HITLStateRepository,
    HITLQuestionRepository,
    HITLApprovalRepository,
    AuditTrailRepository,
    NodeExecutionRepository,
    RepositoryError,
    EntityNotFoundError,
    DuplicateEntityError
)

# Migration management
from .migrations import MigrationManager, get_migration_versions, get_latest_version, get_migration_history

# Repository factory for easy instantiation
class RepositoryFactory:
    """Factory class for creating repository instances."""
    
    @staticmethod
    def create_case_repository() -> CaseRepository:
        """Create a case repository instance."""
        return CaseRepository()
    
    @staticmethod
    def create_evidence_pack_repository() -> EvidencePackRepository:
        """Create an evidence pack repository instance."""
        return EvidencePackRepository()
    
    @staticmethod
    def create_evidence_item_repository() -> EvidenceItemRepository:
        """Create an evidence item repository instance."""
        return EvidenceItemRepository()
    
    @staticmethod
    def create_checklist_repository() -> ChecklistRepository:
        """Create a checklist repository instance."""
        return ChecklistRepository()
    
    @staticmethod
    def create_checklist_item_repository() -> ChecklistItemRepository:
        """Create a checklist item repository instance."""
        return ChecklistItemRepository()
    
    @staticmethod
    def create_ml_outputs_repository() -> MLOutputsRepository:
        """Create an ML outputs repository instance."""
        return MLOutputsRepository()
    
    @staticmethod
    def create_decision_repository() -> DecisionRepository:
        """Create a decision repository instance."""
        return DecisionRepository()
    
    @staticmethod
    def create_guardrails_result_repository() -> GuardrailsResultRepository:
        """Create a guardrails result repository instance."""
        return GuardrailsResultRepository()
    
    @staticmethod
    def create_hitl_state_repository() -> HITLStateRepository:
        """Create a HITL state repository instance."""
        return HITLStateRepository()
    
    @staticmethod
    def create_hitl_question_repository() -> HITLQuestionRepository:
        """Create a HITL question repository instance."""
        return HITLQuestionRepository()
    
    @staticmethod
    def create_hitl_approval_repository() -> HITLApprovalRepository:
        """Create a HITL approval repository instance."""
        return HITLApprovalRepository()
    
    @staticmethod
    def create_audit_trail_repository() -> AuditTrailRepository:
        """Create an audit trail repository instance."""
        return AuditTrailRepository()
    
    @staticmethod
    def create_node_execution_repository() -> NodeExecutionRepository:
        """Create a node execution repository instance."""
        return NodeExecutionRepository()


# Convenience functions for common database operations
def setup_database(database_url: str, **kwargs) -> DatabaseManager:
    """Setup and initialize the database with default configuration."""
    config = DatabaseConfig(database_url, **kwargs)
    initialize_database(config)
    return get_database_manager()


def create_all_tables() -> None:
    """Create all database tables."""
    db_manager = get_database_manager()
    db_manager.create_all_tables()


def run_migrations(target_version: str = None) -> None:
    """Run database migrations up to target version."""
    migration_manager = MigrationManager()
    migration_manager.migrate_up(target_version)


def get_database_status() -> dict:
    """Get database connection and migration status."""
    try:
        db_manager = get_database_manager()
        migration_manager = MigrationManager()
        
        return {
            'database_initialized': True,
            'pool_status': db_manager.get_pool_status(),
            'health_check': db_manager.health_check(),
            'migration_status': migration_manager.get_migration_status()
        }
    except Exception as e:
        return {
            'database_initialized': False,
            'error': str(e)
        }


__all__ = [
    # Database management
    'DatabaseConfig',
    'DatabaseManager',
    'initialize_database',
    'get_database_manager',
    'get_session',
    'get_transaction',
    'DatabaseError',
    'ConnectionError',
    'TransactionError',
    'Base',
    'handle_database_error',
    'execute_in_transaction',
    'execute_with_session',
    'DBMigrationManager',
    'get_migration_manager',
    
    # ORM Models
    'CaseORM',
    'EvidencePackORM',
    'EvidenceItemORM',
    'ChecklistORM',
    'ChecklistItemORM',
    'MLOutputsORM',
    'DecisionORM',
    'GuardrailsResultORM',
    'HITLStateORM',
    'HITLQuestionORM',
    'HITLApprovalORM',
    'AuditTrailORM',
    'NodeExecutionORM',
    
    # Repository classes
    'BaseRepository',
    'CaseRepository',
    'EvidencePackRepository',
    'EvidenceItemRepository',
    'ChecklistRepository',
    'ChecklistItemRepository',
    'MLOutputsRepository',
    'DecisionRepository',
    'GuardrailsResultRepository',
    'HITLStateRepository',
    'HITLQuestionRepository',
    'HITLApprovalRepository',
    'AuditTrailRepository',
    'NodeExecutionRepository',
    'RepositoryError',
    'EntityNotFoundError',
    'DuplicateEntityError',
    
    # Migration management
    'MigrationManager',
    'get_migration_versions',
    'get_latest_version',
    'get_migration_history',
    
    # Factory and convenience functions
    'RepositoryFactory',
    'setup_database',
    'create_all_tables',
    'run_migrations',
    'get_database_status'
]

