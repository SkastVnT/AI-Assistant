"""
ChromaDB Vector Store - FREE Local Database
No API costs, unlimited storage, persistent
With Vietnamese query optimization
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Any
from .config import settings
from .embeddings import get_embedding_model
from .vietnamese_processor import get_vietnamese_processor
import uuid

class VectorStore:
    """
    FREE Vector Database using ChromaDB
    - Completely local (no API calls)
    - Persistent storage
    - Fast similarity search
    """
    
    def __init__(self):
        """Initialize ChromaDB client"""
        print(f"🔄 Initializing ChromaDB at: {settings.CHROMA_PERSIST_DIR}")
        
        # Create persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"description": "RAG document embeddings"}
        )
        
        # Load embedding model
        self.embedding_model = get_embedding_model()
        
        print(f"✅ ChromaDB initialized")
        print(f"   Collection: {settings.CHROMA_COLLECTION_NAME}")
        print(f"   Documents: {self.collection.count()}")
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to vector store
        
        Args:
            texts: List of text chunks
            metadatas: List of metadata dicts
            ids: Optional list of IDs (auto-generated if None)
            
        Returns:
            List of document IDs
        """
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Generate embeddings (FREE - local computation)
        print(f"🔄 Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model.embed_texts(texts)
        
        # Add to ChromaDB
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Added {len(texts)} documents to vector store")
        return ids
    
    def search(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        optimize_vietnamese: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in vector store
        With Vietnamese query optimization
        
        Args:
            query: Search query
            top_k: Number of results (default from settings)
            filter_metadata: Optional metadata filters
            optimize_vietnamese: Apply Vietnamese query processing
            
        Returns:
            List of results with text, metadata, and score
        """
        top_k = top_k or settings.TOP_K_RESULTS
        
        # Optimize query if Vietnamese
        processed_query = query
        if optimize_vietnamese:
            try:
                vi_processor = get_vietnamese_processor()
                lang = vi_processor.detect_language(query)
                
                if lang == 'vi':
                    processed_query = vi_processor.process_query(query, enhance=True)
                    print(f"   🇻🇳 Vietnamese query optimized: '{query}' → '{processed_query}'")
            except Exception as e:
                print(f"   ⚠️  Vietnamese query optimization failed: {e}")
        
        # Generate query embedding (FREE)
        query_embedding = self.embedding_model.embed_text(processed_query)
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                })
        
        # Filter by similarity threshold
        filtered_results = [
            r for r in formatted_results 
            if r['score'] >= settings.SIMILARITY_THRESHOLD
        ]
        
        return filtered_results
    
    def delete_document(self, document_id: str):
        """Delete document by ID"""
        self.collection.delete(ids=[document_id])
        print(f"✅ Deleted document: {document_id}")
    
    def delete_by_source(self, source: str):
        """Delete all documents from a source file"""
        # Get all documents with this source
        results = self.collection.get(
            where={"source": source}
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            print(f"✅ Deleted {len(results['ids'])} documents from: {source}")
    
    def clear_all(self):
        """Clear all documents"""
        count = self.collection.count()
        self.client.delete_collection(settings.CHROMA_COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )
        print(f"✅ Cleared {count} documents from vector store")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        count = self.collection.count()
        
        # Get unique sources
        all_docs = self.collection.get()
        sources = set()
        if all_docs['metadatas']:
            sources = {meta.get('source', 'unknown') for meta in all_docs['metadatas']}
        
        return {
            'total_chunks': count,
            'total_documents': len(sources),
            'sources': list(sources),
            'embedding_model': self.embedding_model.model_name,
            'embedding_dimension': self.embedding_model.dimension
        }


# Global vector store instance
_vector_store = None

def get_vector_store() -> VectorStore:
    """Get or create global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
