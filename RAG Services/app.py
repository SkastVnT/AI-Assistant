"""
RAG Services - Main Flask Application
Phase 1: Core RAG functionality with FREE models
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from werkzeug.utils import secure_filename

from app.core.config import settings, MODELS_INFO
from app.core.vectorstore import get_vector_store
from app.core.document_processor import DocumentProcessor
from app.core.rag_engine import get_rag_engine

# Initialize Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.config['SECRET_KEY'] = 'rag-services-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = settings.MAX_FILE_SIZE

# Enable CORS
CORS(app)

# Ensure upload directory exists
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return jsonify({
            'status': 'healthy',
            'service': settings.APP_NAME,
            'version': settings.VERSION,
            'models': MODELS_INFO,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """
    Upload and process document
    Returns document ID and chunk count
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}'
            }), 400
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = settings.DOCUMENTS_DIR / filename
        file.save(str(file_path))
        
        print(f"📁 Uploaded file: {filename}")
        
        # Process and chunk document
        chunks_data = DocumentProcessor.process_and_chunk(str(file_path))
        
        if not chunks_data:
            return jsonify({'error': 'Failed to extract text from document'}), 400
        
        # Add to vector store
        vector_store = get_vector_store()
        texts = [chunk['text'] for chunk in chunks_data]
        metadatas = [chunk['metadata'] for chunk in chunks_data]
        
        ids = vector_store.add_documents(texts, metadatas)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'chunks': len(ids),
            'message': f'Successfully processed {filename} into {len(ids)} chunks'
        })
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search():
    """
    Semantic search in documents
    Request body: { "query": "...", "top_k": 5 }
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', settings.TOP_K_RESULTS)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Search in vector store
        vector_store = get_vector_store()
        results = vector_store.search(query, top_k=top_k)
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all indexed documents"""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return jsonify({
            'documents': stats['sources'],
            'total_documents': stats['total_documents'],
            'total_chunks': stats['total_chunks']
        })
        
    except Exception as e:
        print(f"❌ Error listing documents: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<path:filename>', methods=['DELETE'])
def delete_document(filename):
    """Delete document by filename"""
    try:
        vector_store = get_vector_store()
        vector_store.delete_by_source(filename)
        
        # Delete file if exists
        file_path = settings.DOCUMENTS_DIR / filename
        if file_path.exists():
            file_path.unlink()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {filename}'
        })
        
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get vector store statistics"""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/query', methods=['POST'])
def rag_query():
    """
    RAG Query - Answer question using retrieved context
    Request body: { 
        "query": "...", 
        "top_k": 5,
        "language": "auto"  // auto, vi, en
    }
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', settings.TOP_K_RESULTS)
        language = data.get('language', 'auto')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get RAG engine
        rag_engine = get_rag_engine()
        
        # Generate answer
        result = rag_engine.query(
            question=query,
            top_k=top_k,
            language=language
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ RAG query error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/status', methods=['GET'])
def rag_status():
    """Check if RAG is available (LLM configured)"""
    try:
        from app.core.llm_client import get_llm_client
        llm_client = get_llm_client()
        
        return jsonify({
            'available': llm_client.model is not None,
            'model': settings.GEMINI_MODEL if llm_client.model else None,
            'message': 'RAG ready' if llm_client.model else 'No API key configured'
        })
        
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print(f"""
    
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     🔍 RAG SERVICES v{settings.VERSION}                         ║
    ║     Semantic Search & Knowledge Base                      ║
    ║                                                           ║
    ║     💰 100% FREE - No API costs                           ║
    ║     🌍 Vietnamese-optimized                               ║
    ║                                                           ║
    ║     Models:                                               ║
    ║     📊 Embedding: {MODELS_INFO['embedding']['name'][:30]:<30} ║
    ║     💾 VectorDB: {MODELS_INFO['vectordb']['name']:<30}      ║
    ║                                                           ║
    ║     🌐 Server: http://{settings.HOST}:{settings.PORT}                    ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Phase 1: Core RAG ✅
    - Document upload
    - Text extraction
    - Semantic search
    - Vector storage
    
    Next: Phase 2 - Web UI 🎨
    """)
    
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    )
