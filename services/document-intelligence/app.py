"""
Document Intelligence Service - Main Flask Application
Phase 1: Basic OCR & WebUI
"""
import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configurations and modules
from config import (
    HOST, PORT, DEBUG, 
    MAX_FILE_SIZE, UPLOAD_FOLDER, OUTPUT_FOLDER,
    OCR_CONFIG, GEMINI_API_KEY, ENABLE_AI_ENHANCEMENT, AI_MODEL, AI_FEATURES,
    allowed_file
)
from src.ocr import PaddleOCREngine, OCRProcessor
from src.ai import GeminiClient, DocumentAnalyzer
from src.utils.advanced_features import (
    BatchProcessor, DocumentTemplates, ProcessingHistory,
    TextFormatter, QuickActions
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['OUTPUT_FOLDER'] = str(OUTPUT_FOLDER)

# Enable CORS
CORS(app)

# Initialize OCR Engine and AI (lazy loading)
ocr_engine = None
ocr_processor = None
gemini_client = None
document_analyzer = None

# Initialize advanced features
batch_processor = None
processing_history = ProcessingHistory(OUTPUT_FOLDER / 'history.json')
quick_actions = QuickActions()


def get_ocr_processor():
    """Get or initialize OCR processor (lazy loading)"""
    global ocr_engine, ocr_processor
    
    if ocr_processor is None:
        logger.info("🚀 Initializing OCR Engine...")
        ocr_engine = PaddleOCREngine(OCR_CONFIG)
        ocr_processor = OCRProcessor(ocr_engine, OUTPUT_FOLDER)
        logger.info("✅ OCR Engine ready!")
    
    return ocr_processor


def get_document_analyzer():
    """Get or initialize Document Analyzer with AI (lazy loading)"""
    global gemini_client, document_analyzer
    
    if not ENABLE_AI_ENHANCEMENT:
        return None
    
    if document_analyzer is None:
        try:
            logger.info("🤖 Initializing Gemini AI...")
            gemini_client = GeminiClient(GEMINI_API_KEY, AI_MODEL)
            document_analyzer = DocumentAnalyzer(gemini_client)
            logger.info("✅ AI Enhancement ready!")
        except Exception as e:
            logger.error(f"❌ AI initialization failed: {e}")
            return None
    
    return document_analyzer


def get_batch_processor():
    """Get or initialize Batch Processor (lazy loading)"""
    global batch_processor
    
    if batch_processor is None:
        processor = get_ocr_processor()
        batch_processor = BatchProcessor(processor, max_batch_size=10)
        logger.info("📦 Batch Processor ready!")
    
    return batch_processor


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Document Intelligence Service',
        'version': '1.5.0 (Phase 1.5 - AI Enhanced)',
        'ocr_engine': 'PaddleOCR',
        'ai_model': AI_MODEL if ENABLE_AI_ENHANCEMENT else None,
        'features': {
            'ocr': True,
            'pdf': True,
            'ai_enhancement': ENABLE_AI_ENHANCEMENT,
            'classification': AI_FEATURES.get('enable_classification', False),
            'extraction': AI_FEATURES.get('enable_extraction', False),
            'summary': AI_FEATURES.get('enable_summary', False),
            'qa': AI_FEATURES.get('enable_qa', False),
            'translation': AI_FEATURES.get('enable_translation', False),
            'table_extraction': False,  # Phase 2
        }
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Upload and process document
    
    Request:
        - file: Document file (image or PDF)
        - options: Processing options (JSON)
        
    Response:
        - success: boolean
        - result: OCR result with text and metadata
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not supported. Allowed: {", ".join(["png", "jpg", "jpeg", "pdf", "bmp", "tiff", "webp"])}'
            }), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(filepath))
        
        logger.info(f"📁 Uploaded file: {filename}")
        
        # Get processing options
        options = request.form.get('options', '{}')
        import json
        options = json.loads(options) if options else {}
        
        # Process file with OCR
        processor = get_ocr_processor()
        result = processor.process_file(str(filepath), options)
        
        # AI Enhancement (if enabled)
        if ENABLE_AI_ENHANCEMENT and result.get('success', False):
            analyzer = get_document_analyzer()
            if analyzer:
                try:
                    logger.info("🤖 Applying AI enhancement...")
                    result = analyzer.analyze_complete(
                        result,
                        enable_classification=AI_FEATURES.get('enable_classification', True) and options.get('ai_classify', True),
                        enable_extraction=AI_FEATURES.get('enable_extraction', True) and options.get('ai_extract', True),
                        enable_summary=AI_FEATURES.get('enable_summary', True) and options.get('ai_summary', True)
                    )
                except Exception as e:
                    logger.error(f"AI enhancement error: {e}")
                    result['ai_error'] = str(e)
        
        # Save to history
        if result.get('success', False):
            processing_history.add_entry({
                'filename': filename,
                'text': result.get('text', '')[:500],  # First 500 chars
                'document_type': result.get('document_type'),
                'ai_enhanced': ENABLE_AI_ENHANCEMENT and 'ai_analysis' in result
            })
        
        # Clean up uploaded file (optional)
        if options.get('delete_after_processing', True):
            filepath.unlink()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/process', methods=['POST'])
