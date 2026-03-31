"""
One-shot local RAG file ingestion into MongoDB.

Reads a file, extracts text, chunks it, optionally embeds, and inserts
rag_documents + rag_chunks + rag_ingestion_jobs into MongoDB.

Supported file types: .txt, .md, .html, .pdf (requires pypdf)

Usage:
    python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file docs/guide.md
    python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file report.pdf --title "Q1 Report"
    python scripts/ingest_file_to_rag_mongodb.py --tenant-id t1 --file notes.txt --dry-run
"""

import argparse
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db, test_connection, DATABASE_NAME

SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".pdf"}
CHUNK_SIZE = 512          # target tokens per chunk
CHUNK_OVERLAP = 64        # overlap tokens between chunks


# ============================================================================
# Text extraction
# ============================================================================

def extract_text_txt(file_path):
    """Read plain text file. Returns [(page, text)]."""
    text = file_path.read_text(encoding="utf-8")
    return [(1, text)]


def extract_text_md(file_path):
    """Read markdown, strip to plain text. Returns [(page, text)]."""
    import markdown
    from bs4 import BeautifulSoup

    raw = file_path.read_text(encoding="utf-8")
    html = markdown.markdown(raw)
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    return [(1, text)]


def extract_text_html(file_path):
    """Read HTML, extract body text. Returns [(page, text)]."""
    from bs4 import BeautifulSoup

    raw = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    # Remove script/style elements
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return [(1, text)]


def extract_text_pdf(file_path):
    """Read PDF, extract text per page. Returns [(page_num, text)]."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("ERROR: pypdf is required for PDF files. Install with:")
        print("  pip install pypdf")
        sys.exit(1)

    reader = PdfReader(str(file_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i + 1, text))
    return pages


EXTRACTORS = {
    ".txt": extract_text_txt,
    ".md": extract_text_md,
    ".html": extract_text_html,
    ".htm": extract_text_html,
    ".pdf": extract_text_pdf,
}


# ============================================================================
# Chunking (token-based using tiktoken)
# ============================================================================

def _get_tokenizer():
    """Get a tiktoken tokenizer (cl100k_base, used by most embedding models)."""
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def chunk_pages(pages, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """
    Split extracted pages into overlapping chunks.
    Returns list of {"content": str, "metadata": {"page": int|None}}.
    """
    enc = _get_tokenizer()
    chunks = []

    for page_num, text in pages:
        # Clean whitespace
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            continue

        tokens = enc.encode(text)
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = enc.decode(chunk_tokens).strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "metadata": {"page": page_num},
                })
            if end >= len(tokens):
                break
            start = end - chunk_overlap

    return chunks


# ============================================================================
# Embedding (optional)
# ============================================================================

def embed_chunks(chunks, model):
    """
    Call OpenAI-compatible embedding API.
    Returns list of embedding vectors (list of floats).
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  WARNING: OPENAI_API_KEY not set, skipping embeddings")
        return [[] for _ in chunks]

    client = openai.OpenAI(api_key=api_key)
    texts = [c["content"] for c in chunks]

    # Batch in groups of 100 (API limit)
    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(input=batch, model=model)
        for item in response.data:
            all_embeddings.append(item.embedding)

    return all_embeddings


# ============================================================================
# MongoDB insertion
# ============================================================================

def _uid():
    return str(uuid.uuid4())


def build_records(tenant_id, document_id, file_path, title, source_uri, chunks, embeddings):
    """Build MongoDB-ready records for documents, chunks, and jobs."""
    now = datetime.utcnow()
    suffix = file_path.suffix.lstrip(".")

    mime_map = {
        "txt": "text/plain",
        "md": "text/markdown",
        "html": "text/html",
        "htm": "text/html",
        "pdf": "application/pdf",
    }

    doc_record = {
        "_id": _uid(),
        "tenant_id": tenant_id,
        "document_id": document_id,
        "title": title,
        "source_type": suffix,
        "source_uri": source_uri,
        "mime_type": mime_map.get(suffix, "application/octet-stream"),
        "object_path": str(file_path),
        "status": "processed",
        "metadata": {
            "file_size": file_path.stat().st_size,
            "num_chunks": len(chunks),
        },
        "created_at": now,
        "updated_at": now,
    }

    chunk_records = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        chunk_records.append({
            "_id": _uid(),
            "tenant_id": tenant_id,
            "document_id": document_id,
            "chunk_id": f"{document_id}-chunk-{i}",
            "chunk_index": i,
            "content": chunk["content"],
            "embedding": emb,
            "metadata": chunk["metadata"],
            "created_at": now,
        })

    job_record = {
        "_id": _uid(),
        "job_id": f"job-{document_id}",
        "tenant_id": tenant_id,
        "document_id": document_id,
        "filename": file_path.name,
        "status": "completed",
        "steps": {
            "extract": {"status": "done"},
            "chunk": {"status": "done", "num_chunks": len(chunks)},
            "embed": {"status": "done" if any(emb for emb in embeddings) else "skipped"},
        },
        "num_chunks": len(chunks),
        "error_message": None,
        "started_at": now,
        "finished_at": now,
    }

    return doc_record, chunk_records, job_record


