"""
Database layer with SQLAlchemy models for Policy Validation Copilot

This module defines the complete database schema including:
- Case: Core case management
- PolicyDocument: Policy document management with versioning
- ExceptionRule: Exception rules with scope and expiration
- EvidencePack: Evidence collection and validation
- Checklist: Policy evaluation checklists
- Decision: Decision records with audit trail
- AuditTrail: Complete execution traceability

All models support versioning, checksums, and audit trails as required
by the functional specification.
"""

import enum
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, JSON, String,
    Text, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

Base = declarative_base()


# Enums matching state schema
class CaseStatusEnum(enum.Enum):
    NUEVO = "NUEVO"
    EN_PROCESO = "EN_PROCESO"
    APROBADO = "APROBADO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    PENDIENTE_DATOS = "PENDIENTE_DATOS"
    PENDIENTE_POLITICA = "PENDIENTE_POLITICA"
    PENDIENTE_ASEGURADORA = "PENDIENTE_ASEGURADORA"
    PENDIENTE_SISTEMA = "PENDIENTE_SISTEMA"
    ESCALADO_HITL = "ESCALADO_HITL"


class PriorityEnum(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionStatusEnum(enum.Enum):
    PENDING = "PENDING"
    APROBADO = "APROBADO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    ESCALADO = "ESCALADO"


class ConfidenceLevelEnum(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskLevelEnum(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Core database models
class Case(Base):
    """Core case management table"""
    __tablename__ = 'cases'
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(String(100), unique=True, nullable=False, index=True)
    crm_ticket_id = Column(String(100), nullable=False, index=True)
    
    # Customer and contract information
    customer_id = Column(String(100), nullable=False, index=True)
    contract_id = Column(String(100), nullable=True, index=True)
    
    # Insurance and service details
    insurer_id = Column(String(100), nullable=False, index=True)
    plan_id = Column(String(100), nullable=False)
    service_code = Column(String(50), nullable=True)
    service_description = Column(Text, nullable=True)
    service_date = Column(DateTime, nullable=False)
    provider_id = Column(String(100), nullable=True, index=True)
    
    # Operational details
    priority = Column(Enum(PriorityEnum), nullable=False, default=PriorityEnum.MEDIUM)
    sla_target = Column(DateTime, nullable=True)
    status = Column(Enum(CaseStatusEnum), nullable=False, default=CaseStatusEnum.NUEVO, index=True)
    assigned_queue = Column(String(100), nullable=True, index=True)
    
    # Additional context
    channel = Column(String(50), nullable=True)
    source_system = Column(String(100), nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attachments = relationship("CaseAttachment", back_populates="case", cascade="all, delete-orphan")
    evidence_packs = relationship("EvidencePack", back_populates="case", cascade="all, delete-orphan")
    checklists = relationship("Checklist", back_populates="case", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="case", cascade="all, delete-orphan")
    audit_trails = relationship("AuditTrail", back_populates="case", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_case_status_priority', 'status', 'priority'),
        Index('idx_case_insurer_service', 'insurer_id', 'service_code'),
        Index('idx_case_created_status', 'created_at', 'status'),
    )


class CaseAttachment(Base):
    """Case attachments with versioning and checksums"""
    __tablename__ = 'case_attachments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    attachment_id = Column(String(100), nullable=False, index=True)
    
    # File metadata
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA-256
    
    # Storage information
    storage_path = Column(String(1000), nullable=False)
    upload_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="attachments")
    
    __table_args__ = (
        UniqueConstraint('case_id', 'attachment_id', name='uq_case_attachment'),
        Index('idx_attachment_checksum', 'checksum'),
    )


class PolicyDocument(Base):
    """Policy documents with versioning and metadata"""
    __tablename__ = 'policy_documents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    doc_id = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    
    # Document metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(String(100), nullable=False)
    scope = Column(JSON, nullable=True)  # Scope definition
    
    # Versioning and validation
    checksum = Column(String(64), nullable=False)  # SHA-256
    is_active = Column(Boolean, nullable=False, default=True)
    vigencia_start = Column(DateTime, nullable=False)
    vigencia_end = Column(DateTime, nullable=True)
    
    # Content and storage
    content_path = Column(String(1000), nullable=False)
    parsed_content = Column(JSON, nullable=True)  # Structured content
    
    # Approval and governance
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_status = Column(String(50), nullable=False, default='PENDING')
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    evidence_items = relationship("EvidenceItem", back_populates="policy_document")
    
    __table_args__ = (
        UniqueConstraint('doc_id', 'version', name='uq_policy_doc_version'),
        Index('idx_policy_active_vigencia', 'is_active', 'vigencia_start', 'vigencia_end'),
        Index('idx_policy_scope', 'scope'),
    )


class ExceptionRule(Base):
    """Exception rules with scope and expiration management"""
    __tablename__ = 'exception_rules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Rule definition
    rule_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    scope = Column(JSON, nullable=False)  # Scope definition
    rule_logic = Column(JSON, nullable=False)  # Rule implementation
    
    # Client and context
    client_id = Column(String(100), nullable=True, index=True)
    insurer_id = Column(String(100), nullable=True, index=True)
    service_codes = Column(JSON, nullable=True)  # List of applicable service codes
    
    # Lifecycle management
    is_active = Column(Boolean, nullable=False, default=False)
    effective_date = Column(DateTime, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    auto_expire = Column(Boolean, nullable=False, default=True)
    
    # Approval workflow
    proposed_by = Column(String(100), nullable=False)
    approved_by = Column(String(100), nullable=True)
    approval_status = Column(String(50), nullable=False, default='PENDING')
    approval_date = Column(DateTime, nullable=True)
    
    # Evidence and justification
    evidence_attachments = Column(JSON, nullable=True)  # List of evidence files
    business_justification = Column(Text, nullable=False)
    
    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_exception_active_scope', 'is_active', 'scope'),
        Index('idx_exception_client_insurer', 'client_id', 'insurer_id'),
        Index('idx_exception_expiration', 'expiration_date', 'auto_expire'),
    )


class EvidencePack(Base):
    """Evidence packs with coverage metrics and validation"""
    __tablename__ = 'evidence_packs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    evidence_pack_id = Column(String(100), nullable=False, index=True)
    
    # Coverage and validation metrics
    coverage_score = Column(Float, nullable=False, default=0.0)
    conflicts_detected = Column(Boolean, nullable=False, default=False)
    conflict_details = Column(JSON, nullable=True)
    missing_sources = Column(JSON, nullable=True)  # List of missing sources
    
    # Validation flags
    allowlist_validated = Column(Boolean, nullable=False, default=False)
    evidence_anchoring_passed = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    retrieval_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="evidence_packs")
    evidence_items = relationship("EvidenceItem", back_populates="evidence_pack", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('case_id', 'evidence_pack_id', name='uq_case_evidence_pack'),
        Index('idx_evidence_coverage', 'coverage_score'),
        CheckConstraint('coverage_score >= 0.0 AND coverage_score <= 1.0', name='chk_coverage_score_range'),
    )


class EvidenceItem(Base):
    """Individual evidence items with document references"""
    __tablename__ = 'evidence_items'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    evidence_pack_id = Column(UUID(as_uuid=True), ForeignKey('evidence_packs.id'), nullable=False)
    policy_document_id = Column(UUID(as_uuid=True), ForeignKey('policy_documents.id'), nullable=False)
    
    # Document reference
    doc_id = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    checksum = Column(String(64), nullable=False)
    pointer = Column(String(500), nullable=False)  # Exact reference (page/cell/section)
    
    # Content
    excerpt = Column(Text, nullable=True)
    table_ref = Column(String(200), nullable=True)
    
    # Scoring
    relevance_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    evidence_pack = relationship("EvidencePack", back_populates="evidence_items")
    policy_document = relationship("PolicyDocument", back_populates="evidence_items")
    
    __table_args__ = (
        Index('idx_evidence_item_scores', 'relevance_score', 'confidence_score'),
        Index('idx_evidence_item_doc', 'doc_id', 'version'),
        CheckConstraint('relevance_score >= 0.0 AND relevance_score <= 1.0', name='chk_relevance_score_range'),
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='chk_confidence_score_range'),
    )


class Checklist(Base):
    """Policy evaluation checklists"""
    __tablename__ = 'checklists'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    checklist_id = Column(String(100), nullable=False, index=True)
    
    # Evaluation metadata
    missing_fields = Column(JSON, nullable=True)  # List of missing fields
    rule_ids_applied = Column(JSON, nullable=True)  # List of applied rule IDs
    evaluation_log = Column(JSON, nullable=True)  # Evaluation log entries
    
    # Completion metrics
    completion_percentage = Column(Float, nullable=False, default=0.0)
    critical_items_passed = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    evaluation_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="checklists")
    checklist_items = relationship("ChecklistItem", back_populates="checklist", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('case_id', 'checklist_id', name='uq_case_checklist'),
        Index('idx_checklist_completion', 'completion_percentage', 'critical_items_passed'),
        CheckConstraint('completion_percentage >= 0.0 AND completion_percentage <= 100.0', name='chk_completion_percentage_range'),
    )


