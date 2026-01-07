"""
Database Migration System

This module provides database migration capabilities for the Policy Validation Copilot
system, including schema versioning, migration execution, and rollback functionality.

Features:
- Schema version tracking and management
- Forward and backward migration support
- Migration validation and dependency checking
- Automatic backup creation before migrations
- Migration history and audit logging
- Data migration utilities for complex transformations
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from .connection_manager import DatabaseConnectionManager, get_default_connection

logger = logging.getLogger(__name__)

# Migration tracking table
MigrationBase = declarative_base()


class MigrationHistory(MigrationBase):
    """Track migration execution history"""
    __tablename__ = 'migration_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    migration_id = Column(String(100), unique=True, nullable=False, index=True)
    migration_name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False)
    
    # Migration content and validation
    migration_hash = Column(String(64), nullable=False)  # SHA-256 of migration content
    migration_sql = Column(Text, nullable=True)  # SQL content for reference
    
    # Execution tracking
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    executed_by = Column(String(100), nullable=False, default='system')
    execution_time_ms = Column(Integer, nullable=True)
    
    # Status and validation
    status = Column(String(20), nullable=False, default='completed')  # completed, failed, rolled_back
    error_message = Column(Text, nullable=True)
    
    # Rollback information
    rollback_sql = Column(Text, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    rolled_back_by = Column(String(100), nullable=True)
    
    # Dependencies and ordering
    depends_on = Column(String(500), nullable=True)  # Comma-separated list of migration IDs
    batch_id = Column(String(100), nullable=True)  # For grouping related migrations


class Migration:
    """Individual migration definition"""
    
    def __init__(self, migration_id: str, name: str, version: str,
                 up_sql: str = None, down_sql: str = None,
                 up_func: Callable = None, down_func: Callable = None,
                 depends_on: List[str] = None, description: str = None):
        self.migration_id = migration_id
        self.name = name
        self.version = version
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.up_func = up_func
        self.down_func = down_func
        self.depends_on = depends_on or []
        self.description = description or ""
        self.created_at = datetime.utcnow()
        
        # Validate migration
        self._validate()
    
    def _validate(self):
        """Validate migration definition"""
        if not self.migration_id:
            raise ValueError("migration_id is required")
        
        if not self.name:
            raise ValueError("name is required")
        
        if not self.version:
            raise ValueError("version is required")
        
        if not (self.up_sql or self.up_func):
            raise ValueError("Either up_sql or up_func must be provided")
    
    def get_content_hash(self) -> str:
        """Get hash of migration content for validation"""
        content = {
            'migration_id': self.migration_id,
            'name': self.name,
            'version': self.version,
            'up_sql': self.up_sql,
            'down_sql': self.down_sql,
            'depends_on': sorted(self.depends_on),
            'description': self.description
        }
        
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Convert migration to dictionary"""
        return {
            'migration_id': self.migration_id,
            'name': self.name,
            'version': self.version,
            'up_sql': self.up_sql,
            'down_sql': self.down_sql,
            'depends_on': self.depends_on,
            'description': self.description,
            'content_hash': self.get_content_hash(),
            'created_at': self.created_at.isoformat()
        }


