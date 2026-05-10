"""
RAG subsystem configuration — all settings from environment variables.
"""
import os
from pathlib import Path

CHATBOT_DIR = Path(__file__).resolve().parent.parent.parent

# ── Feature flag ───────────────────────────────────────────────────────
RAG_ENABLED = os.getenv("RAG_ENABLED", "false").lower() in ("true", "1", "yes")

# ── Storage ────────────────────────────────────────────────────────────
RAG_DATA_DIR = Path(os.getenv("RAG_DATA_DIR", str(CHATBOT_DIR / "data" / "rag")))
RAG_CHROMA_DIR = RAG_DATA_DIR / "chroma"

# ── Embedding ──────────────────────────────────────────────────────────
RAG_EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "openai")  # openai | gemini
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
RAG_EMBEDDING_DIMENSIONS = int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "1536"))

# ── Chunking ───────────────────────────────────────────────────────────
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "512"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "64"))

# ── Retrieval ──────────────────────────────────────────────────────────
RAG_DEFAULT_TOP_K = int(os.getenv("RAG_DEFAULT_TOP_K", "5"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
