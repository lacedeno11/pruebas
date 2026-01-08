"""
Database Migration Management

This module provides database migration functionality for the Policy Validation
Copilot system, including schema creation, updates, and data migrations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect, MetaData, Table, Column
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
import json
import os

from .base import DatabaseManager, Base
from .models import (
    Case, CaseAttachment, Policy, PolicyException, EvidencePack, EvidenceItem,
    Decision, AuditLog, MLPrediction, GuardrailEvent, SystemConfiguration
)

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors"""
    pass


class Migration:
    """Base migration class"""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.timestamp = datetime.utcnow()
    
    def up(self, engine: Engine) -> None:
        """Apply migration"""
        raise NotImplementedError("Subclasses must implement up() method")
    
    def down(self, engine: Engine) -> None:
        """Rollback migration"""
        raise NotImplementedError("Subclasses must implement down() method")
    
    def __repr__(self):
        return f"<Migration(version={self.version}, description={self.description})>"


class InitialSchemaMigration(Migration):
    """Initial schema creation migration"""
    
    def __init__(self):
        super().__init__("001", "Create initial schema")
    
    def up(self, engine: Engine) -> None:
        """Create all tables"""
        logger.info("Creating initial database schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("Initial schema created successfully")
    
    def down(self, engine: Engine) -> None:
        """Drop all tables"""
        logger.info("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")


class AddIndexesMigration(Migration):
    """Add performance indexes migration"""
    
    def __init__(self):
        super().__init__("002", "Add performance indexes")
    
    def up(self, engine: Engine) -> None:
        """Add additional indexes for performance"""
        logger.info("Adding performance indexes...")
        
        with engine.connect() as conn:
            # Additional indexes for better query performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS ix_cases_service_date ON cases(service_date)",
                "CREATE INDEX IF NOT EXISTS ix_cases_amount ON cases(service_amount)",
                "CREATE INDEX IF NOT EXISTS ix_evidence_items_scores ON evidence_items(relevance_score, confidence_score)",
                "CREATE INDEX IF NOT EXISTS ix_decisions_confidence ON decisions(confidence_score)",
                "CREATE INDEX IF NOT EXISTS ix_decisions_risk ON decisions(risk_score)",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_ml_predictions_timestamp ON ml_predictions(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_guardrail_events_timestamp ON guardrail_events(created_at)",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    logger.info(f"Created index: {index_sql}")
                except SQLAlchemyError as e:
                    logger.warning(f"Failed to create index: {index_sql}, error: {e}")
            
            conn.commit()
        
        logger.info("Performance indexes added successfully")
    
    def down(self, engine: Engine) -> None:
        """Remove additional indexes"""
        logger.info("Removing performance indexes...")
        
        with engine.connect() as conn:
            indexes_to_drop = [
                "DROP INDEX IF EXISTS ix_cases_service_date",
                "DROP INDEX IF EXISTS ix_cases_amount",
                "DROP INDEX IF EXISTS ix_evidence_items_scores",
                "DROP INDEX IF EXISTS ix_decisions_confidence",
                "DROP INDEX IF EXISTS ix_decisions_risk",
                "DROP INDEX IF EXISTS ix_audit_logs_timestamp",
                "DROP INDEX IF EXISTS ix_ml_predictions_timestamp",
                "DROP INDEX IF EXISTS ix_guardrail_events_timestamp",
            ]
            
            for drop_sql in indexes_to_drop:
                try:
                    conn.execute(text(drop_sql))
                    logger.info(f"Dropped index: {drop_sql}")
                except SQLAlchemyError as e:
                    logger.warning(f"Failed to drop index: {drop_sql}, error: {e}")
            
            conn.commit()
        
        logger.info("Performance indexes removed successfully")


class SeedDataMigration(Migration):
    """Seed initial data migration"""
    
    def __init__(self):
        super().__init__("003", "Seed initial data")
    
    def up(self, engine: Engine) -> None:
        """Insert initial seed data"""
        logger.info("Seeding initial data...")
        
        from .repositories import SystemConfigurationRepository
        from .base import get_db_session
        
        # Seed system configurations
        with next(get_db_session()) as session:
            config_repo = SystemConfigurationRepository(session)
            
            # Default configurations
            default_configs = [
                {
                    "config_key": "sla.default_hours",
                    "config_category": "SLA",
                    "config_value": 24,
                    "config_type": "INTEGER",
                    "description": "Default SLA hours for cases"
                },
                {
                    "config_key": "sla.priority_multipliers",
                    "config_category": "SLA",
                    "config_value": {
                        "LOW": 2.0,
                        "MEDIUM": 1.0,
                        "HIGH": 0.5,
                        "CRITICAL": 0.25
                    },
                    "config_type": "JSON",
                    "description": "SLA multipliers by priority"
                },
                {
                    "config_key": "decision.confidence_threshold",
                    "config_category": "DECISION",
                    "config_value": 0.8,
                    "config_type": "FLOAT",
                    "description": "Minimum confidence threshold for auto-approval"
                },
                {
                    "config_key": "decision.risk_threshold",
                    "config_category": "DECISION",
                    "config_value": 0.3,
                    "config_type": "FLOAT",
                    "description": "Maximum risk threshold for auto-approval"
                },
                {
                    "config_key": "ml.classification_model_version",
                    "config_category": "ML",
                    "config_value": "classification-v2.1.0",
                    "config_type": "STRING",
                    "description": "Current classification model version"
                },
                {
                    "config_key": "ml.anomaly_model_version",
                    "config_category": "ML",
                    "config_value": "anomaly-v1.5.0",
                    "config_type": "STRING",
                    "description": "Current anomaly detection model version"
                },
                {
                    "config_key": "ml.eta_model_version",
                    "config_category": "ML",
                    "config_value": "eta-v1.2.0",
                    "config_type": "STRING",
                    "description": "Current ETA prediction model version"
                },
                {
                    "config_key": "guardrails.pii_confidence_threshold",
                    "config_category": "GUARDRAILS",
                    "config_value": 0.6,
                    "config_type": "FLOAT",
                    "description": "PII detection confidence threshold"
                },
                {
                    "config_key": "guardrails.injection_risk_threshold",
                    "config_category": "GUARDRAILS",
                    "config_value": 0.7,
                    "config_type": "FLOAT",
                    "description": "Injection detection risk threshold"
                },
                {
                    "config_key": "evidence.minimum_coverage_score",
                    "config_category": "EVIDENCE",
                    "config_value": 0.8,
                    "config_type": "FLOAT",
                    "description": "Minimum evidence coverage score"
                }
            ]
            
            for config_data in default_configs:
                existing = config_repo.get_by_key(config_data["config_key"])
                if not existing:
                    config_repo.create(**config_data)
                    logger.info(f"Created configuration: {config_data['config_key']}")
        
        logger.info("Initial data seeded successfully")
    
    def down(self, engine: Engine) -> None:
        """Remove seed data"""
        logger.info("Removing seed data...")
        
        from .repositories import SystemConfigurationRepository
        from .base import get_db_session
        
        with next(get_db_session()) as session:
            config_repo = SystemConfigurationRepository(session)
            
            # Remove default configurations
            default_keys = [
                "sla.default_hours",
                "sla.priority_multipliers",
                "decision.confidence_threshold",
                "decision.risk_threshold",
                "ml.classification_model_version",
                "ml.anomaly_model_version",
                "ml.eta_model_version",
                "guardrails.pii_confidence_threshold",
                "guardrails.injection_risk_threshold",
                "evidence.minimum_coverage_score"
            ]
            
            for key in default_keys:
                config = config_repo.get_by_key(key)
                if config:
                    config_repo.delete(config.id)
                    logger.info(f"Removed configuration: {key}")
        
        logger.info("Seed data removed successfully")


class MigrationManager:
    """Database migration manager"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager
        self.migrations: List[Migration] = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations"""
        self.migrations = [
            InitialSchemaMigration(),
            AddIndexesMigration(),
            SeedDataMigration(),
        ]
        
        # Sort by version
        self.migrations.sort(key=lambda m: m.version)
    
    def _ensure_migration_table(self, engine: Engine) -> None:
        """Ensure migration tracking table exists"""
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def _get_applied_migrations(self, engine: Engine) -> List[str]:
        """Get list of applied migration versions"""
        self._ensure_migration_table(engine)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
            return [row[0] for row in result]
    
    def _mark_migration_applied(self, engine: Engine, migration: Migration) -> None:
        """Mark migration as applied"""
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO schema_migrations (version, description, applied_at)
                VALUES (:version, :description, :applied_at)
            """), {
                "version": migration.version,
                "description": migration.description,
                "applied_at": migration.timestamp
            })
            conn.commit()
    
    def _mark_migration_reverted(self, engine: Engine, version: str) -> None:
        """Mark migration as reverted"""
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM schema_migrations WHERE version = :version"), {
                "version": version
            })
            conn.commit()
    
    def get_pending_migrations(self, engine: Engine = None) -> List[Migration]:
        """Get list of pending migrations"""
        if not engine:
            engine = self.db_manager.get_engine()
        
        applied_versions = set(self._get_applied_migrations(engine))
        return [m for m in self.migrations if m.version not in applied_versions]
    
    def get_applied_migrations_info(self, engine: Engine = None) -> List[Dict[str, Any]]:
        """Get information about applied migrations"""
        if not engine:
            engine = self.db_manager.get_engine()
        
        self._ensure_migration_table(engine)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT version, description, applied_at
                FROM schema_migrations
                ORDER BY version
            """))
            
            return [
                {
                    "version": row[0],
                    "description": row[1],
                    "applied_at": row[2]
                }
                for row in result
            ]
    
    def migrate(self, target_version: str = None, engine: Engine = None) -> None:
        """Run migrations up to target version"""
        if not engine:
            engine = self.db_manager.get_engine()
        
        pending_migrations = self.get_pending_migrations(engine)
        
        if target_version:
            # Filter to only migrations up to target version
            pending_migrations = [
                m for m in pending_migrations 
                if m.version <= target_version
            ]
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return
        
        logger.info(f"Applying {len(pending_migrations)} migrations...")
        
        for migration in pending_migrations:
            try:
                logger.info(f"Applying migration {migration.version}: {migration.description}")
                migration.up(engine)
                self._mark_migration_applied(engine, migration)
                logger.info(f"Migration {migration.version} applied successfully")
            except Exception as e:
                logger.error(f"Failed to apply migration {migration.version}: {e}")
                raise MigrationError(f"Migration {migration.version} failed: {e}")
        
        logger.info("All migrations applied successfully")
    
    def rollback(self, target_version: str = None, engine: Engine = None) -> None:
        """Rollback migrations to target version"""
        if not engine:
            engine = self.db_manager.get_engine()
        
        applied_versions = self._get_applied_migrations(engine)
        
        if target_version:
            # Find migrations to rollback
            migrations_to_rollback = [
                v for v in applied_versions 
                if v > target_version
            ]
        else:
            # Rollback all migrations
            migrations_to_rollback = applied_versions
        
        if not migrations_to_rollback:
            logger.info("No migrations to rollback")
            return
        
        # Sort in reverse order for rollback
        migrations_to_rollback.sort(reverse=True)
        
        logger.info(f"Rolling back {len(migrations_to_rollback)} migrations...")
        
        for version in migrations_to_rollback:
            # Find migration object
            migration = next((m for m in self.migrations if m.version == version), None)
            if not migration:
                logger.warning(f"Migration {version} not found, skipping rollback")
                continue
            
            try:
                logger.info(f"Rolling back migration {version}: {migration.description}")
                migration.down(engine)
                self._mark_migration_reverted(engine, version)
                logger.info(f"Migration {version} rolled back successfully")
            except Exception as e:
                logger.error(f"Failed to rollback migration {version}: {e}")
                raise MigrationError(f"Rollback of migration {version} failed: {e}")
        
        logger.info("Rollback completed successfully")
    
    def reset_database(self, engine: Engine = None) -> None:
        """Reset database by rolling back all migrations and reapplying them"""
        if not engine:
            engine = self.db_manager.get_engine()
        
        logger.info("Resetting database...")
        
        # Rollback all migrations
        self.rollback(engine=engine)
        
        # Apply all migrations
        self.migrate(engine=engine)
        
        logger.info("Database reset completed")
    
    def get_migration_status(self, engine: Engine = None) -> Dict[str, Any]:
        """Get current migration status"""
        if not engine:
            engine = self.db_manager.get_engine()
        
        applied_migrations = self.get_applied_migrations_info(engine)
        pending_migrations = self.get_pending_migrations(engine)
        
        return {
            "total_migrations": len(self.migrations),
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "applied_migrations": applied_migrations,
            "pending_migrations": [
                {
                    "version": m.version,
                    "description": m.description
                }
                for m in pending_migrations
            ],
            "database_up_to_date": len(pending_migrations) == 0
        }


def create_migration_manager(db_manager: DatabaseManager = None) -> MigrationManager:
    """Factory function to create migration manager"""
    return MigrationManager(db_manager)


# CLI functions for migration management
def init_database(db_manager: DatabaseManager = None) -> None:
    """Initialize database with all migrations"""
    migration_manager = create_migration_manager(db_manager)
    migration_manager.migrate()


def reset_database(db_manager: DatabaseManager = None) -> None:
    """Reset database completely"""
    migration_manager = create_migration_manager(db_manager)
    migration_manager.reset_database()


def get_migration_status(db_manager: DatabaseManager = None) -> Dict[str, Any]:
    """Get migration status"""
    migration_manager = create_migration_manager(db_manager)
    return migration_manager.get_migration_status()


# Global migration manager instance
migration_manager = create_migration_manager()
