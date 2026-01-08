"""
SQLAlchemy Database Models for DERCAS 01 Policy Validation Copilot

Contains SQLAlchemy ORM models that match the Pydantic entities for data persistence.
Includes tables for cases, policies, exceptions, decisions, audit trails, and all supporting entities.
"""

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class BaseModel:
    """Base model with common fields for all entities."""
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(255))
    updated_by = Column(String(255))


class CaseModel(Base, BaseModel):
    """SQLAlchemy model for Case entity."""
    
    __tablename__ = "cases"
    
    # Business identifiers
    case_id = Column(String(255), unique=True, nullable=False, index=True)
    crm_ticket_id = Column(String(255), index=True)
    
    # Customer and contract information
    customer_id = Column(String(255), index=True)
    contract_id = Column(String(255), index=True)
    insurer_id = Column(String(255), nullable=False, index=True)
    plan_id = Column(String(255), nullable=False, index=True)
    
    # Service information
    service_code = Column(String(255), index=True)
    service_description = Column(Text)
    service_date = Column(DateTime(timezone=True), index=True)
    provider_id = Column(String(255), index=True)
    
    # Case metadata
    priority = Column(String(50), nullable=False, default="MEDIUM", index=True)
    sla_target = Column(DateTime(timezone=True), index=True)
    status = Column(String(50), nullable=False, default="CREATED", index=True)
    assigned_queue = Column(String(100), nullable=False, default="AUTO_PROCESSING", index=True)
    
    # Attachments and context (JSON fields)
    attachments = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    
    # Processing metadata
    processing_started_at = Column(DateTime(timezone=True), index=True)
    processing_completed_at = Column(DateTime(timezone=True), index=True)
    last_activity_at = Column(DateTime(timezone=True), index=True)
    
    # Relationships
    evidence_packs = relationship("EvidencePackModel", back_populates="case", cascade="all, delete-orphan")
    checklists = relationship("ChecklistModel", back_populates="case", cascade="all, delete-orphan")
    decisions = relationship("DecisionRecordModel", back_populates="case", cascade="all, delete-orphan")
    ml_scores = relationship("MLScoreRecordModel", back_populates="case", cascade="all, delete-orphan")
    guardrail_records = relationship("GuardrailRecordModel", back_populates="case", cascade="all, delete-orphan")
    hitl_requests = relationship("HITLRequestModel", back_populates="case", cascade="all, delete-orphan")
    external_queries = relationship("ExternalQueryModel", back_populates="case", cascade="all, delete-orphan")
    audit_trails = relationship("AuditTrailModel", back_populates="case", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_case_insurer_plan", "insurer_id", "plan_id"),
        Index("idx_case_status_priority", "status", "priority"),
        Index("idx_case_service_date", "service_date"),
        Index("idx_case_sla_target", "sla_target"),
    )


class PolicyDocumentModel(Base, BaseModel):
    """SQLAlchemy model for PolicyDocument entity."""
    
    __tablename__ = "policy_documents"
    
    # Document identifiers
    doc_id = Column(String(255), nullable=False, index=True)
    version = Column(String(100), nullable=False)
    checksum = Column(String(255), nullable=False)
    
    # Document metadata
    title = Column(String(500), nullable=False)
    document_type = Column(String(50), nullable=False, default="POLICY")
    status = Column(String(50), nullable=False, default="DRAFT", index=True)
    
    # Scope and applicability
    insurer_id = Column(String(255), nullable=False, index=True)
    plan_ids = Column(JSON, default=list)
    service_codes = Column(JSON, default=list)
    
    # Validity period
    effective_date = Column(DateTime(timezone=True), nullable=False, index=True)
    expiration_date = Column(DateTime(timezone=True), index=True)
    
    # Content and processing
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    parsing_quality = Column(Float, default=0.0)
    
    # Approval workflow
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    
    # Priority for conflict resolution
    priority = Column(Integer, default=0)
    
    # Unique constraint on doc_id + version
    __table_args__ = (
        UniqueConstraint("doc_id", "version", name="uq_policy_doc_version"),
        Index("idx_policy_insurer_status", "insurer_id", "status"),
        Index("idx_policy_effective_date", "effective_date"),
    )


class ExceptionRuleModel(Base, BaseModel):
    """SQLAlchemy model for ExceptionRule entity."""
    
    __tablename__ = "exception_rules"
    
    # Rule identifier
    rule_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Scope
    customer_id = Column(String(255), index=True)
    contract_id = Column(String(255), index=True)
    insurer_id = Column(String(255), nullable=False, index=True)
    plan_id = Column(String(255), index=True)
    service_codes = Column(JSON, default=list)
    
    # Rule definition
    rule_type = Column(String(255), nullable=False)
    rule_description = Column(Text, nullable=False)
    rule_logic = Column(JSON, nullable=False)
    
    # Validity
    effective_date = Column(DateTime(timezone=True), nullable=False, index=True)
    expiration_date = Column(DateTime(timezone=True), index=True)
    status = Column(String(50), nullable=False, default="PROPOSED", index=True)
    
    # Evidence and justification
    evidence_links = Column(JSON, default=list)
    justification = Column(Text, nullable=False)
    
    # Approval workflow
    proposed_by = Column(String(255), nullable=False)
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("idx_exception_insurer_status", "insurer_id", "status"),
        Index("idx_exception_effective_date", "effective_date"),
        Index("idx_exception_customer", "customer_id"),
    )