class ChecklistItem(Base):
    """Individual checklist items with outcomes and evidence"""
    __tablename__ = 'checklist_items'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    checklist_id = Column(UUID(as_uuid=True), ForeignKey('checklists.id'), nullable=False)
    item_id = Column(String(100), nullable=False)
    
    # Item definition
    description = Column(Text, nullable=False)
    is_critical = Column(Boolean, nullable=False, default=False)
    
    # Evaluation outcome
    outcome = Column(String(20), nullable=True)  # YES/NO/MISSING/UNKNOWN
    evidence_ref = Column(String(200), nullable=True)  # Reference to evidence item
    rule_id = Column(String(100), nullable=True)  # Associated rule identifier
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    checklist = relationship("Checklist", back_populates="checklist_items")
    
    __table_args__ = (
        UniqueConstraint('checklist_id', 'item_id', name='uq_checklist_item'),
        Index('idx_checklist_item_outcome', 'outcome', 'is_critical'),
    )


class Decision(Base):
    """Decision records with confidence, risk, and audit trail"""
    __tablename__ = 'decisions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    decision_id = Column(String(100), nullable=False, index=True)
    
    # Decision outcome
    status = Column(Enum(DecisionStatusEnum), nullable=False, default=DecisionStatusEnum.PENDING)
    
    # Confidence and risk metrics
    confidence_score = Column(Float, nullable=False, default=0.0)
    confidence_level = Column(Enum(ConfidenceLevelEnum), nullable=False, default=ConfidenceLevelEnum.LOW)
    risk_level = Column(Enum(RiskLevelEnum), nullable=False, default=RiskLevelEnum.MEDIUM)
    anomaly_score = Column(Float, nullable=True)
    
    # ETA and timing
    eta_estimate = Column(Integer, nullable=True)  # ETA in minutes
    
    # Actions and routing
    next_actions = Column(JSON, nullable=True)  # List of next actions
    requires_hitl = Column(Boolean, nullable=False, default=False)
    requires_external_consultation = Column(Boolean, nullable=False, default=False)
    auto_close_eligible = Column(Boolean, nullable=False, default=False)
    
    # Configuration and versioning
    thresholds_version = Column(String(50), nullable=False)
    
    # Decision rationale
    decision_rationale = Column(Text, nullable=True)
    supporting_evidence = Column(JSON, nullable=True)  # List of evidence references
    
    # Timestamps
    decision_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="decisions")
    
    __table_args__ = (
        UniqueConstraint('case_id', 'decision_id', name='uq_case_decision'),
        Index('idx_decision_status_confidence', 'status', 'confidence_level'),
        Index('idx_decision_risk_anomaly', 'risk_level', 'anomaly_score'),
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='chk_confidence_score_range'),
        CheckConstraint('anomaly_score IS NULL OR (anomaly_score >= 0.0 AND anomaly_score <= 1.0)', name='chk_anomaly_score_range'),
    )


