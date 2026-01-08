-- Initial schema migration for DERCAS 01 Policy Validation Copilot
-- Creates all tables for the system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cases table
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Business identifiers
    case_id VARCHAR(255) UNIQUE NOT NULL,
    crm_ticket_id VARCHAR(255),
    
    -- Customer and contract information
    customer_id VARCHAR(255),
    contract_id VARCHAR(255),
    insurer_id VARCHAR(255) NOT NULL,
    plan_id VARCHAR(255) NOT NULL,
    
    -- Service information
    service_code VARCHAR(255),
    service_description TEXT,
    service_date TIMESTAMP WITH TIME ZONE,
    provider_id VARCHAR(255),
    
    -- Case metadata
    priority VARCHAR(50) NOT NULL DEFAULT 'MEDIUM',
    sla_target TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    assigned_queue VARCHAR(100) NOT NULL DEFAULT 'AUTO_PROCESSING',
    
    -- JSON fields
    attachments JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    
    -- Processing metadata
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE
);

-- Policy documents table
CREATE TABLE policy_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Document identifiers
    doc_id VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    checksum VARCHAR(255) NOT NULL,
    
    -- Document metadata
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'POLICY',
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    
    -- Scope and applicability
    insurer_id VARCHAR(255) NOT NULL,
    plan_ids JSONB DEFAULT '[]'::jsonb,
    service_codes JSONB DEFAULT '[]'::jsonb,
    
    -- Validity period
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiration_date TIMESTAMP WITH TIME ZONE,
    
    -- Content and processing
    file_path VARCHAR(1000) NOT NULL,
    file_size INTEGER NOT NULL,
    parsing_quality REAL DEFAULT 0.0,
    
    -- Approval workflow
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- Priority for conflict resolution
    priority INTEGER DEFAULT 0,
    
    CONSTRAINT uq_policy_doc_version UNIQUE (doc_id, version)
);

-- Exception rules table
CREATE TABLE exception_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Rule identifier
    rule_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Scope
    customer_id VARCHAR(255),
    contract_id VARCHAR(255),
    insurer_id VARCHAR(255) NOT NULL,
    plan_id VARCHAR(255),
    service_codes JSONB DEFAULT '[]'::jsonb,
    
    -- Rule definition
    rule_type VARCHAR(255) NOT NULL,
    rule_description TEXT NOT NULL,
    rule_logic JSONB NOT NULL,
    
    -- Validity
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiration_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'PROPOSED',
    
    -- Evidence and justification
    evidence_links JSONB DEFAULT '[]'::jsonb,
    justification TEXT NOT NULL,
    
    -- Approval workflow
    proposed_by VARCHAR(255) NOT NULL,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Evidence packs table
CREATE TABLE evidence_packs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Evidence items (JSON array)
    items JSONB DEFAULT '[]'::jsonb,
    coverage_score REAL DEFAULT 0.0,
    conflicts_detected BOOLEAN DEFAULT FALSE,
    missing_sources JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    retrieval_query TEXT,
    retrieval_timestamp TIMESTAMP WITH TIME ZONE,
    retrieval_model_version VARCHAR(100)
);

-- Checklists table
CREATE TABLE checklists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Checklist data
    items JSONB DEFAULT '[]'::jsonb,
    missing_fields JSONB DEFAULT '[]'::jsonb,
    rule_ids_applied JSONB DEFAULT '[]'::jsonb,
    
    -- Evaluation metadata
    evaluation_timestamp TIMESTAMP WITH TIME ZONE,
    rule_set_version VARCHAR(100),
    evaluation_log JSONB DEFAULT '{}'::jsonb,
    
    -- Summary metrics
    total_items INTEGER DEFAULT 0,
    passed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    missing_items INTEGER DEFAULT 0
);

-- ML score records table
CREATE TABLE ml_score_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Model information
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    
    -- Input and output
    input_features JSONB NOT NULL,
    output_scores JSONB NOT NULL,
    
    -- Metadata
    inference_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    processing_time_ms REAL,
    
    -- Quality metrics
    confidence REAL DEFAULT 0.0,
    drift_score REAL,
    
    -- Fallback information
    fallback_used BOOLEAN DEFAULT FALSE,
    fallback_reason VARCHAR(500)
);

-- Decision records table
CREATE TABLE decision_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Decision status
    status VARCHAR(50) NOT NULL,
    
    -- Decision metrics
    confidence_score REAL NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    anomaly_score REAL,
    eta_estimate INTEGER,
    
    -- Decision logic
    next_actions JSONB DEFAULT '[]'::jsonb,
    thresholds_version VARCHAR(100) NOT NULL,
    
    -- Supporting data references
    checklist_id UUID REFERENCES checklists(id),
    evidence_pack_id UUID REFERENCES evidence_packs(id),
    ml_scores JSONB DEFAULT '[]'::jsonb,
    
    -- HITL information
    requires_hitl BOOLEAN DEFAULT FALSE,
    hitl_reasons JSONB DEFAULT '[]'::jsonb,
    
    -- Final decision (if completed)
    final_decision VARCHAR(50),
    decision_rationale TEXT,
    decided_by VARCHAR(255),
    decided_at TIMESTAMP WITH TIME ZONE
);

