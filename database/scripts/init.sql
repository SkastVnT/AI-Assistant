-- ============================================================================
-- AI-Assistant Database Initialization Script
-- ============================================================================
-- This script runs automatically when PostgreSQL container is first created
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create database if not exists (already created by POSTGRES_DB env var)
-- This is just for documentation

-- Set timezone
SET timezone = 'UTC';

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'AI-Assistant database initialized successfully';
    RAISE NOTICE 'PostgreSQL version: %', version();
    RAISE NOTICE 'Current database: %', current_database();
    RAISE NOTICE 'Current user: %', current_user();
END $$;
