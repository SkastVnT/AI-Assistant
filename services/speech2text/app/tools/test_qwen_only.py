"""
Test Qwen2.5 fusion only - Use existing transcripts from result/dual
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import time

# Existing transcripts from previous run
whisper_transcript = """ Cảm ơn quý khách đã gọi đến giao hàng nhanh. Cước phí của gọi là 1 ngàn đồng 1 phút.  Hãy subscribe cho kênh La La School Để không bỏ lỡ những video hấp dẫn  Nhân viên hỗ trợ khách hàng quay vô sân game  Thì hỗ trợ cho chị  À em ơi em hỗ trợ dùm chị  Cái đơn hàng là  G I  V B  B B B B  I 6  9  F  F là F  Em xin tên chị  À chị Hoàng Đông  Chị đơn gửi cho  Đi xa thật ở Duyên Hải Trà Vinh hả chị?  Đúng rồi  Em thấy đơn mình có xác nhận nhau lại  Mà chưa có phân tuyến cho nhân viên giao  Bà yêu cầu giao đơn đúng không chị?  Dạ  Nhưng mà cho em báo cái này một xíu  Có nghĩa là nhiều lúc  Trong cái thời gian này là  Em vẫn thông cảm cái đoạn là  Mưa gió thì em không nói  Cái vấn đề là  Khách thì cần hàng  Số điện thoại của khách  Em vẫn liên lạc bình thường  Bao nhiêu lần ở trên app báo là không liên lạc được với khách  Khách chặn số này kia em gọi lại cho khách luôn theo số điện thoại đó  Vẫn liên lạc được khách, vẫn chờ hàng  Rồi cuối cùng cũng không giao ngày này qua ngày khác  Từ hôm 4 giờ đi hàng hôm 4 giờ  Mà bây giờ mãi đến giao lại là tụi em phải tốn thêm tiền tiếp  Chứ không phải tốn thêm  Mà cuối cùng là khách kia lỡ việc  Cái đó nhờ mấy anh hội tử giùm em cái chứ  Cái tình hình này đúng là hoàn đơn  Hoàn đơn là tụi em mất tình hoàn  Dạ rồi xin lỗi vấn đề mình gặp phải về đơn ha chị  Thì em để em lưu ý vấn đề này với nhân viên rồi  Báo bộ phận xử lý dân hàng dân"""

phowhisper_transcript = """xin cảm ơn quý khách đã gọi đến giao hàng nhanh cước phí cuộc gọi là một ngàn giờ một phút một ngàn phút cuộc gọi một chút mỗi ai nghe mời. nghĩa là. nhân viên hỗ trợ khách hàng vừa vừa xin em tận hỗ trợ cho anh chị. xa thật ở duy ngã trà vinh hả chị đúng rồi em thấy đơn mình đã sáng tác xác nhận nhau lại rồi mà chưa có phân tuyến cho nhân viên giao như báo yêu cầu mới giao đơn đúng không chị dạ nhưng mà cho em báo cái này xíu có nghĩa là nhiều lúc trong cái thời gian này là em vẫn thông cảm cái đoạn làm mưa gió thì em không nói chứ vấn đề là khách thì cần hàng số điện thoại của khách em vẫn liên lạc bình thường bao nhiêu lần. ở trên áp báo là là không liên lạc được với khách khách chặn số này kia em gọi lại cho khách luôn theo xuân thoại đó vẫn liên lạc được khách vẫn chờ hàng rồi cuối cùng cũng không giao ngày này qua ngày khác từ hôm mùng bốn giờ đi hàng hôm mùng bốn giờ mà bây giờ mà đến giao lại là tụi em thì tốn thêm tiền tiếp chứ không phải tốn thêm mà cuối cùng là khách lỡ việc thế đó nhờ mấy anh hỗ trợ giùm em cái chứ. dạ rồi xin lỗi vấn đề mình gặp phải vậy đơn ha chị thì em để em lưu ý vấn đề này với nhân viên rồi báo bộ phận xử lý dựng hàng gian."""

print("="*80)
print("TEST QWEN2.5-1.5B FUSION ONLY (SMALLER MODEL)")
print("="*80)

# Clear GPU memory
if torch.cuda.is_available():
    print("[GPU] Clearing VRAM...")
    torch.cuda.empty_cache()
    import gc
    gc.collect()

print("[AI] Loading Qwen2.5-1.5B-Instruct (Smaller for 6GB VRAM)...")
load_start = time.time()

model_name = "Qwen/Qwen2.5-1.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

if torch.cuda.is_available():
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="balanced",
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="cpu",
        trust_remote_code=True,
    )

print(f"[OK] Qwen2.5 loaded in {time.time() - load_start:.2f}s")

# Combine both transcripts
full_raw_text = f"TRANSCRIPT 1 (Whisper large-v3):\n{whisper_transcript}\n\nTRANSCRIPT 2 (PhoWhisper-large):\n{phowhisper_transcript}"

# Enhanced prompt with 3 speaker roles: System, Employee, Customer
prompt_text = f"""<|im_start|>system
Bạn là trợ lý chuyên xử lý transcript tiếng Việt, được thiết kế để làm sạch dữ liệu đầu ra từ mô hình nhận dạng giọng nói (speech-to-text).
Nhiệm vụ của bạn là giữ nguyên nội dung và ý nghĩa gốc, nhưng chỉnh sửa toàn bộ lỗi chính tả, ngữ pháp, dấu câu và định dạng lại cho dễ đọc.
<|im_end|>
<|im_start|>user
NHIỆM VỤ:
1. Sửa lỗi chính tả, lỗi gõ, lỗi ngữ pháp.
2. Thêm đầy đủ dấu câu (chấm, phẩy, hỏi, than...) đúng vị trí và tự nhiên.
3. Phân vai người nói rõ ràng, gồm các nhóm:
   - Hệ thống: Giọng máy, thông báo tự động (ví dụ: "Cảm ơn quý khách đã gọi đến...")
   - Nhân viên: Người đại diện công ty, tổng đài viên, nhân viên hỗ trợ.
   - Khách hàng: Người gọi đến hoặc người được gọi.
