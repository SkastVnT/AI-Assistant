# AI-Assistant

Nền tảng microservices tích hợp nhiều dịch vụ AI: chatbot (đa mô hình, voice, OCR, RAG, video generation), stable diffusion, edit image (ComfyUI), mcp server.

## Tổng quan

- **Kiến trúc**: Python microservices — Chatbot chạy **FastAPI** (uvicorn), các service khác dùng Flask.
- **Chạy cục bộ** bằng script (`menu.bat` / `menu.sh`) hoặc Docker Compose.
- **Cấu hình chung** qua file `.env` trong `app/config/` – tải bởi `services/shared_env.py`.
- **Chatbot** tích hợp voice transcription (Whisper API), OCR (Vision APIs), và tạo video AI (Sora 2).

## Dịch vụ đang hoạt động

| Service | Port | Entry Point | Mô tả |
| --- | --- | --- | --- |
| ChatBot | 5000 | `services/chatbot/run.py` | AI Chat + Voice + OCR + Video + Tools |
| Stable Diffusion | 7861 | `services/stable-diffusion/` | Image generation (SDXL) |
| Edit Image | 8100 | `services/edit-image/` | AI image editing (ComfyUI backend) |
| MCP Server | stdio | `services/mcp-server/server.py` | Model Context Protocol tools |

## Tính năng Chatbot

| Tính năng | Mô tả |
| --- | --- |
| Đa mô hình | Grok, OpenAI, DeepSeek, Gemini, Qwen, Local |
| Voice (STT) | Whisper API — transcribe audio sang text |
| OCR | Vision API — đọc nội dung ảnh/PDF |
| RAG | MongoDB Atlas — lưu & tìm kiếm memory theo ngữ nghĩa |
| **Video AI** | **OpenAI Sora 2** — tạo video từ text (4/8/12s, 720p/1080p) |
| Streaming | Server-Sent Events (SSE) |
| Swagger UI | Tài liệu API tự động tại `/docs` |

### API Video (Sora 2)

```
POST /api/video/generate          # Gửi job (trả về ngay)
POST /api/video/generate-sync     # Gửi job + chờ hoàn thành
GET  /api/video/status/{id}       # Kiểm tra tiến độ (progress 0-100%)
GET  /api/video/download/{id}     # Tải file mp4
GET  /api/video/list              # Danh sách video đã tạo
```

Giá: `sora-2` $0.10/s · `sora-2-pro` $0.30/s · Thời lượng: 4, 8, hoặc 12 giây.

## Chạy nhanh

### 1) Clone và chạy menu

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant

# Windows
menu.bat

# Linux/Mac
./menu.sh
```

### 2) Chạy Chatbot (FastAPI mode)

```bash
# Windows
set USE_FASTAPI=true
cd services\chatbot
python run.py

# Linux/Mac
USE_FASTAPI=true python services/chatbot/run.py
```

### 3) Chạy bằng Docker

```bash
# Full stack
docker-compose -f app/config/docker-compose.yml up -d

# Lightweight mode
docker-compose -f app/config/docker-compose.light.yml up -d

# Health check chatbot
curl http://localhost:5000/health
```

### 4) Chạy từng service (Windows)

```bat
app\scripts\start-chatbot.bat
app\scripts\start-stable-diffusion.bat
app\scripts\start-edit-image.bat
app\scripts\start-mcp.bat
```

### 5) Chạy tất cả

```bat
app\scripts\start-all.bat
```

## Cấu hình môi trường

Tạo file môi trường từ mẫu:

```bash
cp app/config/.env.example app/config/.env
```

Biến tối thiểu nên có:

```env
# Chọn ít nhất 1 nhà cung cấp LLM
GROK_API_KEY=
OPENAI_API_KEY=         # Bắt buộc để dùng Sora 2 video generation
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=

# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=chatbot

# Shared env profile
env=dev
```

Cơ chế tải env: Mỗi service gọi `load_shared_env(__file__)` từ `services/shared_env.py` → tự tìm `app/config/.env_{env}` hoặc `app/config/.env`.

## Cấu trúc thư mục chính

```text
app/
  config/          # Cấu hình tập trung (.env, model_config, config.yml)
  scripts/         # Script vận hành (start, stop, health-check)
  requirements/    # Requirements theo nhóm service
  src/             # Shared modules (utils, database, cache, security)
  ComfyUI/         # ComfyUI + extra model paths
services/
  shared_env.py         # Bộ tải env dùng chung
  chatbot/              # Multi-model AI Chatbot (FastAPI)
    fastapi_app/        #   App factory, routers, models, dependencies
    src/                #   Core logic: chatbot, video_generation, OCR, STT
  stable-diffusion/     # Image generation (SDXL)
  edit-image/           # ComfyUI-based image editing
  mcp-server/           # Model Context Protocol server
tests/             # Test suite
private/           # Dữ liệu/submodule nội bộ
  archived-services/    # Dịch vụ đã ngả hưu (speech2text, text2sql, ...)
```

## Kiến trúc tích hợp

```
services/shared_env.py ← tất cả services load .env qua đây
         ↓
     app/config/
         ├── .env               → Biến môi trường
         ├── config.yml          → Service port/host config
         ├── model_config.py     → ServiceConfig dataclasses
         ├── public_urls.py      → Cloudflare tunnel URL manager
         ├── logging_config.py   → Logging setup
         ├── rate_limiter.py     → Gemini/OpenAI rate limiting
         └── response_cache.py   → LLM response caching
```

## Tài liệu liên quan

- [app/scripts/README.md](app/scripts/README.md)
- [app/requirements/README.md](app/requirements/README.md)
- [tests/README.md](tests/README.md)
- [SECURITY.md](SECURITY.md)

## Contributing

1. Tạo nhánh mới từ `master`.
2. Commit theo phạm vi thay đổi.
3. Mở Pull Request.

## Author & Collaborator

- [SkastVnT](https://github.com/SkastVnT)
- [sug1omyo](https://github.com/sug1omyo)

## License

MIT. Xem chi tiết tại [LICENSE](LICENSE).
