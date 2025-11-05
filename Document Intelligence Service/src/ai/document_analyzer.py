"""
Document Analyzer
Combines OCR + AI for intelligent document processing
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """
    Complete Document Analysis Pipeline
    OCR + AI Enhancement
    """
    
    def __init__(self, gemini_client: GeminiClient):
        """
        Initialize Document Analyzer
        
        Args:
            gemini_client: Initialized Gemini client
        """
        self.gemini = gemini_client
        logger.info("📊 Document Analyzer initialized")
    
    def analyze_complete(self, ocr_result: Dict[str, Any], 
                        enable_classification: bool = True,
                        enable_extraction: bool = True,
                        enable_summary: bool = True) -> Dict[str, Any]:
        """
        Complete document analysis with AI enhancement
        
        Args:
            ocr_result: OCR processing result
            enable_classification: Enable document classification
            enable_extraction: Enable information extraction
            enable_summary: Enable summarization
            
        Returns:
            Enhanced analysis result
        """
        if not ocr_result.get('success', False):
            return ocr_result
        
        text = ocr_result.get('full_text') or ocr_result.get('text', '')
        
        if not text or len(text.strip()) < 10:
            logger.warning("Text too short for AI analysis")
            return ocr_result
        
        logger.info("🤖 Starting AI enhancement...")
        
        ai_enhancements = {}
        
        # 1. Document Classification
        if enable_classification:
            try:
                classification = self.gemini.classify_document(text)
                ai_enhancements['classification'] = classification
                logger.info(f"✅ Classification: {classification.get('category', 'Unknown')}")
            except Exception as e:
                logger.error(f"Classification failed: {e}")
                ai_enhancements['classification'] = {"success": False, "error": str(e)}
        
        # 2. Information Extraction
        if enable_extraction:
            try:
                doc_type = ai_enhancements.get('classification', {}).get('category', 'general')
                extraction = self.gemini.extract_information(text, doc_type)
                ai_enhancements['extraction'] = extraction
                logger.info("✅ Information extracted")
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                ai_enhancements['extraction'] = {"success": False, "error": str(e)}
        
        # 3. Summarization
        if enable_summary:
            try:
                summary = self.gemini.summarize_document(text)
                ai_enhancements['summary'] = summary
                logger.info("✅ Summary generated")
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                ai_enhancements['summary'] = {"success": False, "error": str(e)}
        
        # Merge with OCR result
        enhanced_result = {
            **ocr_result,
            'ai_enhanced': True,
            'ai_analysis': ai_enhancements
        }
        
        logger.info("🎉 AI enhancement complete!")
        return enhanced_result
    
    def quick_classify(self, text: str) -> str:
        """
        Quick document classification
        
        Args:
            text: Document text
            
        Returns:
            Document category
        """
        result = self.gemini.classify_document(text)
        return result.get('category', 'Unknown')
    
    def extract_fields(self, text: str, fields: list) -> Dict[str, Any]:
        """
        Extract specific fields from document
        
        Args:
            text: Document text
            fields: List of fields to extract
            
        Returns:
            Extracted field values
        """
        prompt = f"""🔍 TRÍCH XUẤT CÁC TRƯỜNG THÔNG TIN

📋 CÁC TRƯỜNG CẦN TRÍCH:
{', '.join(fields)}

📄 VÀN BẢN:
{text}

⚠️ YÊU CẦU:
- Trả về ĐÚNG định dạng JSON
- Key là tên trường (tiếng Việt không dấu, viết thường, dùng _ thay khoảng trắng)
- Value là giá trị tìm được (tiếng Việt có dấu)
- Nếu không tìm thấy: null
- Chỉ trả về JSON, không markdown, không giải thích

