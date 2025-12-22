"""
SQLAlchemy Models for Policy Validation Copilot

This module defines all database models for the Policy Validation Copilot system,
including cases, policies, evidence, decisions, audit trails, and related entities.
"""

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, JSON,
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from .base import Base, TimestampMixin, UUIDMixin, AuditMixin


class Case(Base, UUIDMixin, TimestampMixin, AuditMixin):
    """
    Case entity representing a policy validation request.
    
    Maps to the Case component in the state schema.
    """
    __tablename__ = "cases"
    
    # Case identification
    crm_ticket_id = Column(String(100), nullable=False, index=True, comment="CRM ticket identifier")
    customer_id = Column(String(100), nullable=False, index=True, comment="Customer identifier")
    contract_id = Column(String(100), nullable=True, index=True, comment="Contract identifier")
    
    # Service information
    insurer_id = Column(String(50), nullable=False, index=True, comment="Insurer identifier")
    plan_id = Column(String(50), nullable=False, comment="Insurance plan identifier")
    service_code = Column(String(50), nullable=False, index=True, comment="Service code")
    service_date = Column(DateTime(timezone=True), nullable=False, comment="Service date")
    provider_id = Column(String(100), nullable=True, comment="Healthcare provider identifier")
    
    # Service details
    service_amount = Column(Float, nullable=True, comment="Service amount")
    service_currency = Column(String(3), default="USD", comment="Service currency")
    service_description = Column(Text, nullable=True, comment="Service description")
    diagnosis_codes = Column(JSON, nullable=True, comment="Diagnosis codes array")
    procedure_codes = Column(JSON, nullable=True, comment="Procedure codes array")
    
    # Case management
    priority = Column(String(20), default="MEDIUM", nullable=False, comment="Case priority")
    status = Column(String(30), default="PENDIENTE", nullable=False, index=True, comment="Case status")
    queue = Column(String(50), nullable=True, index=True, comment="Processing queue")
    assigned_to = Column(String(255), nullable=True, comment="Assigned user")
    
    # SLA management
    sla_target_date = Column(DateTime(timezone=True), nullable=True, comment="SLA target date")
    sla_priority_hours = Column(Integer, nullable=True, comment="SLA hours for this priority")
    
    # Metadata
    source_system = Column(String(50), nullable=True, comment="Source system")
    correlation_id = Column(String(100), nullable=True, index=True, comment="Correlation ID")
    tags = Column(JSON, nullable=True, comment="Case tags")
    metadata = Column(JSON, nullable=True, comment="Additional metadata")
    
    # Relationships
    attachments = relationship("CaseAttachment", back_populates="case", cascade="all, delete-orphan")
    evidence_packs = relationship("EvidencePack", back_populates="case", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        Index("ix_case_customer_service", "customer_id", "service_code", "service_date"),
        Index("ix_case_status_priority", "status", "priority"),
        CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_case_priority"),
        CheckConstraint("status IN ('PENDIENTE', 'EN_REVISION', 'APROBADO', 'RECHAZADO', 'OBSERVADO', 'ESCALAR', 'CERRADO')", name="ck_case_status"),
    )
    
    def __repr__(self):
        return f"<Case(id={self.id}, crm_ticket_id={self.crm_ticket_id}, status={self.status})>"


class CaseAttachment(Base, UUIDMixin, TimestampMixin):
    """Case attachment entity"""
    __tablename__ = "case_attachments"
    
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False, comment="Original filename")
    content_type = Column(String(100), nullable=False, comment="MIME content type")
    size_bytes = Column(Integer, nullable=False, comment="File size in bytes")
    checksum = Column(String(64), nullable=False, comment="File checksum (SHA-256)")
    storage_path = Column(String(500), nullable=False, comment="Storage path or URL")
    
    # Metadata
    description = Column(Text, nullable=True, comment="Attachment description")
    tags = Column(JSON, nullable=True, comment="Attachment tags")
    
    # Relationships
    case = relationship("Case", back_populates="attachments")
    
    def __repr__(self):
        return f"<CaseAttachment(id={self.id}, filename={self.filename})>"


