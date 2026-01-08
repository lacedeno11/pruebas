"""
Policy Copilot Database Package

This package contains data persistence layer components:
- SQLAlchemy models for all entities (cases, policies, exceptions, audit trails)
- Repository pattern implementations for data access
- Database migration scripts and schema management
- Connection management and configuration
- Audit trail persistence and querying
"""

from .base import (
    Base,
    DatabaseConfig,
    DatabaseManager,
    TimestampMixin,
    UUIDMixin,
    AuditMixin,
    db_manager,
    get_db_session,
    get_database_session,
    init_database,
    generate_uuid,
    get_current_timestamp
)

from .models import (
    Case,
    CaseAttachment,
    Policy,
    PolicyException,
    EvidencePack,
    EvidenceItem,
    Decision,
    AuditLog,
    MLPrediction,
    GuardrailEvent,
    SystemConfiguration
)

from .repositories import (
    BaseRepository,
    CaseRepository,
    PolicyRepository,
    PolicyExceptionRepository,
    EvidencePackRepository,
    DecisionRepository,
    AuditLogRepository,
    MLPredictionRepository,
    GuardrailEventRepository,
    SystemConfigurationRepository,
    RepositoryFactory,
    repository_factory
)

from .migrations import (
    Migration,
    MigrationManager,
    MigrationError,
    InitialSchemaMigration,
    AddIndexesMigration,
    SeedDataMigration,
    create_migration_manager,
    init_database as migrate_database,
    reset_database,
    get_migration_status,
    migration_manager
)

__all__ = [
    # Base components
    "Base",
    "DatabaseConfig",
    "DatabaseManager",
    "TimestampMixin",
    "UUIDMixin",
    "AuditMixin",
    "db_manager",
    "get_db_session",
    "get_database_session",
    "init_database",
    "generate_uuid",
    "get_current_timestamp",
    
    # Models
    "Case",
    "CaseAttachment",
    "Policy",
    "PolicyException",
    "EvidencePack",
    "EvidenceItem",
    "Decision",
    "AuditLog",
    "MLPrediction",
    "GuardrailEvent",
    "SystemConfiguration",
    
    # Repositories
    "BaseRepository",
    "CaseRepository",
    "PolicyRepository",
    "PolicyExceptionRepository",
    "EvidencePackRepository",
    "DecisionRepository",
    "AuditLogRepository",
    "MLPredictionRepository",
    "GuardrailEventRepository",
    "SystemConfigurationRepository",
    "RepositoryFactory",
    "repository_factory",
    
    # Migrations
    "Migration",
    "MigrationManager",
    "MigrationError",
    "InitialSchemaMigration",
    "AddIndexesMigration",
    "SeedDataMigration",
    "create_migration_manager",
    "migrate_database",
    "reset_database",
    "get_migration_status",
    "migration_manager"
]


def setup_database(database_url: str = None, echo: bool = False) -> DatabaseManager:
    """
    Setup database with custom configuration.
    
    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements
        
    Returns:
        Configured database manager
    """
    config = DatabaseConfig()
    if database_url:
        config.database_url = database_url
    if echo is not None:
        config.echo = echo
    
    return init_database(config)


def create_all_tables(db_manager: DatabaseManager = None) -> None:
    """
    Create all database tables.
    
    Args:
        db_manager: Database manager instance
    """
    if not db_manager:
        db_manager = db_manager
    
    db_manager.create_all_tables()


def get_repository_factory(session=None) -> RepositoryFactory:
    """
    Get repository factory instance.
    
    Args:
        session: Database session (optional)
        
    Returns:
        Repository factory instance
    """
    return RepositoryFactory(session)


def health_check() -> dict:
    """
    Perform database health check.
    
    Returns:
        Health check results
    """
    return db_manager.health_check()


# Convenience functions for common operations
def get_case_repository(session=None) -> CaseRepository:
    """Get case repository instance"""
    return CaseRepository(session)


def get_policy_repository(session=None) -> PolicyRepository:
    """Get policy repository instance"""
    return PolicyRepository(session)


def get_decision_repository(session=None) -> DecisionRepository:
    """Get decision repository instance"""
    return DecisionRepository(session)


def get_audit_log_repository(session=None) -> AuditLogRepository:
    """Get audit log repository instance"""
    return AuditLogRepository(session)

