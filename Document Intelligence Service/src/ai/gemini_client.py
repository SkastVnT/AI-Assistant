"""
Gemini 2.0 Flash Client
FREE AI model for document understanding
"""
import logging
import os
from typing import Dict, Any, List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Google Gemini 2.0 Flash Client
    FREE API for document intelligence
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google API key
            model_name: Gemini model name
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Gemini API"""
        try:
            genai.configure(api_key=self.api_key)
            
            # Configure model
            generation_config = {
                "temperature": float(os.getenv('AI_TEMPERATURE', 0.7)),
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": int(os.getenv('AI_MAX_TOKENS', 8192)),
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info(f"✅ Gemini {self.model_name} initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate response from Gemini
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return ""
    
    def analyze_text(self, text: str, task: str = "general") -> Dict[str, Any]:
        """
        Analyze text with specific task
        
        Args:
            text: Input text
            task: Analysis task type
            
        Returns:
            Analysis result
        """
        prompts = {
            "general": f"Analyze this document and provide key insights:\n\n{text}",
            "summary": f"Summarize this document in Vietnamese:\n\n{text}",
            "classify": f"Classify this document type (invoice, contract, ID card, form, receipt, etc.):\n\n{text}",
            "extract": f"Extract key information (names, dates, numbers, addresses) from this document in JSON format:\n\n{text}",
        }
        
        prompt = prompts.get(task, prompts["general"])
        
        try:
            result = self.generate(prompt)
            return {
                "success": True,
                "task": task,
                "result": result
            }
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {
                "success": False,
                "task": task,
                "error": str(e)
            }
    
    def classify_document(self, text: str) -> Dict[str, Any]:
        """
        Classify document type
        
        Args:
            text: Document text
            
        Returns:
            Classification result
        """
        prompt = f"""Phân loại loại văn bản tiếng Việt này vào một trong các danh mục sau:

📋 DANH MỤC:
- CMND/CCCD: Chứng minh nhân dân, Căn cước công dân
- Hộ chiếu: Passport
- Bằng lái xe: Giấy phép lái xe
- Hóa đơn: Hóa đơn VAT, hóa đơn điện tử, hóa đơn bán hàng
- Biên lai: Biên lai thu chi, biên lai thanh toán
- Hợp đồng: Hợp đồng lao động, mua bán, thuê nhà, v.v.
- Đơn từ: Đơn xin nghỉ, đơn xin việc, đơn khiếu nại
- Giấy tờ pháp lý: Giấy chứng nhận, giấy tờ tòa án
- Văn bản hành chính: Công văn, thông báo, quyết định
- Bảng lương: Phiếu lương, bảng thanh toán lương
- CV/Hồ sơ: Hồ sơ xin việc, sơ yếu lý lịch
- Khác: Các loại văn bản khác

🎯 YÊU CẦU:
- Chỉ trả về TÊN DANH MỤC (ví dụ: "CMND/CCCD", "Hóa đơn", "Hợp đồng")
- Không giải thích, không thêm ký tự đặc biệt
- Nếu không chắc chắn, chọn danh mục gần nhất

📄 NỘI DUNG VÀN BẢN:
{text[:1500]}"""

        try:
            category = self.generate(prompt).strip()
            return {
                "success": True,
                "category": category,
                "confidence": "high" if len(text) > 100 else "medium"
            }
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {
                "success": False,
                "category": "Unknown",
                "error": str(e)
            }
    
    def extract_information(self, text: str, document_type: str = "general") -> Dict[str, Any]:
        """
        Extract structured information from document
        
        Args:
            text: Document text
            document_type: Type of document
            
        Returns:
            Extracted information
        """
        prompt = f"""Trích xuất thông tin quan trọng từ văn bản {document_type} tiếng Việt này.

🎯 HƯỚNG DẪN THEO LOẠI VÀN BẢN:

📇 CMND/CCCD:
- ho_ten: Họ và tên đầy đủ
- so_cmnd_cccd: Số CMND/CCCD
- ngay_sinh: Ngày tháng năm sinh (DD/MM/YYYY)
- gioi_tinh: Nam/Nữ
- noi_sinh: Nơi sinh
- que_quan: Quê quán
- dia_chi_thuong_tru: Địa chỉ thường trú
- ngay_cap: Ngày cấp
- noi_cap: Nơi cấp

🧾 HÓA ĐƠN:
- ten_cong_ty: Tên công ty/đơn vị
- ma_so_thue: Mã số thuế
- dia_chi: Địa chỉ
- so_hoa_don: Số hóa đơn
- ngay_hoa_don: Ngày lập hóa đơn
- hang_hoa_dich_vu: Danh sách hàng hóa/dịch vụ
- tong_tien: Tổng tiền (số)
- tong_tien_chu: Tổng tiền bằng chữ

📄 HỢP ĐỒNG:
- so_hop_dong: Số hợp đồng
- loai_hop_dong: Loại hợp đồng
- ben_a: Thông tin bên A (tên, địa chỉ, người đại diện)
- ben_b: Thông tin bên B (tên, địa chỉ, người đại diện)
- ngay_ky: Ngày ký kết
- hieu_luc: Thời hạn hiệu lực
- noi_dung: Nội dung chính

📋 ĐƠN TỪ:
- loai_don: Loại đơn (xin nghỉ phép, xin việc, khiếu nại...)
- nguoi_nop_don: Họ tên người nộp đơn
- chuc_vu: Chức vụ/Bộ phận
- ngay_nop: Ngày nộp đơn
- ly_do: Lý do
- thoi_gian: Thời gian (nếu có)

