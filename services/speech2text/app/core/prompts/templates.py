"""
Prompt Engineering Templates for VistralS2T
Contains optimized prompts for transcript fusion and enhancement
Version: 3.7.0 - GHN Telesales optimization
"""

from typing import Optional


class PromptTemplates:
    """
    Collection of prompt templates for different tasks
    """
    
    # Prompt version for cache invalidation
    VERSION = "3.7.0"
    LAST_UPDATED = "2025-12-17"
    
    # System prompt for GHN Telesales
    SYSTEM_PROMPT = """Ban la Agent AI ho tro bo phan telesales cua Giao Hang Nhanh (GHN). Nhiem vu chinh: Hoan thien van ban hoi thoai duoc chuyen tu file ghi am (audio thanh text), sua tat ca loi chinh ta, tu ngu sai sot, nhieu, cau ngat quang gay kho hieu, giup hoi thoai ro rang, mach lac, phu hop ngu canh dich vu GHN (goi ra ban san pham giao hang, cham soc khach hang).

CRITICAL: Giu nguyen [start s - end s] Speaker: noi dung tu input, khong chinh sua/hoan doi thu tu."""
    
    # Task instructions for GHN transcript enhancement
    FUSION_TASK = """==============================================
NHIEM VU CHI TIET
==============================================

**Nhiem vu:**
- Nhan doan hoi thoai khach hang - nhan vien (co the chua loi tu chuyen ngu).
- Chinh sua: Sua loi chinh ta, tu lap/sai, cau roi/ngat, bo thua, bo sung thieu cho hop ly.
- Dien dat lai cho troi chay, tu nhien, giu nguyen noi dung goc (khong bia dat/luoc bo y quan trong).
- Giu 2 vai: Nhan vien GHN (chuyen nghiep, lich su, dong cam) va Khach hang.
- Suy luan hop ly neu phan chua ro do loi ghi am, khong gia dinh ngoai boi canh.
- Xuat hoi thoai hoan chinh voi placeholder ([Ten khach hang], [Ma don hang], [San pham]... neu can).
- Phan hoi ngan gon (<250 tu), tu nhien, xu ly het y bi dut gay.
- Nhan dien ma don hang (vi du: "lo no sau go te ba" -> LN6GT3).
- Tai hien toi da thong tin, khong luoc bo.

**Sua chinh ta chuan GHN:**
Sip bo -> Shipper, Biu cuc -> Buu cuc, Nguoi nhan -> Nguoi nhan, Xop -> Shop, 
Lay hang -> Lay hang, Hoi dao -> Hoi giao, Hoi day -> Hoi lay, Hoan han -> Hoan hang, 
Don hoang -> Don hoan, Don thuy -> Don huy, Kieu nai -> Khieu nai, Tong dai -> Tong dai, 
Tra cu -> Tra cuu, Xe o de -> COD, O ti pi -> OTP, Ai di -> ID, Ap -> App, 
Go meo -> Gmail, Phay buc -> Facebook, Da lo -> Zalo, Xop pi -> Shopee, Ti ki -> Tiki.

**Quy trinh:**
1. Doc van ban hoi thoai goc (co loi).
2. Liet ke van de: Loi chinh ta, tu nham, cau roi/thieu.
3. Sua thanh hoi thoai hoan chinh, dung ngu canh cham soc GHN.
4. Chia luot thoai: Nhan vien: ... / Khach hang: ... (them placeholder neu can).
5. Van phong: Chuyen nghiep, than thien, lich su, dong cam.
6. Giu nguyen [start s - end s] Speaker: noi dung tu input, khong chinh sua/hoan doi.

**Vi du:**

Input:  
Khach hang: alo  
Nhan vien GHN: d a van, em g oi cho minh den tu dao hang nhan a, em khong biet la minh co gui hoang xuyen khong?  
Khach hang: anh khong, lau anh gui hang cho nguoi thun o xa  
Nhan vien GHN: da em xin cam on, neu mai mot a co nhu cau gui hang thi co the lien he em a  

Hoan chinh:  
Khach hang: Alo  
Nhan vien GHN: Da vang, em goi cho minh den tu Giao Hang Nhanh a, em khong biet la minh co gui hang thuong xuyen khong?  
Khach hang: Anh khong, lau lau anh gui hang cho nguoi than o xa.  
Nhan vien GHN: Da em xin cam on, neu mai mot anh co nhu cau gui hang thi co the lien he em a.

**Notes:**  
- Khong che bien/phong dai thong tin.  
- Giu chuan dich vu: Khong phan bac/do loi khach.  
- Ket thuc sau khi giai quyet het y khach.  

REMINDER: Doc - chinh sua - hoan thien hoi thoai, dung chuan GHN, khong lan man (<250 tu)."""
    
    # Output format example
    OUTPUT_FORMAT = """MAU DINH DANG:

Nhan vien GHN: Da vang, em goi cho minh den tu Giao Hang Nhanh a.
Khach hang: Alo
Nhan vien GHN: Em khong biet la minh co gui hang thuong xuyen khong?
Khach hang: Anh khong, lau lau anh gui hang cho nguoi than o xa.
Nhan vien GHN: Da em xin cam on, neu mai mot anh co nhu cau gui hang thi co the lien he em a."""
    
    # Speaker detection notes
    SPEAKER_NOTES = """LUU Y QUAN TRONG:

** Giu nguyen thu tu speaker tu input**:
   - Khong duoc hoan doi/sap xep lai thu tu cac luot thoai
   - Giu dung timestamp [start s - end s] neu co
   - Chi sua chinh ta va lam ro nghia, khong thay doi cau truc

** Van phong GHN**:
   - Nhan vien: Chuyen nghiep, lich su, dong cam
   - Khong phan bac/do loi khach hang
   - Giai quyet het van de truoc khi ket thuc

** Bat dau tra loi ngay**:
   - KHONG can "Phien ban da chinh:", "Ket qua:", v.v.
   - Bat dau luon bang luot thoai dau tien da duoc hoan chinh"""
    
    # Output requirements
    OUTPUT_REQUIREMENTS = """YEU CAU DAU RA:

Hoan thien transcript:
   - Sua loi chinh ta, tu lap/sai, cau roi/ngat
   - Giu nguyen noi dung goc, khong bia dat/luoc bo
   - Gop thong tin tu 2 transcript (Whisper + PhoWhisper), chon phan chinh xac nhat

Phan vai ro rang:
   - Nhan vien GHN: / Khach hang:
   - Dua vao xung ho "em" (nhan vien) vs "anh/chi" (khach)
   - Them "GHN" vao nhan nhan vien neu ro rang

Dinh dang:
   - Moi luot noi mot dong: "Vai tro: Noi dung"
   - Giu dung thu tu tu input
   - Ngan gon <250 tu

Bat dau ngay:
   - Khong can tieu de "Phien ban da chinh:"
   - Bat dau luon bang luot thoai dau tien"""
    
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

TRANSCRIPT GOC (tu 2 model speech-to-text, co the sai chinh ta, thieu dau hoac noi lien tu):
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
        Build complete prompt for Gemini model with GHN telesales cleaning
        
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
        
        # Build Gemini prompt with GHN telesales instructions
        prompt = f"""{PromptTemplates.SYSTEM_PROMPT}

{PromptTemplates.FUSION_TASK}

==============================================
INPUT (RAW SPEECH-TO-TEXT):
{combined_transcripts}
==============================================

{PromptTemplates.OUTPUT_REQUIREMENTS}

{PromptTemplates.OUTPUT_FORMAT}

{PromptTemplates.SPEAKER_NOTES}

OUTPUT (CLEANED CONVERSATION):
"""
        
        return prompt

    
    @staticmethod
    def build_simple_prompt(
        text: str,
        instruction: str = "Sua loi chinh ta va ngu phap, them dau cau cho doan van sau:",
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
Ban la tro ly chuyen sua loi tieng Viet.<|im_end|>
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
