# 🚀 Prompt v3.6.3 - ENFORCED Speaker Role Detection

## 🎯 Mục Tiêu

**"Bây giờ chia phân vai trò nữa là ổn"** - User request

Phiên bản này ÉP BUỘC Qwen phải phân vai người nói rõ ràng, không được bỏ qua!

## ⚡ Thay Đổi Chính

### 1. **SYSTEM_PROMPT Cứng Hơn**

**Before (v3.6.2):**
```
Bạn là trợ lý AI chuyên nghiệp...
Nhiệm vụ: 1. Loại bỏ nhiễu 2. Phân vai người nói...
```

**After (v3.6.3):**
```
Bạn là chuyên gia AI xử lý transcript cuộc gọi.
BẮT BUỘC thực hiện:
1. XÓA HOÀN TOÀN quảng cáo/nhiễu
2. PHÂN VAI NGƯỜI NÓI CỨNG (KHÔNG ĐƯỢC BỎ QUA)
3. Giữ nguyên 100% nội dung

⚠️ CRITICAL: Mỗi câu thoại PHẢI CÓ nhãn vai trò ở đầu dòng!
```

### 2. **FUSION_TASK Có Cấu Trúc Rõ Ràng**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 NHIỆM VỤ: Làm sạch và phân vai transcript
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 BƯỚC 1: XÓA NHIỄU (BẮT BUỘC)
🟢 BƯỚC 2: PHÂN VAI NGƯỜI NÓI (BẮT BUỘC - KHÔNG ĐƯỢC BỎ QUA)
🔵 BƯỚC 3: GIỮ NGUYÊN NỘI DUNG (100%)
🟣 BƯỚC 4: ĐỊNH DẠNG OUTPUT (BẮT BUỘC)
```

### 3. **Quy Tắc Phân Vai Chi Tiết**

```
⚠️ MỖI CÂU THOẠI PHẢI BẮT ĐẦU BẰNG 1 TRONG 3 NHÃN:

📍 "Hệ thống:" - Giọng máy IVR
   Dấu hiệu 100%:
   ✓ Câu đầu tiên: "Cảm ơn quý khách đã gọi đến..."
   ✓ Thông báo cước phí, hướng dẫn
   ✓ Không có xưng hô

📍 "Nhân viên:" - Nhân viên GHN/tổng đài
   Dấu hiệu 100%:
   ✓ Xưng "em"
   ✓ Gọi khách "anh", "chị"
   ✓ Hỏi thông tin, kiểm tra hệ thống
   ✓ Xin lỗi/lịch sự: "Dạ", "Vâng ạ"

📍 "Khách hàng:" - Người gọi
   Dấu hiệu 100%:
   ✓ Xưng "tôi", "anh", "chị"
   ✓ Gọi nhân viên "em"
   ✓ Yêu cầu, phàn nàn, cung cấp thông tin
```

### 4. **Tuyệt Đối Không Dùng**

```
❌ KHÔNG BAO GIỜ viết:
   ▸ "SPEAKER_00:", "SPEAKER_01:" → SAI!
   ▸ "Speaker 1:", "Speaker 2:" → SAI!
   ▸ "Người nói 1:" → SAI!
   
✅ CHỈ DÙNG 3 NHÃN:
   ▸ "Hệ thống:"
   ▸ "Nhân viên:"
   ▸ "Khách hàng:"
```

## 📊 So Sánh Output

### Before (v3.6.2) - Có thể vẫn dùng SPEAKER_XX

```
SPEAKER_00: Cảm ơn quý khách đã gọi đến giao hàng nhanh...
Em ơi, cho chị hiểu nãy cái bạn giao hàng ở vực Đồng Nai...
```
❌ Không rõ ai đang nói
❌ Còn có SPEAKER_00

### After (v3.6.3) - BẮT BUỘC phân vai rõ

```
Hệ thống: Cảm ơn quý khách đã gọi đến giao hàng nhanh. 
Cước phí cuộc gọi là 1000 đồng một phút.

Khách hàng: Em ơi, cho chị hỏi về đơn hàng ở vực Đồng Nai, 
Tâm Phước. Chị đặt mã đơn hàng với em.

Nhân viên: Dạ, em xin mã đơn hàng ạ.

Khách hàng: Mã đơn hàng là G-I-V-6-I-A...
```
✅ Phân vai 100% rõ ràng
✅ Không còn SPEAKER_XX
✅ Xóa nhiễu hoàn toàn

## 🎯 Điểm Khác Biệt Chính

| Aspect | v3.6.2 | v3.6.3 |
|--------|--------|--------|
| **Tone** | Lịch sự, gợi ý | Cứng rắn, bắt buộc |
| **Format** | Paragraph text | Cấu trúc với emoji, đường kẻ |
| **Rules** | "Nên phân vai" | "PHẢI phân vai (KHÔNG ĐƯỢC BỎ QUA)" |
| **Examples** | 1 ví dụ ngắn | 1 ví dụ chi tiết + warning |
| **Emphasis** | Regular text | ⚠️ CRITICAL, 🔴 BẮT BUỘC |
| **Output Control** | Hướng dẫn | "TUYỆT ĐỐI KHÔNG DÙNG" |

## 🔥 Kỹ Thuật Prompt Engineering

### 1. **Visual Hierarchy**
```
━━━━━━━ Đường kẻ phân cách
🔴 🟢 🔵 Emoji màu sắc
📍 Bullet points
✅ ❌ Checkmarks
⚠️ Warning icons
```

### 2. **Explicit Constraints**
```
Before: "Phân vai người nói"
After:  "PHÂN VAI NGƯỜI NÓI (BẮT BUỘC - KHÔNG ĐƯỢC BỎ QUA)"

