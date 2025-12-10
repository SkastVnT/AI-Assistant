"""
OCR Module - PaddleOCR Integration
"""
from .paddle_ocr import PaddleOCREngine
from .processor import OCRProcessor

__all__ = ['PaddleOCREngine', 'OCRProcessor']
