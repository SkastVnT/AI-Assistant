"""
Configuration for Document Intelligence Service
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).parent.parent

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5004))
DEBUG = False  # Disable debug mode to prevent reloader issues

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 20 * 1024 * 1024))  # 20MB
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff', 'webp'}

# OCR Configuration
OCR_CONFIG = {
    'use_angle_cls': os.getenv('ENABLE_ANGLE_CLS', 'True') == 'True',
    'lang': os.getenv('OCR_LANGUAGE', 'vietnam'),  # Vietnamese language support
    'use_gpu': os.getenv('OCR_USE_GPU', 'False') == 'True',
    'det_model_dir': None,  # Auto download
    'rec_model_dir': None,  # Auto download
    'cls_model_dir': None,  # Auto download
    'show_log': False
}

# AI Enhancement Configuration
GROK_API_KEY = os.getenv('GROK_API_KEY', '')
ENABLE_AI_ENHANCEMENT = (os.getenv('ENABLE_AI_ENHANCEMENT', 'True') == 'True') and bool(GROK_API_KEY)
AI_MODEL = os.getenv('AI_MODEL', 'grok-3')

# AI Features
AI_FEATURES = {
    'enable_classification': os.getenv('ENABLE_CLASSIFICATION', 'True') == 'True',
    'enable_extraction': os.getenv('ENABLE_EXTRACTION', 'True') == 'True',
    'enable_summary': os.getenv('ENABLE_SUMMARY', 'True') == 'True',
    'enable_qa': os.getenv('ENABLE_QA', 'True') == 'True',
    'enable_translation': os.getenv('ENABLE_TRANSLATION', 'True') == 'True',
}

# Processing Options
PROCESSING_OPTIONS = {
    'enable_table_recognition': False,  # Phase 2
    'enable_layout_analysis': False,    # Phase 2
    'enable_ai_understanding': ENABLE_AI_ENHANCEMENT,
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
    'GROK_API_KEY', 'ENABLE_AI_ENHANCEMENT', 'AI_MODEL', 'AI_FEATURES',
    'allowed_file'
]