-- Guardrail records table
CREATE TABLE guardrail_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Guardrail checks
    checks JSONB DEFAULT '[]'::jsonb,
    
    -- Overall result
    overall_action VARCHAR(50) NOT NULL,
    blocked_reasons JSONB DEFAULT '[]'::jsonb,
    redactions_applied JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    check_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    guardrails_version VARCHAR(100) NOT NULL
);

-- HITL requests table
CREATE TABLE hitl_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Request details
    reasons JSONB NOT NULL,
    assigned_to_role VARCHAR(50) NOT NULL,
    assigned_to_user VARCHAR(255),
    priority VARCHAR(50) NOT NULL DEFAULT 'MEDIUM',
    
    -- Questions and context
    questions JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    
    -- Response
    answers JSONB DEFAULT '[]'::jsonb,
    decision VARCHAR(50),
    notes TEXT,
    
    -- Workflow
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE,
    responded_at TIMESTAMP WITH TIME ZONE,
    responded_by VARCHAR(255)
);

-- External queries table
CREATE TABLE external_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Query details
    insurer_id VARCHAR(255) NOT NULL,
    query_type VARCHAR(255) NOT NULL,
    query_data JSONB NOT NULL,
    channel VARCHAR(255) NOT NULL,
    
    -- Response
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    response_data JSONB,
    response_checksum VARCHAR(255),
    
    -- Timing
    sent_at TIMESTAMP WITH TIME ZONE,
    received_at TIMESTAMP WITH TIME ZONE,
    timeout_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);

-- Audit trails table
CREATE TABLE audit_trails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Foreign key to case
    case_id VARCHAR(255) NOT NULL REFERENCES cases(case_id),
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    
    -- LangGraph node execution
    node_name VARCHAR(255),
    node_input JSONB,
    node_output JSONB,
    execution_time_ms REAL,
    
    -- Versioning
    model_versions JSONB DEFAULT '{}'::jsonb,
    policy_versions JSONB DEFAULT '{}'::jsonb,
    rule_versions JSONB DEFAULT '{}'::jsonb,
    
    -- Access control
    access_level VARCHAR(100),
    export_restricted BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    correlation_id VARCHAR(255)
);

-- System configuration table
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    config_type VARCHAR(100) NOT NULL DEFAULT 'GENERAL',
    is_sensitive BOOLEAN DEFAULT FALSE
);

-- Model versions table
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    model_id VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(100) NOT NULL,
    
    -- Model metadata
    name VARCHAR(500) NOT NULL,
    description TEXT,
    algorithm VARCHAR(255),
    
    -- Performance metrics
    accuracy REAL,
    precision REAL,
    recall REAL,
    f1_score REAL,
    
    -- Deployment info
    deployed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deployed_by VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    
    -- Training info
    training_data_size INTEGER,
    training_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Configuration
    hyperparameters JSONB DEFAULT '{}'::jsonb,
    feature_importance JSONB,
    
    CONSTRAINT uq_model_version UNIQUE (model_id, version)
);

-- Notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    notification_type VARCHAR(100) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    
    -- Related entities
    case_id VARCHAR(255),
    related_entity_type VARCHAR(100),
    related_entity_id VARCHAR(255),
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- Metadata
    priority VARCHAR(50) DEFAULT 'MEDIUM',
    channel VARCHAR(100) DEFAULT 'EMAIL',
    retry_count INTEGER DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX idx_cases_case_id ON cases(case_id);
CREATE INDEX idx_cases_crm_ticket_id ON cases(crm_ticket_id);
CREATE INDEX idx_cases_customer_id ON cases(customer_id);
CREATE INDEX idx_cases_contract_id ON cases(contract_id);
CREATE INDEX idx_cases_insurer_id ON cases(insurer_id);
CREATE INDEX idx_cases_plan_id ON cases(plan_id);
CREATE INDEX idx_cases_service_code ON cases(service_code);
CREATE INDEX idx_cases_service_date ON cases(service_date);
CREATE INDEX idx_cases_provider_id ON cases(provider_id);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_sla_target ON cases(sla_target);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_assigned_queue ON cases(assigned_queue);
CREATE INDEX idx_cases_processing_started_at ON cases(processing_started_at);
CREATE INDEX idx_cases_processing_completed_at ON cases(processing_completed_at);
CREATE INDEX idx_cases_last_activity_at ON cases(last_activity_at);

-- Composite indexes for common queries
CREATE INDEX idx_case_insurer_plan ON cases(insurer_id, plan_id);
CREATE INDEX idx_case_status_priority ON cases(status, priority);

