-- DERCAS-ONCO-XAI V1 PostgreSQL Initialization Script
-- Creates databases and users for the oncology platform

-- Create additional databases if needed
-- Main database is created by POSTGRES_DB environment variable

-- Create extensions that might be needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas for different services (optional, services can create their own)
-- This is mainly for organization and future multi-tenancy

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE oncology_db TO oncology_user;

-- Create audit schema for centralized audit logging
CREATE SCHEMA IF NOT EXISTS audit;
GRANT USAGE ON SCHEMA audit TO oncology_user;
GRANT CREATE ON SCHEMA audit TO oncology_user;

-- Create ontology schema for ontology management
CREATE SCHEMA IF NOT EXISTS ontology;
GRANT USAGE ON SCHEMA ontology TO oncology_user;
GRANT CREATE ON SCHEMA ontology TO oncology_user;

-- Set default search path
ALTER USER oncology_user SET search_path = public, audit, ontology;

-- Log initialization completion
DO $$
BEGIN
    RAISE NOTICE 'DERCAS-ONCO-XAI V1 database initialization completed successfully';
END $$;
