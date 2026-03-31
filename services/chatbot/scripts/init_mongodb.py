"""
MongoDB Initializer for ChatBot Service

Idempotent script: safe to re-run at any time.
  - Creates collections only if they don't exist.
  - Creates indexes only if they don't exist (PyMongo no-ops duplicates).
  - No ObjectId validators -- all document IDs are string UUIDs.

Canonical collections:
  1. conversations
  2. messages
  3. learning_data
  4. rag_documents
  5. rag_chunks
  6. rag_ingestion_jobs

Usage:
    python scripts/init_mongodb.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import ASCENDING, DESCENDING, IndexModel
from config.mongodb_config import get_db, test_connection, DATABASE_NAME


# ============================================================================
# Schemas (JSON Schema validators)
# ============================================================================

SCHEMAS = {
    "conversations": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "title", "model", "created_at"],
            "properties": {
                "_id":           {"bsonType": "string", "description": "UUID v4"},
                "user_id":       {"bsonType": "string"},
                "title":         {"bsonType": "string"},
                "model":         {"bsonType": "string"},
                "session_id":    {"bsonType": "string"},
                "is_archived":   {"bsonType": "bool"},
                "is_deleted":    {"bsonType": "bool"},
                "message_count": {"bsonType": "int", "minimum": 0},
                "metadata":      {"bsonType": "object"},
                "created_at":    {"bsonType": "date"},
                "updated_at":    {"bsonType": "date"},
            },
        }
    },
    "messages": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["conversation_id", "role", "content", "created_at"],
            "properties": {
                "_id":             {"bsonType": "string", "description": "UUID v4"},
                "conversation_id": {"bsonType": "string", "description": "UUID v4"},
                "role":            {"enum": ["user", "assistant", "system"]},
                "content":         {"bsonType": "string"},
                "metadata":        {"bsonType": "object"},
                "images":          {"bsonType": "array"},
                "tokens":          {"bsonType": ["int", "null"]},
                "is_edited":       {"bsonType": "bool"},
                "edit_history":    {"bsonType": "array"},
                "created_at":      {"bsonType": "date"},
                "updated_at":      {"bsonType": "date"},
            },
        }
    },
    "learning_data": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["source", "category", "data", "created_at"],
            "properties": {
                "_id":              {"bsonType": "string", "description": "UUID v4"},
                "source":           {"bsonType": "string"},
                "category":         {"bsonType": "string"},
                "data":             {"bsonType": "object"},
                "quality_score":    {"bsonType": "double"},
                "is_approved":      {"bsonType": "bool"},
                "created_at":       {"bsonType": "date"},
                "reviewed_at":      {"bsonType": ["date", "null"]},
                "rejection_reason": {"bsonType": ["string", "null"]},
            },
        }
    },
    "rag_documents": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["tenant_id", "document_id", "title", "source_type", "status", "created_at"],
            "properties": {
                "_id":         {"bsonType": "string", "description": "UUID v4"},
                "tenant_id":   {"bsonType": "string"},
                "document_id": {"bsonType": "string"},
                "title":       {"bsonType": "string"},
                "source_type": {"bsonType": "string"},
                "source_uri":  {"bsonType": ["string", "null"]},
                "mime_type":   {"bsonType": ["string", "null"]},
                "object_path": {"bsonType": ["string", "null"]},
                "status":      {"bsonType": "string"},
                "metadata":    {"bsonType": "object"},
                "created_at":  {"bsonType": "date"},
                "updated_at":  {"bsonType": "date"},
            },
        }
    },
    "rag_chunks": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["tenant_id", "document_id", "chunk_id", "chunk_index", "content", "created_at"],
            "properties": {
                "_id":         {"bsonType": "string", "description": "UUID v4"},
                "tenant_id":   {"bsonType": "string"},
                "document_id": {"bsonType": "string"},
                "chunk_id":    {"bsonType": "string"},
                "chunk_index": {"bsonType": "int", "minimum": 0},
                "content":     {"bsonType": "string"},
                "embedding":   {"bsonType": "array"},
                "metadata":    {"bsonType": "object"},
                "created_at":  {"bsonType": "date"},
            },
        }
    },
    "rag_ingestion_jobs": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["job_id", "tenant_id", "document_id", "filename", "status", "started_at"],
            "properties": {
                "_id":           {"bsonType": "string", "description": "UUID v4"},
                "job_id":        {"bsonType": "string"},
                "tenant_id":     {"bsonType": "string"},
                "document_id":   {"bsonType": "string"},
                "filename":      {"bsonType": "string"},
                "status":        {"bsonType": "string"},
                "steps":         {"bsonType": "object"},
                "num_chunks":    {"bsonType": "int", "minimum": 0},
                "error_message": {"bsonType": ["string", "null"]},
                "started_at":    {"bsonType": "date"},
                "finished_at":   {"bsonType": ["date", "null"]},
            },
        }
    },
}


# ============================================================================
# Indexes
# ============================================================================

INDEXES = {
    "conversations": [
        IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
        IndexModel([("session_id", ASCENDING)], unique=True, sparse=True),
        IndexModel([("is_archived", ASCENDING)]),
        IndexModel([("is_deleted", ASCENDING)]),
    ],
    "messages": [
        IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)]),
        IndexModel([("role", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ],
    "learning_data": [
        IndexModel([("source", ASCENDING)]),
        IndexModel([("category", ASCENDING)]),
        IndexModel([("quality_score", DESCENDING)]),
        IndexModel([("is_approved", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ],
    "rag_documents": [
        IndexModel([("tenant_id", ASCENDING), ("document_id", ASCENDING)], unique=True),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ],
    "rag_chunks": [
        IndexModel([("tenant_id", ASCENDING), ("document_id", ASCENDING)]),
        IndexModel([("chunk_id", ASCENDING)], unique=True),
        IndexModel([("chunk_index", ASCENDING)]),
    ],
    "rag_ingestion_jobs": [
        IndexModel([("job_id", ASCENDING)], unique=True),
        IndexModel([("tenant_id", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("started_at", DESCENDING)]),
    ],
}


# ============================================================================
# Helpers
# ============================================================================

def _ensure_collection(db, name, validator):
    """Create a collection if it doesn't exist, or update its validator."""
    existing = db.list_collection_names()
    if name in existing:
        db.command("collMod", name, validator=validator, validationLevel="moderate")
        print(f"  [exists]  {name} -- validator updated")
    else:
        db.create_collection(name, validator=validator)
        print(f"  [created] {name}")


