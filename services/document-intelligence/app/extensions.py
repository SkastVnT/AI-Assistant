"""
Document Intelligence Extensions
Initialize and manage external services
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded components
_ocr_engine = None
_ocr_processor = None
_gemini_client = None
_document_analyzer = None
_batch_processor = None
_processing_history = None
_quick_actions = None


def init_extensions(app):
    """Initialize all extensions with Flask app context."""
    # Create required directories
    upload_folder = Path(app.config.get('UPLOAD_FOLDER', 'uploads'))
    output_folder = Path(app.config.get('OUTPUT_FOLDER', 'output'))
    
    upload_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Initialize history
    global _processing_history, _quick_actions
    from src.utils.advanced_features import ProcessingHistory, QuickActions
    _processing_history = ProcessingHistory(output_folder / 'history.json')
    _quick_actions = QuickActions()
    
    logger.info("Document Intelligence extensions initialized")


def get_ocr_processor():
    """Get or initialize OCR processor (lazy loading)."""
    global _ocr_engine, _ocr_processor
    
    if _ocr_processor is None:
        from flask import current_app
        from src.ocr import PaddleOCREngine, OCRProcessor
        
        logger.info("🚀 Initializing OCR Engine...")
        
        ocr_config = {
            'lang': current_app.config.get('OCR_LANGUAGE', 'vi'),
            'use_gpu': current_app.config.get('OCR_USE_GPU', False),
            'show_log': current_app.config.get('OCR_SHOW_LOG', False)
        }
        
        output_folder = Path(current_app.config.get('OUTPUT_FOLDER', 'output'))
        
        _ocr_engine = PaddleOCREngine(ocr_config)
        _ocr_processor = OCRProcessor(_ocr_engine, output_folder)
        
        logger.info("✅ OCR Engine ready!")
    
    return _ocr_processor


def get_document_analyzer():
    """Get or initialize Document Analyzer with AI (lazy loading)."""
    global _gemini_client, _document_analyzer
    
    from flask import current_app
    
    if not current_app.config.get('ENABLE_AI_ENHANCEMENT', True):
        return None
    
    if _document_analyzer is None:
        try:
            from src.ai import GeminiClient, DocumentAnalyzer
            
            logger.info("🤖 Initializing Gemini AI...")
            
            api_key = current_app.config.get('GEMINI_API_KEY')
            model = current_app.config.get('AI_MODEL', 'gemini-2.0-flash')
            
            _gemini_client = GeminiClient(api_key, model)
            _document_analyzer = DocumentAnalyzer(_gemini_client)
            
            logger.info("✅ AI Enhancement ready!")
        except Exception as e:
            logger.error(f"❌ AI initialization failed: {e}")
            return None
    
    return _document_analyzer


def get_batch_processor():
    """Get or initialize Batch Processor (lazy loading)."""
    global _batch_processor
    
    if _batch_processor is None:
        from src.utils.advanced_features import BatchProcessor
        
        processor = get_ocr_processor()
        _batch_processor = BatchProcessor(processor, max_batch_size=10)
        
        logger.info("📦 Batch Processor ready!")
    
    return _batch_processor


def get_processing_history():
    """Get processing history instance."""
    return _processing_history


def get_quick_actions():
    """Get quick actions instance."""
    return _quick_actions