🎯 KẾT QUẢ JSON:"""

        try:
            result = self.gemini.generate(prompt)
            # Clean markdown
            result = result.strip()
            if result.startswith('```'):
                result = '\n'.join(result.split('\n')[1:-1])
            
            import json
            return json.loads(result)
        except Exception as e:
            logger.error(f"Field extraction error: {e}")
            return {}
    
    def validate_document(self, text: str, document_type: str) -> Dict[str, Any]:
        """
        Validate document completeness and correctness
        
        Args:
            text: Document text
            document_type: Type of document
            
        Returns:
            Validation result
        """
        prompt = f"""✅ KIỂM TRA TÍNH HỢP LỆ CỦA VÀN BẢN {document_type}

🔍 KIỂM TRA:
1. Các trường thông tin bắt buộc có đầy đủ không?
2. Thông tin có đầy đủ và chính xác không?
3. Định dạng văn bản có đúng chuẩn không?
4. Có thiếu sót hoặc lỗi gì không?

📄 NỘI DUNG VÀN BẢN:
{text}

📋 KẾT QUẢ KIỂM TRA (bằng tiếng Việt):
- Trạng thái: [Hợp lệ/Thiếu thông tin/Có lỗi]
- Các vấn đề phát hiện: [liệt kê cụ thể]
- Đề xuất: [nếu có]"""

        try:
            validation = self.gemini.generate(prompt)
            return {
                "success": True,
                "validation": validation.strip()
            }
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def detect_language(self, text: str) -> str:
        """
        Detect document language
        
        Args:
            text: Document text
            
        Returns:
            Language code
        """
        prompt = f"What language is this text in? Return ONLY the language code (vi, en, zh, ja, ko, etc.):\n\n{text[:200]}"
        
        try:
            lang = self.gemini.generate(prompt).strip().lower()
            return lang if len(lang) <= 3 else "unknown"
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return "unknown"
    
    def format_output(self, text: str, format_type: str = "markdown") -> str:
        """
        Format document output
        
        Args:
            text: Document text
            format_type: Output format (markdown, html, plain)
            
        Returns:
            Formatted text
        """
        format_prompts = {
            "markdown": "Convert this text to well-formatted Markdown with proper headings and structure:",
            "html": "Convert this text to clean HTML with proper tags:",
            "plain": "Format this text as clean plain text with proper line breaks:"
        }
        
        prompt = f"{format_prompts.get(format_type, format_prompts['plain'])}\n\n{text}"
        
        try:
            return self.gemini.generate(prompt)
        except Exception as e:
            logger.error(f"Formatting error: {e}")
            return text
    
    def generate_insights(self, text: str) -> Dict[str, Any]:
        """
        Generate insights and analysis about document
        
        Args:
            text: Document text
            
        Returns:
            Insights
        """
        prompt = f"""💡 PHÂN TÍCH CHUYÊN SÂU VÀN BẢN

🎯 MỤC ĐÍCH CHÍNH:
[Xác định mục đích/đối tượng của văn bản]

📌 ĐIỂM QUAN TRỌNG (3-5 điểm):
1. [Điểm quan trọng thứ nhất]
2. [Điểm quan trọng thứ hai]
3. [Điểm quan trọng thứ ba]
...

📅 NGÀY THÁNG & SỐ LIỆU QUAN TRỌNG:
- [Liệt kê các ngày tháng, số tiền, số lượng quan trọng]

👥 CÁC BÊN LIÊN QUAN:
- [Tên cá nhân/tổ chức và vai trò]

⚡ HÀNH ĐỘNG CẦN THỰC HIỆN (nếu có):
- [Các việc cần làm, thời hạn...]

⚠️ LƯU Ý ĐẶC BIỆT:
- [Các điều khoản, quy định cần chú ý]

📄 NỘI DUNG VÀN BẢN:
{text}

🔍 PHÂN TÍCH:"""

        try:
            insights = self.gemini.generate(prompt)
            return {
                "success": True,
                "insights": insights.strip()
            }
        except Exception as e:
            logger.error(f"Insights generation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
