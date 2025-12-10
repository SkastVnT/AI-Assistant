"""
OCR Processing Pipeline
Handles image preprocessing, OCR execution, and post-processing
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import fitz  # PyMuPDF
from PIL import Image
import io

from .paddle_ocr import PaddleOCREngine

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    OCR Processing Pipeline
    Handles complete OCR workflow from input to output
    """
    
    def __init__(self, ocr_engine: PaddleOCREngine, output_folder: Path):
        """
        Initialize OCR Processor
        
        Args:
            ocr_engine: Initialized PaddleOCR engine
            output_folder: Folder to save results
        """
        self.ocr = ocr_engine
        self.output_folder = output_folder
        self.output_folder.mkdir(parents=True, exist_ok=True)
    
    def process_image(self, image_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process single image
        
        Args:
            image_path: Path to image file
            options: Processing options
            
        Returns:
            Processing result with extracted text and metadata
        """
        options = options or {}
        image_path = Path(image_path)
        
        try:
            logger.info(f"📄 Processing image: {image_path.name}")
            
            # Verify file exists
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Extract text (always pass string)
            text_blocks = self.ocr.extract_text(str(image_path))
            full_text = '\n'.join([block['text'] for block in text_blocks])
            avg_confidence = self.ocr.get_average_confidence(str(image_path))
            
            # Build result
            result = {
                'success': True,
                'filename': image_path.name,
                'processed_at': datetime.now().isoformat(),
                'statistics': {
                    'total_blocks': len(text_blocks),
                    'average_confidence': avg_confidence,
                    'total_chars': len(full_text),
                    'total_lines': len(full_text.split('\n'))
                },
                'text': full_text,
                'blocks': text_blocks if options.get('include_blocks', True) else None
            }
            
            # Save result if requested
            if options.get('save_output', True):
                self._save_result(result, image_path.stem)
            
            logger.info(f"✅ Successfully processed {image_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process {image_path.name}: {e}")
            return {
                'success': False,
                'filename': image_path.name,
                'error': str(e)
            }
    
    def process_pdf(self, pdf_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process PDF file (extract pages as images and OCR)
        
        Args:
            pdf_path: Path to PDF file
            options: Processing options
            
        Returns:
            Processing result for all pages
        """
        options = options or {}
        pdf_path = Path(pdf_path)
        
        try:
            logger.info(f"📑 Processing PDF: {pdf_path.name}")
            
            # Open PDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            results = []
            all_text = []
            
            # Process each page
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better quality
                img_data = pix.tobytes("png")
                
                # Save temporary image
                temp_img_path = self.output_folder / f"temp_page_{page_num + 1}.png"
                with open(temp_img_path, 'wb') as f:
                    f.write(img_data)
                
                # OCR the page
                page_result = self.process_image(str(temp_img_path), {**options, 'save_output': False})
                page_result['page_number'] = page_num + 1
                results.append(page_result)
                
                if page_result['success']:
                    all_text.append(f"=== Page {page_num + 1} ===\n{page_result['text']}\n")
                
                # Clean up temp file
                temp_img_path.unlink()
            
            doc.close()
            
            # Combined result
            combined_result = {
                'success': True,
                'filename': pdf_path.name,
                'type': 'pdf',
                'processed_at': datetime.now().isoformat(),
                'statistics': {
                    'total_pages': total_pages,
                    'successful_pages': sum(1 for r in results if r['success']),
                    'total_chars': sum(r.get('statistics', {}).get('total_chars', 0) for r in results if r['success'])
                },
                'full_text': '\n'.join(all_text),
                'pages': results
            }
            
            # Save combined result
            if options.get('save_output', True):
                self._save_result(combined_result, pdf_path.stem)
            
            logger.info(f"✅ Successfully processed PDF with {total_pages} pages")
            return combined_result
            
        except Exception as e:
            logger.error(f"❌ Failed to process PDF {pdf_path.name}: {e}")
            return {
                'success': False,
                'filename': pdf_path.name,
                'type': 'pdf',
                'error': str(e)
            }
    
    def process_file(self, file_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process any supported file (auto-detect type)
        
        Args:
            file_path: Path to file
            options: Processing options
            
        Returns:
            Processing result
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext == '.pdf':
            return self.process_pdf(str(file_path), options)
        else:
            return self.process_image(str(file_path), options)
    
    def _save_result(self, result: Dict[str, Any], base_name: str):
        """
        Save processing result to files
        
        Args:
            result: Processing result dict
            base_name: Base filename (without extension)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save JSON
            json_path = self.output_folder / f"{base_name}_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Save TXT (plain text only)
            if 'text' in result or 'full_text' in result:
                txt_path = self.output_folder / f"{base_name}_{timestamp}.txt"
                text_content = result.get('full_text', result.get('text', ''))
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                logger.info(f"💾 Saved results: {json_path.name}, {txt_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp', 'pdf']