class Policy(Base, UUIDMixin, TimestampMixin, AuditMixin):
    """Policy document entity"""
    __tablename__ = "policies"
    
    # Policy identification
    policy_id = Column(String(100), nullable=False, unique=True, comment="Policy identifier")
    name = Column(String(255), nullable=False, comment="Policy name")
    version = Column(String(50), nullable=False, comment="Policy version")
    
    # Policy content
    content = Column(Text, nullable=True, comment="Policy content")
    content_hash = Column(String(64), nullable=False, comment="Content hash for integrity")
    
    # Policy metadata
    policy_type = Column(String(50), nullable=False, comment="Policy type")
    category = Column(String(100), nullable=True, comment="Policy category")
    tags = Column(JSON, nullable=True, comment="Policy tags")
    
    # Lifecycle management
    status = Column(String(20), default="DRAFT", nullable=False, comment="Policy status")
    effective_date = Column(DateTime(timezone=True), nullable=True, comment="Effective date")
    expiry_date = Column(DateTime(timezone=True), nullable=True, comment="Expiry date")
    
    # Approval workflow
    approved_by = Column(String(255), nullable=True, comment="Approved by user")
    approved_at = Column(DateTime(timezone=True), nullable=True, comment="Approval timestamp")
    
    # Relationships
    exceptions = relationship("PolicyException", back_populates="policy", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="policy")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_policy_version"),
        Index("ix_policy_type_status", "policy_type", "status"),
        Index("ix_policy_effective", "effective_date", "expiry_date"),
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'DEPRECATED', 'ARCHIVED')", name="ck_policy_status"),
    )
    
    def __repr__(self):
        return f"<Policy(id={self.id}, policy_id={self.policy_id}, version={self.version})>"


class PolicyException(Base, UUIDMixin, TimestampMixin, AuditMixin):
    """Policy exception entity for RB-03 compliance"""
    __tablename__ = "policy_exceptions"
    
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False, index=True)
    exception_id = Column(String(100), nullable=False, unique=True, comment="Exception identifier")
    
    # Exception details
    name = Column(String(255), nullable=False, comment="Exception name")
    description = Column(Text, nullable=False, comment="Exception description")
    exception_type = Column(String(50), nullable=False, comment="Exception type")
    
    # Scope definition
    scope_criteria = Column(JSON, nullable=False, comment="Exception scope criteria")
    override_rules = Column(JSON, nullable=False, comment="Override rules")
    
    # Lifecycle management
    status = Column(String(20), default="ACTIVE", nullable=False, comment="Exception status")
    effective_date = Column(DateTime(timezone=True), nullable=False, comment="Effective date")
    expiry_date = Column(DateTime(timezone=True), nullable=True, comment="Expiry date")
    
    # Approval and tracking
    approved_by = Column(String(255), nullable=False, comment="Approved by user")
    approved_at = Column(DateTime(timezone=True), nullable=False, comment="Approval timestamp")
    usage_count = Column(Integer, default=0, comment="Number of times used")
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="Last usage timestamp")
    
    # Relationships
    policy = relationship("Policy", back_populates="exceptions")
    
    # Constraints
    __table_args__ = (
        Index("ix_exception_scope", "exception_type", "status"),
        Index("ix_exception_dates", "effective_date", "expiry_date"),
        CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'EXPIRED', 'REVOKED')", name="ck_exception_status"),
    )
    
    def __repr__(self):
        return f"<PolicyException(id={self.id}, exception_id={self.exception_id})>"


class EvidencePack(Base, UUIDMixin, TimestampMixin):
    """Evidence pack entity"""
    __tablename__ = "evidence_packs"
    
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    
    # Evidence pack metadata
    coverage_score = Column(Float, nullable=True, comment="Coverage score (0.0-1.0)")
    conflicts_detected = Column(Boolean, default=False, comment="Whether conflicts were detected")
    missing_sources = Column(JSON, nullable=True, comment="Missing source identifiers")
    
    # Retrieval metadata
    retrieval_method = Column(String(50), nullable=True, comment="Retrieval method used")
    retrieval_timestamp = Column(DateTime(timezone=True), nullable=True, comment="Retrieval timestamp")
    retrieval_duration_ms = Column(Integer, nullable=True, comment="Retrieval duration in milliseconds")
    
    # Relationships
    case = relationship("Case", back_populates="evidence_packs")
    items = relationship("EvidenceItem", back_populates="evidence_pack", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<EvidencePack(id={self.id}, case_id={self.case_id}, coverage_score={self.coverage_score})>"


class EvidenceItem(Base, UUIDMixin, TimestampMixin):
    """Evidence item entity"""
    __tablename__ = "evidence_items"
    
    evidence_pack_id = Column(String(36), ForeignKey("evidence_packs.id"), nullable=False, index=True)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=True, index=True)
    
    # Document reference
    doc_id = Column(String(100), nullable=False, comment="Document identifier")
    version = Column(String(50), nullable=False, comment="Document version")
    checksum = Column(String(64), nullable=False, comment="Document checksum")
    pointer = Column(String(500), nullable=False, comment="Specific location pointer")
    
    # Evidence content
    excerpt = Column(Text, nullable=False, comment="Relevant text excerpt")
    table_ref = Column(String(100), nullable=True, comment="Table reference")
    
    # Scoring
    relevance_score = Column(Float, nullable=True, comment="Relevance score (0.0-1.0)")
    confidence_score = Column(Float, nullable=True, comment="Confidence score (0.0-1.0)")
    
    # Relationships
    evidence_pack = relationship("EvidencePack", back_populates="items")
    policy = relationship("Policy", back_populates="evidence_items")
    
    # Constraints
    __table_args__ = (
        Index("ix_evidence_doc_version", "doc_id", "version"),
        Index("ix_evidence_scores", "relevance_score", "confidence_score"),
    )
    
    def __repr__(self):
        return f"<EvidenceItem(id={self.id}, doc_id={self.doc_id}, version={self.version})>"


