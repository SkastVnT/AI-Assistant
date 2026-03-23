# AI-Assistant

Nền tảng microservices tích hợp nhiều dịch vụ AI: chatbot, speech-to-text, OCR, text-to-sql, stable diffusion, comfyui, lora training, image upscale, mcp server.

## Tổng quan

- **Kiến trúc**: Python + Flask theo mô hình microservices.
- **Chạy cục bộ** bằng script (`menu.bat` / `menu.sh`) hoặc Docker Compose.
- **Cấu hình chung** qua file `.env` trong `app/config/` – tải bởi `services/shared_env.py`.
- **Hub Gateway** là điểm vào chính, liệt kê tất cả service kèm URL public (Cloudflare tunnel).

## Cổng dịch vụ

| Service | Port | Entry Point |
| --- | --- | --- |
| Hub Gateway | 3000 | `services/hub-gateway/hub.py` |
| ChatBot | 5000 | `services/chatbot/run.py` |
| Speech2Text | 5001 | `services/speech2text/app/web_ui.py` |
| Text2SQL | 5002 | `services/text2sql/run.py` |
| Document Intelligence | 5003 | `services/document-intelligence/run.py` |
| Stable Diffusion | 7861 | `services/stable-diffusion/` |
| LoRA Training | 7862 | `services/lora-training/webui.py --port 7862` |
| Image Upscale | 7863 | `services/image-upscale/src/upscale_tool/app.py` |
| ComfyUI | 8189 | `app/ComfyUI/main.py` |
| MCP Server | 8000 | `services/mcp-server/server.py` |

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

### 2) Chạy bằng Docker

```bash
# Full stack
docker-compose -f app/config/docker-compose.yml up -d

# Lightweight mode
docker-compose -f app/config/docker-compose.light.yml up -d

# Health check chatbot
curl http://localhost:5000/health
```

### 3) Chạy từng service (Windows)

```bat
app\scripts\start-hub-gateway.bat
app\scripts\start-chatbot.bat
app\scripts\start-speech2text.bat
app\scripts\start-text2sql.bat
app\scripts\start-document-intelligence.bat
app\scripts\start-stable-diffusion.bat
app\scripts\start-lora-training.bat
app\scripts\start-image-upscale.bat
```

### 4) Chạy tất cả

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
OPENAI_API_KEY=
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
  shared_env.py    # Bộ tải env dùng chung
  hub-gateway/     # API Gateway & Dashboard
  chatbot/         # Multi-model AI Chatbot
  speech2text/     # Audio → Text (Whisper)
  text2sql/        # NL → SQL
  document-intelligence/  # OCR + AI document analysis
  stable-diffusion/       # Image generation
  lora-training/          # LoRA fine-tuning
  image-upscale/          # AI image enhancement
  edit-image/             # ComfyUI-based image editing
  mcp-server/             # Model Context Protocol server
tests/             # Test suite
private/           # Dữ liệu/submodule nội bộ
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
