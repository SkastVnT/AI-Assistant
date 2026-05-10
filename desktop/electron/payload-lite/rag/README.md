# RAG System

Production-ready Retrieval-Augmented Generation platform built incrementally.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| API Framework | FastAPI |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| LLM / Embeddings | OpenAI API (provider-abstracted) |
| Containerization | Docker Compose |

## Project Structure

```
rag/
├── apps/
│   ├── api/                 # FastAPI application + Dockerfile
│   │   ├── main.py          # App factory, lifespan, CORS
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── dependencies.py  # FastAPI DI (db, providers)
│   │   ├── Dockerfile
│   │   └── routes/
│   │       ├── health.py    # GET /health
│   │       ├── ingest.py    # CRUD /api/v1/documents/
│   │       └── query.py     # POST /api/v1/query/
│   └── worker/              # Background ingestion worker + Dockerfile
│       └── main.py          # Polling loop for pending documents
├── libs/
│   ├── core/                # Shared foundation
│   │   ├── settings.py      # Pydantic-settings (env-driven config)
│   │   ├── database.py      # AsyncSession factory (SQLAlchemy)
│   │   ├── models.py        # Document + Chunk ORM with pgvector
│   │   ├── cache.py         # Redis client factory
│   │   ├── storage.py       # MinIO client factory
│   │   ├── logging.py       # Structured logging (text/JSON)
│   │   └── providers/       # LLM + Embedding abstractions
│   │       ├── base.py      # Protocol definitions
│   │       ├── openai_provider.py
│   │       └── factory.py   # Provider factory
│   ├── ingestion/           # Document processing pipeline
│   │   ├── extractor.py     # Text extraction (.txt, .md)
│   │   ├── chunker.py       # Recursive character splitter
│   │   ├── pipeline.py      # Sync ingestion (API-driven)
│   │   └── worker_tasks.py  # Async ingestion (worker-driven)
│   └── retrieval/           # Search + RAG generation
│       ├── search.py        # Vector similarity (pgvector cosine)
│       └── generator.py     # Context assembly + LLM answer
├── infra/
│   └── init.sql             # DB schema: documents, chunks, pgvector
├── alembic/                 # Database migrations
├── tests/                   # Unit + integration tests
├── docker-compose.yml       # All services: postgres, redis, minio, api, worker
├── Makefile                 # Task runner (Linux/Mac)
├── tasks.ps1               # Task runner (Windows PowerShell)
├── requirements.txt
├── pyproject.toml           # ruff, pytest, mypy config
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- An OpenAI API key (or other supported LLM provider)

### Option A: Local Development (recommended)

Infrastructure in Docker, Python apps running locally with hot-reload.

**Linux/Mac:**
```bash
cd rag/
make setup        # creates venv + .env
# Edit .env → set LLM_API_KEY and EMBEDDING_API_KEY
make infra-up     # start postgres, redis, minio
make dev          # run API with auto-reload (port 8000)
# In another terminal:
make worker       # run background worker
```

**Windows (PowerShell):**
```powershell
cd rag\
.\tasks.ps1 setup        # creates venv + .env
# Edit .env → set LLM_API_KEY and EMBEDDING_API_KEY
.\tasks.ps1 infra-up     # start postgres, redis, minio
.\tasks.ps1 dev           # run API with auto-reload (port 8000)
# In another terminal:
.\tasks.ps1 worker        # run background worker
```

### Option B: Full Docker

Everything in containers. No local Python needed.

```bash
cp .env.example .env      # edit with your API keys
docker compose up -d --build
# API at http://localhost:8000
# MinIO console at http://localhost:9001
```

### Verify

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"healthy","postgres":true,"redis":true,"minio":true}

# Upload a document
curl -X POST http://localhost:8000/api/v1/documents/ -F "file=@README.md"

# Ask a question
curl -X POST http://localhost:8000/api/v1/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What tech stack does this project use?"}'
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Infrastructure health check |
| POST | `/api/v1/documents/` | Upload & ingest a document |
| GET | `/api/v1/documents/` | List all documents |
| DELETE | `/api/v1/documents/{id}` | Delete a document + chunks |
| POST | `/api/v1/query/` | RAG query (retrieve + generate) |

## Common Commands

| Command | Linux/Mac | Windows |
|---------|-----------|---------|
| Run tests | `make test` | `.\tasks.ps1 test` |
| Lint | `make lint` | `.\tasks.ps1 lint` |
| Auto-fix | `make lint-fix` | `.\tasks.ps1 lint-fix` |
| Format | `make format` | `.\tasks.ps1 format` |
| All checks | `make check` | `.\tasks.ps1 check` |
| View logs | `make logs` | `.\tasks.ps1 logs` |
| DB migrate | `make db-upgrade` | `.\tasks.ps1 db-upgrade` |

## Roadmap

- [x] MVP: ingest → embed → search → generate
- [x] Dockerized api + worker services
- [x] Structured logging (text/JSON)
- [x] Task runner (Makefile + PowerShell)
- [ ] Hybrid search (BM25 + vector via tsvector)
- [ ] Reranking (cross-encoder)
- [ ] PDF / DOCX ingestion
- [ ] Embedding cache (Redis)
- [ ] Query transformation (HyDE, decomposition)
- [ ] GraphRAG
- [ ] Agentic RAG
- [ ] ReBAC / multi-tenant access control
- [ ] RAGOps (evaluation, monitoring, drift detection)
