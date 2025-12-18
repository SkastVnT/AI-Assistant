# 🎨 Hướng dẫn Hybrid Img2Img Mode

## 📋 Tổng quan

Img2Img hiện có **2 modes** kết hợp để tối ưu cho cả người mới và power users:

### **🧠 Smart Mode** (80% Features + 20% Prompt)
- Tự động kết hợp đặc trưng ảnh với prompt của bạn
- Tạo ảnh giống ảnh gốc nhất
- Phù hợp: **Người không biết viết prompt**, muốn recreate ảnh

### **✍️ Manual Mode** (Full Control)
- Kiểm soát hoàn toàn mọi tham số
- Tự do sáng tạo với ảnh gốc làm base
- Phù hợp: **Power users**, muốn biến đổi lớn

---

## 🚀 Luồng sử dụng

### **Smart Mode Flow**

```
1. Chọn tab "Tạo ảnh theo hình ảnh"
2. ✅ Bật Smart Mode (checkbox "🧠 Smart Mode")
3. 📤 Upload ảnh gốc
4. 🔬 Click "Trích xuất đặc trưng"
   → Nhận được tags từ DeepDanbooru
   → (Optional) Click tags để loại bỏ những tag không mong muốn
5. ✨ Click "Tự tạo prompt (GROK)"
   → GROK FREE API tự động tạo prompt tối ưu từ tags
6. (Optional) Chỉnh sửa prompt, negative, denoising strength
7. (Optional) Bật "🧠 Suy luận sâu" để chạy kỹ hơn (50-70 steps)
8. 🎨 Click "Tạo ảnh từ hình ảnh"
   → Tạo ảnh với 80% đặc trưng + 20% prompt
   → Tự động lưu vào Storage/Image_Gen/
   → Tự động gửi vào chat
```

### **Manual Mode Flow**

```
1. Chọn tab "Tạo ảnh theo hình ảnh"
2. ❌ Tắt Smart Mode (uncheck checkbox)
3. 📤 Upload ảnh gốc
4. (Optional) Trích xuất đặc trưng để tham khảo
5. ✍️ Tự viết prompt hoàn chỉnh
6. 📝 Tự nhập negative prompt, width, height, steps, CFG, denoising
7. 🎨 Click "Tạo ảnh từ hình ảnh"
   → Tạo ảnh theo config của bạn
   → Tự động lưu + gửi vào chat
```

---

## 🔧 Tham số quan trọng

### **Denoising Strength**

| Mode | Giá trị | Ý nghĩa |
|------|---------|---------|
| **Smart Mode** | 0.3-0.5 | Giữ nhiều từ ảnh gốc (70-50% giống) |
| **Manual Mode** | 0.6-0.8 | Cho phép biến đổi nhiều (40-20% giống) |

- `0.0` = Giữ nguyên ảnh gốc 100%
- `1.0` = Tạo mới hoàn toàn (Text2Img)

### **Feature Weight** (Smart Mode only)

- **80%** (default): Tags chiếm 80%, prompt của bạn chiếm 20%
- **100%**: Chỉ dùng tags, bỏ qua prompt
- **50%**: Cân bằng giữa tags và prompt

### **Deep Thinking** (Smart Mode only)

- ❌ Tắt: 30 steps (nhanh, đủ dùng)
- ✅ Bật: 50-70 steps (chậm hơn nhưng chi tiết hơn)

---

## 📊 So sánh 2 Modes

| Tiêu chí | Smart Mode | Manual Mode |
|----------|------------|-------------|
| **Độ khó** | ⭐ Dễ | ⭐⭐⭐⭐ Khó |
| **Kiểm soát** | ⭐⭐ Hạn chế | ⭐⭐⭐⭐⭐ Hoàn toàn |
| **Tương đồng ảnh gốc** | ⭐⭐⭐⭐⭐ 70-90% | ⭐⭐⭐ 20-40% |
| **Sáng tạo** | ⭐⭐ Thấp | ⭐⭐⭐⭐⭐ Cao |
| **Tốc độ** | ⏱️ Nhanh (30s) | ⏱️⏱️ Chậm (nếu bật Deep Thinking) |
| **Cần biết viết prompt** | ❌ Không | ✅ Có |

---

## 🤖 GROK FREE API

### Tính năng
- Tự động tạo prompt chất lượng cao từ extracted tags
- Sử dụng model: `llama-3.3-70b-versatile` (GROK FREE)
- Fallback: Nếu GROK lỗi → Tự động dùng tags concatenation

### Cách GROK hoạt động

```
Input:
  Character: 1girl, solo, long_hair
  Style: anime, illustration
  Quality: masterpiece, best_quality

Output (GROK):
  "A solo anime illustration of a beautiful girl with flowing long hair,
   rendered in masterpiece quality with the best details, soft lighting,
   highly detailed facial features, elegant composition"
```

