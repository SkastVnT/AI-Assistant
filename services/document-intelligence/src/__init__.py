"""
Document Intelligence Service - Source Package

Uses lazy imports to handle numpy/opencv compatibility issues.
"""

import logging

logger = logging.getLogger(__name__)

# Lazy imports to avoid ABI compatibility issues
_ocr_loaded = False
_ocr_module = None


def get_ocr():
    """Lazy load OCR module to avoid import issues."""
    global _ocr_loaded, _ocr_module
    if not _ocr_loaded:
        try:
            from . import ocr
            _ocr_module = ocr
        except ImportError as e:
            logger.warning(f"OCR module unavailable: {e}")
            _ocr_module = None
        except Exception as e:
            logger.warning(f"OCR module error: {e}")
            _ocr_module = None
        _ocr_loaded = True
    return _ocr_module


# Utils don't have heavy dependencies
try:
    from . import utils
except ImportError:
    utils = None


__all__ = ['get_ocr', 'utils']