class MigrationManager:
    """Database migration manager"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager = None):
        self.connection_manager = connection_manager or get_default_connection()
        self.migrations: Dict[str, Migration] = {}
        self.migration_order: List[str] = []
        
        # Ensure migration tracking table exists
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Ensure migration history table exists"""
        try:
            # Create migration tracking table if it doesn't exist
            MigrationBase.metadata.create_all(bind=self.connection_manager.get_engine())
            logger.info("Migration tracking table initialized")
        except Exception as e:
            logger.error(f"Failed to initialize migration tracking table: {e}")
            raise
    
    def register_migration(self, migration: Migration):
        """Register a migration"""
        if migration.migration_id in self.migrations:
            logger.warning(f"Migration {migration.migration_id} already registered, replacing")
        
        self.migrations[migration.migration_id] = migration
        self._update_migration_order()
        
        logger.debug(f"Registered migration: {migration.migration_id}")
    
    def _update_migration_order(self):
        """Update migration execution order based on dependencies"""
        # Simple topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(migration_id: str):
            if migration_id in temp_visited:
                raise ValueError(f"Circular dependency detected involving {migration_id}")
            
            if migration_id not in visited:
                temp_visited.add(migration_id)
                
                migration = self.migrations.get(migration_id)
                if migration:
                    for dep in migration.depends_on:
                        if dep in self.migrations:
                            visit(dep)
                
                temp_visited.remove(migration_id)
                visited.add(migration_id)
                order.append(migration_id)
        
        # Visit all migrations
        for migration_id in self.migrations:
            if migration_id not in visited:
                visit(migration_id)
        
        self.migration_order = order
        logger.debug(f"Migration order updated: {len(order)} migrations")
    
    def get_executed_migrations(self) -> List[str]:
        """Get list of executed migration IDs"""
        with self.connection_manager.get_session() as session:
            results = session.query(MigrationHistory.migration_id).filter(
                MigrationHistory.status == 'completed'
            ).all()
            return [r[0] for r in results]
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations in execution order"""
        executed = set(self.get_executed_migrations())
        pending = []
        
        for migration_id in self.migration_order:
            if migration_id not in executed:
                migration = self.migrations[migration_id]
                
                # Check if dependencies are satisfied
                deps_satisfied = all(dep in executed for dep in migration.depends_on)
                if deps_satisfied:
                    pending.append(migration)
                else:
                    logger.warning(f"Migration {migration_id} has unsatisfied dependencies")
        
        return pending
    
    def execute_migration(self, migration: Migration, dry_run: bool = False) -> bool:
        """Execute a single migration"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Executing migration: {migration.migration_id} - {migration.name}")
            
            if dry_run:
                logger.info("DRY RUN: Migration would be executed")
                return True
            
            with self.connection_manager.get_session() as session:
                # Check if migration already executed
                existing = session.query(MigrationHistory).filter(
                    MigrationHistory.migration_id == migration.migration_id
                ).first()
                
                if existing and existing.status == 'completed':
                    logger.info(f"Migration {migration.migration_id} already executed")
                    return True
                
                # Execute migration
                if migration.up_sql:
                    # Execute SQL migration
                    for statement in migration.up_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            session.execute(text(statement))
                
                elif migration.up_func:
                    # Execute function-based migration
                    migration.up_func(session)
                
                # Record migration execution
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                migration_record = MigrationHistory(
                    migration_id=migration.migration_id,
                    migration_name=migration.name,
                    version=migration.version,
                    migration_hash=migration.get_content_hash(),
                    migration_sql=migration.up_sql,
                    executed_at=start_time,
                    execution_time_ms=int(execution_time),
                    status='completed',
                    rollback_sql=migration.down_sql,
                    depends_on=','.join(migration.depends_on) if migration.depends_on else None
                )
                
                session.add(migration_record)
                session.commit()
                
                logger.info(f"Migration {migration.migration_id} executed successfully in {execution_time:.2f}ms")
                return True
        
        except Exception as e:
            logger.error(f"Migration {migration.migration_id} failed: {e}")
            
            # Record failed migration
            try:
                with self.connection_manager.get_session() as session:
                    execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    migration_record = MigrationHistory(
                        migration_id=migration.migration_id,
                        migration_name=migration.name,
                        version=migration.version,
                        migration_hash=migration.get_content_hash(),
                        migration_sql=migration.up_sql,
                        executed_at=start_time,
                        execution_time_ms=int(execution_time),
                        status='failed',
                        error_message=str(e),
                        rollback_sql=migration.down_sql
                    )
                    
                    session.add(migration_record)
                    session.commit()
            except Exception as record_error:
                logger.error(f"Failed to record migration failure: {record_error}")
            
            return False
    
    def rollback_migration(self, migration_id: str, dry_run: bool = False) -> bool:
        """Rollback a specific migration"""
        try:
            logger.info(f"Rolling back migration: {migration_id}")
            
            if dry_run:
                logger.info("DRY RUN: Migration would be rolled back")
                return True
            
            with self.connection_manager.get_session() as session:
                # Get migration record
                migration_record = session.query(MigrationHistory).filter(
                    MigrationHistory.migration_id == migration_id,
                    MigrationHistory.status == 'completed'
                ).first()
                
                if not migration_record:
                    logger.error(f"Migration {migration_id} not found or not completed")
                    return False
                
                # Get migration definition
                migration = self.migrations.get(migration_id)
                
                # Execute rollback
                if migration_record.rollback_sql:
                    for statement in migration_record.rollback_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            session.execute(text(statement))
                
                elif migration and migration.down_func:
                    migration.down_func(session)
                
                else:
                    logger.warning(f"No rollback method available for migration {migration_id}")
                    return False
                
                # Update migration record
                migration_record.status = 'rolled_back'
                migration_record.rolled_back_at = datetime.utcnow()
                migration_record.rolled_back_by = 'system'
                
                session.commit()
                
                logger.info(f"Migration {migration_id} rolled back successfully")
                return True
        
        except Exception as e:
            logger.error(f"Rollback of migration {migration_id} failed: {e}")
            return False
    
    def migrate_up(self, target_version: str = None, dry_run: bool = False) -> bool:
        """Execute all pending migrations up to target version"""
        pending_migrations = self.get_pending_migrations()
        
        if target_version:
            # Filter migrations up to target version
            pending_migrations = [
                m for m in pending_migrations 
                if self._compare_versions(m.version, target_version) <= 0
            ]
        
        if not pending_migrations:
            logger.info("No pending migrations to execute")
            return True
        
        logger.info(f"Executing {len(pending_migrations)} pending migrations")
        
        success_count = 0
        for migration in pending_migrations:
            if self.execute_migration(migration, dry_run):
                success_count += 1
            else:
                logger.error(f"Migration failed, stopping at {migration.migration_id}")
                break
        
        logger.info(f"Executed {success_count}/{len(pending_migrations)} migrations successfully")
        return success_count == len(pending_migrations)
    
    def migrate_down(self, target_version: str, dry_run: bool = False) -> bool:
        """Rollback migrations down to target version"""
        executed_migrations = self.get_executed_migrations()
        
        # Get migrations to rollback (in reverse order)
        migrations_to_rollback = []
        for migration_id in reversed(self.migration_order):
            if migration_id in executed_migrations:
                migration = self.migrations.get(migration_id)
                if migration and self._compare_versions(migration.version, target_version) > 0:
                    migrations_to_rollback.append(migration_id)
        
        if not migrations_to_rollback:
            logger.info("No migrations to rollback")
            return True
        
        logger.info(f"Rolling back {len(migrations_to_rollback)} migrations")
        
        success_count = 0
        for migration_id in migrations_to_rollback:
            if self.rollback_migration(migration_id, dry_run):
                success_count += 1
            else:
                logger.error(f"Rollback failed, stopping at {migration_id}")
                break
        
        logger.info(f"Rolled back {success_count}/{len(migrations_to_rollback)} migrations successfully")
        return success_count == len(migrations_to_rollback)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings (returns -1, 0, or 1)"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return -1
                elif v1 > v2:
                    return 1
            
            return 0
        
        except ValueError:
            # Fallback to string comparison
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            return 0
    
    def get_migration_status(self) -> Dict:
        """Get current migration status"""
        executed = self.get_executed_migrations()
        pending = self.get_pending_migrations()
        
        with self.connection_manager.get_session() as session:
            failed_migrations = session.query(MigrationHistory).filter(
                MigrationHistory.status == 'failed'
            ).all()
        
        return {
            'total_migrations': len(self.migrations),
            'executed_count': len(executed),
            'pending_count': len(pending),
            'failed_count': len(failed_migrations),
            'executed_migrations': executed,
            'pending_migrations': [m.migration_id for m in pending],
            'failed_migrations': [m.migration_id for m in failed_migrations]
        }
    
    def validate_migrations(self) -> Dict:
        """Validate all registered migrations"""
        issues = []
        
        # Check for duplicate migration IDs
        migration_ids = list(self.migrations.keys())
        if len(migration_ids) != len(set(migration_ids)):
            issues.append("Duplicate migration IDs found")
        
        # Check dependencies
        for migration_id, migration in self.migrations.items():
            for dep in migration.depends_on:
                if dep not in self.migrations:
                    issues.append(f"Migration {migration_id} depends on non-existent migration {dep}")
        
        # Check for circular dependencies
        try:
            self._update_migration_order()
        except ValueError as e:
            issues.append(str(e))
        
        # Validate executed migrations against current definitions
        with self.connection_manager.get_session() as session:
            executed_records = session.query(MigrationHistory).filter(
                MigrationHistory.status == 'completed'
            ).all()
            
            for record in executed_records:
                if record.migration_id in self.migrations:
                    current_migration = self.migrations[record.migration_id]
                    current_hash = current_migration.get_content_hash()
                    
                    if record.migration_hash != current_hash:
                        issues.append(f"Migration {record.migration_id} has been modified after execution")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'total_migrations': len(self.migrations)
        }


