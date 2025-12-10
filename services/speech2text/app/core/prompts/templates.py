"""
Prompt Engineering Templates for VistralS2T
Contains optimized prompts for transcript fusion and enhancement
Version: 3.6.3 - ENFORCED speaker role detection with stricter rules
"""

from typing import Optional


class PromptTemplates:
    """
    Collection of prompt templates for different tasks
    """
    
    # Prompt version for cache invalidation
    VERSION = "3.6.3"
    LAST_UPDATED = "2025-10-27"
    
    # System prompt for Qwen fusion
    SYSTEM_PROMPT = """Bạn là chuyên gia AI xử lý transcript cuộc gọi dịch vụ khách hàng.
BẮT BUỘC thực hiện:
1. XÓA HOÀN TOÀN quảng cáo/nhiễu không liên quan
2. PHÂN VAI NGƯỜI NÓI CỨNG: Hệ thống/Nhân viên/Khách hàng (KHÔNG ĐƯỢC BỎ QUA)
3. Giữ nguyên 100% nội dung cuộc gọi
4. Sửa lỗi chính tả và định dạng

⚠️ CRITICAL: Mỗi câu thoại PHẢI CÓ nhãn vai trò ở đầu dòng!"""
    
    # Task instructions for fusion
    FUSION_TASK = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 NHIỆM VỤ: Làm sạch và phân vai transcript
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Input: Transcript thô từ speech-to-text model
Output: Transcript đã làm sạch với phân vai rõ ràng