def process_text():
    """
    Process extracted text (post-processing)
    
    Request:
        - text: Extracted text
        - action: Processing action (format, clean, etc.)
        
    Response:
        - success: boolean
        - result: Processed text
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        action = data.get('action', 'format')
        
        if action == 'format':
            # Basic formatting
            result = text.strip()
            result = '\n'.join([line.strip() for line in result.split('\n') if line.strip()])
        
        elif action == 'clean':
            # Remove extra whitespace
            import re
            result = re.sub(r'\s+', ' ', text)
            result = result.strip()
        
        else:
            result = text
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_result(filename):
    """Download processed result file"""
    try:
        output_folder = Path(app.config['OUTPUT_FOLDER']).resolve()
        requested_path = (output_folder / filename).resolve()
        
        # Ensure the requested path is within the output folder
        try:
            # Python 3.9+ provides is_relative_to, fallback for older Python is manual check
            if hasattr(requested_path, "is_relative_to"):
                if not requested_path.is_relative_to(output_folder):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid file path'
                    }), 400
            else:
                # Fallback for Python < 3.9
                if str(requested_path).startswith(str(output_folder) + os.sep):
                    pass
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid file path'
                    }), 400
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 400

        if not requested_path.exists():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(str(requested_path), as_attachment=True)
        
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/formats', methods=['GET'])
def get_supported_formats():
    """Get list of supported file formats"""
    processor = get_ocr_processor()
    return jsonify({
        'formats': processor.get_supported_formats(),
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024)
    })


# ============ AI Enhancement Endpoints ============

@app.route('/api/ai/classify', methods=['POST'])
def ai_classify():
    """
    Classify document type using AI
    
    Request:
        - text: Document text
        
    Response:
        - category: Document category
        - confidence: Confidence level
    """
    if not ENABLE_AI_ENHANCEMENT:
        return jsonify({
            'success': False,
            'error': 'AI enhancement is not enabled'
        }), 400
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        analyzer = get_document_analyzer()
        if not analyzer:
            return jsonify({
                'success': False,
                'error': 'AI analyzer not available'
            }), 503
        
        result = analyzer.gemini.classify_document(text)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Classification error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/extract', methods=['POST'])
def ai_extract():
    """
    Extract structured information using AI
    
    Request:
        - text: Document text
        - document_type: Type of document (optional)
        
    Response:
        - data: Extracted structured data
    """
    if not ENABLE_AI_ENHANCEMENT:
        return jsonify({
            'success': False,
            'error': 'AI enhancement is not enabled'
        }), 400
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        doc_type = data.get('document_type', 'general')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        analyzer = get_document_analyzer()
        if not analyzer:
            return jsonify({
                'success': False,
                'error': 'AI analyzer not available'
            }), 503
        
        result = analyzer.gemini.extract_information(text, doc_type)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Extraction error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/summarize', methods=['POST'])
def ai_summarize():
    """
    Summarize document using AI
    
    Request:
        - text: Document text
        - max_sentences: Maximum sentences (optional)
        
    Response:
        - summary: Document summary
    """
    if not ENABLE_AI_ENHANCEMENT:
        return jsonify({
            'success': False,
            'error': 'AI enhancement is not enabled'
        }), 400
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        max_sentences = data.get('max_sentences', 5)
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        analyzer = get_document_analyzer()
        if not analyzer:
            return jsonify({
                'success': False,
                'error': 'AI analyzer not available'
            }), 503
        
        result = analyzer.gemini.summarize_document(text, max_sentences)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Summarization error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/qa', methods=['POST'])
def ai_question_answer():
    """
    Answer questions about document using AI
    
    Request:
        - text: Document text
        - question: User question
        
    Response:
        - answer: AI answer
    """
    if not ENABLE_AI_ENHANCEMENT:
        return jsonify({
            'success': False,
            'error': 'AI enhancement is not enabled'
        }), 400
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        question = data.get('question', '')
        
        if not text or not question:
            return jsonify({
                'success': False,
                'error': 'Text and question are required'
            }), 400
        
        analyzer = get_document_analyzer()
        if not analyzer:
            return jsonify({
                'success': False,
                'error': 'AI analyzer not available'
            }), 503
        
        result = analyzer.gemini.answer_question(text, question)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ QA error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/translate', methods=['POST'])
def ai_translate():
    """
    Translate document using AI
    
    Request:
        - text: Document text
        - target_language: Target language code (en, vi, zh, etc.)
        
    Response:
        - translation: Translated text
    """
    if not ENABLE_AI_ENHANCEMENT:
        return jsonify({
            'success': False,
            'error': 'AI enhancement is not enabled'
        }), 400
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_lang = data.get('target_language', 'en')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        analyzer = get_document_analyzer()
        if not analyzer:
            return jsonify({
                'success': False,
                'error': 'AI analyzer not available'
            }), 503
        
        result = analyzer.gemini.translate_document(text, target_lang)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Translation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/insights', methods=['POST'])
def ai_insights():
    """
    Generate insights about document using AI
    
    Request:
        - text: Document text
        
    Response:
        - insights: Document insights
    """
    if not ENABLE_AI_ENHANCEMENT:
        return jsonify({
            'success': False,
            'error': 'AI enhancement is not enabled'
        }), 400
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        analyzer = get_document_analyzer()
        if not analyzer:
            return jsonify({
                'success': False,
                'error': 'AI analyzer not available'
            }), 503
        
        result = analyzer.generate_insights(text)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Insights error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB'
    }), 413


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server error"""
    logger.error(f"Internal error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ===== NEW FEATURES: Advanced Tools =====

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all document templates"""
    return jsonify({
        'success': True,
        'templates': DocumentTemplates.get_all_templates()
    })


@app.route('/api/templates/match', methods=['POST'])
def match_template():
    """Match document text to best template"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'No text provided'
        }), 400
    
    matched = DocumentTemplates.match_document(text)
    template = DocumentTemplates.get_template(matched) if matched else None
    
    return jsonify({
        'success': True,
        'matched_template': matched,
        'template': template
    })


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get processing history"""
    limit = request.args.get('limit', 20, type=int)
    history = processing_history.get_history(limit)
    
    return jsonify({
        'success': True,
        'count': len(history),
        'history': history
    })


@app.route('/api/history/search', methods=['GET'])
def search_history():
    """Search processing history"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'No query provided'
        }), 400
    
    results = processing_history.search_history(query)
    
    return jsonify({
        'success': True,
        'query': query,
        'count': len(results),
        'results': results
    })


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear processing history"""
    processing_history.clear_history()
    
    return jsonify({
        'success': True,
        'message': 'History cleared'
    })


@app.route('/api/quick-actions/clean', methods=['POST'])
def quick_clean():
    """Clean text (remove duplicates, fix spacing)"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'No text provided'
        }), 400
    
    result = quick_actions.clean_text(text)
    return jsonify(result)


