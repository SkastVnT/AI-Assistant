"""
FREE Embedding Models Handler
Uses sentence-transformers - completely free and open source
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from .config import settings

class FreeEmbeddingModel:
    """
    Wrapper for FREE embedding models
    Using sentence-transformers (Vietnamese-optimized)
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize FREE embedding model
        
        Args:
            model_name: Model to use (default from settings)
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        print(f"🔄 Loading FREE embedding model: {self.model_name}")
        
        try:
            # Load model - downloads once, cached locally
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Embedding model loaded successfully")
            print(f"   Dimension: {self.model.get_sentence_embedding_dimension()}")
            
        except Exception as e:
            print(f"⚠️  Failed to load {self.model_name}, using fallback")
            # Fallback to smaller multilingual model
            self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Loaded fallback model: {self.model_name}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Embed single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (embedding vector)
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple texts efficiently
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        emb1 = self.model.encode(text1, convert_to_numpy=True)
        emb2 = self.model.encode(text2, convert_to_numpy=True)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


# Global embedding model instance
_embedding_model = None

def get_embedding_model() -> FreeEmbeddingModel:
    """Get or create global embedding model instance"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = FreeEmbeddingModel()
    return _embedding_model


# Alternative FREE models you can use:
ALTERNATIVE_FREE_MODELS = {
    "vietnamese_sbert": "keepitreal/vietnamese-sbert",  # Vietnamese-optimized
    "vietnamese_embedding": "dangvantuan/vietnamese-embedding",  # Vietnamese-specific
    "vietnamese_bkai": "bkai-foundation-models/vietnamese-bi-encoder",  # SOTA Vietnamese
    "multilingual_mini": "paraphrase-multilingual-MiniLM-L12-v2",  # Small, fast
    "multilingual_mpnet": "paraphrase-multilingual-mpnet-base-v2",  # Better quality
    "labse": "sentence-transformers/LaBSE",  # 109 languages
}

def switch_model(model_key: str):
    """
    Switch to different FREE embedding model
    
    Args:
        model_key: Key from ALTERNATIVE_FREE_MODELS
    """
    global _embedding_model
    if model_key in ALTERNATIVE_FREE_MODELS:
        model_name = ALTERNATIVE_FREE_MODELS[model_key]
        _embedding_model = FreeEmbeddingModel(model_name)
        print(f"✅ Switched to model: {model_name}")
    else:
        print(f"❌ Model key '{model_key}' not found")
        print(f"Available models: {list(ALTERNATIVE_FREE_MODELS.keys())}")