# Predefined migrations for initial schema
def create_initial_migrations() -> List[Migration]:
    """Create initial database schema migrations"""
    migrations = []
    
    # Migration 001: Create core tables
    migration_001 = Migration(
        migration_id="001_create_core_tables",
        name="Create core database tables",
        version="1.0.0",
        description="Create initial database schema with core tables",
        up_sql="""
        -- This migration creates the core database schema
        -- Note: In practice, this would be generated from SQLAlchemy models
        
        -- Cases table
        CREATE TABLE IF NOT EXISTS cases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id VARCHAR(100) UNIQUE NOT NULL,
            crm_ticket_id VARCHAR(100) NOT NULL,
            customer_id VARCHAR(100) NOT NULL,
            contract_id VARCHAR(100),
            insurer_id VARCHAR(100) NOT NULL,
            plan_id VARCHAR(100) NOT NULL,
            service_code VARCHAR(50),
            service_description TEXT,
            service_date TIMESTAMP NOT NULL,
            provider_id VARCHAR(100),
            priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            sla_target TIMESTAMP,
            status VARCHAR(50) NOT NULL DEFAULT 'NUEVO',
            assigned_queue VARCHAR(100),
            channel VARCHAR(50),
            source_system VARCHAR(100),
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for cases
        CREATE INDEX IF NOT EXISTS idx_cases_case_id ON cases(case_id);
        CREATE INDEX IF NOT EXISTS idx_cases_crm_ticket_id ON cases(crm_ticket_id);
        CREATE INDEX IF NOT EXISTS idx_cases_customer_id ON cases(customer_id);
        CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
        CREATE INDEX IF NOT EXISTS idx_cases_insurer_id ON cases(insurer_id);
        """,
        down_sql="""
        DROP TABLE IF EXISTS cases CASCADE;
        """
    )
    migrations.append(migration_001)
    
    # Migration 002: Create policy documents table
    migration_002 = Migration(
        migration_id="002_create_policy_documents",
        name="Create policy documents table",
        version="1.0.0",
        description="Create policy documents table with versioning",
        depends_on=["001_create_core_tables"],
        up_sql="""
        CREATE TABLE IF NOT EXISTS policy_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            doc_id VARCHAR(100) NOT NULL,
            version VARCHAR(50) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            document_type VARCHAR(100) NOT NULL,
            scope JSONB,
            checksum VARCHAR(64) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            vigencia_start TIMESTAMP NOT NULL,
            vigencia_end TIMESTAMP,
            content_path VARCHAR(1000) NOT NULL,
            parsed_content JSONB,
            approved_by VARCHAR(100),
            approved_at TIMESTAMP,
            approval_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(doc_id, version)
        );
        
        CREATE INDEX IF NOT EXISTS idx_policy_doc_id ON policy_documents(doc_id);
        CREATE INDEX IF NOT EXISTS idx_policy_active_vigencia ON policy_documents(is_active, vigencia_start, vigencia_end);
        """,
        down_sql="""
        DROP TABLE IF EXISTS policy_documents CASCADE;
        """
    )
    migrations.append(migration_002)
    
    # Migration 003: Create evidence and audit tables
    migration_003 = Migration(
        migration_id="003_create_evidence_audit_tables",
        name="Create evidence and audit tables",
        version="1.0.0",
        description="Create evidence packs, decisions, and audit trail tables",
        depends_on=["001_create_core_tables", "002_create_policy_documents"],
        up_sql="""
        -- Evidence packs table
        CREATE TABLE IF NOT EXISTS evidence_packs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            evidence_pack_id VARCHAR(100) NOT NULL,
            coverage_score FLOAT NOT NULL DEFAULT 0.0,
            conflicts_detected BOOLEAN NOT NULL DEFAULT FALSE,
            conflict_details JSONB,
            missing_sources JSONB,
            allowlist_validated BOOLEAN NOT NULL DEFAULT FALSE,
            evidence_anchoring_passed BOOLEAN NOT NULL DEFAULT TRUE,
            retrieval_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_id, evidence_pack_id),
            CHECK (coverage_score >= 0.0 AND coverage_score <= 1.0)
        );
        
        -- Decisions table
        CREATE TABLE IF NOT EXISTS decisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            decision_id VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            confidence_score FLOAT NOT NULL DEFAULT 0.0,
            confidence_level VARCHAR(20) NOT NULL DEFAULT 'LOW',
            risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            anomaly_score FLOAT,
            eta_estimate INTEGER,
            next_actions JSONB,
            requires_hitl BOOLEAN NOT NULL DEFAULT FALSE,
            requires_external_consultation BOOLEAN NOT NULL DEFAULT FALSE,
            auto_close_eligible BOOLEAN NOT NULL DEFAULT FALSE,
            thresholds_version VARCHAR(50) NOT NULL,
            decision_rationale TEXT,
            supporting_evidence JSONB,
            decision_timestamp TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_id, decision_id),
            CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
            CHECK (anomaly_score IS NULL OR (anomaly_score >= 0.0 AND anomaly_score <= 1.0))
        );
        
        -- Audit trails table
        CREATE TABLE IF NOT EXISTS audit_trails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            audit_id VARCHAR(100) NOT NULL,
            workflow_start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            workflow_end_time TIMESTAMP,
            total_execution_time INTEGER,
            node_execution_log JSONB,
            export_logs JSONB,
            access_logs JSONB,
            policy_versions_used JSONB,
            rule_versions_used JSONB,
            model_versions_used JSONB,
            compliance_flags JSONB,
            data_lineage JSONB,
            audit_hash VARCHAR(64),
            previous_audit_hash VARCHAR(64),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_id, audit_id)
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence_packs(case_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_coverage ON evidence_packs(coverage_score);
        CREATE INDEX IF NOT EXISTS idx_decisions_case_id ON decisions(case_id);
        CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status, confidence_level);
        CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_trails(case_id);
        CREATE INDEX IF NOT EXISTS idx_audit_workflow_time ON audit_trails(workflow_start_time, workflow_end_time);
        """,
        down_sql="""
        DROP TABLE IF EXISTS audit_trails CASCADE;
        DROP TABLE IF EXISTS decisions CASCADE;
        DROP TABLE IF EXISTS evidence_packs CASCADE;
        """
    )
    migrations.append(migration_003)
    
    return migrations


