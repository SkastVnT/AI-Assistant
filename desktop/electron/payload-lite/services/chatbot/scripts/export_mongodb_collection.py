"""
Export a MongoDB collection to JSON for the ChatBot service.

Converts BSON types (ObjectId, datetime, etc.) to JSON-safe values.
String UUID _id fields are preserved as-is. Legacy ObjectId values are
converted to their hex string representation.

Output is a JSON array that can be re-imported with import_json_to_mongodb.py.

Usage:
    python scripts/export_mongodb_collection.py --collection conversations
    python scripts/export_mongodb_collection.py --collection messages --out backup.json
    python scripts/export_mongodb_collection.py --collection messages --query '{"role":"assistant"}' --limit 50
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId
from config.mongodb_config import get_db, test_connection, DATABASE_NAME

VALID_COLLECTIONS = {
    "conversations", "messages", "learning_data",
    "rag_documents", "rag_chunks", "rag_ingestion_jobs",
}


# ============================================================================
# BSON -> JSON-safe conversion
# ============================================================================

def bson_to_json(value):
    """Recursively convert BSON types to JSON-serialisable Python types."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: bson_to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [bson_to_json(item) for item in value]
    if isinstance(value, bytes):
        return value.hex()
    # int, float, str, bool, None pass through
    return value


# ============================================================================
# Export logic
# ============================================================================

def export_collection(db, collection, query, limit):
    """Query the collection and return a list of JSON-safe dicts."""
    cursor = db[collection].find(query)
    if limit:
        cursor = cursor.limit(limit)

    docs = []
    for doc in cursor:
        docs.append(bson_to_json(doc))
    return docs


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Export MongoDB collection to JSON")
    parser.add_argument("--collection", required=True, choices=sorted(VALID_COLLECTIONS),
                        help="Collection to export")
    parser.add_argument("--out", type=str, default=None,
                        help="Output file path (default: <collection>_export.json)")
    parser.add_argument("--query", type=str, default="{}",
                        help='MongoDB query filter as JSON string (default: "{}")')
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of documents to export")
    args = parser.parse_args()

    # Parse query
    try:
        query = json.loads(args.query)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid --query JSON: {e}")
        sys.exit(1)

    if not isinstance(query, dict):
        print("ERROR: --query must be a JSON object")
        sys.exit(1)

    out_path = Path(args.out) if args.out else Path(f"{args.collection}_export.json")

    print(f"=== MongoDB Export | {DATABASE_NAME} ===\n")
    print(f"  collection: {args.collection}")
    print(f"  query:      {json.dumps(query)}")
    print(f"  limit:      {args.limit or 'none'}")
    print(f"  output:     {out_path}\n")

    # Connect
    print("[connect]")
    if not test_connection():
        print("  FAIL -- check MONGODB_URI")
        sys.exit(2)
    db = get_db()
    print(f"  OK -- {DATABASE_NAME}\n")

    # Export
    print("[export]")
    docs = export_collection(db, args.collection, query, args.limit)
    print(f"  documents: {len(docs)}")

    if not docs:
        print("  (empty collection or no matching documents)")

    # Write
    print(f"\n[write] {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
    size_kb = out_path.stat().st_size / 1024
    print(f"  {len(docs)} documents, {size_kb:.1f} KB")

    # ID type summary
    id_types = {}
    for doc in docs:
        t = type(doc.get("_id")).__name__
        id_types[t] = id_types.get(t, 0) + 1
    print(f"\n[id types] {id_types}")

    print("\nDone.")


if __name__ == "__main__":
    main()
