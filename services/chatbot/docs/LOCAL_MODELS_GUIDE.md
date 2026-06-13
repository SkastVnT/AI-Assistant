# 🖥️ Local Models Setup Guide

## ✅ Đã tích hợp 3 Local Models vào ChatBot!

### **1. Qwen1.5-1.8B Local** (Nhỏ gọn - Nhanh)
- **Kích thước:** ~3.6GB
- **VRAM:** 2GB (FP16) hoặc 1GB (8-bit)
- **Tốc độ:** ~50 tokens/second (GPU)
- **Đặc điểm:** Nhỏ, nhanh, đa ngôn ngữ

### **2. BloomVN-8B Local** (Tiếng Việt)
- **Kích thước:** ~15GB  
- **VRAM:** 8GB (FP16) hoặc 4GB (8-bit)
- **Tốc độ:** ~20 tokens/second (GPU)
- **Đặc điểm:** Model tiếng Việt native, hiểu văn hóa VN

### **3. Qwen2.5-14B Local** ⭐ (Mạnh nhất)
- **Kích thước:** ~28GB
- **VRAM:** 14GB (FP16) hoặc **7GB (8-bit)** ✅  
- **Tốc độ:** ~15 tokens/second (GPU)
- **Đặc điểm:**
  - Chất lượng gần GPT-4
  - Code generation xuất sắc
  - 128K context window
  - Multilingual (EN, ZH, VI, ...)

---

## 🚀 Hướng dẫn sử dụng:

### Bước 1: Cài dependencies

```powershell
cd i:\AI-Assistant\ChatBot
pip install torch transformers accelerate sentencepiece bitsandbytes
```

**Lưu ý:**
- Nếu có GPU: Cài `torch` với CUDA support
- Nếu chỉ CPU: Cài `torch` CPU version

### Bước 2: Kiểm tra models đã có

Models đã được download tại:
```
ChatBot/models/
├── BloomVN-8B-chat/           ✅
├── Qwen1.5-1.8B-Chat/         ✅
└── Qwen2.5-14B-Instruct/      ✅
```

### Bước 3: Khởi động ChatBot

```powershell
python services/chatbot/run.py
```

### Bước 4: Sử dụng

1. Mở trình duyệt: `http://127.0.0.1:5000`
2. Dropdown "Chọn Model"
3. Chọn một trong 3 local models:
   - 🖥️ Qwen1.5-1.8B Local (nhanh nhất)
   - 🖥️ BloomVN-8B Local (tiếng Việt)
   - 🖥️ Qwen2.5-14B Local ⭐ (chất lượng cao nhất)
4. Chat bình thường!

---

## 💻 Yêu cầu hệ thống:

### GPU (Khuyến nghị)

| Model | VRAM FP16 | VRAM 8-bit | RAM |
|-------|-----------|------------|-----|
| Qwen1.5-1.8B | 2GB | 1GB | 8GB |
| BloomVN-8B | 8GB | 4GB | 16GB |
| Qwen2.5-14B | 14GB | **7GB** ✅ | 16GB |

**GPU khuyến nghị:**
- RTX 3060 (12GB): Chạy tất cả với 8-bit
- RTX 3060 Ti (8GB): Chạy BloomVN hoặc Qwen1.5
- RTX 3080/3090 (10-24GB): Chạy tất cả mượt mà

### CPU (Không có GPU)

| Model | RAM | Tốc độ |
|-------|-----|--------|
| Qwen1.5-1.8B | 8GB | ~5 tokens/s |
| BloomVN-8B | 16GB | ~2 tokens/s |
| Qwen2.5-14B | 32GB | ~1 token/s |

**Lưu ý:** CPU mode chậm hơn GPU 10-50x!

---

## 🎯 Khi nào dùng model nào?

### **Qwen1.5-1.8B Local** - Tốt cho:
✅ Máy yếu (< 8GB VRAM)
✅ Chat nhanh, đơn giản
✅ Test, development
❌ Code phức tạp
❌ Reasoning cao

### **BloomVN-8B Local** - Tốt cho:
✅ Chat tiếng Việt tự nhiên
✅ Hiểu văn hóa, ngữ cảnh VN
✅ Tâm lý, tư vấn đời sống
❌ Code generation
❌ English content

### **Qwen2.5-14B Local** ⭐ - Tốt cho:
✅ **MỌI TASK** (tốt nhất)
✅ Code generation (ngang GPT-4)
✅ Complex reasoning
✅ Long context (128K)
✅ Multilingual
✅ Production use
⚠️ Cần 7-14GB VRAM

---

