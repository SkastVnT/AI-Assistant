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
    OCR_CONFIG, allowed_file
)
from src.ocr import PaddleOCREngine, OCRProcessor

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

# Initialize OCR Engine (lazy loading)
ocr_engine = None
ocr_processor = None


def get_ocr_processor():
    """Get or initialize OCR processor (lazy loading)"""
    global ocr_engine, ocr_processor
    
    if ocr_processor is None:
        logger.info("🚀 Initializing OCR Engine...")
        ocr_engine = PaddleOCREngine(OCR_CONFIG)
        ocr_processor = OCRProcessor(ocr_engine, OUTPUT_FOLDER)
        logger.info("✅ OCR Engine ready!")
    
    return ocr_processor


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
        'version': '1.0.0 (Phase 1)',
        'ocr_engine': 'PaddleOCR',
        'features': {
            'ocr': True,
            'pdf': True,
            'table_extraction': False,  # Phase 2
            'ai_understanding': False   # Phase 4
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
        
        # Process file
        processor = get_ocr_processor()
        result = processor.process_file(str(filepath), options)
        
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
        filepath = Path(app.config['OUTPUT_FOLDER']) / filename
        
        if not filepath.exists():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(str(filepath), as_attachment=True)
        
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


if __name__ == '__main__':
    logger.info(f"""
    ╔════════════════════════════════════════════════════╗
    ║   📄 Document Intelligence Service - Phase 1      ║
    ║   OCR & WebUI with FREE models                    ║
    ╠════════════════════════════════════════════════════╣
    ║   🌐 URL: http://{HOST}:{PORT}                    
    ║   🎯 OCR Engine: PaddleOCR (Vietnamese)           ║
    ║   📊 Status: Active Development                   ║
    ╚════════════════════════════════════════════════════╝
    """)
    
    app.run(host=HOST, port=PORT, debug=DEBUG)
