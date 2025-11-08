"""
RAG Services - Main Application
Retrieval-Augmented Generation Service for Intelligent Q&A
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
app_dir = Path(__file__).parent / 'app'
sys.path.insert(0, str(app_dir))

# Initialize Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'rag-services-secret-key-2025')
app.config['DEBUG'] = os.getenv('FLASK_ENV', 'development') == 'development'

# Enable CORS
CORS(app, origins='*')

# Port configuration
PORT = int(os.getenv('PORT', 5004))
HOST = os.getenv('HOST', '0.0.0.0')

# Try to import RAG components
try:
    from app.core.rag_engine import RAGEngine
    RAG_AVAILABLE = True
    rag_engine = None  # Will be initialized on first use
except ImportError as e:
    print(f"⚠️  RAG Engine not available: {e}")
    print("📝 Running in demo mode - RAG features will be simulated")
    RAG_AVAILABLE = False
    rag_engine = None


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'RAG Services',
        'version': '1.0.0',
        'rag_available': RAG_AVAILABLE,
        'port': PORT
    })


@app.route('/api/query', methods=['POST'])
def query():
    """
    Query endpoint for RAG
    
    Request body:
    {
        "question": "Your question here",
        "top_k": 5,  // optional
        "language": "auto"  // optional: auto, vi, en
    }
    """
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'Question is required'
            }), 400
        
        # Get optional parameters
        top_k = data.get('top_k', 5)
        language = data.get('language', 'auto')
        
        if RAG_AVAILABLE:
            # Initialize RAG engine if needed
            global rag_engine
            if rag_engine is None:
                try:
                    rag_engine = RAGEngine()
                except Exception as e:
                    print(f"❌ Failed to initialize RAG engine: {e}")
                    return jsonify({
                        'success': False,
                        'error': f'RAG engine initialization failed: {str(e)}'
                    }), 500
            
            # Query RAG engine
            try:
                result = rag_engine.query(
                    question=question,
                    top_k=top_k,
                    language=language
                )
                
                return jsonify({
                    'success': True,
                    'question': question,
                    'answer': result.get('answer', ''),
                    'sources': result.get('sources', []),
                    'metadata': result.get('metadata', {})
                })
            except Exception as e:
                print(f"❌ RAG query error: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Query failed: {str(e)}'
                }), 500
        else:
            # Demo mode response
            return jsonify({
                'success': True,
                'question': question,
                'answer': f'[DEMO MODE] RAG Services đang trong quá trình phát triển. Câu hỏi của bạn: "{question}"',
                'sources': [],
                'metadata': {
                    'mode': 'demo',
                    'note': 'RAG engine not available. Please configure the service properly.'
                }
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/documents')
def list_documents():
    """List all documents in knowledge base"""
    try:
        documents_dir = Path(__file__).parent / 'app' / 'data' / 'documents'
        
        if not documents_dir.exists():
            return jsonify({
                'success': True,
                'documents': [],
                'count': 0
            })
        
        documents = []
        for file_path in documents_dir.rglob('*'):
            if file_path.is_file():
                documents.append({
                    'name': file_path.name,
                    'path': str(file_path.relative_to(documents_dir)),
                    'size': file_path.stat().st_size,
                    'type': file_path.suffix
                })
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """Get service statistics"""
    return jsonify({
        'success': True,
        'stats': {
            'rag_available': RAG_AVAILABLE,
            'total_queries': 0,  # TODO: Implement tracking
            'cache_hits': 0,     # TODO: Implement cache
            'avg_response_time': 0.0
        }
    })


def print_banner():
    """Print startup banner"""
    print("=" * 70)
    print("🚀 RAG SERVICES - RETRIEVAL-AUGMENTED GENERATION")
    print("=" * 70)
    print(f"📍 Service URL: http://{HOST}:{PORT}")
    print(f"🐛 Debug Mode: {app.config['DEBUG']}")
    print(f"🤖 RAG Engine: {'✅ Available' if RAG_AVAILABLE else '⚠️  Not Available (Demo Mode)'}")
    print(f"")
    print(f"📦 Features:")
    print(f"   • Document retrieval with semantic search")
    print(f"   • Multi-LLM support (OpenAI, DeepSeek, Gemini)")
    print(f"   • Vietnamese language optimization")
    print(f"   • Intelligent caching & monitoring")
    print(f"")
    print(f"💡 Important Notes:")
    print(f"   • API endpoint: POST /api/query")
    print(f"   • Health check: GET /api/health")
    print(f"   • Configure .env file with API keys")
    print(f"   • Add documents to app/data/documents/")
    print("=" * 70)


if __name__ == '__main__':
    print_banner()
    
    app.run(
        debug=app.config['DEBUG'],
        host=HOST,
        port=PORT
    )