💵 BIÊN LAI:
- so_bien_lai: Số biên lai
- ngay: Ngày lập
- nguoi_nop: Người nộp tiền
- so_tien: Số tiền (số)
- so_tien_chu: Số tiền bằng chữ
- noi_dung: Nội dung thu
- nguoi_thu: Người thu tiền

📄 NỘI DUNG VÀN BẢN:
{text}

⚠️ LƯU Ý:
- Trả về ĐÚNG định dạng JSON
- Giá trị là chuỗi tiếng Việt có dấu
- Nếu không tìm thấy thông tin: null
- Không thêm markdown code block
- Không thêm giải thích"""

        try:
            result = self.generate(prompt)
            # Try to clean JSON from markdown
            result = result.strip()
            if result.startswith('```'):
                result = '\n'.join(result.split('\n')[1:-1])
            
            import json
            extracted = json.loads(result)
            
            return {
                "success": True,
                "data": extracted
            }
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def summarize_document(self, text: str, max_sentences: int = 5) -> Dict[str, Any]:
        """
        Summarize document
        
        Args:
            text: Document text
            max_sentences: Maximum sentences in summary
            
        Returns:
            Summary
        """
        prompt = f"""📝 TÓM TẮT VÀN BẢN TIẾNG VIỆT

🎯 YÊU CẦU:
- Tóm tắt trong tối đa {max_sentences} câu
- Sử dụng tiếng Việt có dấu, chuẩn chính tả
- Tập trung vào thông tin quan trọng: ai, cái gì, khi nào, ở đâu, tại sao
- Giữ nguyên số liệu, tên riêng, địa chỉ nếu có
- Viết súc tích, dễ hiểu
- Không thêm ý kiến cá nhân

📄 VÀN BẢN GỐC:
{text}

💡 TÓM TẮT:"""

        try:
            summary = self.generate(prompt)
            return {
                "success": True,
                "summary": summary.strip()
            }
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def answer_question(self, text: str, question: str) -> Dict[str, Any]:
        """
        Answer question about document
        
        Args:
            text: Document text
            question: User question
            
        Returns:
            Answer
        """
        prompt = f"""❓ TRẢ LỜI CÂU HỎI VỀ VÀN BẢN

📄 NỘI DUNG VÀN BẢN:
{text}

🎯 CÂU HỎI:
{question}

📝 HƯỚNG DẪN TRẢ LỜI:
- Trả lời bằng tiếng Việt có dấu
- Dựa CHÍNH XÁC vào nội dung văn bản
- Trích dẫn cụ thể nếu có số liệu, tên riêng
- Nếu không tìm thấy thông tin: "Không tìm thấy thông tin về [câu hỏi] trong văn bản."
- Trả lời ngắn gọn, súc tích
- Không suy đoán thông tin không có trong văn bản

💬 TRẢ LỜI:"""

        try:
            answer = self.generate(prompt)
            return {
                "success": True,
                "question": question,
                "answer": answer.strip()
            }
        except Exception as e:
            logger.error(f"QA error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def translate_document(self, text: str, target_language: str = "en") -> Dict[str, Any]:
        """
        Translate document
        
        Args:
            text: Document text
            target_language: Target language code (en, vi, zh, ja, ko, etc.)
            
        Returns:
            Translated text
        """
        language_names = {
            "en": "tiếng Anh (English)",
            "vi": "tiếng Việt (Vietnamese)", 
            "zh": "tiếng Trung (Chinese)",
            "ja": "tiếng Nhật (Japanese)",
            "ko": "tiếng Hàn (Korean)",
            "fr": "tiếng Pháp (French)",
            "de": "tiếng Đức (German)",
            "es": "tiếng Tây Ban Nha (Spanish)"
        }
        
        target_lang_name = language_names.get(target_language, target_language)
        
        prompt = f"""🌐 DỊCH VÀN BẢN

🎯 YÊU CẦU:
- Dịch sang: {target_lang_name}
- Giữ nguyên ý nghĩa và ngữ cảnh
- Dịch tự nhiên, không dịch máy cứng nhắc
- Giữ nguyên tên riêng, địa danh nếu không có tên dịch chuẩn
- Giữ nguyên số liệu, ngày tháng, địa chỉ
- Giữ format đoạn văn (xuống dòng, đánh số...)
- Chỉ trả về BẢN DỊCH, không thêm giải thích

📄 VÀN BẢN GỐC:
{text}

✨ BẢN DỊCH:"""

        try:
            translation = self.generate(prompt)
            return {
                "success": True,
                "source_language": "auto",
                "target_language": target_language,
                "translation": translation.strip()
            }
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def compare_documents(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        Compare two documents
        
        Args:
            text1: First document
            text2: Second document
            
        Returns:
            Comparison result
        """
        prompt = f"""🔄 SO SÁNH HAI VÀN BẢN

🎯 YÊU CẦU PHÂN TÍCH:
1️⃣ ĐIỂM GIỐNG NHAU:
   - Nội dung tương đồng
   - Thông tin trùng khớp
   
2️⃣ ĐIỂM KHÁC BIỆT:
   - Thông tin khác nhau
   - Nội dung thêm/bớt
   - Số liệu thay đổi
   
3️⃣ THAY ĐỔI QUAN TRỌNG:
   - Thay đổi về con số, ngày tháng
   - Thay đổi về tên, địa chỉ
   - Thay đổi về điều khoản, quy định

📄 VÀN BẢN 1:
{text1[:1200]}

📄 VÀN BẢN 2:
{text2[:1200]}

📊 KẾT QUẢ SO SÁNH:"""

        try:
            comparison = self.generate(prompt)
            return {
                "success": True,
                "comparison": comparison.strip()
            }
        except Exception as e:
            logger.error(f"Comparison error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
