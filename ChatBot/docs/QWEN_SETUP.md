# 🤖 Qwen1.5b Integration Guide

## 📋 Overview
Qwen (通义千问) là AI model của Alibaba Cloud, hỗ trợ tiếng Việt và nhiều ngôn ngữ khác.

---

## 🔑 Cách lấy API Key

### Bước 1: Tạo tài khoản Alibaba Cloud
1. Truy cập: https://www.alibabacloud.com/
2. Đăng ký tài khoản (có thể dùng email hoặc phone)
3. Xác thực tài khoản

### Bước 2: Kích hoạt DashScope
1. Truy cập: https://dashscope.aliyun.com/
2. Đăng nhập bằng tài khoản Alibaba Cloud
3. Click "开通服务" (Activate Service)
4. Chọn gói miễn phí (Free Tier) hoặc trả phí

### Bước 3: Lấy API Key
1. Vào Dashboard: https://dashscope.console.aliyun.com/
2. Click "API-KEY" ở menu bên trái
3. Click "创建新的API-KEY" (Create new API Key)
4. Copy API Key (dạng: `sk-xxxxxxxxxxxxx`)

### Bước 4: Thêm vào .env
```env
QWEN_API_KEY=sk-your-api-key-here
```

---

## 🎯 Models Available

| Model | Size | Speed | Quality | Cost |
|-------|------|-------|---------|------|
| `qwen-turbo` | Small | ⚡ Fast | Good | 💰 Rẻ nhất |
| `qwen-plus` | Medium | 🚀 Medium | Better | 💰💰 Trung bình |
| `qwen-max` | Large | 🐌 Slow | Best | 💰💰💰 Đắt nhất |
| `qwen1.5-1.8b-chat` | 1.8B | ⚡⚡ Very Fast | OK | 💰 Rất rẻ |

**Hiện tại sử dụng:** `qwen-turbo` (cân bằng giữa tốc độ và chất lượng)

---

## 💡 Pricing (Alibaba Cloud DashScope)

### Free Tier
- ✅ 1 triệu tokens/tháng miễn phí
- ✅ Áp dụng cho tất cả models
- ✅ Không cần credit card (chỉ cần tài khoản)

### Paid Plans (sau khi hết Free Tier)
| Model | Input (¥/1M tokens) | Output (¥/1M tokens) |
|-------|---------------------|----------------------|
| qwen-turbo | ¥0.30 (~$0.04) | ¥0.60 (~$0.08) |
| qwen-plus | ¥4.00 (~$0.55) | ¥12.00 (~$1.65) |
| qwen-max | ¥40.00 (~$5.50) | ¥120.00 (~$16.50) |

**So sánh:**
- DeepSeek: $0.14/$0.28 per 1M tokens
- OpenAI GPT-4o-mini: $0.15/$0.60 per 1M tokens
- Gemini: FREE (có giới hạn rate limit)

---

## 🛠️ Technical Details

### API Endpoint
```
https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
```

### Request Format (OpenAI-compatible)
```python
headers = {
    "Authorization": f"Bearer {QWEN_API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "qwen-turbo",
    "messages": [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User message"}
    ],
    "temperature": 0.7,
    "max_tokens": 1000
}
```

### Response Format
```json
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Response text"
            }
        }
    ]
}
```

---

## 🎨 Features in ChatBot

### 1. Tất cả tính năng như các model khác
- ✅ Trò chuyện vui vẻ (Casual)
- ✅ Tâm lý - Tâm sự (Psychological)
- ✅ Giải pháp đời sống (Lifestyle)
- ✅ Lập trình - Công nghệ (Programming)
- ✅ Deep Thinking Mode

### 2. Conversation History
- ✅ Lưu 5 tin nhắn gần nhất làm context
- ✅ Hiểu ngữ cảnh cuộc trò chuyện

### 3. Temperature Control
- Normal mode: 0.7 (creative)
- Deep Thinking: 0.5 (more focused)

### 4. Token Limits
- Normal: 1000 tokens
- Deep Thinking: 2000 tokens

---

## 🔍 Troubleshooting

### 1. "Lỗi: Chưa cấu hình QWEN_API_KEY"
**Nguyên nhân:** Chưa thêm API key vào `.env`
**Giải pháp:**
```bash
# Mở ChatBot/.env và thêm:
QWEN_API_KEY=sk-your-api-key-here
```

