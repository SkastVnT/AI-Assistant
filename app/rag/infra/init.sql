-- =============================================================================
-- RAG Platform — Initial Schema
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Enum types
-- =============================================================================

CREATE TYPE sensitivity_level_enum AS ENUM ('public', 'internal', 'confidential', 'restricted');
CREATE TYPE source_type_enum AS ENUM ('upload', 's3', 'gcs', 'google_drive', 'web_crawl', 'api');
CREATE TYPE document_status_enum AS ENUM ('active', 'archived', 'deleted');
CREATE TYPE version_status_enum AS ENUM ('pending', 'processing', 'ready', 'error', 'superseded');
CREATE TYPE job_status_enum AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled');

-- =============================================================================
-- Tenants
-- =============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(63) NOT NULL UNIQUE,
    settings JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants (slug);

-- =============================================================================
-- Users
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(320) NOT NULL,
    display_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email)
);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users (tenant_id);

-- =============================================================================
-- Data Sources
-- =============================================================================

CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type source_type_enum NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_data_sources_tenant_id ON data_sources (tenant_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_source_type ON data_sources (source_type);

-- =============================================================================
-- Documents (logical identity)
-- =============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    data_source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    title VARCHAR(1024) NOT NULL,
    source_uri TEXT,
    author VARCHAR(255),
    sensitivity_level sensitivity_level_enum NOT NULL DEFAULT 'internal',
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    tags TEXT[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    status document_status_enum NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_data_source_id ON documents (data_source_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_sensitivity ON documents (sensitivity_level);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents (language);

-- =============================================================================
-- Document Versions (immutable snapshots)
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    storage_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type VARCHAR(255),
    file_size_bytes INTEGER,
    checksum VARCHAR(128) NOT NULL,
    status version_status_enum NOT NULL DEFAULT 'pending',
    error_message TEXT,
    raw_text TEXT,
    parsed_content JSONB,
    metadata JSONB NOT NULL DEFAULT '{}',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_docversion_doc_ver UNIQUE (document_id, version_number)
);
CREATE INDEX IF NOT EXISTS idx_docversions_tenant_id ON document_versions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_docversions_document_id ON document_versions (document_id);
CREATE INDEX IF NOT EXISTS idx_docversions_checksum ON document_versions (checksum);
CREATE INDEX IF NOT EXISTS idx_docversions_status ON document_versions (status);

-- =============================================================================
-- Document Chunks (atomic retrieval units)
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    embedding vector(1536),
    embedding_model VARCHAR(100),
    embedding_version VARCHAR(50),
    sensitivity_level sensitivity_level_enum,
    language VARCHAR(10),
    tags TEXT[],
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chunks_tenant_id ON document_chunks (tenant_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_version_id ON document_chunks (version_id);
CREATE INDEX IF NOT EXISTS idx_chunks_sensitivity ON document_chunks (sensitivity_level);
CREATE INDEX IF NOT EXISTS idx_chunks_language ON document_chunks (language);
CREATE INDEX IF NOT EXISTS idx_chunks_tags ON document_chunks USING GIN (tags);
-- HNSW vector index (works well even on empty tables, unlike ivfflat)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =============================================================================
-- Ingestion Jobs
-- =============================================================================

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    status job_status_enum NOT NULL DEFAULT 'queued',
    attempt_number SMALLINT NOT NULL DEFAULT 1,
    chunks_total INTEGER,
    chunks_processed INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_id ON ingestion_jobs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_version_id ON ingestion_jobs (version_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON ingestion_jobs (status);

-- =============================================================================
-- Retrieval Traces (RAGOps observability)
-- =============================================================================

CREATE TABLE IF NOT EXISTS retrieval_traces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    transformed_query TEXT,
    retrieval_strategy VARCHAR(50),
    top_k SMALLINT,
    retrieved_chunks JSONB NOT NULL DEFAULT '[]',
    answer_text TEXT,
    llm_model VARCHAR(100),
    latency_ms INTEGER,
    retrieval_latency_ms INTEGER,
    generation_latency_ms INTEGER,
    feedback_score FLOAT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_traces_tenant_id ON retrieval_traces (tenant_id);
CREATE INDEX IF NOT EXISTS idx_traces_user_id ON retrieval_traces (user_id);
CREATE INDEX IF NOT EXISTS idx_traces_created_at ON retrieval_traces (created_at);

-- =============================================================================
-- Auto-update triggers for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'tenants', 'users', 'data_sources', 'documents',
        'document_versions', 'document_chunks', 'ingestion_jobs', 'retrieval_traces'
    ] LOOP
        EXECUTE format(
            'CREATE OR REPLACE TRIGGER %I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;