class Decision(Base, UUIDMixin, TimestampMixin, AuditMixin):
    """Decision entity"""
    __tablename__ = "decisions"
    
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    
    # Decision details
    status = Column(String(30), nullable=False, comment="Decision status")
    confidence_score = Column(Float, nullable=True, comment="Confidence score (0.0-1.0)")
    risk_score = Column(Float, nullable=True, comment="Risk score (0.0-1.0)")
    
    # Decision content
    explanation = Column(Text, nullable=True, comment="Decision explanation")
    next_actions = Column(JSON, nullable=True, comment="Next actions array")
    supporting_evidence = Column(JSON, nullable=True, comment="Supporting evidence references")
    
    # Thresholds and rules
    thresholds_version = Column(String(50), nullable=True, comment="Thresholds version used")
    rules_applied = Column(JSON, nullable=True, comment="Rules applied array")
    
    # HITL information
    requires_hitl = Column(Boolean, default=False, comment="Requires human in the loop")
    hitl_reason = Column(String(255), nullable=True, comment="HITL requirement reason")
    hitl_assigned_to = Column(String(255), nullable=True, comment="HITL assigned user")
    hitl_completed_at = Column(DateTime(timezone=True), nullable=True, comment="HITL completion timestamp")
    
    # Finalization
    is_final = Column(Boolean, default=False, comment="Whether decision is final")
    finalized_at = Column(DateTime(timezone=True), nullable=True, comment="Finalization timestamp")
    finalized_by = Column(String(255), nullable=True, comment="Finalized by user")
    
    # Relationships
    case = relationship("Case", back_populates="decisions")
    
    # Constraints
    __table_args__ = (
        Index("ix_decision_status_final", "status", "is_final"),
        Index("ix_decision_scores", "confidence_score", "risk_score"),
        CheckConstraint("status IN ('APROBADO', 'RECHAZADO', 'OBSERVADO', 'ESCALAR', 'PENDIENTE')", name="ck_decision_status"),
        CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)", name="ck_confidence_range"),
        CheckConstraint("risk_score IS NULL OR (risk_score >= 0.0 AND risk_score <= 1.0)", name="ck_risk_range"),
    )
    
    def __repr__(self):
        return f"<Decision(id={self.id}, case_id={self.case_id}, status={self.status})>"


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Audit log entity for comprehensive audit trails"""
    __tablename__ = "audit_logs"
    
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    
    # Event information
    event_type = Column(String(50), nullable=False, index=True, comment="Event type")
    event_category = Column(String(30), nullable=False, index=True, comment="Event category")
    event_description = Column(Text, nullable=False, comment="Event description")
    
    # Actor information
    user_id = Column(String(255), nullable=True, comment="User who performed the action")
    user_roles = Column(JSON, nullable=True, comment="User roles at time of action")
    session_id = Column(String(100), nullable=True, comment="Session identifier")
    
    # Context information
    source_ip = Column(String(45), nullable=True, comment="Source IP address")
    user_agent = Column(String(500), nullable=True, comment="User agent")
    correlation_id = Column(String(100), nullable=True, index=True, comment="Correlation ID")
    
    # Event data
    before_state = Column(JSON, nullable=True, comment="State before change")
    after_state = Column(JSON, nullable=True, comment="State after change")
    event_data = Column(JSON, nullable=True, comment="Additional event data")
    
    # Processing information
    node_name = Column(String(100), nullable=True, comment="LangGraph node name")
    processing_time_ms = Column(Integer, nullable=True, comment="Processing time in milliseconds")
    
    # Security and compliance
    security_level = Column(String(20), default="NORMAL", comment="Security level")
    compliance_flags = Column(JSON, nullable=True, comment="Compliance flags")
    
    # Relationships
    case = relationship("Case", back_populates="audit_logs")
    
    # Constraints
    __table_args__ = (
        Index("ix_audit_event_time", "event_type", "created_at"),
        Index("ix_audit_user_time", "user_id", "created_at"),
        Index("ix_audit_correlation", "correlation_id", "created_at"),
        CheckConstraint("event_category IN ('CASE', 'DECISION', 'EVIDENCE', 'SECURITY', 'SYSTEM', 'USER')", name="ck_audit_category"),
        CheckConstraint("security_level IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')", name="ck_security_level"),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"


class MLPrediction(Base, UUIDMixin, TimestampMixin):
    """ML prediction results entity"""
    __tablename__ = "ml_predictions"
    
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    
    # Prediction metadata
    service_name = Column(String(50), nullable=False, comment="ML service name")
    model_version = Column(String(50), nullable=False, comment="Model version used")
    prediction_type = Column(String(30), nullable=False, comment="Prediction type")
    
    # Input and output
    input_features = Column(JSON, nullable=False, comment="Input features")
    prediction_result = Column(JSON, nullable=False, comment="Prediction result")
    
    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True, comment="Processing time in milliseconds")
    confidence_score = Column(Float, nullable=True, comment="Prediction confidence")
    
    # Relationships
    case = relationship("Case")
    
    # Constraints
    __table_args__ = (
        Index("ix_ml_service_type", "service_name", "prediction_type"),
        Index("ix_ml_model_time", "model_version", "created_at"),
        CheckConstraint("prediction_type IN ('CLASSIFICATION', 'ANOMALY', 'ETA')", name="ck_prediction_type"),
    )
    
    def __repr__(self):
        return f"<MLPrediction(id={self.id}, service_name={self.service_name}, prediction_type={self.prediction_type})>"


class GuardrailEvent(Base, UUIDMixin, TimestampMixin):
    """Guardrail security events entity"""
    __tablename__ = "guardrail_events"
    
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    
    # Event information
    event_type = Column(String(50), nullable=False, index=True, comment="Guardrail event type")
    severity = Column(String(20), nullable=False, index=True, comment="Event severity")
    decision = Column(String(20), nullable=False, comment="Guardrail decision")
    
    # Context
    user_id = Column(String(255), nullable=True, comment="User ID")
    session_id = Column(String(100), nullable=True, comment="Session ID")
    source_ip = Column(String(45), nullable=True, comment="Source IP")
    
    # Event details
    description = Column(Text, nullable=False, comment="Event description")
    flags = Column(JSON, nullable=True, comment="Guardrail flags")
    redactions = Column(JSON, nullable=True, comment="PII redactions")
    
    # Processing
    guardrail_version = Column(String(50), nullable=True, comment="Guardrail version")
    processing_time_ms = Column(Integer, nullable=True, comment="Processing time")
    
    # Relationships
    case = relationship("Case")
    
    # Constraints
    __table_args__ = (
        Index("ix_guardrail_severity_time", "severity", "created_at"),
        Index("ix_guardrail_decision_time", "decision", "created_at"),
        CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_guardrail_severity"),
        CheckConstraint("decision IN ('ALLOW', 'REDACT', 'BLOCK', 'REQUIRE_HITL')", name="ck_guardrail_decision"),
    )
    
    def __repr__(self):
        return f"<GuardrailEvent(id={self.id}, event_type={self.event_type}, severity={self.severity})>"


class SystemConfiguration(Base, UUIDMixin, TimestampMixin, AuditMixin):
    """System configuration entity"""
    __tablename__ = "system_configurations"
    
    # Configuration identification
    config_key = Column(String(100), nullable=False, unique=True, comment="Configuration key")
    config_category = Column(String(50), nullable=False, index=True, comment="Configuration category")
    
    # Configuration value
    config_value = Column(JSON, nullable=False, comment="Configuration value")
    config_type = Column(String(20), nullable=False, comment="Configuration type")
    
    # Metadata
    description = Column(Text, nullable=True, comment="Configuration description")
    is_sensitive = Column(Boolean, default=False, comment="Whether configuration is sensitive")
    is_active = Column(Boolean, default=True, comment="Whether configuration is active")
    
    # Validation
    validation_schema = Column(JSON, nullable=True, comment="JSON schema for validation")
    
    # Constraints
    __table_args__ = (
        Index("ix_config_category_active", "config_category", "is_active"),
        CheckConstraint("config_type IN ('STRING', 'INTEGER', 'FLOAT', 'BOOLEAN', 'JSON', 'ARRAY')", name="ck_config_type"),
    )
    
    def __repr__(self):
        return f"<SystemConfiguration(id={self.id}, config_key={self.config_key})>"
