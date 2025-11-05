"""
Configuration for Document Intelligence Service
"""
import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).parent.parent

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5003))
DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 20 * 1024 * 1024))  # 20MB
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff', 'webp'}

# OCR Configuration
OCR_CONFIG = {
    'use_angle_cls': os.getenv('ENABLE_ANGLE_CLS', 'True') == 'True',
    'lang': os.getenv('OCR_LANGUAGE', 'ch'),  # 'ch' includes Vietnamese
    'use_gpu': os.getenv('OCR_USE_GPU', 'False') == 'True',
    'det_model_dir': None,  # Auto download
    'rec_model_dir': None,  # Auto download
    'show_log': False
}

# Processing Options
PROCESSING_OPTIONS = {
    'enable_table_recognition': False,  # Phase 2
    'enable_layout_analysis': False,    # Phase 2
    'enable_ai_understanding': False,   # Phase 4
}

# Create directories if not exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Export configuration
__all__ = [
    'HOST', 'PORT', 'DEBUG',
    'MAX_FILE_SIZE', 'UPLOAD_FOLDER', 'OUTPUT_FOLDER',
    'OCR_CONFIG', 'PROCESSING_OPTIONS',
    'allowed_file'
]
