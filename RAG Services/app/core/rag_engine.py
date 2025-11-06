"""
RAG Engine - Retrieval Augmented Generation
Combines vector search with LLM generation
"""
from typing import Dict, List, Optional
from .vectorstore import get_vector_store
from .llm_client import get_llm_client
from .config import settings

class RAGEngine:
    """
    Complete RAG pipeline:
    1. Retrieve relevant chunks (semantic search)
    2. Generate answer using LLM with context
    3. Return answer with sources
    """
    
    def __init__(self):
        """Initialize RAG components"""
        self.vector_store = get_vector_store()
        self.llm_client = get_llm_client()
        print("✅ RAG Engine initialized")
    
    def query(
        self,
        question: str,
        top_k: int = None,
        language: str = "auto",
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Answer question using RAG
        
        Args:
            question: User question
            top_k: Number of chunks to retrieve
            language: Response language (auto, vi, en)
            filter_metadata: Optional filters for search
            
        Returns:
            Dict with answer, sources, and metadata
        """
        top_k = top_k or settings.TOP_K_RESULTS
        
        print(f"🔍 RAG Query: {question}")
        print(f"   Retrieving top {top_k} chunks...")
        
        # Step 1: Retrieve relevant chunks
        search_results = self.vector_store.search(
            query=question,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        if not search_results:
            return {
                'answer': "❌ No relevant documents found. Please upload documents first.",
                'sources': [],
                'retrieved_chunks': 0,
                'mode': 'no_results'
            }
        
        print(f"   ✓ Retrieved {len(search_results)} relevant chunks")
        
        # Step 2: Generate answer with LLM
        print(f"   🤖 Generating answer with {self.llm_client.model.model_name if self.llm_client.model else 'LLM'}...")
        
        llm_response = self.llm_client.generate_answer(
            query=question,
            context_chunks=search_results,
            language=language
        )
        
        print(f"   ✓ Answer generated")
        
        # Combine results
        return {
            'answer': llm_response['answer'],
            'sources': llm_response['sources'],
            'retrieved_chunks': len(search_results),
            'search_results': search_results,  # Include for debugging/display
            'model': llm_response.get('model', 'unknown'),
            'mode': 'rag',
            'query': question
        }
    
    def query_with_history(
        self,
        question: str,
        chat_history: List[Dict],
        top_k: int = None
    ) -> Dict:
        """
        Answer with conversation history
        
        Args:
            question: Current question
            chat_history: Previous messages [{'role': 'user/assistant', 'content': '...'}]
            top_k: Number of chunks
            
        Returns:
            RAG response
        """
        # TODO: Implement conversation-aware RAG
        # For now, just use current question
        return self.query(question, top_k)
    
    def search_only(
        self,
        query: str,
        top_k: int = None
    ) -> List[Dict]:
        """
        Just search, no LLM generation
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of search results
        """
        return self.vector_store.search(query, top_k)
    
    def explain_sources(self, sources: List[Dict]) -> str:
        """
        Generate human-readable explanation of sources
        
        Args:
            sources: List of source documents
            
        Returns:
            Formatted string
        """
        if not sources:
            return "No sources"
        
        explanation = "📚 **Sources:**\n\n"
        for i, source in enumerate(sources, 1):
            name = source['name']
            relevance = int(source['relevance'] * 100)
            explanation += f"{i}. **{name}** (relevance: {relevance}%)\n"
        
        return explanation


# Global RAG engine instance
_rag_engine = None

def get_rag_engine() -> RAGEngine:
    """Get or create global RAG engine"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
