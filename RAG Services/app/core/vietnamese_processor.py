"""
Vietnamese Text Processor
Optimize text processing for Vietnamese language
"""
import re
from typing import List, Optional
import unicodedata

try:
    from underthesea import word_tokenize, sent_tokenize
    from pyvi import ViTokenizer
    VIETNAMESE_AVAILABLE = True
except ImportError:
    print("⚠️  Vietnamese libraries not installed. Install: pip install underthesea pyvi")
    VIETNAMESE_AVAILABLE = False

class VietnameseTextProcessor:
    """
    Vietnamese text processing utilities
    - Normalize Vietnamese characters
    - Tokenize Vietnamese text
    - Segment sentences properly
    - Remove stopwords
    - Clean and preprocess
    """
    
    # Common Vietnamese stopwords
    VIETNAMESE_STOPWORDS = {
        # Articles
        'các', 'một', 'những', 'mỗi', 'nhiều', 'ít', 'vài',
        # Prepositions
        'của', 'cho', 'với', 'về', 'từ', 'trong', 'trên', 'dưới', 'ngoài', 'giữa',
        'bên', 'cạnh', 'gần', 'xa', 'sau', 'trước', 'đằng', 'phía',
        # Conjunctions
        'và', 'hay', 'hoặc', 'nhưng', 'mà', 'nên', 'thì', 'nếu', 'vì',
        # Pronouns
        'tôi', 'bạn', 'anh', 'chị', 'em', 'nó', 'họ', 'chúng', 'mình',
        # Verbs (common)
        'là', 'có', 'được', 'đã', 'sẽ', 'đang', 'bị', 'cho',
        # Others
        'này', 'đó', 'kia', 'như', 'thế', 'sao', 'gì', 'ai', 'đâu',
        'khi', 'lúc', 'bao', 'bây', 'giờ', 'rất', 'lắm', 'quá',
        'cũng', 'đều', 'vẫn', 'còn', 'chỉ', 'đến', 'đi', 'ra', 'vào'
    }
    
    def __init__(self, use_tokenization: bool = True, remove_stopwords: bool = False):
        """
        Initialize Vietnamese processor
        
        Args:
            use_tokenization: Apply word tokenization
            remove_stopwords: Remove Vietnamese stopwords
        """
        self.use_tokenization = use_tokenization and VIETNAMESE_AVAILABLE
        self.remove_stopwords = remove_stopwords
        
        if not VIETNAMESE_AVAILABLE:
            print("⚠️  Vietnamese processing disabled. Basic mode only.")
    
    def normalize_vietnamese(self, text: str) -> str:
        """
        Normalize Vietnamese text
        - Fix Unicode composition (NFC)
        - Standardize characters
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        # Normalize Unicode (NFC - canonical composition)
        text = unicodedata.normalize('NFC', text)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', text)
        
        return text
    
    def clean_text(self, text: str) -> str:
        """
        Clean Vietnamese text
        - Remove extra whitespace
        - Fix punctuation spacing
        - Remove special characters (keep Vietnamese)
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Normalize first
        text = self.normalize_vietnamese(text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix punctuation spacing (Vietnamese style)
        text = re.sub(r'\s*([,.:;!?])\s*', r'\1 ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def tokenize_words(self, text: str) -> List[str]:
        """
        Tokenize Vietnamese text into words
        Uses underthesea for proper Vietnamese word segmentation
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        if not VIETNAMESE_AVAILABLE or not self.use_tokenization:
            # Fallback: simple split
            return text.split()
        
        try:
            # Use underthesea for better tokenization
            tokens = word_tokenize(text, format="text")
            return tokens.split()
        except:
            # Fallback
            return text.split()
    
    def segment_sentences(self, text: str) -> List[str]:
        """
        Segment text into sentences (Vietnamese-aware)
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if not VIETNAMESE_AVAILABLE:
            # Fallback: simple split on punctuation
            return self._simple_sentence_split(text)
        
        try:
            # Use underthesea for proper sentence segmentation
            sentences = sent_tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except:
            return self._simple_sentence_split(text)
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """Fallback sentence splitter"""
        # Split on common sentence endings
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def remove_vietnamese_stopwords(self, text: str) -> str:
        """
        Remove Vietnamese stopwords
        
        Args:
            text: Input text
            
        Returns:
            Text without stopwords
        """
        if not self.remove_stopwords:
            return text
        
        # Tokenize
        tokens = self.tokenize_words(text)
        
        # Remove stopwords (case-insensitive)
        filtered = [
            token for token in tokens 
            if token.lower() not in self.VIETNAMESE_STOPWORDS
        ]
        
        return ' '.join(filtered)
    
    def preprocess_for_embedding(self, text: str) -> str:
        """
        Preprocess text for embedding
        - Clean text
        - Normalize
        - Optionally tokenize and remove stopwords
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text
        """
        # Clean and normalize
        text = self.clean_text(text)
        
        # Tokenize if enabled
        if self.use_tokenization:
            tokens = self.tokenize_words(text)
            text = ' '.join(tokens)
        
        # Remove stopwords if enabled
        if self.remove_stopwords:
            text = self.remove_vietnamese_stopwords(text)
        
        return text
    
    def chunk_vietnamese_text(
        self, 
        text: str, 
        chunk_size: int = 512, 
        overlap: int = 50
    ) -> List[str]:
        """
        Chunk Vietnamese text with sentence awareness
        
        Args:
            text: Input text
            chunk_size: Target chunk size (in words)
            overlap: Overlap between chunks (in words)
            
        Returns:
            List of text chunks
        """
        # Segment into sentences
        sentences = self.segment_sentences(text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            # Count words in sentence
            words = self.tokenize_words(sentence)
            sentence_size = len(words)
            
            # Check if adding this sentence exceeds chunk size
            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                # Keep last few sentences for context
                overlap_size = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    s_words = len(self.tokenize_words(s))
                    if overlap_size + s_words <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_size += s_words
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_size = overlap_size
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection (Vietnamese vs other)
        
        Args:
            text: Input text
            
        Returns:
            'vi' for Vietnamese, 'other' for non-Vietnamese
        """
        # Check for Vietnamese-specific characters
        vietnamese_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
        vietnamese_chars += vietnamese_chars.upper()
        
        # Count Vietnamese characters
        vi_count = sum(1 for c in text if c in vietnamese_chars)
        total_alpha = sum(1 for c in text if c.isalpha())
        
        if total_alpha == 0:
            return 'other'
        
        # If more than 10% are Vietnamese characters, consider it Vietnamese
        vi_ratio = vi_count / total_alpha
        return 'vi' if vi_ratio > 0.1 else 'other'
    
    def process_query(self, query: str, enhance: bool = True) -> str:
        """
        Process user query for better search
        
        Args:
            query: User query
            enhance: Apply enhancement (tokenization, etc.)
            
        Returns:
            Processed query
        """
        # Detect language
        lang = self.detect_language(query)
        
        # Clean and normalize
        query = self.clean_text(query)
        
        if enhance and lang == 'vi' and VIETNAMESE_AVAILABLE:
            # Apply Vietnamese tokenization
            query = ' '.join(self.tokenize_words(query))
        
        return query
    
    def highlight_keywords(
        self, 
        text: str, 
        keywords: List[str],
        context_chars: int = 100
    ) -> List[dict]:
        """
        Find and highlight keywords in text (Vietnamese-aware)
        
        Args:
            text: Full text
            keywords: Keywords to find
            context_chars: Characters of context around keyword
            
        Returns:
            List of snippets with highlights
        """
        snippets = []
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Find all occurrences
            pos = 0
            while True:
                pos = text_lower.find(keyword_lower, pos)
                if pos == -1:
                    break
                
                # Extract context
                start = max(0, pos - context_chars // 2)
                end = min(len(text), pos + len(keyword) + context_chars // 2)
                
                snippet = text[start:end]
                
                # Add ellipsis
                if start > 0:
                    snippet = '...' + snippet
                if end < len(text):
                    snippet = snippet + '...'
                
                snippets.append({
                    'text': snippet,
                    'keyword': keyword,
                    'position': pos
                })
                
                pos += len(keyword)
        
        return snippets
    
    @staticmethod
    def get_statistics(text: str) -> dict:
        """
        Get text statistics
        
        Args:
            text: Input text
            
        Returns:
            Dict with statistics
        """
        # Character count
        char_count = len(text)
        
        # Word count (simple)
        words = text.split()
        word_count = len(words)
        
        # Sentence count (approximate)
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Vietnamese character ratio
        vietnamese_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
        vietnamese_chars += vietnamese_chars.upper()
        vi_count = sum(1 for c in text if c in vietnamese_chars)
        
        return {
            'characters': char_count,
            'words': word_count,
            'sentences': sentence_count,
            'vietnamese_chars': vi_count,
            'vietnamese_ratio': vi_count / char_count if char_count > 0 else 0
        }


# Global instance
_vietnamese_processor = None

def get_vietnamese_processor(
    use_tokenization: bool = True,
    remove_stopwords: bool = False
) -> VietnameseTextProcessor:
    """Get or create global Vietnamese processor"""
    global _vietnamese_processor
    
    if _vietnamese_processor is None:
        _vietnamese_processor = VietnameseTextProcessor(
            use_tokenization=use_tokenization,
            remove_stopwords=remove_stopwords
        )
    
    return _vietnamese_processor
