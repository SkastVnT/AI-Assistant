"""
FREE LLM Client - Gemini API
No costs, 15 requests/min, 1500/day
"""
import google.generativeai as genai
from typing import List, Dict, Optional
import os
from .config import settings

class FreeLLMClient:
    """
    FREE LLM using Google Gemini API
    - 15 requests per minute
    - 1,500 requests per day
    - 1M token context window
    - Completely FREE
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key (or from environment)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("⚠️  No Gemini API key found. RAG responses will be disabled.")
            print("   Get FREE key at: https://makersuite.google.com/app/apikey")
            self.model = None
            return
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use FREE Flash model (faster, still very good)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        print(f"✅ Gemini LLM initialized: {settings.GEMINI_MODEL}")
        print(f"   Rate limit: 15 req/min, 1500 req/day")
    
    def generate_answer(
        self,
        query: str,
        context_chunks: List[Dict],
        language: str = "auto",
        conversation_context: Optional[str] = None
    ) -> Dict:
        """
        Generate answer from query and context
        
        Args:
            query: User question
            context_chunks: Retrieved relevant chunks
            language: Response language (auto, vi, en)
            conversation_context: Previous conversation for context
            
        Returns:
            Dict with answer, sources, and metadata
        """
        if not self.model:
            return {
                'answer': "⚠️ LLM not configured. Please set GEMINI_API_KEY to enable RAG responses.",
                'sources': [],
                'error': 'no_api_key'
            }
        
        try:
            # Build context from chunks
            context = self._build_context(context_chunks)
            
            # Create prompt (with conversation context if available)
            prompt = self._create_prompt(query, context, language, conversation_context)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Extract sources
            sources = self._extract_sources(context_chunks)
            
            return {
                'answer': response.text,
                'sources': sources,
                'context_chunks': len(context_chunks),
                'model': settings.GEMINI_MODEL
            }
            
        except Exception as e:
            print(f"❌ LLM generation error: {e}")
            return {
                'answer': f"Error generating response: {str(e)}",
                'sources': [],
                'error': str(e)
            }
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context string from chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            source = chunk['metadata'].get('source', 'Unknown')
            text = chunk['text']
            
            context_parts.append(f"""
[Document {i}: {source}]
{text}
""")
        
        return "\n".join(context_parts)
    
    def _create_prompt(
        self, 
        query: str, 
        context: str, 
        language: str,
        conversation_context: Optional[str] = None
    ) -> str:
        """Create RAG prompt with optional conversation context"""
        
        language_instruction = ""
        if language == "vi":
            language_instruction = "Trả lời bằng tiếng Việt."
        elif language == "en":
            language_instruction = "Answer in English."
        else:
            language_instruction = "Detect the query language and respond in the same language."
        
        # Add conversation context if available
        context_section = ""
        if conversation_context:
            context_section = f"\n{conversation_context}\n"
        
        prompt = f"""You are a helpful AI assistant that answers questions based on provided documents.

IMPORTANT INSTRUCTIONS:
1. Answer the question using ONLY the information from the provided documents
2. If the documents don't contain relevant information, say so clearly
3. Cite sources by mentioning the document name
4. Be concise but comprehensive
5. {language_instruction}
6. Format your answer with markdown (bold, bullet points, etc.)
{context_section}
DOCUMENTS:
{context}

USER QUESTION:
{query}

ANSWER:
"""
        return prompt
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Extract unique sources from chunks"""
        sources = {}
        
        for chunk in chunks:
            source = chunk['metadata'].get('source', 'Unknown')
            if source not in sources:
                sources[source] = {
                    'name': source,
                    'file_type': chunk['metadata'].get('file_type', 'unknown'),
                    'relevance': chunk['score']
                }
        
        return list(sources.values())
    
    def stream_answer(
        self,
        query: str,
        context_chunks: List[Dict],
        language: str = "auto"
    ):
        """
        Stream answer generation (for real-time display)
        
        Yields:
            Text chunks as they're generated
        """
        if not self.model:
            yield "⚠️ LLM not configured."
            return
        
        try:
            context = self._build_context(context_chunks)
            prompt = self._create_prompt(query, context, language)
            
            response = self.model.generate_content(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"\n\n❌ Error: {str(e)}"


# Global LLM client instance
_llm_client = None

def get_llm_client() -> FreeLLMClient:
    """Get or create global LLM client"""
    global _llm_client
    if _llm_client is None:
        _llm_client = FreeLLMClient()
    return _llm_client


# Alternative FREE LLM options (if Gemini quota exceeded)
class OllamaClient:
    """
    Local Ollama client - Completely FREE, no limits
    Requires: ollama installed locally
    """
    
    def __init__(self, model: str = "llama2"):
        try:
            import ollama
            self.client = ollama.Client()
            self.model = model
            print(f"✅ Ollama initialized: {model}")
        except ImportError:
            print("⚠️  Ollama not installed. Run: pip install ollama")
            self.client = None
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Dict:
        """Generate answer using Ollama"""
        if not self.client:
            return {'answer': 'Ollama not available', 'sources': []}
        
        # Similar implementation as Gemini
        # ...


class HuggingFaceClient:
    """
    HuggingFace Inference API - FREE tier available
    """
    
    def __init__(self, model: str = "google/flan-t5-large"):
        self.model = model
        # Implementation...
