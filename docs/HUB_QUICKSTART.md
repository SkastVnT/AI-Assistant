# AI Assistant Hub - Quick Start Guide

## 🚀 Giới Thiệu

AI Assistant Hub là **giao diện trung tâm** (port 3000) giúp bạn quản lý và truy cập tất cả 6 dịch vụ AI trong hệ thống.

## 📊 Tổng Quan Services

| Service | Port | URL | Mô tả |
|---------|------|-----|-------|
| **Hub Gateway** | 3000 | http://localhost:3000 | Giao diện chính (bắt đầu từ đây) |
| **ChatBot** | 5000 | http://localhost:5000 | Trợ lý AI với Gemini, GPT, Local LLMs |
| **Text2SQL** | 5001 | http://localhost:5001 | Chuyển ngôn ngữ tự nhiên → SQL |
| **Speech2Text** | 5002 | http://localhost:5002 | Chuyển giọng nói → văn bản |
| **Document Intelligence** | 5003 | http://localhost:5003 | OCR + AI phân tích tài liệu |
| **RAG Services** | 5004 | http://localhost:5004 | Q&A thông minh với RAG |
| **Stable Diffusion** | 7860 | http://localhost:7860 | Tạo hình ảnh từ text |

## 🎯 Cách Sử Dụng (Khuyến Nghị)

### Bước 1: Khởi động Hub Gateway (port 3000)

```batch
cd i:\AI-Assistant\scripts\startup
start_hub.bat
```

Truy cập: **http://localhost:3000**

### Bước 2: Từ Hub, chọn service bạn muốn dùng

Hub sẽ hiển thị tất cả 6 services với:
- ✅ Thông tin chi tiết
- ✅ Tính năng chính
- ✅ Nút "Mở dịch vụ" để truy cập trực tiếp

### Bước 3: Service tự động mở trong tab mới

Click vào service card → Service mở trong tab mới → Bắt đầu sử dụng!

## ⚡ Khởi Động Tất Cả Services (1 Click)

Nếu muốn khởi động tất cả 7 services cùng lúc:

```batch
cd i:\AI-Assistant\scripts\startup
start_all_services.bat
```

Script này sẽ:
1. Mở 7 terminal windows riêng biệt
2. Khởi động mỗi service trong window của nó
3. Hub tự động mở sau 30 giây

## 📁 Cấu Trúc Hub

```
i:\AI-Assistant\
├── src\
│   └── hub.py                    # Hub backend (Flask)
├── templates\
│   └── index.html                # Hub frontend (Tailwind CSS)
├── config\
│   └── model_config.py           # Service configs (ports, features)
├── scripts\
│   └── startup\
│       ├── start_hub.bat         # Khởi động Hub
│       └── start_all_services.bat # Khởi động tất cả
└── venv_hub\                     # Virtual env cho Hub
```

## 🔧 Cấu Hình Services

### Thêm/Sửa Service

Edit file `config/model_config.py`:

```python
SERVICES: Dict[str, ServiceConfig] = {
    "your_service": ServiceConfig(
        name="Your Service Name",
        description="Mô tả ngắn gọn",
        icon="🎯",                    # Emoji icon
        port=5005,                     # Port riêng
        url="http://localhost:5005",
        color="from-purple-500 to-pink-600",  # Tailwind gradient
        features=[
            "Tính năng 1",
            "Tính năng 2",
            "Tính năng 3"
        ]
    )
}
```

### Thay Đổi Port Hub

Edit `.env` hoặc `config/model_config.py`:

```python
PORT = int(os.getenv("HUB_PORT", "3000"))  # Đổi 3000 thành port khác
```

## 🎨 Giao Diện Hub

### Features:

- ✅ **Modern UI**: Tailwind CSS + Gradient animations
- ✅ **Service Cards**: Hiển thị đẹp với icons, colors, features
- ✅ **Statistics**: Real-time stats (total services, status, models)
- ✅ **Responsive**: Tương thích mobile, tablet, desktop
- ✅ **Modal Info**: Chi tiết service khi click "Thông tin chi tiết"
- ✅ **Quick Launch**: Nút "Mở dịch vụ" mở service trong tab mới

### Screenshots Flow:

```
Hub (3000)
   ↓
[Card: ChatBot 🤖]
   ↓ Click "Mở dịch vụ"
   ↓
ChatBot UI (5000)
```

