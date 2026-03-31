"""
Import RAG documents, chunks, and ingestion jobs into MongoDB.

Validates cross-references (every chunk's document_id must exist in
rag_documents) and upserts by natural keys:
  - rag_documents:      tenant_id + document_id
  - rag_chunks:         chunk_id
  - rag_ingestion_jobs: job_id

Usage:
    python scripts/import_rag_data.py --tenant-id t1 \\
        --documents-file data/rag_documents.json \\
        --chunks-file data/rag_chunks.json

    python scripts/import_rag_data.py --tenant-id t1 \\
        --documents-file data/rag_documents.json \\
        --chunks-file data/rag_chunks.json \\
        --jobs-file data/rag_ingestion_jobs.json \\
        --dry-run
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db, test_connection, DATABASE_NAME


# ============================================================================
# Validation helpers
# ============================================================================

def _uid():
    return str(uuid.uuid4())


def _parse_date(value):
    """Convert ISO string to datetime; pass through datetime and None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"cannot parse date from {type(value).__name__}: {value}")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print(f"ERROR: {path} root must be a JSON array")
        sys.exit(1)
    return data


# ============================================================================
# Document validation
# ============================================================================

def validate_documents(records, tenant_id):
    """Validate rag_documents records. Returns (clean_docs, errors)."""
    clean = []
    errors = []
    seen_ids = set()

    for i, rec in enumerate(records):
        errs = []

        # Required fields
        for field in ("document_id", "title", "source_type", "status"):
            if field not in rec or not rec[field]:
                errs.append(f"missing required field '{field}'")

        # Types
        if "document_id" in rec and not isinstance(rec["document_id"], str):
            errs.append(f"document_id must be string, got {type(rec['document_id']).__name__}")

        # Duplicate check within batch
        did = rec.get("document_id")
        if did in seen_ids:
            errs.append(f"duplicate document_id '{did}' in input")
        if did:
            seen_ids.add(did)

        if errs:
            errors.append((i, errs))
            continue

        # Build clean record
        try:
            now = datetime.utcnow()
            doc = {
                "_id": rec.get("_id") or _uid(),
                "tenant_id": tenant_id,
                "document_id": rec["document_id"],
                "title": rec["title"],
                "source_type": rec["source_type"],
                "source_uri": rec.get("source_uri"),
                "mime_type": rec.get("mime_type"),
                "object_path": rec.get("object_path"),
                "status": rec["status"],
                "metadata": rec.get("metadata", {}),
                "created_at": _parse_date(rec.get("created_at")) or now,
                "updated_at": _parse_date(rec.get("updated_at")) or now,
            }
            clean.append(doc)
        except Exception as e:
            errors.append((i, [str(e)]))

    return clean, errors


# ============================================================================
# Chunk validation
# ============================================================================

def validate_chunks(records, tenant_id, valid_doc_ids):
    """Validate rag_chunks records. Returns (clean_chunks, errors)."""
    clean = []
    errors = []

    for i, rec in enumerate(records):
        errs = []

        # Required fields
        for field in ("document_id", "chunk_id", "chunk_index", "content"):
            if field not in rec:
                errs.append(f"missing required field '{field}'")

        # document_id must reference an existing document
        did = rec.get("document_id")
        if did and did not in valid_doc_ids:
            errs.append(f"document_id '{did}' not found in rag_documents")

        # chunk_index must be int
        if "chunk_index" in rec and not isinstance(rec["chunk_index"], int):
            errs.append(f"chunk_index must be int, got {type(rec['chunk_index']).__name__}")

        # embedding validation
        embedding = rec.get("embedding")
        if embedding is not None:
            if not isinstance(embedding, list):
                errs.append(f"embedding must be an array, got {type(embedding).__name__}")
            elif embedding and not all(isinstance(v, (int, float)) for v in embedding):
                errs.append("embedding must contain only numbers")

        if errs:
            errors.append((i, errs))
            continue

        # Build clean record
        try:
            doc = {
                "_id": rec.get("_id") or _uid(),
                "tenant_id": tenant_id,
                "document_id": rec["document_id"],
                "chunk_id": rec["chunk_id"],
                "chunk_index": rec["chunk_index"],
                "content": rec["content"],
                "embedding": embedding or [],
                "metadata": rec.get("metadata", {}),
                "created_at": _parse_date(rec.get("created_at")) or datetime.utcnow(),
            }
            clean.append(doc)
        except Exception as e:
            errors.append((i, [str(e)]))

    return clean, errors


# ============================================================================
# Job validation
# ============================================================================

def validate_jobs(records, tenant_id, valid_doc_ids):
    """Validate rag_ingestion_jobs records. Returns (clean_jobs, errors)."""
    clean = []
    errors = []

    for i, rec in enumerate(records):
        errs = []

        for field in ("job_id", "document_id", "filename", "status"):
            if field not in rec or not rec[field]:
                errs.append(f"missing required field '{field}'")

        did = rec.get("document_id")
        if did and did not in valid_doc_ids:
            errs.append(f"document_id '{did}' not found in rag_documents")

        if errs:
            errors.append((i, errs))
            continue

        try:
            doc = {
                "_id": rec.get("_id") or _uid(),
                "job_id": rec["job_id"],
                "tenant_id": tenant_id,
                "document_id": rec["document_id"],
                "filename": rec["filename"],
                "status": rec["status"],
                "steps": rec.get("steps", {}),
                "num_chunks": rec.get("num_chunks", 0),
                "error_message": rec.get("error_message"),
                "started_at": _parse_date(rec.get("started_at")) or datetime.utcnow(),
                "finished_at": _parse_date(rec.get("finished_at")),
            }
            clean.append(doc)
        except Exception as e:
            errors.append((i, [str(e)]))

    return clean, errors


