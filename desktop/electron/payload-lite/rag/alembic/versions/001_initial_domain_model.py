"""Initial domain model — 8 table multi-tenant RAG platform.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- Enum types ---
    sensitivity_enum = sa.Enum(
        "public", "internal", "confidential", "restricted",
        name="sensitivitylevel",
    )
    sensitivity_enum.create(op.get_bind(), checkfirst=True)

    source_type_enum = sa.Enum(
        "upload", "s3", "gcs", "azure_blob", "web_crawl", "api",
        name="sourcetype",
    )
    source_type_enum.create(op.get_bind(), checkfirst=True)

    document_status_enum = sa.Enum(
        "active", "archived", "deleted", name="documentstatus"
    )
    document_status_enum.create(op.get_bind(), checkfirst=True)

    version_status_enum = sa.Enum(
        "pending", "processing", "ready", "error", "superseded",
        name="versionstatus",
    )
    version_status_enum.create(op.get_bind(), checkfirst=True)

    job_status_enum = sa.Enum(
        "pending", "running", "completed", "failed", "cancelled",
        name="jobstatus",
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)

    # --- tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column("settings", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default=sa.text("'member'"), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # --- data_sources ---
    op.create_table(
        "data_sources",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("config", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_data_sources_tenant_id", "data_sources", ["tenant_id"])

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_source_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("source_uri", sa.String(2048)),
        sa.Column("author", sa.String(255)),
        sa.Column("sensitivity_level", sensitivity_enum, server_default=sa.text("'internal'"), nullable=False),
        sa.Column("language", sa.String(10), server_default=sa.text("'en'"), nullable=False),
        sa.Column("tags", sa.dialects.postgresql.ARRAY(sa.Text), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("metadata_", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", document_status_enum, server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_data_source_id", "documents", ["data_source_id"])
    op.create_index("ix_documents_tags", "documents", ["tags"], postgresql_using="gin")
    op.create_index("ix_documents_sensitivity", "documents", ["tenant_id", "sensitivity_level"])

    # --- document_versions ---
    op.create_table(
        "document_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("status", version_status_enum, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("metadata_", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("chunk_count", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_doc_version", "document_versions", ["document_id", "version_number"])
    op.create_index("ix_document_versions_tenant_id", "document_versions", ["tenant_id"])
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_checksum", "document_versions", ["checksum"])

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer),
        sa.Column("embedding", Vector(1536)),
        sa.Column("embedding_model", sa.String(128)),
        sa.Column("sensitivity_level", sensitivity_enum),
        sa.Column("language", sa.String(10)),
        sa.Column("tags", sa.dialects.postgresql.ARRAY(sa.Text)),
        sa.Column("metadata_", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_document_chunks_tenant_id", "document_chunks", ["tenant_id"])
    op.create_index("ix_document_chunks_version_id", "document_chunks", ["version_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_tags", "document_chunks", ["tags"], postgresql_using="gin")
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # --- ingestion_jobs ---
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", job_status_enum, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_number", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column("chunks_total", sa.Integer),
        sa.Column("chunks_processed", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata_", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ingestion_jobs_tenant_id", "ingestion_jobs", ["tenant_id"])
    op.create_index("ix_ingestion_jobs_version_id", "ingestion_jobs", ["version_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    # --- retrieval_traces ---
    op.create_table(
        "retrieval_traces",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("transformed_query", sa.Text),
        sa.Column("retrieval_strategy", sa.String(100)),
        sa.Column("top_k", sa.Integer),
        sa.Column("retrieved_chunks", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("answer_text", sa.Text),
        sa.Column("llm_model", sa.String(128)),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("retrieval_latency_ms", sa.Integer),
        sa.Column("generation_latency_ms", sa.Integer),
        sa.Column("feedback_score", sa.Float),
        sa.Column("metadata_", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_retrieval_traces_tenant_id", "retrieval_traces", ["tenant_id"])
    op.create_index("ix_retrieval_traces_user_id", "retrieval_traces", ["user_id"])
    op.create_index("ix_retrieval_traces_created_at", "retrieval_traces", ["created_at"])


def downgrade() -> None:
    op.drop_table("retrieval_traces")
    op.drop_table("ingestion_jobs")
    op.drop_table("document_chunks")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("data_sources")
    op.drop_table("users")
    op.drop_table("tenants")

    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS versionstatus")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS sensitivitylevel")