4. Tách đoạn theo từng người nói, mỗi lượt nói một đoạn riêng.
5. Giữ nguyên nội dung và ý nghĩa gốc.
6. Không bỏ hoặc thêm ý.
7. Đảm bảo đoạn hội thoại dễ đọc, đúng chuẩn tiếng Việt.
8. Không giải thích, không thêm ghi chú.

TRANSCRIPT GỐC (có thể sai chính tả, thiếu dấu hoặc nối liền từ):
{full_raw_text}

YÊU CẦU ĐẦU RA:
- Chỉ trả về transcript đã được sửa lỗi, chia vai và format rõ ràng.
- Mỗi người nói hiển thị trên một dòng riêng, có dạng như sau:

MẪU ĐỊNH DẠNG:
Hệ thống: Xin cảm ơn quý khách đã gọi đến tổng đài Giao Hàng Nhanh.
Khách hàng: Alo, cho tôi hỏi về đơn hàng mã GHN12345 ạ.
Nhân viên: Dạ, em xin chào anh ạ. Anh vui lòng chờ em kiểm tra thông tin đơn hàng nhé.
Khách hàng: Vâng, cảm ơn em.

LƯU Ý:
- Nếu không chắc người nói là ai, hãy suy luận dựa trên ngữ cảnh, ví dụ:
  - "Xin chào quý khách..." thường là Hệ thống hoặc Nhân viên.
  - "Alo, tôi muốn hỏi..." thường là Khách hàng.
  - "Em kiểm tra đơn giúp anh nhé" thường là Nhân viên.
- Nếu vẫn không rõ, gán là "Người nói không xác định:".
- Không thêm tiêu đề, không in lại transcript gốc, không thêm giải thích.
- Đảm bảo văn bản cuối cùng sạch, rõ, tự nhiên, dễ đọc, đúng ngữ pháp tiếng Việt.
<|im_end|>
<|im_start|>assistant
"""

print("[AI] Processing with Qwen2.5...")
process_start = time.time()

inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=2048,
        temperature=0.3,
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

response = tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
fused_text = response.strip()

process_time = time.time() - process_start

print("\n" + "="*80)
print("🎉 QWEN2.5-7B ENHANCED RESULT:")
print("="*80)
print(fused_text)
print("="*80)
print(f"⏱️ Processing time: {process_time:.2f}s")
print("="*80)

# Save result
output_file = "./result/vistral/test_qwen_enhanced.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(fused_text)
print(f"💾 Saved to: {output_file}")