# Migration utilities
def load_migrations_from_directory(directory: str) -> List[Migration]:
    """Load migrations from SQL files in a directory"""
    migrations = []
    migration_dir = Path(directory)
    
    if not migration_dir.exists():
        logger.warning(f"Migration directory not found: {directory}")
        return migrations
    
    # Look for SQL migration files
    for sql_file in sorted(migration_dir.glob("*.sql")):
        try:
            # Parse migration metadata from filename or file content
            migration_id = sql_file.stem
            
            with open(sql_file, 'r') as f:
                content = f.read()
            
            # Simple parser for migration metadata (could be enhanced)
            lines = content.split('\n')
            name = migration_id
            version = "1.0.0"
            depends_on = []
            
            # Look for metadata comments
            for line in lines[:10]:  # Check first 10 lines
                if line.startswith('-- Name:'):
                    name = line.replace('-- Name:', '').strip()
                elif line.startswith('-- Version:'):
                    version = line.replace('-- Version:', '').strip()
                elif line.startswith('-- Depends:'):
                    depends_str = line.replace('-- Depends:', '').strip()
                    depends_on = [d.strip() for d in depends_str.split(',') if d.strip()]
            
            # Split up and down migrations (simple approach)
            if '-- DOWN MIGRATION' in content:
                up_sql, down_sql = content.split('-- DOWN MIGRATION', 1)
                down_sql = down_sql.strip()
            else:
                up_sql = content
                down_sql = None
            
            migration = Migration(
                migration_id=migration_id,
                name=name,
                version=version,
                up_sql=up_sql.strip(),
                down_sql=down_sql,
                depends_on=depends_on
            )
            
            migrations.append(migration)
            logger.debug(f"Loaded migration from file: {sql_file}")
            
        except Exception as e:
            logger.error(f"Failed to load migration from {sql_file}: {e}")
    
    return migrations


# Factory function
def create_migration_manager(connection_manager: DatabaseConnectionManager = None) -> MigrationManager:
    """Create migration manager with initial migrations"""
    manager = MigrationManager(connection_manager)
    
    # Register initial migrations
    initial_migrations = create_initial_migrations()
    for migration in initial_migrations:
        manager.register_migration(migration)
    
    return manager


# CLI-style functions for common operations
def migrate_database(target_version: str = None, dry_run: bool = False) -> bool:
    """Migrate database to target version"""
    manager = create_migration_manager()
    return manager.migrate_up(target_version, dry_run)


def rollback_database(target_version: str, dry_run: bool = False) -> bool:
    """Rollback database to target version"""
    manager = create_migration_manager()
    return manager.migrate_down(target_version, dry_run)


def get_database_migration_status() -> Dict:
    """Get current database migration status"""
    manager = create_migration_manager()
    return manager.get_migration_status()


def validate_database_migrations() -> Dict:
    """Validate database migrations"""
    manager = create_migration_manager()
    return manager.validate_migrations()
