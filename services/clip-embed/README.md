# CLIP Embed Sidecar

A small FastAPI service that produces **CLIP multimodal embeddings** for the
RAG image subsystem. It runs on the **image dependency profile** (`venv-image`)
because it depends on `torch` / `open-clip-torch`, which must never be installed
into `venv-core`.

The chatbot (`venv-core`) talks to this service over HTTP via
`services/chatbot/core/clip_adapter.py`. Text and image encoders share the same
vector space, so a text query can be cosine-matched against image vectors.

## Endpoints

| Method | Path           | Body                              | Response |
|--------|----------------|-----------------------------------|----------|
| GET    | `/health`      | —                                 | `{"status": "ok", "model": str, "dim": int}` |
| POST   | `/embed/text`  | `{"texts": ["..."]}`              | `{"embeddings": [[...]], "dim": int}` |
| POST   | `/embed/image` | `{"images": ["<base64|url>"]}`    | `{"embeddings": [[...]], "dim": int}` |

Images may be passed as raw base64, `data:` URLs, or `http(s)://` URLs.

## Run

```bash
# from repo root, with venv-image active
python -m uvicorn services.clip-embed.server:app --host 0.0.0.0 --port 8200
```

Or directly:

```bash
cd services/clip-embed
python server.py
```

## Environment

| Var | Default | Meaning |
|-----|---------|---------|
| `CLIP_MODEL_NAME` | `ViT-B-32` | open-clip architecture |
| `CLIP_PRETRAINED` | `laion2b_s34b_b79k` | pretrained weights tag |
| `CLIP_DEVICE` | `cpu` | `cpu` or `cuda` |
| `CLIP_EMBED_PORT` | `8200` | listen port |

The vector dimension is derived from the model (ViT-B-32 → 512). Keep
`CLIP_EMBED_DIM` on the chatbot side in sync (default 512).