class AuditTrail(Base):
    """Complete execution traceability and audit logs"""
    __tablename__ = 'audit_trails'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    audit_id = Column(String(100), nullable=False, index=True)
    
    # Workflow execution
    workflow_start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    workflow_end_time = Column(DateTime, nullable=True)
    total_execution_time = Column(Integer, nullable=True)  # Total time in seconds
    
    # Node execution tracking
    node_execution_log = Column(JSON, nullable=True)  # List of node executions
    
    # Export and access logs
    export_logs = Column(JSON, nullable=True)  # List of export events
    access_logs = Column(JSON, nullable=True)  # List of access events
    
    # Traceability
    policy_versions_used = Column(JSON, nullable=True)  # Dict of policy versions
    rule_versions_used = Column(JSON, nullable=True)  # Dict of rule versions
    model_versions_used = Column(JSON, nullable=True)  # Dict of model versions
    
    # Compliance and governance
    compliance_flags = Column(JSON, nullable=True)  # List of compliance flags
    data_lineage = Column(JSON, nullable=True)  # Data lineage information
    
    # Immutability controls
    audit_hash = Column(String(64), nullable=True)  # SHA-256 of audit data
    previous_audit_hash = Column(String(64), nullable=True)  # Previous audit hash for chaining
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="audit_trails")
    
    __table_args__ = (
        UniqueConstraint('case_id', 'audit_id', name='uq_case_audit'),
        Index('idx_audit_workflow_time', 'workflow_start_time', 'workflow_end_time'),
        Index('idx_audit_hash_chain', 'audit_hash', 'previous_audit_hash'),
    )


# Database connection and session management
class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or "sqlite:///policy_validation.db"
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize database engine with appropriate configuration"""
        if self.database_url.startswith("sqlite"):
            # SQLite configuration for development
            self.engine = create_engine(
                self.database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            # PostgreSQL configuration for production
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def get_engine(self):
        """Get database engine"""
        return self.engine


# Event listeners for automatic timestamp updates
@event.listens_for(Case, 'before_update')
def update_case_timestamp(mapper, connection, target):
    target.updated_at = datetime.utcnow()


@event.listens_for(PolicyDocument, 'before_update')
def update_policy_timestamp(mapper, connection, target):
    target.updated_at = datetime.utcnow()


@event.listens_for(ExceptionRule, 'before_update')
def update_exception_timestamp(mapper, connection, target):
    target.updated_at = datetime.utcnow()


@event.listens_for(AuditTrail, 'before_update')
def update_audit_timestamp(mapper, connection, target):
    target.updated_at = datetime.utcnow()


# Database initialization function
def initialize_database(database_url: str = None) -> DatabaseManager:
    """Initialize database with all tables and return manager"""
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager


# Migration utilities
def create_migration_script():
    """Generate Alembic migration script template"""
    migration_template = '''"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: {create_date}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create all tables using Base.metadata
    from src.data_layer.database import Base, DatabaseManager
    
    # This would be replaced with actual table creation commands
    # generated by alembic revision --autogenerate
    pass

def downgrade():
    # Drop all tables
    pass
'''.format(create_date=datetime.utcnow().isoformat())
    
    return migration_template
