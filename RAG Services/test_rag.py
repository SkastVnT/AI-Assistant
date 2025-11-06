"""
Test RAG Services - Phase 1
Tests core functionality with FREE models
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:5003"

def test_health():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    
    print(f"   Status: {data['status']}")
    print(f"   Service: {data['service']} v{data['version']}")
    print(f"   Embedding: {data['models']['embedding']['name']}")
    print(f"   VectorDB: {data['models']['vectordb']['name']}")
    print(f"   Documents: {data['stats']['total_documents']}")
    print(f"   Chunks: {data['stats']['total_chunks']}")
    print("   ✅ Health check passed\n")

def test_upload():
    """Test document upload"""
    print("📤 Testing document upload...")
    
    # Create a test document
    test_file = "test_document.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("""
        Machine Learning là gì?
        
        Machine Learning (Học máy) là một nhánh của Trí tuệ nhân tạo (AI) 
        cho phép máy tính học từ dữ liệu mà không cần được lập trình cụ thể.
        
        Các loại Machine Learning:
        1. Supervised Learning (Học có giám sát)
        2. Unsupervised Learning (Học không giám sát)
        3. Reinforcement Learning (Học tăng cường)
        
        Machine Learning được ứng dụng trong nhiều lĩnh vực như:
        - Nhận dạng hình ảnh
        - Xử lý ngôn ngữ tự nhiên
        - Hệ thống gợi ý
        - Xe tự lái
        """)
    
    # Upload
    with open(test_file, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/api/upload",
            files={'file': f}
        )
    
    data = response.json()
    print(f"   Filename: {data['filename']}")
    print(f"   Chunks created: {data['chunks']}")
    print("   ✅ Upload successful\n")
    
    # Clean up
    Path(test_file).unlink()

def test_search():
    """Test semantic search"""
    print("🔍 Testing semantic search...")
    
    queries = [
        "Machine Learning là gì?",
        "Các loại học máy",
        "Ứng dụng của AI"
    ]
    
    for query in queries:
        print(f"\n   Query: {query}")
        response = requests.post(
            f"{BASE_URL}/api/search",
            json={'query': query, 'top_k': 3}
        )
        
        data = response.json()
        print(f"   Results found: {data['count']}")
        
        for i, result in enumerate(data['results'][:2], 1):
            print(f"\n   Result {i}:")
            print(f"   Score: {result['score']:.3f}")
            print(f"   Text: {result['text'][:100]}...")
            print(f"   Source: {result['metadata']['source']}")
    
    print("\n   ✅ Search successful\n")

def test_list_documents():
    """Test listing documents"""
    print("📋 Testing document listing...")
    response = requests.get(f"{BASE_URL}/api/documents")
    data = response.json()
    
    print(f"   Total documents: {data['total_documents']}")
    print(f"   Total chunks: {data['total_chunks']}")
    print(f"   Documents: {', '.join(data['documents'])}")
    print("   ✅ List successful\n")

def test_stats():
    """Test statistics"""
    print("📊 Testing statistics...")
    response = requests.get(f"{BASE_URL}/api/stats")
    data = response.json()
    
    print(f"   Embedding model: {data['embedding_model']}")
    print(f"   Embedding dimension: {data['embedding_dimension']}")
    print(f"   Total chunks: {data['total_chunks']}")
    print(f"   Total documents: {data['total_documents']}")
    print("   ✅ Stats successful\n")

def main():
    """Run all tests"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║   RAG Services - Test Suite              ║
    ║   Phase 1: Core Functionality            ║
    ║   100% FREE Models                       ║
    ╚═══════════════════════════════════════════╝
    """)
    
    try:
        test_health()
        test_upload()
        test_search()
        test_list_documents()
        test_stats()
        
        print("""
        ╔═══════════════════════════════════════════╗
        ║   ✅ ALL TESTS PASSED                    ║
        ║                                           ║
        ║   Phase 1 Complete! 🎉                   ║
        ║   Next: Phase 2 - Web UI                 ║
        ╚═══════════════════════════════════════════╝
        """)
        
    except requests.exceptions.ConnectionError:
        print("""
        ❌ ERROR: Cannot connect to server
        
        Please start the server first:
        python app.py
        """)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