-- Policy documents indexes
CREATE INDEX idx_policy_doc_id ON policy_documents(doc_id);
CREATE INDEX idx_policy_status ON policy_documents(status);
CREATE INDEX idx_policy_insurer_id ON policy_documents(insurer_id);
CREATE INDEX idx_policy_effective_date ON policy_documents(effective_date);
CREATE INDEX idx_policy_insurer_status ON policy_documents(insurer_id, status);

-- Exception rules indexes
CREATE INDEX idx_exception_rule_id ON exception_rules(rule_id);
CREATE INDEX idx_exception_insurer_id ON exception_rules(insurer_id);
CREATE INDEX idx_exception_status ON exception_rules(status);
CREATE INDEX idx_exception_effective_date ON exception_rules(effective_date);
CREATE INDEX idx_exception_customer_id ON exception_rules(customer_id);
CREATE INDEX idx_exception_insurer_status ON exception_rules(insurer_id, status);

-- Evidence packs indexes
CREATE INDEX idx_evidence_case_id ON evidence_packs(case_id);

-- Checklists indexes
CREATE INDEX idx_checklist_case_id ON checklists(case_id);

-- ML score records indexes
CREATE INDEX idx_ml_score_case_id ON ml_score_records(case_id);
CREATE INDEX idx_ml_score_model_type ON ml_score_records(model_type);
CREATE INDEX idx_ml_score_inference_time ON ml_score_records(inference_timestamp);

-- Decision records indexes
CREATE INDEX idx_decision_case_id ON decision_records(case_id);
CREATE INDEX idx_decision_status ON decision_records(status);
CREATE INDEX idx_decision_confidence ON decision_records(confidence_score);
CREATE INDEX idx_decision_risk ON decision_records(risk_level);

-- Guardrail records indexes
CREATE INDEX idx_guardrail_case_id ON guardrail_records(case_id);
CREATE INDEX idx_guardrail_check_timestamp ON guardrail_records(check_timestamp);

-- HITL requests indexes
CREATE INDEX idx_hitl_case_id ON hitl_requests(case_id);
CREATE INDEX idx_hitl_assigned_role ON hitl_requests(assigned_to_role);
CREATE INDEX idx_hitl_requested_at ON hitl_requests(requested_at);

-- External queries indexes
CREATE INDEX idx_external_query_case_id ON external_queries(case_id);
CREATE INDEX idx_external_query_status ON external_queries(status);
CREATE INDEX idx_external_query_insurer ON external_queries(insurer_id);

-- Audit trails indexes
CREATE INDEX idx_audit_case_id ON audit_trails(case_id);
CREATE INDEX idx_audit_event_type ON audit_trails(event_type);
CREATE INDEX idx_audit_timestamp ON audit_trails(timestamp);
CREATE INDEX idx_audit_correlation ON audit_trails(correlation_id);
CREATE INDEX idx_audit_node_name ON audit_trails(node_name);
CREATE INDEX idx_audit_user_id ON audit_trails(user_id);
CREATE INDEX idx_audit_session_id ON audit_trails(session_id);

-- Composite audit index
CREATE INDEX idx_audit_trails_composite ON audit_trails(case_id, event_type, timestamp);

-- System config indexes
CREATE INDEX idx_config_key ON system_config(key);
CREATE INDEX idx_config_type ON system_config(config_type);

-- Model versions indexes
CREATE INDEX idx_model_id ON model_versions(model_id);
CREATE INDEX idx_model_type ON model_versions(model_type);
CREATE INDEX idx_model_type_status ON model_versions(model_type, status);

-- Notifications indexes
CREATE INDEX idx_notification_type ON notifications(notification_type);
CREATE INDEX idx_notification_recipient ON notifications(recipient);
CREATE INDEX idx_notification_status ON notifications(status);
CREATE INDEX idx_notification_type_status ON notifications(notification_type, status);

-- Add comments to tables
COMMENT ON TABLE cases IS 'Core cases table for policy validation requests';
COMMENT ON TABLE policy_documents IS 'Policy documents with versioning and metadata';
COMMENT ON TABLE exception_rules IS 'Exception rules with approval workflows';
COMMENT ON TABLE evidence_packs IS 'Evidence collections for case decisions';
COMMENT ON TABLE checklists IS 'Rule evaluation checklists';
COMMENT ON TABLE ml_score_records IS 'ML model inference results';
COMMENT ON TABLE decision_records IS 'Decision orchestration records';
COMMENT ON TABLE guardrail_records IS 'Security and compliance checks';
COMMENT ON TABLE hitl_requests IS 'Human-in-the-loop review requests';
COMMENT ON TABLE external_queries IS 'External insurance company queries';
COMMENT ON TABLE audit_trails IS 'Complete audit trail for all operations';
COMMENT ON TABLE system_config IS 'System configuration key-value store';
COMMENT ON TABLE model_versions IS 'ML model version tracking';
COMMENT ON TABLE notifications IS 'System notifications and alerts';
