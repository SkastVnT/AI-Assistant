"""
Import JSON data into MongoDB for the ChatBot service.

Reads a JSON file (array of objects) and inserts/upserts into a canonical
collection. Validates each record against the collection schema before
writing. All document IDs must be string UUIDs.

Round-trip compatible with export_mongodb_collection.py:
  export → JSON (ISO dates, stringified ObjectIds) → import

Usage:
    python scripts/import_json_to_mongodb.py --collection conversations --file data.json
    python scripts/import_json_to_mongodb.py --collection messages --file msgs.json --upsert-key _id
    python scripts/import_json_to_mongodb.py --collection learning_data --file ld.json --dry-run
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db, test_connection, DATABASE_NAME

VALID_COLLECTIONS = {
    "conversations", "messages", "learning_data",
    "rag_documents", "rag_chunks", "rag_ingestion_jobs",
}

# ============================================================================
# Schema definitions (required fields + type checks)
# ============================================================================

REQUIRED_FIELDS = {
    "conversations": ["user_id", "title", "model", "created_at"],
    "messages": ["conversation_id", "role", "content", "created_at"],
    "learning_data": ["source", "category", "data", "created_at"],
    "rag_documents": ["tenant_id", "document_id", "title", "source_type", "status", "created_at"],
    "rag_chunks": ["tenant_id", "document_id", "chunk_id", "chunk_index", "content", "created_at"],
    "rag_ingestion_jobs": ["job_id", "tenant_id", "document_id", "filename", "status", "started_at"],
}

FIELD_TYPES = {
    "conversations": {
        "_id": str,
        "user_id": str,
        "title": str,
        "model": str,
        "session_id": str,
        "is_archived": bool,
        "is_deleted": bool,
        "message_count": int,
        "metadata": dict,
        "created_at": (str, datetime),
        "updated_at": (str, datetime),
    },
    "messages": {
        "_id": str,
        "conversation_id": str,
        "role": str,
        "content": str,
        "metadata": dict,
        "images": list,
        "tokens": (int, type(None)),
        "is_edited": bool,
        "edit_history": list,
        "created_at": (str, datetime),
        "updated_at": (str, datetime),
    },
    "learning_data": {
        "_id": str,
        "source": str,
        "category": str,
        "data": dict,
        "quality_score": (int, float),
        "is_approved": bool,
        "created_at": (str, datetime),
        "reviewed_at": (str, datetime, type(None)),
        "rejection_reason": (str, type(None)),
    },
    "rag_documents": {
        "_id": str,
        "tenant_id": str,
        "document_id": str,
        "title": str,
        "source_type": str,
        "source_uri": (str, type(None)),
        "mime_type": (str, type(None)),
        "object_path": (str, type(None)),
        "status": str,
        "metadata": dict,
        "created_at": (str, datetime),
        "updated_at": (str, datetime),
    },
    "rag_chunks": {
        "_id": str,
        "tenant_id": str,
        "document_id": str,
        "chunk_id": str,
        "chunk_index": int,
        "content": str,
        "embedding": list,
        "metadata": dict,
        "created_at": (str, datetime),
    },
    "rag_ingestion_jobs": {
        "_id": str,
        "job_id": str,
        "tenant_id": str,
        "document_id": str,
        "filename": str,
        "status": str,
        "steps": dict,
        "num_chunks": int,
        "error_message": (str, type(None)),
        "started_at": (str, datetime),
        "finished_at": (str, datetime, type(None)),
    },
}

VALID_ROLES = {"user", "assistant", "system"}

# ISO format strings that we accept for date fields
DATE_FIELDS = {
    "conversations": ["created_at", "updated_at"],
    "messages": ["created_at", "updated_at"],
    "learning_data": ["created_at", "reviewed_at"],
    "rag_documents": ["created_at", "updated_at"],
    "rag_chunks": ["created_at"],
    "rag_ingestion_jobs": ["started_at", "finished_at"],
}


# ============================================================================
# Validation
# ============================================================================

def validate_record(record, collection, index):
    """Validate a single record. Returns (cleaned_record, errors)."""
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS[collection]:
        if field not in record:
            errors.append(f"missing required field '{field}'")

    # Check field types
    type_map = FIELD_TYPES[collection]
    for field, value in record.items():
        if field in type_map and value is not None:
            expected = type_map[field]
            if not isinstance(value, expected):
                errors.append(
                    f"field '{field}': expected {expected}, got {type(value).__name__}"
                )

    # Role enum check for messages
    if collection == "messages" and "role" in record:
        if record["role"] not in VALID_ROLES:
            errors.append(f"field 'role': must be one of {VALID_ROLES}, got '{record['role']}'")

    # Assign UUID _id if missing
    if "_id" not in record:
        record["_id"] = str(uuid.uuid4())

    # _id must be string
    if not isinstance(record.get("_id"), str):
        errors.append(f"_id must be a string UUID, got {type(record['_id']).__name__}")

    # Parse ISO date strings into datetime objects (known date fields)
    for field in DATE_FIELDS.get(collection, []):
        if field in record and isinstance(record[field], str):
            try:
                record[field] = datetime.fromisoformat(record[field])
            except ValueError:
                errors.append(f"field '{field}': invalid ISO date string '{record[field]}'")

    # Parse any extra *_at fields that look like ISO dates (round-trip support)
    known_dates = set(DATE_FIELDS.get(collection, []))
    for field, value in record.items():
        if field.endswith("_at") and field not in known_dates and isinstance(value, str):
            try:
                record[field] = datetime.fromisoformat(value)
            except ValueError:
                pass  # not a date string, leave as-is

    return record, errors


# ============================================================================
# Import logic
# ============================================================================

def import_records(db, collection, records, upsert_key, dry_run):
    """Import validated records into MongoDB. Returns stats dict."""
    coll = None if dry_run else db[collection]
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
    error_details = []

    for i, raw in enumerate(records):
        record, errs = validate_record(raw, collection, i)
        if errs:
            stats["errors"] += 1
            error_details.append((i, errs))
            continue

        if dry_run:
            stats["inserted"] += 1
            continue

        try:
            if upsert_key:
                key_val = record.get(upsert_key)
                if key_val is None:
                    stats["skipped"] += 1
                    error_details.append((i, [f"upsert key '{upsert_key}' is missing or null"]))
                    continue
                result = coll.update_one(
                    {upsert_key: key_val},
                    {"$set": record},
                    upsert=True,
                )
                if result.upserted_id is not None:
                    stats["inserted"] += 1
                elif result.modified_count > 0:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                # Plain insert — skip if _id already exists
                if coll.count_documents({"_id": record["_id"]}, limit=1):
                    stats["skipped"] += 1
                else:
                    coll.insert_one(record)
                    stats["inserted"] += 1
        except Exception as e:
            stats["errors"] += 1
            error_details.append((i, [str(e)]))

    return stats, error_details


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Import JSON data into MongoDB")
    parser.add_argument("--collection", required=True, choices=sorted(VALID_COLLECTIONS),
                        help="Target collection")
    parser.add_argument("--file", required=True, type=str,
                        help="Path to JSON file (array of objects)")
    parser.add_argument("--upsert-key", type=str, default=None,
                        help="Field to use as upsert key (e.g. _id). Without this, plain insert is used.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only, do not write to database")
    args = parser.parse_args()

    # Load JSON
    json_path = Path(args.file)
    if not json_path.exists():
        print(f"ERROR: file not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON: {e}")
            sys.exit(1)

    if not isinstance(data, list):
        print("ERROR: JSON root must be an array of objects")
        sys.exit(1)

    print(f"=== MongoDB Import | {DATABASE_NAME} ===\n")
    print(f"  collection: {args.collection}")
    print(f"  file:       {json_path}")
    print(f"  records:    {len(data)}")
    print(f"  upsert-key: {args.upsert_key or '(none — plain insert)'}")
    print(f"  dry-run:    {args.dry_run}\n")

    if args.dry_run:
        print("[dry-run] Validating only...\n")
    else:
        # Connect
        print("[connect]")
        if not test_connection():
            print("  FAIL -- check MONGODB_URI")
            sys.exit(2)
        print(f"  OK -- {DATABASE_NAME}\n")

    db = None if args.dry_run else get_db()

    # Import
    print(f"[import] Processing {len(data)} records...")
    stats, error_details = import_records(db, args.collection, data, args.upsert_key, args.dry_run)

    # Results
    print(f"\n[results]")
    print(f"  inserted: {stats['inserted']}")
    print(f"  updated:  {stats['updated']}")
    print(f"  skipped:  {stats['skipped']}")
    print(f"  errors:   {stats['errors']}")

    if error_details:
        print(f"\n[errors]")
        for idx, errs in error_details:
            for e in errs:
                print(f"  record {idx}: {e}")

    if stats["errors"] > 0:
        print(f"\nFAIL -- {stats['errors']} record(s) rejected")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