## 🔥 Workflow Tiêu Biểu

### Scenario 1: Chỉ dùng 1 service

```batch
# Khởi động Hub
cd i:\AI-Assistant\scripts\startup
start_hub.bat

# Truy cập http://localhost:3000
# Click vào service muốn dùng (VD: ChatBot)
# Hub tự động mở ChatBot trong tab mới
```

### Scenario 2: Dùng nhiều services

```batch
# Khởi động tất cả
cd i:\AI-Assistant\scripts\startup
start_all_services.bat

# Đợi 30-60s để services khởi động
# Truy cập Hub: http://localhost:3000
# Switch giữa các services bằng tabs
```

### Scenario 3: Development mode

```batch
# Terminal 1: Hub
cd i:\AI-Assistant
venv_hub\Scripts\activate.bat
python src\hub.py

# Terminal 2: Service bạn đang dev (VD: ChatBot)
cd i:\AI-Assistant\ChatBot
venv_chatbot\Scripts\activate.bat
python app.py

# Truy cập Hub để test
```

## 🛠️ Setup Hub Lần Đầu

### Auto Setup (Khuyến nghị):

```batch
cd i:\AI-Assistant\scripts\startup
start_hub.bat
```

Script tự động:
1. Tạo `venv_hub` nếu chưa có
2. Cài Flask, Flask-CORS, python-dotenv
3. Khởi động Hub

### Manual Setup:

```batch
cd i:\AI-Assistant
python -m venv venv_hub
venv_hub\Scripts\activate.bat
pip install flask flask-cors python-dotenv
python src\hub.py
```

## 📡 API Endpoints

Hub cũng cung cấp REST API:

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | Hub homepage (HTML) |
| `/api/services` | GET | List tất cả services (JSON) |
| `/api/services/<name>` | GET | Chi tiết 1 service |
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Hub statistics |

### Ví dụ:

```bash
# Get all services
curl http://localhost:3000/api/services

# Get specific service
curl http://localhost:3000/api/services/chatbot

# Health check
curl http://localhost:3000/api/health
```

## 🔍 Troubleshooting

### Port 3000 đã được dùng

```batch
# Tìm process đang dùng port 3000
netstat -ano | findstr :3000

# Kill process
taskkill /PID <process-id> /F

# Hoặc đổi port trong config/model_config.py
```

### Hub không mở được services

**Nguyên nhân**: Services chưa khởi động

**Giải pháp**: Khởi động service trước:
```batch
# VD: Khởi động ChatBot
cd i:\AI-Assistant\ChatBot
venv_chatbot\Scripts\activate.bat
python app.py
```

### Lỗi "Module not found"

```batch
cd i:\AI-Assistant
venv_hub\Scripts\activate.bat
pip install -r requirements.txt
```

## 💡 Best Practices

1. **Luôn khởi động Hub trước** - Đây là điểm truy cập chính
2. **Sử dụng `start_all_services.bat`** cho full experience
3. **Kiểm tra logs** nếu service không hoạt động
4. **Đóng services đúng cách** (Ctrl+C) để tránh zombie processes
5. **Dùng Hub để quản lý** thay vì nhớ từng port

## 📚 Tài Liệu Liên Quan

- [VENV_SETUP_GUIDE.md](./VENV_SETUP_GUIDE.md) - Setup virtual environments
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Quick reference guide
- [docs/](../docs/) - Detailed documentation

## 🎯 Summary

```
┌─────────────────────────────────────┐
│   AI ASSISTANT HUB (Port 3000)     │
│   ================================   │
│                                     │
│   🎯 Điểm truy cập trung tâm       │
│   📊 Quản lý 6 services             │
│   🚀 One-click service launch       │
│   📱 Modern, responsive UI          │
│                                     │
└─────────────────────────────────────┘
            │
            ├──→ ChatBot (5000)
            ├──→ Text2SQL (5001)
            ├──→ Speech2Text (5002)
            ├──→ Document Intelligence (5003)
            ├──→ RAG Services (5004)
            └──→ Stable Diffusion (7860)
```

**Bắt đầu ngay:**
```batch
cd i:\AI-Assistant\scripts\startup
start_hub.bat
```

**→ http://localhost:3000**