### Khi nào nên dùng GROK?

✅ **Nên dùng:**
- Bạn không biết viết prompt
- Muốn prompt tự nhiên, mạch lạc
- Cần combine nhiều tags phức tạp

❌ **Không cần:**
- Bạn đã có prompt sẵn
- Chỉ cần vài tags đơn giản
- Không có internet/GROK API key

---

## 💡 Tips & Best Practices

### Smart Mode
1. **Loại bỏ tags không mong muốn** trước khi generate
   - Click vào tag để toggle on/off
   - VD: Bỏ "glasses" nếu không muốn nhân vật đeo kính

2. **Dùng Feature Weight để điều chỉnh**
   - 90% features: Ảnh gần giống nhất
   - 70% features: Cân bằng giữa giống và sáng tạo
   - 50% features: Có thể khác khá nhiều

3. **Bật Deep Thinking khi:**
   - Ảnh gốc phức tạp (nhiều chi tiết)
   - Muốn extract kỹ càng hơn
   - Không vội (chấp nhận chờ lâu)

### Manual Mode
1. **Viết prompt chi tiết**
   - Bắt đầu: `1girl, solo, ...` (character)
   - Giữa: `long hair, blue eyes, ...` (appearance)
   - Cuối: `masterpiece, best quality` (quality tags)

2. **Denoising 0.7-0.8** cho creative work
   - VD: Biến ảnh thật → anime
   - VD: Đổi style hoàn toàn

3. **Dùng LoRA models** để enhance
   - Detail enhancer: Tăng chi tiết
   - Style LoRA: Đổi art style

---

## 🔍 Troubleshooting

### "⚠️ Vui lòng trích xuất đặc trưng trước!"
- **Nguyên nhân:** Chưa click "Trích xuất đặc trưng"
- **Giải pháp:** Upload ảnh → Click "🔬 Trích xuất đặc trưng"

### "❌ Lỗi tạo prompt: GROK API key not configured"
- **Nguyên nhân:** Chưa cấu hình GROK_API_KEY trong .env
- **Giải pháp:** 
  1. Thêm `GROK_API_KEY=your_key` vào `.env`
  2. Hoặc dùng fallback (tự động join tags)

### "HTTP 400: Bad Request"
- **Nguyên nhân:** Thiếu params hoặc image
- **Giải pháp:** Đảm bảo đã upload ảnh trước khi generate

### Ảnh quá khác ảnh gốc (Smart Mode)
- **Giải pháp 1:** Tăng Feature Weight lên 90-95%
- **Giải pháp 2:** Giảm Denoising xuống 0.3
- **Giải pháp 3:** Loại bỏ tags không liên quan

### Ảnh quá giống ảnh gốc (Manual Mode)
- **Giải pháp:** Tăng Denoising lên 0.8-0.9

---

## 📁 File Storage

Tất cả ảnh generated đều được lưu tự động:

**Local:**
```
services/chatbot/Storage/Image_Gen/
  └── img2img_20251218_143052_0.png
```

**Cloud (nếu có ImgBB):**
```
https://i.ibb.co/xxxxxxx/generated.png
```

**Chat history:**
- Hiển thị thumbnail
- Click để xem full size
- Link cloud URL (nếu có)

---

## 🎯 Examples

### Example 1: Recreate ảnh anime chính xác

```yaml
Mode: Smart Mode ✅
Upload: anime_girl.jpg
Extract: ✅ (200 tags)
GROK: ✅ Auto-generated prompt
Feature Weight: 90%
Denoising: 0.3
Deep Thinking: ❌
Result: 85% giống ảnh gốc
```

### Example 2: Biến ảnh thật → anime style

```yaml
Mode: Manual Mode ❌
Upload: real_photo.jpg
Extract: (Optional - for reference)
Prompt: "1girl, anime style, detailed eyes, colorful, masterpiece"
Negative: "realistic, photo, 3d"
Denoising: 0.8
LoRA: anime_style_v2
Result: Hoàn toàn anime style
```

### Example 3: Tăng chất lượng ảnh cũ

```yaml
Mode: Smart Mode ✅
Upload: old_low_quality.jpg
Extract: ✅
GROK: ✅
Feature Weight: 95%
Denoising: 0.4
Deep Thinking: ✅ (60 steps)
LoRA: detail_enhancer
Result: Chất lượng cao hơn, giữ nguyên composition
```

---

## 🔄 Version History

- **v1.0** (2024-12-18): Initial hybrid mode implementation
  - Smart Mode with auto-tag integration
  - GROK FREE API for prompt generation
  - Chat integration
  - Auto-save to storage

---

## 📞 Support

Nếu gặp lỗi hoặc cần hỗ trợ:
1. Check logs trong console (F12)
2. Đọc error message cụ thể
3. Tham khảo Troubleshooting section
4. Report issue trên GitHub

---

**🎨 Happy Generating! 🚀**
