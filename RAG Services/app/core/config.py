"""
RAG Services Configuration
Uses FREE models and services only
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings using FREE resources"""
    
    # App Config
    APP_NAME: str = "RAG Services"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 5003
    
    # Data Directories
    DATA_DIR: Path = BASE_DIR / "data"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"
    VECTORDB_DIR: Path = DATA_DIR / "vectordb"
    
    # FREE Embedding Model (sentence-transformers)
    # Vietnamese-optimized multilingual model
    EMBEDDING_MODEL: str = "keepitreal/vietnamese-sbert"
    EMBEDDING_DIMENSION: int = 768
    
    # Alternative FREE embedding models:
    # - "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (smaller, faster)
    # - "dangvantuan/vietnamese-embedding" (Vietnamese-specific)
    # - "bkai-foundation-models/vietnamese-bi-encoder" (Vietnamese SOTA)
    
    # ChromaDB Config (FREE - Local vector database)
    CHROMA_PERSIST_DIR: str = str(VECTORDB_DIR)
    CHROMA_COLLECTION_NAME: str = "rag_documents"
    
    # Chunking Strategy
    CHUNK_SIZE: int = 512  # tokens per chunk
    CHUNK_OVERLAP: int = 50  # overlap between chunks
    
    # Retrieval Config
    TOP_K_RESULTS: int = 5  # number of relevant chunks to retrieve
    SIMILARITY_THRESHOLD: float = 0.7  # minimum similarity score
    
    # LLM Config (FREE APIs)
    # Using Gemini Free API (15 requests/min, 1500/day)
    LLM_PROVIDER: str = "gemini"  # Options: "gemini", "qwen", "ollama"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"  # FREE tier
    
    # Alternative FREE LLM options:
    # - Local Qwen models (via transformers)
    # - Ollama (local, completely free)
    # - HuggingFace Inference API (free tier)
    
    # File Upload Limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {
        "pdf", "txt", "docx", "doc",
        "pptx", "xlsx", "md", "html"
    }
    
    # Vietnamese Processing
    VIETNAMESE_TOKENIZER: str = "underthesea"  # FREE Vietnamese NLP
    LANGUAGE_DETECTION: bool = True
    
    # Search Config
    ENABLE_RERANKING: bool = False  # Can enable with free cross-encoder
    ENABLE_QUERY_EXPANSION: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if not exist
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTORDB_DIR.mkdir(parents=True, exist_ok=True)

# Global settings instance
settings = Settings()

# Model Information
MODELS_INFO = {
    "embedding": {
        "name": settings.EMBEDDING_MODEL,
        "type": "sentence-transformers",
        "cost": "FREE",
        "languages": ["Vietnamese", "English", "100+ languages"],
        "dimension": settings.EMBEDDING_DIMENSION
    },
    "vectordb": {
        "name": "ChromaDB",
        "type": "Local vector database",
        "cost": "FREE",
        "features": ["Persistent storage", "Fast retrieval", "No API limits"]
    },
    "llm": {
        "name": settings.GEMINI_MODEL,
        "provider": settings.LLM_PROVIDER,
        "cost": "FREE (15 req/min, 1500/day)",
        "context_window": "1M tokens"
    }
}
