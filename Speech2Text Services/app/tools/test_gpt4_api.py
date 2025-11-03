"""
Use OpenAI API for transcript fusion - NO VRAM ISSUES
"""
import os
from openai import OpenAI
import time

# API key from .env
client = OpenAI(api_key="sk-proj-Yg_Z-7u04hibB-EGG1qSEWV8KXXh6Oc7Z0KKs0mP5iTXzPSZXzQ4cHLLCmyxcg6VHHPy0OFhBpT3BlbkFJBh3o9fAT6XtCH7t4d4y-4d9jkUhUgQPkLfgdHEDvvBXjIHcLXy1z0Gr6RmTMZg0HdjQA")

# Existing transcripts
whisper_transcript = """ Cảm ơn quý khách đã gọi đến giao hàng nhanh. Cước phí của gọi là 1 ngàn đồng 1 phút.  Hãy subscribe cho kênh La La School Để không bỏ lỡ những video hấp dẫn  Nhân viên hỗ trợ khách hàng quay vô sân game  Thì hỗ trợ cho chị  À em ơi em hỗ trợ dùm chị  Cái đơn hàng là  G I  V B  B B B B  I 6  9  F  F là F  Em xin tên chị  À chị Hoàng Đông  Chị đơn gửi cho  Đi xa thật ở Duyên Hải Trà Vinh hả chị?  Đúng rồi  Em thấy đơn mình có xác nhận nhau lại  Mà chưa có phân tuyến cho nhân viên giao  Bà yêu cầu giao đơn đúng không chị?  Dạ  Nhưng mà cho em báo cái này một xíu  Có nghĩa là nhiều lúc  Trong cái thời gian này là  Em vẫn thông cảm cái đoạn là  Mưa gió thì em không nói  Cái vấn đề là  Khách thì cần hàng  Số điện thoại của khách  Em vẫn liên lạc bình thường  Bao nhiêu lần ở trên app báo là không liên lạc được với khách  Khách chặn số này kia em gọi lại cho khách luôn theo số điện thoại đó  Vẫn liên lạc được khách, vẫn chờ hàng  Rồi cuối cùng cũng không giao ngày này qua ngày khác  Từ hôm 4 giờ đi hàng hôm 4 giờ  Mà bây giờ mãi đến giao lại là tụi em phải tốn thêm tiền tiếp  Chứ không phải tốn thêm  Mà cuối cùng là khách kia lỡ việc  Cái đó nhờ mấy anh hội tử giùm em cái chứ  Cái tình hình này đúng là hoàn đơn  Hoàn đơn là tụi em mất tình hoàn  Dạ rồi xin lỗi vấn đề mình gặp phải về đơn ha chị  Thì em để em lưu ý vấn đề này với nhân viên rồi  Báo bộ phận xử lý dân hàng dân"""

phowhisper_transcript = """xin cảm ơn quý khách đã gọi đến giao hàng nhanh cước phí cuộc gọi là một ngàn giờ một phút một ngàn phút cuộc gọi một chút mỗi ai nghe mời. nghĩa là. nhân viên hỗ trợ khách hàng vừa vừa xin em tận hỗ trợ cho anh chị. xa thật ở duy ngã trà vinh hả chị đúng rồi em thấy đơn mình đã sáng tác xác nhận nhau lại rồi mà chưa có phân tuyến cho nhân viên giao như báo yêu cầu mới giao đơn đúng không chị dạ nhưng mà cho em báo cái này xíu có nghĩa là nhiều lúc trong cái thời gian này là em vẫn thông cảm cái đoạn làm mưa gió thì em không nói chứ vấn đề là khách thì cần hàng số điện thoại của khách em vẫn liên lạc bình thường bao nhiêu lần. ở trên áp báo là là không liên lạc được với khách khách chặn số này kia em gọi lại cho khách luôn theo xuân thoại đó vẫn liên lạc được khách vẫn chờ hàng rồi cuối cùng cũng không giao ngày này qua ngày khác từ hôm mùng bốn giờ đi hàng hôm mùng bốn giờ mà bây giờ mà đến giao lại là tụi em thì tốn thêm tiền tiếp chứ không phải tốn thêm mà cuối cùng là khách lỡ việc thế đó nhờ mấy anh hỗ trợ giùm em cái chứ. dạ rồi xin lỗi vấn đề mình gặp phải vậy đơn ha chị thì em để em lưu ý vấn đề này với nhân viên rồi báo bộ phận xử lý dựng hàng gian."""

print("="*80)
print("OPENAI GPT-4 FUSION - NO VRAM ISSUES")
print("="*80)

full_raw_text = f"TRANSCRIPT 1 (Whisper large-v3):\n{whisper_transcript}\n\nTRANSCRIPT 2 (PhoWhisper-large):\n{phowhisper_transcript}"

prompt = f"""Bạn là trợ lý chuyên xử lý transcript tiếng Việt từ speech-to-text.

🎯 NHIỆM VỤ CHÍNH:
1. ✅ Sửa lỗi chính tả, lỗi gõ, lỗi ngữ pháp
2. ✅ Thêm đầy đủ dấu câu: chấm (.), phẩy (,), hỏi (?), than (!), ba chấm (...)
3. ✅ TÁCH NGƯỜI NÓI: Bắt buộc phải có "Người tổng đài:" hoặc "Khách hàng:" trước mỗi lượt nói
4. ✅ Chia đoạn văn hợp lý (2-5 câu/đoạn)
5. ✅ Giữ nguyên 100% nội dung và ý nghĩa gốc
6. ❌ KHÔNG thêm, KHÔNG bỏ nội dung
7. ❌ KHÔNG viết tắt, KHÔNG chêm tiếng Anh
8. ❌ KHÔNG thêm lời bình, tiêu đề hay chú thích ngoài nhãn người nói

📋 YÊU CẦU ĐẦU RA:
→ Chỉ trả về transcript đã được làm sạch và format đẹp
→ BẮT BUỘC có nhãn "Người tổng đài:" hoặc "Khách hàng:" trước mỗi lượt nói
→ Mỗi người nói tách thành đoạn riêng với khoảng trắng giữa các lượt
→ Giữ nguyên ngôn ngữ tiếng Việt

💡 VÍ DỤ:
📥 Đầu vào: 
cám ơn quý khách đã gọi đến giao hàng nhanh em là nhân viên tổng đài xin hỏi anh cần gì ạ dạ em muốn hỏi đơn hàng

📤 Đầu ra:
Người tổng đài: Cảm ơn quý khách đã gọi đến Giao Hàng Nhanh. Em là nhân viên tổng đài, xin hỏi anh cần gì ạ?

Khách hàng: Dạ, em muốn hỏi về đơn hàng.

---

TRANSCRIPT GỐC (đầu vào từ speech-to-text, có thể chứa nhiều lỗi):
{full_raw_text}

Hãy làm sạch và format lại transcript này theo đúng yêu cầu."""

print("[API] Calling OpenAI GPT-4...")
start = time.time()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "Bạn là chuyên gia xử lý transcript tiếng Việt."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3,
    max_tokens=2048
)

result = response.choices[0].message.content
process_time = time.time() - start

print("\n" + "="*80)
print("🎉 GPT-4 ENHANCED RESULT:")
print("="*80)
print(result)
print("="*80)
print(f"⏱️ Processing time: {process_time:.2f}s")
print("="*80)

# Save result
output_file = "./result/vistral/test_gpt4_enhanced.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(result)
print(f"💾 Saved to: {output_file}")