class EvidencePackModel(Base, BaseModel):
    """SQLAlchemy model for EvidencePack entity."""
    
    __tablename__ = "evidence_packs"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Evidence items (JSON array)
    items = Column(JSON, default=list)
    coverage_score = Column(Float, default=0.0)
    conflicts_detected = Column(Boolean, default=False)
    missing_sources = Column(JSON, default=list)
    
    # Metadata
    retrieval_query = Column(Text)
    retrieval_timestamp = Column(DateTime(timezone=True))
    retrieval_model_version = Column(String(100))
    
    # Relationship
    case = relationship("CaseModel", back_populates="evidence_packs")


class ChecklistModel(Base, BaseModel):
    """SQLAlchemy model for Checklist entity."""
    
    __tablename__ = "checklists"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Checklist data
    items = Column(JSON, default=list)
    missing_fields = Column(JSON, default=list)
    rule_ids_applied = Column(JSON, default=list)
    
    # Evaluation metadata
    evaluation_timestamp = Column(DateTime(timezone=True))
    rule_set_version = Column(String(100))
    evaluation_log = Column(JSON, default=dict)
    
    # Summary metrics
    total_items = Column(Integer, default=0)
    passed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    missing_items = Column(Integer, default=0)
    
    # Relationship
    case = relationship("CaseModel", back_populates="checklists")


class MLScoreRecordModel(Base, BaseModel):
    """SQLAlchemy model for MLScoreRecord entity."""
    
    __tablename__ = "ml_score_records"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Model information
    model_type = Column(String(50), nullable=False, index=True)
    model_version = Column(String(100), nullable=False)
    
    # Input and output
    input_features = Column(JSON, nullable=False)
    output_scores = Column(JSON, nullable=False)
    
    # Metadata
    inference_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    processing_time_ms = Column(Float)
    
    # Quality metrics
    confidence = Column(Float, default=0.0)
    drift_score = Column(Float)
    
    # Fallback information
    fallback_used = Column(Boolean, default=False)
    fallback_reason = Column(String(500))
    
    # Relationship
    case = relationship("CaseModel", back_populates="ml_scores")
    
    __table_args__ = (
        Index("idx_ml_score_model_type", "model_type"),
        Index("idx_ml_score_inference_time", "inference_timestamp"),
    )


class DecisionRecordModel(Base, BaseModel):
    """SQLAlchemy model for DecisionRecord entity."""
    
    __tablename__ = "decision_records"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Decision status
    status = Column(String(50), nullable=False, index=True)
    
    # Decision metrics
    confidence_score = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False)
    anomaly_score = Column(Float)
    eta_estimate = Column(Integer)
    
    # Decision logic
    next_actions = Column(JSON, default=list)
    thresholds_version = Column(String(100), nullable=False)
    
    # Supporting data references
    checklist_id = Column(PostgresUUID(as_uuid=True), ForeignKey("checklists.id"))
    evidence_pack_id = Column(PostgresUUID(as_uuid=True), ForeignKey("evidence_packs.id"))
    ml_scores = Column(JSON, default=list)  # List of ML score record IDs
    
    # HITL information
    requires_hitl = Column(Boolean, default=False)
    hitl_reasons = Column(JSON, default=list)
    
    # Final decision (if completed)
    final_decision = Column(String(50))
    decision_rationale = Column(Text)
    decided_by = Column(String(255))
    decided_at = Column(DateTime(timezone=True))
    
    # Relationship
    case = relationship("CaseModel", back_populates="decisions")
    
    __table_args__ = (
        Index("idx_decision_status", "status"),
        Index("idx_decision_confidence", "confidence_score"),
        Index("idx_decision_risk", "risk_level"),
    )


class GuardrailRecordModel(Base, BaseModel):
    """SQLAlchemy model for GuardrailRecord entity."""
    
    __tablename__ = "guardrail_records"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Guardrail checks
    checks = Column(JSON, default=list)
    
    # Overall result
    overall_action = Column(String(50), nullable=False)
    blocked_reasons = Column(JSON, default=list)
    redactions_applied = Column(JSON, default=list)
    
    # Metadata
    check_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    guardrails_version = Column(String(100), nullable=False)
    
    # Relationship
    case = relationship("CaseModel", back_populates="guardrail_records")


class HITLRequestModel(Base, BaseModel):
    """SQLAlchemy model for HITLRequest entity."""
    
    __tablename__ = "hitl_requests"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Request details
    reasons = Column(JSON, nullable=False)
    assigned_to_role = Column(String(50), nullable=False)
    assigned_to_user = Column(String(255))
    priority = Column(String(50), nullable=False, default="MEDIUM")
    
    # Questions and context
    questions = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    
    # Response
    answers = Column(JSON, default=list)
    decision = Column(String(50))
    notes = Column(Text)
    
    # Workflow
    requested_at = Column(DateTime(timezone=True), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))
    responded_by = Column(String(255))
    
    # Relationship
    case = relationship("CaseModel", back_populates="hitl_requests")
    
    __table_args__ = (
        Index("idx_hitl_assigned_role", "assigned_to_role"),
        Index("idx_hitl_requested_at", "requested_at"),
    )