## 🔥 Tối ưu VRAM:

### Nếu thiếu VRAM:

**1. Enable 8-bit quantization (Tự động)**
- Qwen2.5-14B: 14GB → **7GB** ✅
- BloomVN-8B: 8GB → **4GB** ✅
- Quality chỉ giảm ~2-3%

**2. Giảm max_tokens**
- Normal: 1000 tokens
- Deep Thinking: 2000 tokens
- Có thể giảm xuống 500 nếu cần

**3. Unload models không dùng**
```javascript
// Call API to unload
fetch('/api/unload-model', {
    method: 'POST',
    body: JSON.stringify({model_key: 'qwen2.5'})
})
```

**4. Chỉ load 1 model tại 1 thời điểm**
- Models sẽ lazy load khi cần
- Tự động cache khi đã load

---

## 📊 So sánh với Cloud API:

| Feature | Local | Cloud |
|---------|-------|-------|
| **Chi phí** | FREE (0đ) | $0.04-0.15/1M tokens |
| **Internet** | Không cần | Bắt buộc |
| **Privacy** | 100% private | Đi qua server |
| **Tốc độ** | Phụ thuộc GPU | Nhanh & ổn định |
| **Quality** | Qwen2.5 ≈ GPT-4 | GPT-4o best |
| **Giới hạn** | Không giới hạn | Rate limits |
| **Setup** | Phức tạp | Dễ (chỉ cần API key) |

---

## 🐛 Troubleshooting:

### ❌ "Out of memory" error
**Giải pháp:**
1. Dùng model nhỏ hơn (Qwen1.5 thay vì Qwen2.5)
2. Close các chương trình khác
3. Enable 8-bit quantization (tự động)
4. Restart ChatBot

### ❌ "Model not found" error  
**Giải pháp:**
1. Kiểm tra path: `ChatBot/models/Qwen2.5-14B-Instruct/`
2. Verify files exist (model-*.safetensors)
3. Re-download model nếu thiếu files

### ❌ Response rất chậm
**Giải pháp:**
1. Check GPU usage (Task Manager)
2. Dùng model nhỏ hơn
3. Nếu CPU: Chấp nhận chậm hoặc dùng Cloud API

### ❌ "CUDA out of memory"
**Giải pháp:**
1. Close Stable Diffusion WebUI (giải phóng VRAM)
2. Dùng 8-bit quantization
3. Dùng model nhỏ hơn

### ❌ Import error "torch not found"
**Giải pháp:**
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 🎓 Best Practices:

### 1. **Chọn model phù hợp**
- Máy yếu: Qwen1.5
- Tiếng Việt: BloomVN
- Production: Qwen2.5 ⭐

### 2. **Quản lý memory**
- Chỉ load model đang dùng
- Unload model cũ trước khi load mới
- Close app không cần thiết

### 3. **Optimize cho tốc độ**
- Dùng GPU nếu có
- Enable 8-bit quantization
- Giảm max_tokens nếu không cần

### 4. **Backup và update**
- Backup models folder định kỳ
- Check updates trên Hugging Face
- Test model mới trước khi replace

---

## 📈 Performance Tips:

### GPU Optimization:
```python
# Already implemented in code:
- device_map="auto"          # Auto GPU selection
- load_in_8bit=True          # 8-bit quantization
- torch_dtype=torch.float16  # FP16 precision
```

### CPU Optimization:
```python
# For CPU mode:
- Use smaller model (Qwen1.5)
- Reduce max_tokens (500 instead of 1000)
- Lower temperature (0.5 instead of 0.7)
```

---

## 🔗 Resources:

- **Qwen2.5-14B:** https://huggingface.co/Qwen/Qwen2.5-14B-Instruct
- **Qwen1.5-1.8B:** https://huggingface.co/Qwen/Qwen1.5-1.8B-Chat
- **BloomVN-8B:** https://huggingface.co/BlossomsAI/BloomVN-8B-chat
- **Transformers Docs:** https://huggingface.co/docs/transformers

---

## ✅ Checklist:

- [ ] Cài dependencies: `torch`, `transformers`, `accelerate`
- [ ] Kiểm tra models đã tải: `models/` folder
- [ ] Khởi động ChatBot: `python services/chatbot/run.py`
- [ ] Chọn local model trong dropdown
- [ ] Test chat với từng model
- [ ] Verify VRAM usage (Task Manager → GPU)
- [ ] Compare quality vs cloud models

---

**Enjoy 100% FREE local AI!** 🎉

**No internet. No API keys. No limits. Just pure AI power on your machine!** 💪
