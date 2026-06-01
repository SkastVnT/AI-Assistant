# Image RAG (CLIP multimodal)

The RAG subsystem can retrieve **images** alongside text by embedding both into
a shared CLIP vector space. A text query is embedded with the CLIP text encoder
and cosine-matched against image embeddings, then merged with normal text-chunk
hits before grounding the model.

This feature is **opt-in** and off by default. With `RAG_IMAGE_ENABLED=false`
(default) nothing changes.

## Architecture

```
chat request ──▶ routes/stream.py
                   │  (rag_collection_ids present?)
                   ▼
            RAGOrchestrator.retrieve_for_chat()
                   ├── RetrievalService.retrieve()         → rag_chunks   (text vectors)
                   └── RetrievalService.retrieve_images()  → rag_image_chunks (CLIP vectors)
                              │
                              ▼  HTTP
                   core/clip_adapter.py ──▶ services/clip-embed (FastAPI, venv-image)
                                                 open-clip ViT-B/32 (512d)
```

Text and image embeddings live in **separate tables** (`rag_chunks` vs
`rag_image_chunks`) because the text embedding provider (e.g. OpenAI 1536d) and
CLIP (512d) use different, incompatible vector spaces.

## Why a sidecar

`torch` / `open-clip-torch` belong to the **image dependency profile**
(`venv-image`) and must never be installed into `venv-core`. The chatbot calls
the CLIP encoder over HTTP via `core/clip_adapter.py`, mirroring the
`character_select_adapter` / `hermes_adapter` pattern.

## Running the CLIP sidecar

```bash
# venv-image active
cd services/clip-embed
python server.py            # listens on :8200
```

See `services/clip-embed/README.md` for endpoints and model env vars.

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `RAG_IMAGE_ENABLED` | `false` | Enable CLIP image retrieval / ingest |
| `CLIP_EMBED_URL` | `http://localhost:8200` | CLIP sidecar base URL |
| `CLIP_EMBED_DIM` | `512` | CLIP vector dim (ViT-B/32 → 512) |
| `CLIP_EMBED_TIMEOUT` | `30.0` | HTTP timeout (seconds) |

Keep `CLIP_EMBED_DIM` in sync with the sidecar model and the
`rag_image_chunks` migration (`0002_create_rag_image_chunks.py`, `CLIP_DIM`).

## Database

Migration `0002_create_rag_image_chunks` adds `rag_image_chunks`
(`embedding Vector(512)`, `object_path`, `caption`, `metadata_json`) with an
HNSW cosine index. Apply with Alembic against the pgvector database.

## Chat wiring

`routes/stream.py` accepts two optional request fields:

- `rag_collection_ids`: list of document IDs (or `["default"]`) to ground on.
  When empty, RAG is skipped entirely.
- `rag_tenant_id`: tenant isolation key (default `"default"`).

When hits are found, the user message is prefixed with a `[RAG_CONTEXT]` block
and the SSE `complete` event includes a `citations` array. Image hits carry
`metadata.source = "image"` and `metadata.object_path`.

## Ingesting images

`IngestService.ingest()` routes `image/*` files (by MIME or extension) through
CLIP: upload to MinIO → embed via the sidecar → persist `RagDocument` +
`RagImageChunk` (no text parsing/chunking). Requires `RAG_IMAGE_ENABLED=true`
and a reachable sidecar.

## Fail-soft behaviour

Every image path degrades gracefully: if the sidecar is disabled or
unreachable, image retrieval returns `[]` and text-only RAG continues. Chat
streaming is never blocked by RAG errors.
