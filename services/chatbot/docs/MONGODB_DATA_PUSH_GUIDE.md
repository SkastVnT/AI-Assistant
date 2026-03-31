# MongoDB Setup & Data Push Guide

Operational guide for the chatbot service MongoDB toolkit.
All commands run from `services/chatbot/`.

---

## 1. Environment Setup

Copy and fill `.env`:

```bash
cp .env.example .env
```

Required variables:

| Variable | Example | Notes |
|---|---|---|
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster.mongodb.net/...` | Atlas connection string |
| `MONGODB_DB_NAME` | `chatbot_db` | Database name (default: `chatbot_db`) |
| `OPENAI_API_KEY` | `sk-proj-...` | Only needed for `--embed` in ingestion |
| `RAG_EMBED_MODEL` | `text-embedding-3-small` | Embedding model (default: `text-embedding-3-small`) |

Activate the virtualenv:

```powershell
# Windows
& .\venv\Scripts\Activate.ps1

# Linux/macOS
source venv/bin/activate
```

---

## 2. Initialize Database

Creates all 6 canonical collections with JSON Schema validators and indexes.
Idempotent — safe to re-run at any time.

```bash
python scripts/init_mongodb.py
```

**Collections created:**

| Collection | Purpose |
|---|---|
| `conversations` | Chat sessions |
| `messages` | Individual messages |
| `learning_data` | Training/feedback data |
| `rag_documents` | RAG source documents |
| `rag_chunks` | Chunked text + embeddings |
| `rag_ingestion_jobs` | Ingestion job tracking |

---

## 3. Seed Demo Data

Inserts demo conversations, messages, and learning data with a `seed_demo` marker.

```bash
# Seed 1 conversation (default)
python scripts/seed_mongodb.py

# Seed 5 conversations
python scripts/seed_mongodb.py --count 5

# Delete existing demo data and reseed
python scripts/seed_mongodb.py --reset --count 3
```

---

## 4. Import JSON Data

Import a JSON array file into any canonical collection.

```bash
# Basic import
python scripts/import_json_to_mongodb.py --collection conversations --file data/convos.json

# Upsert by _id (skip duplicates)
python scripts/import_json_to_mongodb.py --collection messages --file data/msgs.json --upsert-key _id

# Dry run (validate only, no writes)
python scripts/import_json_to_mongodb.py --collection learning_data --file data/ld.json --dry-run
```

**Sample JSON files** are in `local_data/sample_seed/`:

```
local_data/sample_seed/
├── conversations.json
├── messages.json
├── learning_data.json
├── rag_documents.json
├── rag_chunks.json
└── rag_ingestion_jobs.json
```

Import all sample data:

```bash
python scripts/import_json_to_mongodb.py --collection conversations --file local_data/sample_seed/conversations.json --upsert-key _id
python scripts/import_json_to_mongodb.py --collection messages --file local_data/sample_seed/messages.json --upsert-key _id
python scripts/import_json_to_mongodb.py --collection learning_data --file local_data/sample_seed/learning_data.json --upsert-key _id
```

### Export (round-trip)

Export any collection to JSON. Output is re-importable.

```bash
python scripts/export_mongodb_collection.py --collection conversations
python scripts/export_mongodb_collection.py --collection messages --out backup.json --limit 100
python scripts/export_mongodb_collection.py --collection messages --query '{"role":"assistant"}'
```

---

## 5. Create RAG Collections

RAG collections (`rag_documents`, `rag_chunks`, `rag_ingestion_jobs`) are created
automatically by `init_mongodb.py` (Step 2). No separate step needed.

If you only need to verify they exist:

```bash
python scripts/check_mongodb_state.py
```

---

## 6. Import RAG Documents & Chunks

### Option A — Bulk JSON import (pre-built data)

```bash
python scripts/import_rag_data.py --tenant-id t1 \
    --documents-file local_data/sample_seed/rag_documents.json \
    --chunks-file local_data/sample_seed/rag_chunks.json \
    --jobs-file local_data/sample_seed/rag_ingestion_jobs.json

# Dry run
python scripts/import_rag_data.py --tenant-id t1 \
    --documents-file local_data/sample_seed/rag_documents.json \
    --chunks-file local_data/sample_seed/rag_chunks.json \
    --dry-run
