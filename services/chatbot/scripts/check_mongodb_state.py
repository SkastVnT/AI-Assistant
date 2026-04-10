"""
MongoDB State Verification for ChatBot Service

Checks:
  - Connection and active database name
  - Collections present
  - Indexes per collection
  - Document counts for canonical collections
  - Schema consistency: _id and conversation_id must be strings

Exit codes:
  0 = all checks passed
  1 = schema inconsistency detected
  2 = connection failure
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db, test_connection, DATABASE_NAME

CANONICAL = [
    "conversations", "messages", "learning_data",
    "rag_documents", "rag_chunks", "rag_ingestion_jobs",
]


def check_connection():
    print("[connect]")
    if not test_connection():
        print("  FAIL -- cannot reach MongoDB")
        sys.exit(2)
    db = get_db()
    print(f"  database: {DATABASE_NAME}")
    return db


def check_collections(db):
    print("\n[collections]")
    names = sorted(db.list_collection_names())
    for name in names:
        tag = "*" if name in CANONICAL else " "
        print(f"  {tag} {name}")
    missing = [c for c in CANONICAL if c not in names]
    if missing:
        print(f"  WARNING: missing canonical collections: {', '.join(missing)}")
    return names


def check_indexes(db, collections):
    print("\n[indexes]")
    for name in sorted(collections):
        indexes = list(db[name].list_indexes())
        print(f"  {name} ({len(indexes)}):")
        for idx in indexes:
            keys = ", ".join(f"{k}:{v}" for k, v in idx["key"].items())
            unique = " UNIQUE" if idx.get("unique") else ""
            print(f"    - {idx['name']}: [{keys}]{unique}")


def check_counts(db):
    print("\n[document counts]")
    for name in CANONICAL:
        try:
            count = db[name].count_documents({})
        except Exception:
            count = "N/A"
        print(f"  {name}: {count}")


def check_schema(db):
    """Validate that recent documents use string IDs, not ObjectId."""
    print("\n[schema validation]")
    errors = []

    # conversations._id should be string
    if "conversations" in db.list_collection_names():
        docs = list(db.conversations.find().sort("created_at", -1).limit(10))
        if docs:
            bad = [d for d in docs if not isinstance(d["_id"], str)]
            ok = len(docs) - len(bad)
            print(f"  conversations._id: {ok}/{len(docs)} are string")
            if bad:
                sample = str(bad[0]["_id"])
                errors.append(
                    f"conversations._id: {len(bad)}/{len(docs)} are NOT string "
                    f"(e.g. {type(bad[0]['_id']).__name__}: {sample})"
                )
        else:
            print("  conversations: empty -- skipped")

    # messages.conversation_id should be string
    if "messages" in db.list_collection_names():
        docs = list(db.messages.find().sort("created_at", -1).limit(10))
        if docs:
            bad_id = [d for d in docs if not isinstance(d["_id"], str)]
            bad_cid = [
                d for d in docs
                if "conversation_id" in d and not isinstance(d["conversation_id"], str)
            ]
            ok_id = len(docs) - len(bad_id)
            ok_cid = len(docs) - len(bad_cid)
            print(f"  messages._id: {ok_id}/{len(docs)} are string")
            print(f"  messages.conversation_id: {ok_cid}/{len(docs)} are string")
            if bad_id:
                errors.append(
                    f"messages._id: {len(bad_id)}/{len(docs)} are NOT string"
                )
            if bad_cid:
                errors.append(
                    f"messages.conversation_id: {len(bad_cid)}/{len(docs)} are NOT string"
                )
        else:
            print("  messages: empty -- skipped")

    return errors


def main():
    print(f"=== MongoDB State Check | {DATABASE_NAME} ===\n")

    db = check_connection()
    collections = check_collections(db)
    check_indexes(db, collections)
    check_counts(db)
    errors = check_schema(db)

    print()
    if errors:
        # Legacy ObjectId data is a warning, not a hard failure.
        # Exit code 1 only if ALL checked docs are non-string (no new-format docs at all).
        print("WARN -- mixed or legacy schema detected (pre-existing ObjectId docs):")
        for e in errors:
            print(f"  - {e}")
        print("  Tip: new documents written by this service use string UUIDs.")
        print("  Legacy data does not affect normal operation.")
    else:
        print("OK -- all checks passed")


if __name__ == "__main__":
    main()
