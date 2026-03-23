# AI-Enhanced Service Setup Guide

## 🚀 Tính Năng Mới

### AI-Powered Health Checker
Script setup đã được nâng cấp với trí tuệ nhân tạo để:

- ✅ **Tự động kiểm tra dependencies** - So sánh `pip list` với `requirements.txt` bằng AI
- ✅ **Phát hiện thư viện thiếu** - AI xác định chính xác package nào cần cài
- ✅ **Chẩn đoán lỗi thông minh** - Phân biệt lỗi do thiếu thư viện vs lỗi code
- ✅ **Tự động sửa lỗi** - Auto-install missing packages và fix version conflicts
- ✅ **Fallback thông minh** - Sử dụng GROK-3 (FREE) làm model mặc định

## 📋 Yêu Cầu Hệ Thống

### Python Version
- **Khuyến nghị**: Python **3.11.9**
- **Tương thích**: Python 3.10.x

### API Keys (Tùy chọn - cho AI features)
Tạo file `.env` ở thư mục root:

```env
# GROK API (FREE - Mặc định)
GROK_API_KEY=xai-your_grok_api_key

# OpenAI API (Tùy chọn)
OPENAI_API_KEY=sk-your_openai_api_key

# DeepSeek API (Tùy chọn)
DEEPSEEK_API_KEY=sk-your_deepseek_api_key
```

**Lưu ý**: Nếu không có API key, script vẫn chạy với basic dependency check.

## 🛠️ Hướng Dẫn Sử dụng

### Option 1: Setup Tất Cả Services (Có AI)

```bash
# Chạy menu
menu.bat

# Chọn option P
P. Setup All Services
```

Script sẽ:
1. Tạo virtual environment cho mỗi service
2. Cài đặt dependencies từ requirements.txt
3. **Chạy AI health check** cho từng service
4. **Tự động fix** các vấn đề phát hiện được

### Option 2: Setup Virtual Environment (Root)

```bash
# Chạy menu
menu.bat

# Chọn option V
V. Setup venv for all
```

Tạo `.venv` ở root folder với Python 3.11.

### Option 3: Health Check Thủ Công

```bash
# Activate venv
.venv\Scripts\activate.bat

# Chạy health check cho 1 service
python scripts\utilities\service_health_checker.py "ChatBot" "services\chatbot"

# Hoặc với test command
python scripts\utilities\service_health_checker.py "Text2SQL" "services\text2sql" "python -c \"import flask; print('OK')\""
```

## 📊 Cách AI Health Checker Hoạt Động

### Bước 1: Dependency Analysis
```
[CHECK] Analyzing dependencies for ChatBot...
```

AI so sánh:
- `pip list` (đã cài)
- `requirements.txt` (yêu cầu)

Output:
```json
{
  "status": "missing",
  "missing_packages": ["torch", "transformers"],
  "recommendations": [
    "pip install torch==2.0.0",
    "pip install transformers>=4.37.0"
  ]
}
```

### Bước 2: Auto-Fix
```
[FIX] Attempting auto-fix...
[RUN] pip install torch==2.0.0
[OK] Command succeeded
```

### Bước 3: Service Test (Optional)
```
[TEST] Running service test: python -c "import flask"
[OK] Service test passed
```

### Bước 4: Error Diagnosis (Nếu có lỗi)
```
[AI] Diagnosing error...
[DIAGNOSIS] Missing library: paddleocr
[FIX] pip install paddleocr==2.7.3
```

## 🎯 Service-Specific Notes

### ChatBot (Port 5000)
- Python: 3.11.x recommended
- Venv: `venv_chatbot`
- Heavy dependencies: torch, transformers

### Speech2Text (Port 7860)
- Python: 3.11.x recommended
- Venv: `venv`
- Special: pyannote.audio requires HF_TOKEN

### Stable Diffusion (Port 7861)
- Python: 3.11.x recommended
- Venv: `venv`
- Note: May complete setup on first run

### Document Intelligence (Port 5003)
- Python: 3.11.x recommended
- Venv: `venv`
- Special: paddlepaddle (Windows specific)

### LoRA Training (Port 7862)
- Python: 3.11.x recommended
- Venv: `lora`
- New: GROK-3 integration

### Text2SQL (Port 5002)
- Python: 3.11.x recommended
- Venv: `venv`
- Lightweight setup

### Image Upscale (Port 7863)
- Python: 3.11.x recommended
- Venv: `venv`
- Flexible torch version (>=1.7.0)

### MCP Server
- Python: 3.11.x recommended
- Venv: `venv`
- Minimal dependencies

### Hub Gateway (Port 3000)
- Python: 3.11.x recommended
- Venv: `venv`
- No requirements.txt (basic Flask only)

## 🔧 Troubleshooting

### AI Health Check Không Chạy
```
[WARNING] No AI service available. Running basic checks only.
```

**Nguyên nhân**: Thiếu API key hoặc package

**Giải pháp**:
```bash
# Cài packages
pip install openai python-dotenv

# Thêm API key vào .env
echo GROK_API_KEY=xai-your_key >> .env
```

### Service Vẫn Lỗi Sau Auto-Fix
```
[FAIL] ❌ ChatBot has issues
```

**Kiểm tra**:
1. Đọc error message từ AI diagnosis
2. Check Python version: `python --version`
3. Xem log chi tiết ở console
4. Thử cài thủ công: `cd services\chatbot && pip install -r requirements.txt`

### Version Conflict

**Ví dụ**: torch 2.0.1 vs torch 2.4.0

**Giải pháp**:
```bash
# AI sẽ suggest:
pip install torch==2.0.1 --force-reinstall
```

### Lỗi Import Module

**AI phân tích**:
```json
{
  "error_type": "missing_library",
  "diagnosis": "Module 'paddleocr' not found in pip list",
  "fix_commands": ["pip install paddleocr==2.7.3"],
  "is_critical": true
}
```

## 📝 Changelog

### v2.4 (2025-12-17)
- ✅ Added AI-powered health checker
- ✅ GROK-3 integration as default model
- ✅ Auto-fix for missing dependencies
- ✅ Smart error diagnosis
- ✅ Updated Python recommendation to 3.11.x

### v2.3
- Basic setup for all services
- Python 3.10.6 requirement

## 🤝 Contributing

Để cải thiện AI health checker:

1. Update prompt trong `service_health_checker.py`
2. Thêm service-specific tests
3. Improve error diagnosis logic

## 📚 Tài Liệu Liên Quan

- [GETTING_STARTED.md](../docs/GETTING_STARTED.md)
- [SCRIPTS_GUIDE.md](../docs/SCRIPTS_GUIDE.md)
- [API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md)

---

**Made with ❤️ and 🤖 AI**
