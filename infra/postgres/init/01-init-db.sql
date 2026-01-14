-- DERCAS-ONCO-XAI Database Initialization Script
-- This script creates the initial database structure and users

-- Create additional databases if needed
-- CREATE DATABASE dercas_onco_xai_test;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas for different services
CREATE SCHEMA IF NOT EXISTS case_service;
CREATE SCHEMA IF NOT EXISTS image_service;
CREATE SCHEMA IF NOT EXISTS inference_service;
CREATE SCHEMA IF NOT EXISTS ehr_service;
CREATE SCHEMA IF NOT EXISTS graph_service;
CREATE SCHEMA IF NOT EXISTS ontology_admin_service;
CREATE SCHEMA IF NOT EXISTS audit_service;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA case_service TO dercas_user;
GRANT ALL PRIVILEGES ON SCHEMA image_service TO dercas_user;
GRANT ALL PRIVILEGES ON SCHEMA inference_service TO dercas_user;
GRANT ALL PRIVILEGES ON SCHEMA ehr_service TO dercas_user;
GRANT ALL PRIVILEGES ON SCHEMA graph_service TO dercas_user;
GRANT ALL PRIVILEGES ON SCHEMA ontology_admin_service TO dercas_user;
GRANT ALL PRIVILEGES ON SCHEMA audit_service TO dercas_user;

-- Set default search path
ALTER USER dercas_user SET search_path = public, case_service, image_service, inference_service, ehr_service, graph_service, ontology_admin_service, audit_service;
