"""
OCR Routes
OCR processing endpoints
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__)


@ocr_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload file for OCR processing."""
    from ..config import allowed_file
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        allowed = current_app.config.get('ALLOWED_EXTENSIONS', set())
        return jsonify({
            'error': f'File type not allowed. Allowed: {", ".join(allowed)}'
        }), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        filepath = upload_folder / filename
        file.save(str(filepath))
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            'size': os.path.getsize(filepath)
        })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/process', methods=['POST'])
def process_ocr():
    """Process uploaded file with OCR."""
    from ..extensions import get_ocr_processor, get_processing_history
    
    data = request.get_json() or {}
    filename = data.get('filename')
    output_format = data.get('format', 'txt')
    
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400
    
    try:
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        filepath = upload_folder / filename
        
        if not filepath.exists():
            return jsonify({'error': 'File not found'}), 404
        
        # Process with OCR
        processor = get_ocr_processor()
        result = processor.process(str(filepath), output_format)
        
        # Save to history
        history = get_processing_history()
        if history:
            history.add_entry({
                'filename': filename,
                'format': output_format,
                'result': result
            })
        
        return jsonify({
            'success': True,
            'filename': filename,
            'result': result
        })
    
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename: str):
    """Download processed file."""
    output_folder = Path(current_app.config['OUTPUT_FOLDER'])
    filepath = output_folder / filename
    
    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(str(filepath), as_attachment=True)


@ocr_bp.route('/formats', methods=['GET'])
def get_formats():
    """Get supported output formats."""
    return jsonify({
        'formats': ['txt', 'json', 'docx', 'pdf', 'html', 'md'],
        'default': 'txt'
    })