### 2. "Lỗi Qwen API: 401 - Unauthorized"
**Nguyên nhân:** API key sai hoặc hết hạn
**Giải pháp:**
- Kiểm tra lại API key
- Tạo API key mới từ Dashboard

### 3. "Lỗi Qwen API: 429 - Too Many Requests"
**Nguyên nhân:** Vượt quá rate limit (miễn phí: 60 requests/phút)
**Giải pháp:**
- Đợi 1 phút rồi thử lại
- Upgrade lên paid plan

### 4. "Lỗi Qwen API: 400 - Bad Request"
**Nguyên nhân:** Request format sai
**Giải pháp:**
- Check logs để xem chi tiết lỗi
- Verify model name (qwen-turbo, qwen-plus, etc.)

### 5. "Lỗi Qwen: Connection timeout"
**Nguyên nhân:** Mạng chậm hoặc API down
**Giải pháp:**
- Kiểm tra kết nối internet
- Thử lại sau vài phút
- Check status: https://status.aliyun.com/

---

## 📊 Performance Comparison

### Response Time
| Model | Avg Response | Quality |
|-------|-------------|---------|
| Qwen Turbo | ~1-2s | ⭐⭐⭐⭐ |
| Gemini 2.0 | ~2-3s | ⭐⭐⭐⭐⭐ |
| DeepSeek | ~3-5s | ⭐⭐⭐⭐ |
| GPT-4o-mini | ~2-4s | ⭐⭐⭐⭐⭐ |

### Tiếng Việt Support
| Model | Vietnamese | Notes |
|-------|-----------|-------|
| Qwen | ⭐⭐⭐⭐ | Good, trained on Vietnamese |
| Gemini | ⭐⭐⭐⭐⭐ | Excellent |
| DeepSeek | ⭐⭐⭐ | OK, but sometimes mix Chinese |
| GPT-4o-mini | ⭐⭐⭐⭐⭐ | Excellent |

---

## 🚀 Usage Examples

### 1. Trò chuyện thông thường
```
User: Cho tôi vài lời khuyên để học lập trình hiệu quả
Qwen: Để học lập trình hiệu quả, bạn nên:
1. Thực hành hàng ngày...
2. Làm dự án thực tế...
```

### 2. Deep Thinking Mode
```
User: [Deep Thinking] Phân tích ưu nhược điểm của microservices
Qwen: [Phân tích chi tiết với cấu trúc rõ ràng]
Ưu điểm:
- Scalability độc lập...
- Technology diversity...
```

### 3. Psychological Support
```
User: [Chế độ: Tâm lý] Tôi đang stress vì công việc
Qwen: Tôi hiểu bạn đang gặp áp lực. Hãy thử...
```

---

## 🔄 Change Model (Code)

### Trong app.py (line 176-218)
```python
def chat_with_qwen(self, message, context='casual', deep_thinking=False):
    """Chat using Qwen 1.5b"""
    # Có thể thay đổi model:
    data = {
        "model": "qwen-turbo",  # <-- Thay đổi ở đây
        # Options: qwen-turbo, qwen-plus, qwen-max
        ...
    }
```

### Thay đổi parameters
```python
data = {
    "model": "qwen-turbo",
    "temperature": 0.8,  # 0.0-1.0 (cao = creative)
    "max_tokens": 3000,  # Tăng cho response dài hơn
    "top_p": 0.9,        # Thêm parameter này nếu muốn
}
```

---

## 📚 Additional Resources

### Official Documentation
- DashScope Docs: https://help.aliyun.com/zh/dashscope/
- API Reference: https://help.aliyun.com/zh/dashscope/developer-reference/api-details
- Models List: https://help.aliyun.com/zh/dashscope/developer-reference/model-square

### Community
- GitHub: https://github.com/QwenLM/Qwen
- Discord: https://discord.gg/qwen
- Forum: https://discuss.aliyun.com/

---

## ✅ Checklist

- [ ] Tạo tài khoản Alibaba Cloud
- [ ] Kích hoạt DashScope
- [ ] Lấy API Key
- [ ] Thêm `QWEN_API_KEY` vào `.env`
- [ ] Restart ChatBot server
- [ ] Test chat với Qwen model
- [ ] Verify response quality

---

**Version:** 1.5.2  
**Added:** October 29, 2025  
**Status:** ✅ Ready to use