def _upsert(collection, filter_doc, record):
    """Upsert a record, keeping _id in $setOnInsert to avoid immutable field error."""
    doc = {k: v for k, v in record.items() if k != "_id"}
    collection.update_one(
        filter_doc,
        {"$set": doc, "$setOnInsert": {"_id": record["_id"]}},
        upsert=True,
    )


def insert_to_db(db, doc_record, chunk_records, job_record, dry_run):
    """Upsert records into MongoDB."""
    if dry_run:
        return

    _upsert(
        db.rag_documents,
        {"tenant_id": doc_record["tenant_id"], "document_id": doc_record["document_id"]},
        doc_record,
    )

    for chunk in chunk_records:
        _upsert(db.rag_chunks, {"chunk_id": chunk["chunk_id"]}, chunk)

    _upsert(db.rag_ingestion_jobs, {"job_id": job_record["job_id"]}, job_record)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Ingest a file into RAG MongoDB collections")
    parser.add_argument("--tenant-id", required=True, help="Tenant identifier")
    parser.add_argument("--file", required=True, help="Path to file to ingest")
    parser.add_argument("--title", default=None, help="Document title (default: filename)")
    parser.add_argument("--source-uri", default=None, help="Original source URI")
    parser.add_argument("--embed", action="store_true",
                        help="Generate embeddings (requires OPENAI_API_KEY)")
    parser.add_argument("--embed-model", default=None,
                        help="Embedding model (default: RAG_EMBED_MODEL env or text-embedding-3-small)")
    parser.add_argument("--dry-run", action="store_true", help="Extract and chunk only, do not write to DB")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ERROR: file not found: {file_path}")
        sys.exit(1)

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"ERROR: unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    title = args.title or file_path.stem
    document_id = f"doc-{file_path.stem.lower().replace(' ', '-')}"
    embed_model = args.embed_model or os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small")

    print(f"=== RAG Ingest | {DATABASE_NAME} ===\n")
    print(f"  tenant:      {args.tenant_id}")
    print(f"  file:        {file_path}")
    print(f"  title:       {title}")
    print(f"  document_id: {document_id}")
    print(f"  embed:       {args.embed} ({embed_model})")
    print(f"  dry-run:     {args.dry_run}\n")

    # 1. Extract
    print("[extract]")
    extractor = EXTRACTORS[ext]
    pages = extractor(file_path)
    total_chars = sum(len(t) for _, t in pages)
    print(f"  pages: {len(pages)}, chars: {total_chars}")

    if not pages:
        print("  ERROR: no text extracted")
        sys.exit(1)

    # 2. Chunk
    print("\n[chunk]")
    chunks = chunk_pages(pages)
    print(f"  chunks: {len(chunks)} (target {CHUNK_SIZE} tokens, overlap {CHUNK_OVERLAP})")

    if not chunks:
        print("  ERROR: no chunks produced")
        sys.exit(1)

    # 3. Embed (optional)
    embeddings = [[] for _ in chunks]
    if args.embed:
        print(f"\n[embed] model={embed_model}")
        embeddings = embed_chunks(chunks, embed_model)
        dims = len(embeddings[0]) if embeddings and embeddings[0] else 0
        print(f"  vectors: {len(embeddings)}, dimensions: {dims}")
    else:
        print("\n[embed] skipped (use --embed to generate)")

    # 4. Build records
    doc_record, chunk_records, job_record = build_records(
        args.tenant_id, document_id, file_path, title, args.source_uri, chunks, embeddings
    )

    # 5. Insert
    db = None
    if not args.dry_run:
        print("\n[connect]")
        if not test_connection():
            print("  FAIL -- check MONGODB_URI")
            sys.exit(2)
        db = get_db()
        print(f"  OK -- {DATABASE_NAME}")

    mode = "dry-run" if args.dry_run else "upsert"
    print(f"\n[{mode}]")
    insert_to_db(db, doc_record, chunk_records, job_record, args.dry_run)
    print(f"  rag_documents:      1")
    print(f"  rag_chunks:         {len(chunk_records)}")
    print(f"  rag_ingestion_jobs: 1")

    # 6. Summary
    print(f"\n[result]")
    print(f"  document_id: {document_id}")
    print(f"  chunks:      {len(chunk_records)}")
    print(f"  embedded:    {args.embed}")

    print("\nDone.")


if __name__ == "__main__":
    main()