# ============================================================================
# Upsert logic
# ============================================================================

def upsert_documents(db, docs, dry_run):
    inserted = updated = skipped = 0
    coll = None if dry_run else db["rag_documents"]
    for doc in docs:
        if dry_run:
            inserted += 1
            continue
        result = coll.update_one(
            {"tenant_id": doc["tenant_id"], "document_id": doc["document_id"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count > 0:
            updated += 1
        else:
            skipped += 1
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def upsert_chunks(db, chunks, dry_run):
    inserted = updated = skipped = 0
    coll = None if dry_run else db["rag_chunks"]
    for doc in chunks:
        if dry_run:
            inserted += 1
            continue
        result = coll.update_one(
            {"chunk_id": doc["chunk_id"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count > 0:
            updated += 1
        else:
            skipped += 1
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def upsert_jobs(db, jobs, dry_run):
    inserted = updated = skipped = 0
    coll = None if dry_run else db["rag_ingestion_jobs"]
    for doc in jobs:
        if dry_run:
            inserted += 1
            continue
        result = coll.update_one(
            {"job_id": doc["job_id"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count > 0:
            updated += 1
        else:
            skipped += 1
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


# ============================================================================
# Print helpers
# ============================================================================

def _print_errors(label, errors):
    if not errors:
        return
    print(f"\n  [{label} errors]")
    for idx, errs in errors:
        for e in errs:
            print(f"    record {idx}: {e}")


def _print_stats(label, stats):
    print(f"  {label:25s}  inserted={stats['inserted']}  updated={stats['updated']}  skipped={stats['skipped']}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Import RAG data into MongoDB")
    parser.add_argument("--tenant-id", required=True, help="Tenant identifier")
    parser.add_argument("--documents-file", required=True, help="Path to rag_documents.json")
    parser.add_argument("--chunks-file", required=True, help="Path to rag_chunks.json")
    parser.add_argument("--jobs-file", default=None, help="Path to rag_ingestion_jobs.json (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not write")
    args = parser.parse_args()

    # Load files
    docs_path = Path(args.documents_file)
    chunks_path = Path(args.chunks_file)

    if not docs_path.exists():
        print(f"ERROR: documents file not found: {docs_path}")
        sys.exit(1)
    if not chunks_path.exists():
        print(f"ERROR: chunks file not found: {chunks_path}")
        sys.exit(1)

    raw_docs = _load_json(docs_path)
    raw_chunks = _load_json(chunks_path)
    raw_jobs = []
    if args.jobs_file:
        jobs_path = Path(args.jobs_file)
        if not jobs_path.exists():
            print(f"ERROR: jobs file not found: {jobs_path}")
            sys.exit(1)
        raw_jobs = _load_json(jobs_path)

    print(f"=== RAG Import | {DATABASE_NAME} ===\n")
    print(f"  tenant:    {args.tenant_id}")
    print(f"  documents: {len(raw_docs)} from {docs_path}")
    print(f"  chunks:    {len(raw_chunks)} from {chunks_path}")
    if raw_jobs:
        print(f"  jobs:      {len(raw_jobs)} from {args.jobs_file}")
    print(f"  dry-run:   {args.dry_run}\n")

    # Connect (unless dry-run)
    db = None
    if not args.dry_run:
        print("[connect]")
        if not test_connection():
            print("  FAIL -- check MONGODB_URI")
            sys.exit(2)
        db = get_db()
        print(f"  OK -- {DATABASE_NAME}\n")

    # 1. Validate documents
    print("[validate]")
    clean_docs, doc_errors = validate_documents(raw_docs, args.tenant_id)
    valid_doc_ids = {d["document_id"] for d in clean_docs}
    print(f"  documents: {len(clean_docs)} valid, {len(doc_errors)} rejected")

    # 2. Validate chunks (cross-ref against documents)
    clean_chunks, chunk_errors = validate_chunks(raw_chunks, args.tenant_id, valid_doc_ids)
    print(f"  chunks:    {len(clean_chunks)} valid, {len(chunk_errors)} rejected")

    # 3. Validate jobs
    clean_jobs, job_errors = [], []
    if raw_jobs:
        clean_jobs, job_errors = validate_jobs(raw_jobs, args.tenant_id, valid_doc_ids)
        print(f"  jobs:      {len(clean_jobs)} valid, {len(job_errors)} rejected")

    # Print errors
    all_errors = doc_errors + chunk_errors + job_errors
    _print_errors("documents", doc_errors)
    _print_errors("chunks", chunk_errors)
    _print_errors("jobs", job_errors)

    if all_errors:
        print(f"\n  TOTAL: {len(all_errors)} record(s) rejected")
        if not clean_docs and not clean_chunks:
            print("\nFAIL -- nothing to import")
            sys.exit(1)

    # 4. Upsert
    print(f"\n[{'dry-run' if args.dry_run else 'upsert'}]")
    doc_stats = upsert_documents(db, clean_docs, args.dry_run)
    _print_stats("rag_documents", doc_stats)

    chunk_stats = upsert_chunks(db, clean_chunks, args.dry_run)
    _print_stats("rag_chunks", chunk_stats)

    if clean_jobs:
        job_stats = upsert_jobs(db, clean_jobs, args.dry_run)
        _print_stats("rag_ingestion_jobs", job_stats)

    # 5. Summary
    if not args.dry_run and db:
        print("\n[summary]")
        for name in ("rag_documents", "rag_chunks", "rag_ingestion_jobs"):
            count = db[name].count_documents({"tenant_id": args.tenant_id})
            print(f"  {name:25s}  tenant docs={count}")

    print("\nDone.")


if __name__ == "__main__":
    main()