```

Cross-reference validation: every `chunk.document_id` must exist in the documents file.

### Option B — File ingestion (extract → chunk → embed → insert)

Ingest a single file directly into RAG collections:

```bash
# Text / Markdown / HTML
python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file docs/guide.md

# With embeddings
python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file docs/guide.md --embed

# PDF (requires: pip install pypdf)
python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file report.pdf --title "Q1 Report"

# Custom title + source URI
python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file notes.txt \
    --title "Meeting Notes" --source-uri "s3://bucket/notes.txt"

# Dry run
python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file docs/guide.md --dry-run
```

Supported file types: `.txt`, `.md`, `.html`, `.pdf`

---

## 7. Verify Data in MongoDB Atlas UI

### Via script

```bash
python scripts/check_mongodb_state.py
```

Checks: connection, collections present, indexes, document counts, `_id` type consistency.

Exit codes: `0` = OK, `1` = schema issue, `2` = connection failure.

### Via Atlas UI

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Select your cluster → **Browse Collections**
3. Select database `chatbot_db` (or your `MONGODB_DB_NAME`)
4. Verify each collection has documents with string `_id` fields (not ObjectId)
5. Check **Indexes** tab — each collection should have the indexes from `init_mongodb.py`

**Quick checks:**
- `conversations` → `_id` is a UUID string, has `user_id` index
- `messages` → `conversation_id` is a string, has compound index on `(conversation_id, created_at)`
- `rag_chunks` → has `chunk_id` field, optional `embedding` array
- `rag_documents` → has compound index on `(tenant_id, document_id)`

---

## 8. Common Failure Cases & Fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ServerSelectionTimeoutError` | Wrong URI or network blocked | Check `MONGODB_URI` in `.env`. Verify IP whitelist in Atlas → Network Access |
| `authentication failed` | Wrong credentials | Regenerate password in Atlas → Database Access. Update `.env` |
| `[SSL: CERTIFICATE_VERIFY_FAILED]` | Missing CA certs or corporate proxy | `pip install certifi` and set `tlsCAFile` in URI, or add `?tlsAllowInvalidCertificates=true` (dev only) |
| `check_mongodb_state.py` exits with code 1 | ObjectId `_id` found in documents | Legacy data. Re-import with `--upsert-key _id` to overwrite with string UUIDs |
| `import_json_to_mongodb.py` validation error | Missing required field | Check `REQUIRED_FIELDS` in the script. Ensure JSON has all required keys |
| `import_rag_data.py` cross-ref error | `chunk.document_id` not in documents file | Ensure documents file includes all referenced `document_id` values |
| `ingest_file_to_rag_mongodb.py` exits on PDF | `pypdf` not installed | `pip install pypdf` |
| `seed_mongodb.py` says "already seeded" | Demo data exists | Use `--reset` to delete and reseed |
| `OPENAI_API_KEY` warning during `--embed` | Key not set in `.env` | Add `OPENAI_API_KEY` to `.env`. Embeddings are optional — omit `--embed` to skip |
| `Document failed validation` on insert | Schema validator rejects document | Run `init_mongodb.py` to update validators (uses `validationLevel: moderate`) |

---

## Script Reference

| Script | Purpose |
|---|---|
| `scripts/init_mongodb.py` | Create collections, validators, indexes |
| `scripts/check_mongodb_state.py` | Verify DB state and schema consistency |
| `scripts/seed_mongodb.py` | Insert demo data (`--count`, `--reset`) |
| `scripts/import_json_to_mongodb.py` | Import JSON array (`--collection`, `--file`, `--upsert-key`, `--dry-run`) |
| `scripts/export_mongodb_collection.py` | Export to JSON (`--collection`, `--out`, `--query`, `--limit`) |
| `scripts/import_rag_data.py` | Import RAG data with cross-ref validation (`--tenant-id`, `--dry-run`) |
| `scripts/ingest_file_to_rag_mongodb.py` | File → extract → chunk → embed → insert (`--tenant-id`, `--embed`, `--dry-run`) |

All scripts use `config/mongodb_config.py` for connection. All `_id` fields are string UUIDs.