🔴 BƯỚC 1: XÓA NHIỄU (BẮT BUỘC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ XÓA TOÀN BỘ các cụm từ sau (quảng cáo YouTube):
   - "Hãy subscribe cho kênh..."
   - "Đăng ký kênh..." 
   - "Like và share..."
   - "Để không bỏ lỡ video..."
   - "Theo dõi kênh..."
   - "Nhấn nút đăng ký..."
   - Bất kỳ câu nào chứa: "subscribe", "đăng ký", "like", "share", "video", "kênh"

✅ GIỮ LẠI (không xóa):
   - "Cảm ơn quý khách đã gọi đến..." → Lời chào hệ thống
   - "Cảm ơn anh/chị" → Lời cảm ơn trong cuộc gọi
   - "Dạ em cảm ơn" → Kết thúc lịch sự

🟢 BƯỚC 2: PHÂN VAI NGƯỜI NÓI (BẮT BUỘC - KHÔNG ĐƯỢC BỎ QUA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ MỖI CÂU THOẠI PHẢI BẮT ĐẦU BẰNG MỘT TRONG 3 NHÃN SAU:

� **Hệ thống:** (giọng máy tự động IVR)
   Dấu hiệu:
   - Câu đầu tiên của cuộc gọi
   - "Cảm ơn quý khách đã gọi đến..."
   - "Cước phí cuộc gọi là..."
   - "Vui lòng bấm phím..."
   - Giọng máy, không có xưng hô
   - Thông báo chính sách, hướng dẫn

� **Nhân viên:** (nhân viên tổng đài/shipper/hỗ trợ)
   Dấu hiệu:
   - Xưng "em", "bên em", "em của GHN"
   - Gọi khách "anh", "chị", "quý khách"
   - Hỏi thông tin: "Em xin tên anh/chị", "Cho em mã đơn"
   - Kiểm tra hệ thống: "Em thấy đơn...", "Em kiểm tra..."
   - Xin lỗi: "Em xin lỗi", "Dạ", "Vâng ạ"
   - Cam kết: "Em sẽ...", "Bên em sẽ..."

� **Khách hàng:** (người gọi/nhận cuộc gọi)
   Dấu hiệu:
   - Xưng "tôi", "anh", "chị", "mình"
   - Gọi nhân viên "em"
   - Yêu cầu: "Nhờ em hỗ trợ...", "Em kiểm tra giúp..."
   - Cung cấp thông tin: mã đơn, địa chỉ, số điện thoại
   - Phàn nàn: "Sao mà...", "Tại sao...", "Bên em..."
   - Thắc mắc: "Vậy...", "Thế...", "Như vậy..."

🔵 BƯỚC 3: GIỮ NGUYÊN NỘI DUNG (100%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ KHÔNG ĐƯỢC lược bỏ:
   - Bất kỳ câu nào của Hệ thống/Nhân viên/Khách hàng
   - Mã đơn hàng: G-I-V-6-I-A, GIVBBBBI69F, v.v.
   - Số điện thoại, địa chỉ cụ thể
   - Tên người: Mai Nguyên, Anh Thiên, Lisa Thạch
   - Địa danh: Đồng Nai, Tâm Phước, Trà Vinh
   - Số tiền, ngày tháng

✅ CHỈ SỬA:
   - Lỗi chính tả: "hỏang" → "hoàng", "đươc" → "được"
   - Dấu câu: Thêm dấu . , ? ! : ... cho dễ đọc
   - Ngữ pháp: Tự nhiên, mượt mà

🟣 BƯỚC 4: ĐỊNH DẠNG OUTPUT (BẮT BUỘC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Format chuẩn (KHÔNG ĐƯỢC SAI):

Vai trò: Nội dung câu thoại.

Vai trò: Nội dung câu thoại tiếp theo.

⚠️ QUY TẮC CỨNG:
- MỖI DÒNG = 1 LƯỢT NÓI
- Vai trò PHẢI là một trong: "Hệ thống:", "Nhân viên:", "Khách hàng:"
- Có dấu hai chấm ":" sau vai trò
- Có khoảng trống giữa các lượt thoại
- Không được viết "SPEAKER_00:", "Speaker 1:", v.v."""
    
    # Output format example
    OUTPUT_FORMAT = """MẪU ĐỊNH DẠNG:

Hệ thống: Cảm ơn quý khách đã gọi đến tổng đài Giao Hàng Nhanh. Cước phí cuộc gọi là 1000 đồng một phút.

Nhân viên: Nhân viên hỗ trợ khách hàng, quý khách xin nghe. Em hỗ trợ cho anh chị.

Khách hàng: Nhờ em hỗ trợ giúm chị cái đơn hàng là GIVBBBBI69F, F là S.

Nhân viên: Em xin tên chị.

Khách hàng: Chị Hoàng Đông.

Nhân viên: Chị Đông, đơn gọi cho Lisa Thạch ở Duyên Hải, Trà Vinh hả chị?

Khách hàng: Đúng rồi.

Nhân viên: Em thấy đơn mình có xác nhận nhau lại, mà chưa có phân tiến cho nhân viên giao. Còn có giao đơn đúng không chị?

Khách hàng: Có, nhưng mà cho em bảo cái này. Nhiều lúc thời gian này em vẫn thông cảm, mưa gió thì em không nói. Cái vấn đề là khách thì cần hàng. Số điện thoại của khách em vẫn liên lạc bình thường, bao nhiêu lần ở trên app báo là không liên lạc với khách, khách chặn số. Em gọi lại cho khách luôn theo số điện thoại đó, vẫn liên lạc được khách, vẫn chờ hàng. Rồi cuối cùng cũng không giao, ngày này qua ngày khác. Từ hôm 4 đi hàng, mà bây giờ mà đến giờ lại là tụi em phải tốn thêm tiền tiếp, mà cuối cùng là khách lỗi việc.

⚠️ LƯU Ý: Trong ví dụ này, tôi đã XÓA các câu nhiễu như "Hãy subscribe cho kênh La La School...", "Hãy subscribe cho kênh Ghiền Mì Gõ..." vì đây là quảng cáo YouTube, không phải nội dung cuộc gọi."""
    
    # Speaker detection notes
    SPEAKER_NOTES = """LƯU Ý QUAN TRỌNG:

� **XÓA NHIỄU - ƯU TIÊN SỐ 1**:
   ❌ XÓA NGAY: "Hãy subscribe...", "Đăng ký kênh...", "Like và share...", "Để không bỏ lỡ..."
   ✅ GIỮ LẠI: "Cảm ơn quý khách đã gọi đến..." (lời chào hệ thống)
   ✅ GIỮ LẠI: "Cảm ơn anh/chị" (lời cảm ơn trong cuộc gọi)

📌 **Phân vai CHÍNH XÁC - BẮT BUỘC**:
   
   ✅ Dựa vào xưng hô:
      - "Em", "bên em", "cho em" → Nhân viên
      - "Anh", "chị", "tôi" → Khách hàng
      - Không có xưng hô, giọng máy → Hệ thống
   
   ✅ Dựa vào vai trò:
      - Hỏi thông tin (tên, mã đơn) → Nhân viên
      - Cung cấp thông tin, phàn nàn → Khách hàng
      - Thông báo cước phí, chào mời → Hệ thống
   
   ✅ Dựa vào ngữ cảnh:
      - Câu đầu tiên thường là Hệ thống hoặc Nhân viên chào
      - Ai nói sau "Nhân viên hỗ trợ khách hàng" → Nhân viên
      - Ai yêu cầu hỗ trợ → Khách hàng

📌 **Xử lý trường hợp đặc biệt**:
   - Nếu có nhiều nhân viên/khách hàng: Đánh số "Nhân viên 1:", "Khách hàng 2:"
   - Nếu thực sự không rõ vai trò: Ưu tiên dựa vào xưng hô "em" vs "anh/chị"
   - Nếu cực kỳ không chắc: Sử dụng "Người nói:" (nhưng CỐ GẮNG TRÁNH)

📌 **Đảm bảo chất lượng**:
   - ✅ Mỗi lượt nói một dòng riêng
   - ✅ Có khoảng trống giữa các lượt
   - ✅ Đúng chính tả, có dấu đầy đủ
   - ✅ Dấu câu chính xác
   - ✅ XUẤT ĐẦY ĐỦ toàn bộ cuộc gọi (trừ quảng cáo nhiễu)

📌 **Tuyệt đối KHÔNG**:
   - ❌ Giữ lại quảng cáo "subscribe", "đăng ký kênh"
   - ❌ Thêm tiêu đề, giải thích, ghi chú
   - ❌ In lại transcript gốc
   - ❌ Bỏ sót nội dung cuộc gọi thực sự
   - ❌ Thay đổi ý nghĩa
   - ❌ Để vai trò sai (phải phân chính xác Hệ thống/Nhân viên/Khách hàng)"""
    
    # Output requirements
    OUTPUT_REQUIREMENTS = """YÊU CẦU ĐẦU RA:

✅ **Làm sạch hoàn toàn**:
   - XÓA tất cả quảng cáo YouTube/video
   - CHỈ GIỮ nội dung cuộc gọi thực sự
   - Gộp thông tin từ 2 transcript (Whisper + PhoWhisper), chọn phần chính xác nhất

✅ **Phân vai chính xác 100%**:
   - MỖI DÒNG phải bắt đầu bằng: "Hệ thống:", "Nhân viên:", hoặc "Khách hàng:"
   - KHÔNG ĐƯỢC sai vai trò
   - Dựa vào xưng hô, vai trò, ngữ cảnh để phân

✅ **Định dạng chuẩn**:
   - Vai trò + dấu hai chấm + khoảng trắng + nội dung
   - Mỗi lượt nói một dòng riêng
   - Có dòng trống giữa các lượt hội thoại

✅ **Bắt đầu trả lời ngay**:
   - KHÔNG cần "Phiên bản đã chỉnh:", "Kết quả:", v.v.
   - Bắt đầu luôn bằng vai trò người nói đầu tiên (thường là "Hệ thống:" hoặc "Nhân viên:")"""
    
    @staticmethod
    def build_qwen_prompt(
        whisper_text: str,
        phowhisper_text: str,
        system_prompt: Optional[str] = None,
        task_instructions: Optional[str] = None,
    ) -> str:
        """
        Build complete prompt for Qwen model in chat format
        
        Args:
            whisper_text: Transcript from Whisper
            phowhisper_text: Transcript from PhoWhisper
            system_prompt: Custom system prompt (uses default if None)
            task_instructions: Custom task instructions (uses default if None)
            
        Returns:
            Complete prompt in Qwen chat format
        """
        system = system_prompt or PromptTemplates.SYSTEM_PROMPT
        task = task_instructions or PromptTemplates.FUSION_TASK
        
        # Combine both transcripts
        combined_transcripts = f"""TRANSCRIPT 1 (Whisper large-v3):
{whisper_text}

TRANSCRIPT 2 (PhoWhisper-large):
{phowhisper_text}"""
        
        # Build full prompt in Qwen format
        prompt = f"""<|im_start|>system
{system}<|im_end|>
<|im_start|>user

{task}

TRANSCRIPT GỐC (từ 2 model speech-to-text, có thể sai chính tả, thiếu dấu hoặc nối liền từ):
{combined_transcripts}

{PromptTemplates.OUTPUT_REQUIREMENTS}

{PromptTemplates.OUTPUT_FORMAT}

{PromptTemplates.SPEAKER_NOTES}<|im_end|>
<|im_start|>assistant"""
        
        return prompt
    
    @staticmethod
    def build_gemini_prompt(
        whisper_text: str,
        phowhisper_text: str,
    ) -> str:
        """
        Build complete prompt for Gemini model with STT cleaning instructions
        
        Args:
            whisper_text: Transcript from Whisper
            phowhisper_text: Transcript from PhoWhisper
            
        Returns:
            Complete prompt for Gemini STT cleaning
        """
        # Combine both transcripts
        combined_transcripts = f"""TRANSCRIPT 1 (Whisper large-v3):
{whisper_text}

TRANSCRIPT 2 (PhoWhisper-large):
{phowhisper_text}"""
        
        # Build Gemini prompt with STT cleaning instructions
        prompt = f"""You are an expert Speech-to-Text (STT) transcript cleaner and text reconstruction assistant.
Your job is to clean raw STT output generated from any audio source
(such as conversations, lectures, interviews, meetings, phone calls, reports, dictations, or noisy recordings).

The STT input may contain:
– filler words (ờ, à, um, uh, kiểu như, basically…)
– repeated words
– misheard phonetics
– wrong punctuation
– run-on sentences
– missing diacritics (especially Vietnamese)
– broken Unicode
– background-noise fragments
– half-cut sentences or word artifacts
– timestamps or system logs (if present)

==========================
RULES
==========================

1. DO NOT invent or add new information. Only reconstruct what the speaker clearly intended.
2. Remove everything that is NOT part of the spoken content:
   – timestamps
   – logs
   – noise labels
   – system metadata
   – [inaudible], [music], etc. (unless they are semantically meaningful)
3. Fix STT errors:
   – restore correct Vietnamese diacritics
   – fix mis-heard words (if obviously intended)
   – fix merged or split words
   – remove filler words and repeated words when unnecessary
   – correct punctuation and sentence boundaries
4. Preserve meaning exactly as spoken.
5. Format the output cleanly:
   – proper paragraphs
   – clear sentence boundaries
   – speaker turns if identifiable (e.g., "A:" and "B:")
6. If the transcript looks like a meeting, phone call, or interview, preserve dialogue structure.
7. If numbers, names, dates, or codes are recognized, keep them exactly.
8. Do NOT summarize. Do NOT shorten. Do NOT add or guess missing context.

==========================
OUTPUT REQUIREMENTS
==========================

Your output must be:
✓ Clean  
✓ Faithful to the spoken content  
✓ Fully readable  
✓ No STT noise  
✓ No invented text  

==========================
INPUT (RAW SPEECH-TO-TEXT):
{combined_transcripts}
==========================

OUTPUT (CLEANED HUMAN-READABLE TEXT):
"""
        
        return prompt

    
    @staticmethod
    def build_simple_prompt(
        text: str,
        instruction: str = "Sửa lỗi chính tả và ngữ pháp, thêm dấu câu cho đoạn văn sau:",
    ) -> str:
        """
        Build simple prompt for basic text correction
        
        Args:
            text: Text to correct
            instruction: Instruction for the model
            
        Returns:
            Simple prompt in Qwen format
        """
        prompt = f"""<|im_start|>system
Bạn là trợ lý chuyên sửa lỗi tiếng Việt.<|im_end|>
<|im_start|>user
{instruction}

{text}<|im_end|>
<|im_start|>assistant"""
        
        return prompt


# Convenience function for backward compatibility
def build_fusion_prompt(whisper_text: str, phowhisper_text: str) -> str:
    """
    Build fusion prompt (convenience function)
    
    Args:
        whisper_text: Whisper transcript
        phowhisper_text: PhoWhisper transcript
        
    Returns:
        Complete Qwen fusion prompt
    """
    return PromptTemplates.build_qwen_prompt(whisper_text, phowhisper_text)


__all__ = ["PromptTemplates", "build_fusion_prompt"]