@app.route('/api/quick-actions/extract', methods=['POST'])
def quick_extract():
    """Extract information (numbers, dates, emails, phones)"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'No text provided'
        }), 400
    
    result = quick_actions.extract_info(text)
    return jsonify(result)


@app.route('/api/quick-actions/format', methods=['POST'])
def quick_format():
    """Format text (capitalize, line numbers, etc.)"""
    data = request.get_json()
    text = data.get('text', '')
    action = data.get('action', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'No text provided'
        }), 400
    
    if not action:
        return jsonify({
            'success': False,
            'error': 'No action specified'
        }), 400
    
    result = quick_actions.format_text(text, action)
    return jsonify(result)


@app.route('/api/batch', methods=['POST'])
def batch_upload():
    """
    Batch upload and process multiple files
    
    Request:
        - files: Multiple files
        
    Response:
        - success: boolean
        - results: Array of processing results
    """
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        files = request.files.getlist('files')
        
        if len(files) == 0:
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400
        
        # Save files temporarily
        file_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = UPLOAD_FOLDER / filename
                file.save(str(filepath))
                file_paths.append(str(filepath))
        
        if len(file_paths) == 0:
            return jsonify({
                'success': False,
                'error': 'No valid files provided'
            }), 400
        
        # Process batch
        processor = get_batch_processor()
        result = processor.process_batch(file_paths)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in batch upload: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    ai_status = "✅ Enabled" if ENABLE_AI_ENHANCEMENT else "❌ Disabled"
    ai_model_info = f" ({AI_MODEL})" if ENABLE_AI_ENHANCEMENT else ""
    
    logger.info(f"""
    ╔════════════════════════════════════════════════════╗
    ║   📄 Document Intelligence Service v1.6.0         ║
    ║   OCR + AI + Advanced Tools                       ║
    ╠════════════════════════════════════════════════════╣
    ║   🌐 URL: http://{HOST}:{PORT}                    
    ║   🎯 OCR: PaddleOCR (Vietnamese)                  ║
    ║   🤖 AI: {ai_status}{ai_model_info}
    ║   📊 Status: Production Ready                     ║
    ╚════════════════════════════════════════════════════╝
    
    🚀 Core Features:
       ✅ OCR Text Extraction (Vietnamese optimized)
       ✅ PDF Multi-page Support
       {"✅" if ENABLE_AI_ENHANCEMENT else "❌"} AI Document Classification
       {"✅" if ENABLE_AI_ENHANCEMENT else "❌"} Smart Information Extraction
       {"✅" if ENABLE_AI_ENHANCEMENT else "❌"} Document Summarization
       {"✅" if ENABLE_AI_ENHANCEMENT else "❌"} Q&A over Documents
       {"✅" if ENABLE_AI_ENHANCEMENT else "❌"} Multi-language Translation
    
    ⚡ NEW Advanced Features:
       ✅ Batch Processing (up to 10 files)
       ✅ Document Templates (CMND, Invoice, Contract...)
       ✅ Processing History with Search
       ✅ Quick Actions (Clean, Extract, Format)
       ✅ Text Formatter Utilities
    """)
    
    app.run(host=HOST, port=PORT, debug=DEBUG)
