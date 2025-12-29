-- Initialize PostgreSQL schemas for oncology-xai services
-- Each service will manage its own migrations, but we create schemas upfront

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE oncology_xai TO oncology;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL initialized for oncology-xai';
END $$;