def _key_pattern(index_doc):
    """Return a frozenset of (field, direction) from an index document."""
    return tuple((k, v) for k, v in index_doc["key"].items() if k != "_id")


def _ensure_indexes(db, name, index_models):
    """Create indexes idempotently, skipping any whose key pattern already exists."""
    existing = list(db[name].list_indexes())
    existing_patterns = {_key_pattern(idx) for idx in existing}
    existing_names = {idx["name"] for idx in existing}

    to_create = []
    skipped = []
    for model in index_models:
        # Build the key pattern from the IndexModel's document specification
        pattern = tuple((k, v) for k, v in model.document["key"].items())
        if pattern in existing_patterns:
            skipped.append(pattern)
        else:
            to_create.append(model)

    if not to_create:
        print(f"  [exists]  {name}: all indexes already present")
        return

    result = db[name].create_indexes(to_create)
    new = [n for n in result if n not in existing_names]
    if new:
        print(f"  [created] {name}: {', '.join(new)}")
    if skipped:
        print(f"  [skipped] {name}: {len(skipped)} indexes already exist with different names")


# ============================================================================
# Main
# ============================================================================

def main():
    print(f"=== MongoDB Init | database: {DATABASE_NAME} ===\n")

    # 1. Connect
    print("[connect]")
    if not test_connection():
        print("  FAIL -- check MONGODB_URI")
        return
    db = get_db()
    print(f"  OK -- {DATABASE_NAME}\n")

    # 2. Collections
    print("[collections]")
    for name, validator in SCHEMAS.items():
        _ensure_collection(db, name, validator)
    print()

    # 3. Indexes
    print("[indexes]")
    for name, models in INDEXES.items():
        _ensure_indexes(db, name, models)
    print()

    # 4. Summary
    print("[summary]")
    for name in SCHEMAS:
        count = db[name].count_documents({})
        idx = len(list(db[name].list_indexes()))
        print(f"  {name:20s}  docs={count:<6d}  indexes={idx}")

    print("\nDone.")


if __name__ == "__main__":
    main()
