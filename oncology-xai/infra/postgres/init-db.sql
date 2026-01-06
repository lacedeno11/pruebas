-- DERCAS-ONCO-XAI V1 - PostgreSQL Initialization Script
-- Database initialization for the oncology platform

-- Create additional databases for testing and development
CREATE DATABASE oncology_xai_test;
CREATE DATABASE oncology_xai_dev;

-- Create extensions that will be needed by the application
\c oncology_xai;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full-text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enable case-insensitive text operations
CREATE EXTENSION IF NOT EXISTS "citext";

-- Enable cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application-specific schemas
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE SCHEMA IF NOT EXISTS clinical;

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON SCHEMA public TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA audit TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA ontology TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA clinical TO oncology_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO oncology_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON TABLES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON SEQUENCES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON FUNCTIONS TO oncology_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA ontology GRANT ALL ON TABLES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ontology GRANT ALL ON SEQUENCES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ontology GRANT ALL ON FUNCTIONS TO oncology_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA clinical GRANT ALL ON TABLES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA clinical GRANT ALL ON SEQUENCES TO oncology_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA clinical GRANT ALL ON FUNCTIONS TO oncology_user;

-- Create custom types for the application
CREATE TYPE case_status AS ENUM ('CREATED', 'READY', 'PROCESSING', 'REVIEW_REQUIRED', 'CLOSED');
CREATE TYPE job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE pattern_type AS ENUM ('lepidic', 'acinar', 'papillary', 'micropapillary', 'solid');
CREATE TYPE mutation_type AS ENUM ('EGFR', 'KRAS', 'TP53');
CREATE TYPE mutation_status AS ENUM ('POS', 'NEG', 'INCONCLUSIVE');
CREATE TYPE ontology_name AS ENUM ('NCIt', 'MONDO', 'SO');

-- Create audit trigger function for tracking changes
CREATE OR REPLACE FUNCTION audit.audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit.audit_log (
            table_name,
            operation,
            old_values,
            changed_by,
            changed_at
        ) VALUES (
            TG_TABLE_NAME,
            TG_OP,
            row_to_json(OLD),
            current_user,
            now()
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.audit_log (
            table_name,
            operation,
            old_values,
            new_values,
            changed_by,
            changed_at
        ) VALUES (
            TG_TABLE_NAME,
            TG_OP,
            row_to_json(OLD),
            row_to_json(NEW),
            current_user,
            now()
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit.audit_log (
            table_name,
            operation,
            new_values,
            changed_by,
            changed_at
        ) VALUES (
            TG_TABLE_NAME,
            TG_OP,
            row_to_json(NEW),
            current_user,
            now()
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create indexes for audit log
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit.audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit.audit_log(changed_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_by ON audit.audit_log(changed_by);

-- Set up the test database
\c oncology_xai_test;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE SCHEMA IF NOT EXISTS clinical;

GRANT ALL PRIVILEGES ON SCHEMA public TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA audit TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA ontology TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA clinical TO oncology_user;

-- Create the same custom types for test database
CREATE TYPE case_status AS ENUM ('CREATED', 'READY', 'PROCESSING', 'REVIEW_REQUIRED', 'CLOSED');
CREATE TYPE job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE pattern_type AS ENUM ('lepidic', 'acinar', 'papillary', 'micropapillary', 'solid');
CREATE TYPE mutation_type AS ENUM ('EGFR', 'KRAS', 'TP53');
CREATE TYPE mutation_status AS ENUM ('POS', 'NEG', 'INCONCLUSIVE');
CREATE TYPE ontology_name AS ENUM ('NCIt', 'MONDO', 'SO');

-- Set up the development database
\c oncology_xai_dev;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE SCHEMA IF NOT EXISTS clinical;

GRANT ALL PRIVILEGES ON SCHEMA public TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA audit TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA ontology TO oncology_user;
GRANT ALL PRIVILEGES ON SCHEMA clinical TO oncology_user;

-- Create the same custom types for dev database
CREATE TYPE case_status AS ENUM ('CREATED', 'READY', 'PROCESSING', 'REVIEW_REQUIRED', 'CLOSED');
CREATE TYPE job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE pattern_type AS ENUM ('lepidic', 'acinar', 'papillary', 'micropapillary', 'solid');
CREATE TYPE mutation_type AS ENUM ('EGFR', 'KRAS', 'TP53');
CREATE TYPE mutation_status AS ENUM ('POS', 'NEG', 'INCONCLUSIVE');
CREATE TYPE ontology_name AS ENUM ('NCIt', 'MONDO', 'SO');

-- Return to main database
\c oncology_xai;

-- Log completion
SELECT 'PostgreSQL initialization completed successfully' AS status;
