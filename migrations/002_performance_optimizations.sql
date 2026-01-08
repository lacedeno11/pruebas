-- Performance optimization migration for DERCAS 01 Policy Validation Copilot
-- Adds additional indexes and constraints for optimal query performance

-- Additional composite indexes for complex queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_composite_status 
ON cases (status, priority, sla_target) 
WHERE status IN ('CREATED', 'INGESTED', 'ROUTING', 'RETRIEVING_POLICY', 'BUILDING_CHECKLIST', 'DECIDING', 'HITL_REVIEW');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_sla_monitoring 
ON cases (sla_target, status, priority) 
WHERE sla_target IS NOT NULL AND status NOT IN ('APPROVED', 'REJECTED', 'CLOSED');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_processing_time 
ON cases (processing_started_at, processing_completed_at, status);

-- Policy document performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policy_applicability 
ON policy_documents (insurer_id, status, effective_date, expiration_date) 
WHERE status = 'ACTIVE';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policy_plan_service 
ON policy_documents USING GIN (plan_ids, service_codes) 
WHERE status = 'ACTIVE';

-- Exception rules performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exception_applicability 
ON exception_rules (insurer_id, status, effective_date, expiration_date) 
WHERE status = 'APPROVED';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exception_scope 
ON exception_rules (customer_id, contract_id, plan_id) 
WHERE status = 'APPROVED';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exception_service_codes 
ON exception_rules USING GIN (service_codes) 
WHERE status = 'APPROVED';

-- ML score records performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ml_scores_composite 
ON ml_score_records (case_id, model_type, inference_timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ml_scores_latest 
ON ml_score_records (model_type, inference_timestamp DESC, case_id);

-- Decision records performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_decisions_composite 
ON decision_records (case_id, status, decided_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_decisions_hitl 
ON decision_records (requires_hitl, status, created_at) 
WHERE requires_hitl = TRUE;

-- HITL requests performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hitl_pending 
ON hitl_requests (assigned_to_role, priority, requested_at) 
WHERE responded_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hitl_workload 
ON hitl_requests (assigned_to_user, requested_at) 
WHERE responded_at IS NULL;

-- Audit trails performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_node_execution 
ON audit_trails (node_name, timestamp, case_id) 
WHERE node_name IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user_activity 
ON audit_trails (user_id, timestamp, event_type) 
WHERE user_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_export_tracking 
ON audit_trails (export_restricted, timestamp, user_id) 
WHERE export_restricted = TRUE;

-- External queries performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_external_query_monitoring 
ON external_queries (status, sent_at, timeout_at) 
WHERE status IN ('PENDING', 'IN_PROGRESS');

-- Notifications performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_pending 
ON notifications (status, priority, created_at) 
WHERE status = 'PENDING';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_delivery 
ON notifications (channel, status, retry_count) 
WHERE status IN ('PENDING', 'FAILED');

-- Partial indexes for active/pending records
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_active 
ON cases (case_id, status, last_activity_at) 
WHERE status NOT IN ('APPROVED', 'REJECTED', 'CLOSED');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policies_active 
ON policy_documents (doc_id, version, insurer_id) 
WHERE status = 'ACTIVE';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exceptions_active 
ON exception_rules (rule_id, insurer_id, usage_count) 
WHERE status = 'APPROVED';

-- JSON indexes for better performance on JSON queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_attachments 
ON cases USING GIN (attachments);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cases_context 
ON cases USING GIN (context);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_items 
ON evidence_packs USING GIN (items);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_checklist_items 
ON checklists USING GIN (items);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ml_input_features 
ON ml_score_records USING GIN (input_features);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ml_output_scores 
ON ml_score_records USING GIN (output_scores);

-- Add check constraints for data integrity
ALTER TABLE cases ADD CONSTRAINT chk_cases_priority 
CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'));

ALTER TABLE cases ADD CONSTRAINT chk_cases_status 
CHECK (status IN ('CREATED', 'INGESTED', 'ROUTING', 'RETRIEVING_POLICY', 'BUILDING_CHECKLIST', 'DECIDING', 'EXTERNAL_QUERY', 'HITL_REVIEW', 'APPROVED', 'OBSERVED', 'REJECTED', 'PENDIENTE_POLITICA', 'PENDIENTE_DATOS', 'PENDIENTE_ASEGURADORA', 'PENDIENTE_SISTEMA', 'CLOSED', 'ERROR'));

ALTER TABLE cases ADD CONSTRAINT chk_cases_processing_time 
CHECK (processing_completed_at IS NULL OR processing_completed_at >= processing_started_at);

ALTER TABLE policy_documents ADD CONSTRAINT chk_policy_status 
CHECK (status IN ('DRAFT', 'PENDING_QA', 'PENDING_APPROVAL', 'ACTIVE', 'DEPRECATED', 'ARCHIVED'));

ALTER TABLE policy_documents ADD CONSTRAINT chk_policy_validity 
CHECK (expiration_date IS NULL OR expiration_date > effective_date);

ALTER TABLE policy_documents ADD CONSTRAINT chk_policy_file_size 
CHECK (file_size > 0);

ALTER TABLE policy_documents ADD CONSTRAINT chk_policy_parsing_quality 
CHECK (parsing_quality >= 0.0 AND parsing_quality <= 1.0);

ALTER TABLE exception_rules ADD CONSTRAINT chk_exception_status 
CHECK (status IN ('PROPOSED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXPIRED', 'REVOKED'));

ALTER TABLE exception_rules ADD CONSTRAINT chk_exception_validity 
CHECK (expiration_date IS NULL OR expiration_date > effective_date);

ALTER TABLE exception_rules ADD CONSTRAINT chk_exception_usage_count 
CHECK (usage_count >= 0);

ALTER TABLE evidence_packs ADD CONSTRAINT chk_evidence_coverage_score 
CHECK (coverage_score >= 0.0 AND coverage_score <= 1.0);

ALTER TABLE ml_score_records ADD CONSTRAINT chk_ml_confidence 
CHECK (confidence >= 0.0 AND confidence <= 1.0);

ALTER TABLE ml_score_records ADD CONSTRAINT chk_ml_drift_score 
CHECK (drift_score IS NULL OR (drift_score >= 0.0 AND drift_score <= 1.0));

ALTER TABLE ml_score_records ADD CONSTRAINT chk_ml_processing_time 
CHECK (processing_time_ms IS NULL OR processing_time_ms >= 0);

ALTER TABLE decision_records ADD CONSTRAINT chk_decision_confidence 
CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0);

ALTER TABLE decision_records ADD CONSTRAINT chk_decision_anomaly_score 
CHECK (anomaly_score IS NULL OR (anomaly_score >= 0.0 AND anomaly_score <= 1.0));

ALTER TABLE decision_records ADD CONSTRAINT chk_decision_eta 
CHECK (eta_estimate IS NULL OR eta_estimate >= 0);

ALTER TABLE decision_records ADD CONSTRAINT chk_decision_timing 
CHECK (decided_at IS NULL OR decided_at >= created_at);

ALTER TABLE hitl_requests ADD CONSTRAINT chk_hitl_priority 
CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'));

ALTER TABLE hitl_requests ADD CONSTRAINT chk_hitl_timing 
CHECK (
    (assigned_at IS NULL OR assigned_at >= requested_at) AND
    (responded_at IS NULL OR responded_at >= requested_at)
);

ALTER TABLE external_queries ADD CONSTRAINT chk_external_query_status 
CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'TIMEOUT'));

