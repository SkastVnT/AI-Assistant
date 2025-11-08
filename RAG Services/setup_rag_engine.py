"""Initialize RAG Engine với ChromaDB + Gemini"""
import os
from dotenv import load_dotenv
from pathlib import Path

def setup_rag():
    load_dotenv()
    
    # Create directories
    Path("data/vectordb").mkdir(parents=True, exist_ok=True)
    Path("data/documents").mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")
    print(f"✅ API Key: {os.getenv('GOOGLE_API_KEY')[:20]}...")
    print(f"✅ Port: {os.getenv('PORT')}")
    print("\n🚀 RAG Engine ready!")

if __name__ == "__main__":
    setup_rag()