Before: "Mỗi dòng một người"
After:  "⚠️ MỖI CÂU THOẠI PHẢI BẮT ĐẦU BẰNG 1 TRONG 3 NHÃN"
```

### 3. **Negative Examples**
```
❌ KHÔNG BAO GIỜ viết:
   ▸ "SPEAKER_00:"
   ▸ "Speaker 1:"
   
Giúp model biết chính xác cái GÌ KHÔNG được làm
```

### 4. **100% Indicators**
```
"Dấu hiệu 100% là Hệ thống:"
"Dấu hiệu 100% là Nhân viên:"

Tạo confidence cho model khi classify
```

### 5. **Step-by-Step Process**
```
BƯỚC 1: XÓA NHIỄU
BƯỚC 2: PHÂN VAI  
BƯỚC 3: GIỮ NGUYÊN
BƯỚC 4: ĐỊNH DẠNG

Model xử lý tuần tự, không bỏ bước
```

## 🧪 Testing Plan

### Test 1: Basic Role Detection
**Input:**
```
Cảm ơn quý khách đã gọi. 
Em xin mã đơn ạ.
Mã đơn là ABC123.
```

**Expected Output:**
```
Hệ thống: Cảm ơn quý khách đã gọi đến.

Nhân viên: Dạ, em xin mã đơn ạ.

Khách hàng: Mã đơn là ABC123.
```

### Test 2: Noise Removal + Role Detection
**Input:**
```
Cảm ơn quý khách đã gọi.
Hãy subscribe cho kênh Ghiền Mì Gõ.
Em xin mã đơn.
```

**Expected Output:**
```
Hệ thống: Cảm ơn quý khách đã gọi đến.

Nhân viên: Dạ, em xin mã đơn.
```
(Subscribe line deleted)

### Test 3: Complex Conversation
**Input:** (Transcript from user - có nhiễu + không phân vai)

**Expected Output:**
- ✅ Không còn "Hãy subscribe"
- ✅ Mỗi dòng có "Hệ thống:", "Nhân viên:", "Khách hàng:"
- ✅ Không có "SPEAKER_00:"

## 📝 Migration Steps

### Step 1: Update Prompt
```bash
# File đã updated: app/core/prompts/templates.py
# Version: 3.6.3
```

### Step 2: Clear ALL Cache
```powershell
# Web UI
1. Open http://localhost:5000
2. Click "💥 Clear Server"
3. Click "🗑️ Clear Cache"
```

### Step 3: Test
```powershell
# Upload test audio
# Verify output có đúng format:
# - "Hệ thống:", "Nhân viên:", "Khách hàng:"
# - Không có "SPEAKER_XX:"
# - Không còn nhiễu
```

## 🎯 Success Criteria

- [x] Prompt updated to v3.6.3
- [x] VERSION constant updated
- [x] System prompt more enforcing
- [x] Step-by-step structure added
- [x] Visual hierarchy with emoji
- [x] Explicit "KHÔNG ĐƯỢC" rules
- [x] 100% confidence indicators
- [x] Detailed role detection guide
- [ ] User tests and confirms it works

## 💡 Key Insights

**Why v3.6.2 Failed:**
- Quá "polite" - chỉ gợi ý, không ép buộc
- Thiếu emphasis - model có thể bỏ qua
- Format dạng paragraph - khó parse rules

**Why v3.6.3 Will Work:**
- ⚠️ CRITICAL, 🔴 BẮT BUỘC - model phải chú ý
- Cấu trúc step-by-step - model follow từng bước
- Visual cues - dễ phân biệt quan trọng vs thứ yếu
- Negative examples - model biết chính xác điều gì SAI

## 🚀 Next Steps

1. **Test Immediately:**
   ```bash
   .\start_webui.bat
   # Clear cache
   # Upload audio
   # Verify output
   ```

2. **If Still Wrong:**
   - Check Qwen có chạy không (pipeline.log)
   - Check enhanced_transcript.txt có tồn tại không
   - Check prompt có được load đúng không

3. **If Works:**
   - Document success case
   - Consider further optimization:
     - Few-shot examples
     - Chain-of-thought prompting
     - Output format validation

---

*Version: 3.6.3*
*Updated: October 27, 2025*
*Status: Ready for testing*