ALTER TABLE external_queries ADD CONSTRAINT chk_external_query_retry_count 
CHECK (retry_count >= 0);

ALTER TABLE external_queries ADD CONSTRAINT chk_external_query_timing 
CHECK (
    (sent_at IS NULL OR sent_at >= created_at) AND
    (received_at IS NULL OR received_at >= sent_at) AND
    (timeout_at IS NULL OR timeout_at >= sent_at)
);

ALTER TABLE notifications ADD CONSTRAINT chk_notification_priority 
CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'));

ALTER TABLE notifications ADD CONSTRAINT chk_notification_status 
CHECK (status IN ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'CANCELLED'));

ALTER TABLE notifications ADD CONSTRAINT chk_notification_retry_count 
CHECK (retry_count >= 0);

ALTER TABLE notifications ADD CONSTRAINT chk_notification_timing 
CHECK (
    (sent_at IS NULL OR sent_at >= created_at) AND
    (delivered_at IS NULL OR delivered_at >= sent_at)
);

-- Add foreign key constraints with proper cascading
ALTER TABLE evidence_packs 
ADD CONSTRAINT fk_evidence_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE checklists 
ADD CONSTRAINT fk_checklist_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE ml_score_records 
ADD CONSTRAINT fk_ml_score_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE decision_records 
ADD CONSTRAINT fk_decision_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE guardrail_records 
ADD CONSTRAINT fk_guardrail_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE hitl_requests 
ADD CONSTRAINT fk_hitl_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE external_queries 
ADD CONSTRAINT fk_external_query_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE audit_trails 
ADD CONSTRAINT fk_audit_case 
FOREIGN KEY (case_id) REFERENCES cases(case_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- Create views for common queries
CREATE OR REPLACE VIEW v_active_cases AS
SELECT 
    c.*,
    CASE 
        WHEN c.sla_target IS NOT NULL AND c.sla_target <= NOW() + INTERVAL '1 hour' 
        THEN 'AT_RISK'
        WHEN c.sla_target IS NOT NULL AND c.sla_target <= NOW() + INTERVAL '4 hours'
        THEN 'WARNING'
        ELSE 'OK'
    END as sla_status,
    EXTRACT(EPOCH FROM (NOW() - c.created_at))/60 as age_minutes
FROM cases c
WHERE c.status NOT IN ('APPROVED', 'REJECTED', 'CLOSED');

CREATE OR REPLACE VIEW v_case_summary AS
SELECT 
    c.case_id,
    c.status,
    c.priority,
    c.insurer_id,
    c.created_at,
    c.sla_target,
    d.confidence_score,
    d.risk_level,
    d.requires_hitl,
    h.assigned_to_role as hitl_assigned_role,
    h.requested_at as hitl_requested_at,
    COUNT(a.id) as audit_events_count
FROM cases c
LEFT JOIN decision_records d ON c.case_id = d.case_id
LEFT JOIN hitl_requests h ON c.case_id = h.case_id AND h.responded_at IS NULL
LEFT JOIN audit_trails a ON c.case_id = a.case_id
GROUP BY c.case_id, c.status, c.priority, c.insurer_id, c.created_at, c.sla_target, 
         d.confidence_score, d.risk_level, d.requires_hitl, h.assigned_to_role, h.requested_at;

CREATE OR REPLACE VIEW v_policy_coverage AS
SELECT 
    p.insurer_id,
    p.status,
    COUNT(*) as policy_count,
    COUNT(CASE WHEN p.expiration_date IS NULL OR p.expiration_date > NOW() THEN 1 END) as active_policies,
    MIN(p.effective_date) as earliest_effective_date,
    MAX(p.effective_date) as latest_effective_date
FROM policy_documents p
GROUP BY p.insurer_id, p.status;

CREATE OR REPLACE VIEW v_exception_usage AS
SELECT 
    e.rule_id,
    e.insurer_id,
    e.rule_type,
    e.status,
    e.usage_count,
    e.last_used_at,
    CASE 
        WHEN e.expiration_date IS NOT NULL AND e.expiration_date <= NOW() THEN 'EXPIRED'
        WHEN e.status = 'APPROVED' AND (e.expiration_date IS NULL OR e.expiration_date > NOW()) THEN 'ACTIVE'
        ELSE e.status
    END as effective_status
FROM exception_rules e;

CREATE OR REPLACE VIEW v_ml_performance AS
SELECT 
    m.model_type,
    m.model_version,
    COUNT(*) as inference_count,
    AVG(m.confidence) as avg_confidence,
    AVG(m.processing_time_ms) as avg_processing_time_ms,
    COUNT(CASE WHEN m.fallback_used THEN 1 END) as fallback_count,
    MAX(m.inference_timestamp) as last_inference
FROM ml_score_records m
WHERE m.inference_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY m.model_type, m.model_version;

-- Add table statistics update
ANALYZE cases;
ANALYZE policy_documents;
ANALYZE exception_rules;
ANALYZE evidence_packs;
ANALYZE checklists;
ANALYZE ml_score_records;
ANALYZE decision_records;
ANALYZE guardrail_records;
ANALYZE hitl_requests;
ANALYZE external_queries;
ANALYZE audit_trails;
ANALYZE system_config;
ANALYZE model_versions;
ANALYZE notifications;

-- Add comments for the new objects
COMMENT ON INDEX idx_cases_composite_status IS 'Composite index for active case monitoring';
COMMENT ON INDEX idx_policy_applicability IS 'Index for finding applicable policies';
COMMENT ON INDEX idx_exception_applicability IS 'Index for finding applicable exceptions';
COMMENT ON INDEX idx_ml_scores_composite IS 'Composite index for ML score queries';
COMMENT ON INDEX idx_hitl_pending IS 'Index for pending HITL requests';
COMMENT ON INDEX idx_audit_node_execution IS 'Index for LangGraph node execution tracking';

COMMENT ON VIEW v_active_cases IS 'View of active cases with SLA status';
COMMENT ON VIEW v_case_summary IS 'Summary view of cases with key metrics';
COMMENT ON VIEW v_policy_coverage IS 'Policy coverage statistics by insurer';
COMMENT ON VIEW v_exception_usage IS 'Exception rule usage and status';
COMMENT ON VIEW v_ml_performance IS 'ML model performance metrics';