class ExternalQueryModel(Base, BaseModel):
    """SQLAlchemy model for ExternalQuery entity."""
    
    __tablename__ = "external_queries"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Query details
    insurer_id = Column(String(255), nullable=False)
    query_type = Column(String(255), nullable=False)
    query_data = Column(JSON, nullable=False)
    channel = Column(String(255), nullable=False)
    
    # Response
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    response_data = Column(JSON)
    response_checksum = Column(String(255))
    
    # Timing
    sent_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    timeout_at = Column(DateTime(timezone=True))
    
    # Error handling
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Relationship
    case = relationship("CaseModel", back_populates="external_queries")
    
    __table_args__ = (
        Index("idx_external_query_status", "status"),
        Index("idx_external_query_insurer", "insurer_id"),
    )


class AuditTrailModel(Base, BaseModel):
    """SQLAlchemy model for AuditTrail entity."""
    
    __tablename__ = "audit_trails"
    
    # Foreign key to case
    case_id = Column(String(255), ForeignKey("cases.case_id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    user_id = Column(String(255), index=True)
    session_id = Column(String(255), index=True)
    
    # LangGraph node execution
    node_name = Column(String(255), index=True)
    node_input = Column(JSON)
    node_output = Column(JSON)
    execution_time_ms = Column(Float)
    
    # Versioning
    model_versions = Column(JSON, default=dict)
    policy_versions = Column(JSON, default=dict)
    rule_versions = Column(JSON, default=dict)
    
    # Access control
    access_level = Column(String(100))
    export_restricted = Column(Boolean, default=False)
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    correlation_id = Column(String(255), index=True)
    
    # Relationship
    case = relationship("CaseModel", back_populates="audit_trails")
    
    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_correlation", "correlation_id"),
        Index("idx_audit_node_name", "node_name"),
    )


# Additional utility tables

class SystemConfigModel(Base, BaseModel):
    """System configuration table for storing key-value configuration."""
    
    __tablename__ = "system_config"
    
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    config_type = Column(String(100), nullable=False, default="GENERAL")
    is_sensitive = Column(Boolean, default=False)
    
    __table_args__ = (
        Index("idx_config_type", "config_type"),
    )


class ModelVersionModel(Base, BaseModel):
    """Model version tracking table."""
    
    __tablename__ = "model_versions"
    
    model_id = Column(String(255), nullable=False, index=True)
    model_type = Column(String(50), nullable=False, index=True)
    version = Column(String(100), nullable=False)
    
    # Model metadata
    name = Column(String(500), nullable=False)
    description = Column(Text)
    algorithm = Column(String(255))
    
    # Performance metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    # Deployment info
    deployed_at = Column(DateTime(timezone=True), nullable=False)
    deployed_by = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")
    
    # Training info
    training_data_size = Column(Integer)
    training_completed_at = Column(DateTime(timezone=True))
    
    # Configuration
    hyperparameters = Column(JSON, default=dict)
    feature_importance = Column(JSON)
    
    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_version"),
        Index("idx_model_type_status", "model_type", "status"),
    )


class NotificationModel(Base, BaseModel):
    """Notification tracking table."""
    
    __tablename__ = "notifications"
    
    notification_type = Column(String(100), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related entities
    case_id = Column(String(255), index=True)
    related_entity_type = Column(String(100))
    related_entity_id = Column(String(255))
    
    # Status
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Metadata
    priority = Column(String(50), default="MEDIUM")
    channel = Column(String(100), default="EMAIL")
    retry_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index("idx_notification_type_status", "notification_type", "status"),
        Index("idx_notification_recipient", "recipient"),
    )


# Database utility functions

def get_table_names() -> List[str]:
    """Get all table names defined in this module."""
    return [
        "cases",
        "policy_documents", 
        "exception_rules",
        "evidence_packs",
        "checklists",
        "ml_score_records",
        "decision_records",
        "guardrail_records",
        "hitl_requests",
        "external_queries",
        "audit_trails",
        "system_config",
        "model_versions",
        "notifications",
    ]


def create_indexes(engine):
    """Create additional indexes for performance optimization."""
    from sqlalchemy import text
    
    # Additional composite indexes for common query patterns
    additional_indexes = [
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_composite_status ON cases (status, priority, sla_target) WHERE status IN ('CREATED', 'INGESTED', 'ROUTING')",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trails_composite ON audit_trails (case_id, event_type, timestamp)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ml_scores_composite ON ml_score_records (case_id, model_type, inference_timestamp)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_decisions_composite ON decision_records (case_id, status, decided_at)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hitl_composite ON hitl_requests (assigned_to_role, status, requested_at) WHERE responded_at IS NULL",
    ]
    
    with engine.connect() as conn:
        for index_sql in additional_indexes:
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception as e:
                print(f"Warning: Could not create index: {e}")
                conn.rollback()
