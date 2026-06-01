"""create rag_image_chunks with CLIP pgvector

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-01
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match CLIP_EMBED_DIM default (ViT-B/32 → 512). Pinned as a constant so
# the migration stays reproducible even if the env var changes later.
CLIP_DIM = 512


def upgrade() -> None:
    # pgvector extension already created by 0001; CREATE IF NOT EXISTS is safe.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "rag_image_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("rag_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "object_path",
            sa.Text(),
            nullable=True,
            comment="MinIO/S3 object key of the image",
        ),
        sa.Column(
            "caption", sa.Text(), nullable=True, comment="Optional caption / alt text"
        ),
        sa.Column("embedding", Vector(CLIP_DIM), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_rag_image_chunks_embedding_hnsw",
        "rag_image_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_image_chunks_embedding_hnsw", table_name="rag_image_chunks"
    )
    op.drop_table("rag_image_chunks")
