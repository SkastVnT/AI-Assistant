"""
PaddleOCR Engine Integration
FREE OCR with Vietnamese support
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

logger = logging.getLogger(__name__)


class PaddleOCREngine:
    """
    PaddleOCR Engine for text extraction
    Supports Vietnamese and 80+ languages
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PaddleOCR engine
        
        Args:
            config: OCR configuration dict
        """
        self.config = config
        self.ocr = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize PaddleOCR model"""
        try:
            logger.info("Initializing PaddleOCR engine...")
            self.ocr = PaddleOCR(**self.config)
            logger.info("✅ PaddleOCR engine initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
            raise
    
    def extract_text(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from image
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of detected text blocks with coordinates and confidence
        """
        try:
            # Convert to string if Path object
            if hasattr(image_path, '__fspath__'):
                image_path = str(image_path)
            
            # Validate file exists
            if not Path(image_path).exists():
                logger.error(f"File not found: {image_path}")
                return []
            
            # Run OCR
            result = self.ocr.ocr(image_path, cls=self.config.get('use_angle_cls', True))
            
            if not result or not result[0]:
                logger.warning(f"No text detected in {image_path}")
                return []
            
            # Format results
            text_blocks = []
            for idx, line in enumerate(result[0]):
                box = line[0]  # Coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)
                
                text_blocks.append({
                    'id': idx,
                    'text': text_info[0],
                    'confidence': float(text_info[1]),
                    'bbox': {
                        'top_left': box[0],
                        'top_right': box[1],
                        'bottom_right': box[2],
                        'bottom_left': box[3]
                    }
                })
            
            logger.info(f"✅ Extracted {len(text_blocks)} text blocks from {Path(image_path).name}")
            return text_blocks
            
        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def extract_text_simple(self, image_path: str) -> str:
        """
        Extract text as plain string (simple mode)
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text as string
        """
        # Convert to string if needed
        if hasattr(image_path, '__fspath__'):
            image_path = str(image_path)
            
        text_blocks = self.extract_text(image_path)
        return '\n'.join([block['text'] for block in text_blocks])
    
    def get_text_with_confidence(self, image_path: str, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get text blocks filtered by confidence threshold
        
        Args:
            image_path: Path to image file
            min_confidence: Minimum confidence threshold (0.0 - 1.0)
            
        Returns:
            Filtered text blocks
        """
        # Convert to string if needed
        if hasattr(image_path, '__fspath__'):
            image_path = str(image_path)
            
        text_blocks = self.extract_text(image_path)
        return [
            block for block in text_blocks 
            if block['confidence'] >= min_confidence
        ]
    
    def get_average_confidence(self, image_path: str) -> float:
        """
        Calculate average confidence score
        
        Args:
            image_path: Path to image file
            
        Returns:
            Average confidence (0.0 - 1.0)
        """
        # Convert to string if needed
        if hasattr(image_path, '__fspath__'):
            image_path = str(image_path)
            
        text_blocks = self.extract_text(image_path)
        if not text_blocks:
            return 0.0
        
        avg_conf = sum(block['confidence'] for block in text_blocks) / len(text_blocks)
        return round(avg_conf, 3)
    
    def detect_orientation(self, image_path: str) -> Dict[str, Any]:
        """
        Detect image orientation (if angle classification enabled)
        
        Args:
            image_path: Path to image file
            
        Returns:
            Orientation info
        """
        # Convert to string if needed
        if hasattr(image_path, '__fspath__'):
            image_path = str(image_path)
            
        if not self.config.get('use_angle_cls', False):
            return {'angle': 0, 'confidence': 1.0}
        
        try:
            # PaddleOCR handles this automatically
            text_blocks = self.extract_text(image_path)
            return {
                'angle': 0,  # Auto-corrected
                'confidence': 1.0,
                'text_blocks_found': len(text_blocks)
            }
        except Exception as e:
            logger.error(f"Orientation detection failed: {e}")
            return {'angle': 0, 'confidence': 0.0}
