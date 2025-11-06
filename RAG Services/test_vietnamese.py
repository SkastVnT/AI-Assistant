"""
Test Vietnamese Optimization
Verify Vietnamese text processing capabilities
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.vietnamese_processor import get_vietnamese_processor, VIETNAMESE_AVAILABLE

def test_vietnamese_processor():
    """Test Vietnamese text processor"""
    
    print("="*60)
    print("🇻🇳 Vietnamese Optimization Test")
    print("="*60)
    print()
    
    # Check if libraries available
    print(f"Vietnamese libraries available: {VIETNAMESE_AVAILABLE}")
    print()
    
    if not VIETNAMESE_AVAILABLE:
        print("⚠️  Vietnamese libraries not installed!")
        print("   Install with: pip install underthesea pyvi")
        return
    
    # Create processor
    vi_processor = get_vietnamese_processor(
        use_tokenization=True,
        remove_stopwords=False
    )
    
    # Test texts
    test_texts = {
        'vietnamese': "Xin chào! Tôi là trợ lý AI thông minh. Tôi có thể giúp bạn tìm kiếm thông tin trong tài liệu.",
        'english': "Hello! I am an intelligent AI assistant. I can help you search for information in documents.",
        'mixed': "Hôm nay tôi học về Machine Learning và Deep Learning rất thú vị."
    }
    
    for name, text in test_texts.items():
        print(f"{'='*60}")
        print(f"Test: {name.upper()}")
        print(f"{'='*60}")
        print(f"Original text:")
        print(f"  {text}")
        print()
        
        # Language detection
        lang = vi_processor.detect_language(text)
        print(f"Detected language: {lang}")
        print()
        
        # Statistics
        stats = vi_processor.get_statistics(text)
        print(f"Statistics:")
        print(f"  - Characters: {stats['characters']}")
        print(f"  - Words: {stats['words']}")
        print(f"  - Sentences: {stats['sentences']}")
        print(f"  - Vietnamese chars: {stats['vietnamese_chars']}")
        print(f"  - Vietnamese ratio: {stats['vietnamese_ratio']*100:.1f}%")
        print()
        
        # Cleaning
        cleaned = vi_processor.clean_text(text)
        print(f"Cleaned text:")
        print(f"  {cleaned}")
        print()
        
        # Tokenization
        if lang == 'vi':
            tokens = vi_processor.tokenize_words(text)
            print(f"Tokens (first 10):")
            print(f"  {tokens[:10]}")
            print()
            
            # Sentence segmentation
            sentences = vi_processor.segment_sentences(text)
            print(f"Sentences ({len(sentences)}):")
            for i, sent in enumerate(sentences, 1):
                print(f"  {i}. {sent}")
            print()
        
        print()
    
    # Test chunking
    print(f"{'='*60}")
    print("Test: VIETNAMESE TEXT CHUNKING")
    print(f"{'='*60}")
    
    long_text = """
    Trí tuệ nhân tạo (AI) là một lĩnh vực nghiên cứu khoa học máy tính tập trung vào việc tạo ra các hệ thống thông minh. 
    Các hệ thống này có khả năng thực hiện các nhiệm vụ thường đòi hỏi trí tuệ con người. 
    Machine Learning là một nhánh quan trọng của AI, cho phép máy tính học từ dữ liệu.
    Deep Learning sử dụng mạng neural nhân tạo với nhiều lớp để xử lý thông tin phức tạp.
    Các ứng dụng của AI rất đa dạng, từ nhận diện giọng nói, xử lý ngôn ngữ tự nhiên, đến xe tự lái.
    Trong tương lai, AI sẽ ngày càng đóng vai trò quan trọng trong cuộc sống hàng ngày của chúng ta.
    """
    
    print(f"Original text length: {len(long_text)} characters")
    print()
    
    chunks = vi_processor.chunk_vietnamese_text(long_text, chunk_size=50, overlap=10)
    
    print(f"Number of chunks: {len(chunks)}")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        word_count = len(vi_processor.tokenize_words(chunk))
        print(f"Chunk {i} ({word_count} words):")
        print(f"  {chunk[:100]}...")
        print()
    
    # Test query processing
    print(f"{'='*60}")
    print("Test: QUERY PROCESSING")
    print(f"{'='*60}")
    
    test_queries = [
        "Tìm kiếm thông tin về máy học",
        "What is deep learning?",
        "Làm thế nào để huấn luyện mô hình AI?"
    ]
    
    for query in test_queries:
        print(f"Original query: {query}")
        processed = vi_processor.process_query(query, enhance=True)
        print(f"Processed query: {processed}")
        lang = vi_processor.detect_language(query)
        print(f"Language: {lang}")
        print()
    
    print("="*60)
    print("✅ Vietnamese Optimization Test Complete!")
    print("="*60)


if __name__ == '__main__':
    try:
        test_vietnamese_processor()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
