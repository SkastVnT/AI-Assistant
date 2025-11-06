"""
RAG Services - Main Flask Application
Phase 1: Core RAG functionality with FREE models
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime
import time

from app.core.config import settings, MODELS_INFO
from app.core.vectorstore import get_vector_store
from app.core.document_processor import DocumentProcessor
from app.core.rag_engine import get_rag_engine
from app.core.chat_history import get_chat_history
from app.core.filters import SearchFilters
from app.core.analytics import get_analytics_tracker

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
    Request body: { 
        "query": "...", 
        "top_k": 5,
        "filters": {
            "documents": [...],
            "file_types": [...],
            "min_score": 0.7
        }
    }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', settings.TOP_K_RESULTS)
        filters = data.get('filters', {})
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Search in vector store
        vector_store = get_vector_store()
        results = vector_store.search(query, top_k=top_k * 2)  # Get more for filtering
        
        # Apply advanced filters
        if filters.get('documents'):
            results = SearchFilters.filter_by_documents(results, filters['documents'])
        
        if filters.get('file_types'):
            results = SearchFilters.filter_by_file_type(results, filters['file_types'])
        
        if filters.get('min_score'):
            results = SearchFilters.filter_by_score(
                results, 
                min_score=filters['min_score']
            )
        
        # Limit to top_k after filtering
        results = results[:top_k]
        
        # Track analytics
        response_time = time.time() - start_time
        documents_used = SearchFilters.get_available_documents(results)
        
        analytics = get_analytics_tracker()
        analytics.track_query(
            query=query,
            mode='search',
            results_count=len(results),
            response_time=response_time,
            success=True,
            documents_used=documents_used
        )
        
        # Get statistics
        stats = SearchFilters.get_statistics(results)
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results),
            'stats': stats,
            'response_time': response_time
        })
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        
        # Track failed query
        try:
            analytics = get_analytics_tracker()
            analytics.track_query(
                query=query,
                mode='search',
                results_count=0,
                response_time=time.time() - start_time,
                success=False
            )
        except:
            pass
        
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
        "language": "auto",  // auto, vi, en
        "use_history": false,
        "session_id": null
    }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', settings.TOP_K_RESULTS)
        language = data.get('language', 'auto')
        use_history = data.get('use_history', False)
        session_id = data.get('session_id')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get RAG engine
        rag_engine = get_rag_engine()
        
        # Get chat history if needed
        chat_history = get_chat_history()
        conversation_context = None
        
        if use_history and session_id:
            try:
                chat_history.load_session(session_id)
                conversation_context = chat_history.get_context_for_query(max_messages=6)
            except:
                pass  # Continue without history
        
        # Generate answer
        result = rag_engine.query(
            question=query,
            top_k=top_k,
            language=language,
            conversation_context=conversation_context
        )
        
        # Save to chat history if session active
        if session_id:
            try:
                if not use_history:  # Start new session
                    chat_history.start_session(session_id)
                
                chat_history.add_message('user', query)
                chat_history.add_message(
                    'assistant', 
                    result['answer'],
                    metadata={'sources': result.get('sources', [])}
                )
            except Exception as e:
                print(f"⚠️ Failed to save to chat history: {e}")
        
        # Track analytics
        response_time = time.time() - start_time
        documents_used = [s['source'] for s in result.get('sources', [])]
        
        analytics = get_analytics_tracker()
        analytics.track_query(
            query=query,
            mode='rag',
            results_count=len(result.get('sources', [])),
            response_time=response_time,
            success=True,
            documents_used=documents_used
        )
        
        result['response_time'] = response_time
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ RAG query error: {e}")
        
        # Track failed query
        try:
            analytics = get_analytics_tracker()
            analytics.track_query(
                query=query,
                mode='rag',
                results_count=0,
                response_time=time.time() - start_time,
                success=False
            )
        except:
            pass
        
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


# ==================== CHAT HISTORY ENDPOINTS ====================

@app.route('/api/chat/start', methods=['POST'])
def start_chat():
    """
    Start new chat session
    Request body: { "session_id": "optional-custom-id" }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        chat_history = get_chat_history()
        session_id = chat_history.start_session(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'New chat session started'
        })
        
    except Exception as e:
        print(f"❌ Start chat error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/sessions', methods=['GET'])
def list_sessions():
    """List all saved chat sessions"""
    try:
        chat_history = get_chat_history()
        sessions = chat_history.list_sessions()
        
        return jsonify({
            'sessions': sessions,
            'count': len(sessions)
        })
        
    except Exception as e:
        print(f"❌ List sessions error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Load specific chat session"""
    try:
        chat_history = get_chat_history()
        session_data = chat_history.load_session(session_id)
        
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify(session_data)
        
    except Exception as e:
        print(f"❌ Get session error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/session/<session_id>/save', methods=['POST'])
def save_session(session_id):
    """
    Save current session
    Request body: { "session_name": "Optional custom name" }
    """
    try:
        data = request.get_json() or {}
        session_name = data.get('session_name')
        
        chat_history = get_chat_history()
        chat_history.load_session(session_id)  # Load if not current
        chat_history.save_session(session_name)
        
        return jsonify({
            'success': True,
            'message': 'Session saved successfully'
        })
        
    except Exception as e:
        print(f"❌ Save session error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete chat session"""
    try:
        chat_history = get_chat_history()
        chat_history.delete_session(session_id)
        
        return jsonify({
            'success': True,
            'message': f'Session {session_id} deleted'
        })
        
    except Exception as e:
        print(f"❌ Delete session error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/session/<session_id>/export', methods=['GET'])
def export_session(session_id):
    """
    Export chat session
    Query params: ?format=txt (or md)
    """
    try:
        format_type = request.args.get('format', 'txt')
        
        chat_history = get_chat_history()
        content = chat_history.export_session(session_id, format_type)
        
        if not content:
            return jsonify({'error': 'Session not found'}), 404
        
        # Return as file
        from flask import Response
        
        filename = f"chat_{session_id}.{format_type}"
        return Response(
            content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        print(f"❌ Export session error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== FILTER & ANALYTICS ENDPOINTS ====================

@app.route('/api/filters/available', methods=['GET'])
def get_available_filters():
    """Get available filter options"""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        
        # Get all documents
        documents = stats.get('sources', [])
        
        # Extract file types
        file_types = set()
        for doc in documents:
            ext = '.' + doc.get('file_type', '').lower()
            if ext != '.':
                file_types.add(ext)
        
        return jsonify({
            'documents': [d['name'] for d in documents],
            'file_types': sorted(list(file_types)),
            'total_documents': len(documents)
        })
        
    except Exception as e:
        print(f"❌ Get filters error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/dashboard', methods=['GET'])
def get_analytics_dashboard():
    """Get complete analytics dashboard"""
    try:
        analytics = get_analytics_tracker()
        dashboard = analytics.get_dashboard_data()
        
        return jsonify(dashboard)
        
    except Exception as e:
        print(f"❌ Analytics error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/trends', methods=['GET'])
def get_query_trends():
    """
    Get query trends
    Query params: ?period=day (or hour, week)
    """
    try:
        period = request.args.get('period', 'day')
        
        analytics = get_analytics_tracker()
        trends = analytics.get_query_trends(period)
        
        return jsonify({
            'period': period,
            'trends': trends
        })
        
    except Exception as e:
        print(f"❌ Trends error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/popular', methods=['GET'])
def get_popular_items():
    """Get popular queries and documents"""
    try:
        top_n = int(request.args.get('top_n', 10))
        
        analytics = get_analytics_tracker()
        
        return jsonify({
            'popular_queries': analytics.get_popular_queries(top_n),
            'popular_documents': analytics.get_popular_documents(top_n)
        })
        
    except Exception as e:
        print(f"❌ Popular items error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/export', methods=['GET'])
def export_analytics():
    """Export analytics report"""
    try:
        analytics = get_analytics_tracker()
        
        # Export to temp file
        from tempfile import NamedTemporaryFile
        
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            analytics.export_report(Path(f.name))
            temp_path = f.name
        
        # Read and return
        from flask import send_file
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f'analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
    except Exception as e:
        print(f"❌ Export analytics error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== VIETNAMESE OPTIMIZATION ENDPOINTS ====================

@app.route('/api/vietnamese/analyze', methods=['POST'])
def analyze_vietnamese_text():
    """
    Analyze Vietnamese text
    Request body: { "text": "..." }
    """
    try:
        from app.core.vietnamese_processor import get_vietnamese_processor
        
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        vi_processor = get_vietnamese_processor()
        
        # Analyze text
        result = {
            'language': vi_processor.detect_language(text),
            'statistics': vi_processor.get_statistics(text),
            'cleaned': vi_processor.clean_text(text),
            'sentences': vi_processor.segment_sentences(text),
            'tokens': vi_processor.tokenize_words(text)
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Vietnamese analysis error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vietnamese/process', methods=['POST'])
def process_vietnamese_query():
    """
    Process Vietnamese query for search
    Request body: { "query": "...", "enhance": true }
    """
    try:
        from app.core.vietnamese_processor import get_vietnamese_processor
        
        data = request.get_json()
        query = data.get('query', '')
        enhance = data.get('enhance', True)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        vi_processor = get_vietnamese_processor()
        
        # Process query
        result = {
            'original': query,
            'language': vi_processor.detect_language(query),
            'processed': vi_processor.process_query(query, enhance),
            'tokens': vi_processor.tokenize_words(query),
            'cleaned': vi_processor.clean_text(query)
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Vietnamese processing error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vietnamese/status', methods=['GET'])
def vietnamese_status():
    """Check if Vietnamese libraries are available"""
    try:
        from app.core.vietnamese_processor import VIETNAMESE_AVAILABLE
        
        return jsonify({
            'available': VIETNAMESE_AVAILABLE,
            'message': 'Vietnamese optimization ready' if VIETNAMESE_AVAILABLE else 'Vietnamese libraries not installed'
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
    ║     �🇳 Vietnamese-optimized (Phase 5)                     ║
    ║                                                           ║
    ║     Models:                                               ║
    ║     📊 Embedding: {MODELS_INFO['embedding']['name'][:30]:<30} ║
    ║     💾 VectorDB: {MODELS_INFO['vectordb']['name']:<30}      ║
    ║                                                           ║
    ║     🌐 Server: http://{settings.HOST}:{settings.PORT}                    ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Phase 1: Core RAG ✅
    Phase 2: Web UI ✅  
    Phase 3: LLM Integration ✅
    Phase 4: Advanced Features ✅
    Phase 5: Vietnamese Optimization ✅
    
    Features:
    - 🔍 Semantic search
    - 💬 Chat history
    - 🔧 Advanced filters
    - 📊 Analytics dashboard
    - 🇻🇳 Vietnamese text processing
    
    Ready to serve! 🚀
    """)
    
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    )
