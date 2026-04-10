# AI-Assistant

Nền tảng microservices tích hợp nhiều dịch vụ AI: chatbot (đa mô hình, voice, OCR, RAG, web search, image gen, video generation), stable diffusion, edit image (ComfyUI), mcp server.

## Tổng quan

- **Kiến trúc**: Python microservices — Chatbot chạy **Flask** (mặc định, cổng 5000); FastAPI mode tùy chọn qua `USE_FASTAPI=true`.
- **Chạy cục bộ** bằng script (`menu.bat` / `menu.sh`) hoặc Docker Compose.
- **Cấu hình chung** qua file `.env` trong `app/config/` – tải bởi `services/shared_env.py`.
- **Chatbot** tích hợp voice transcription (Whisper API), OCR (Vision APIs), web search đa engine (SerpAPI), reverse image search, tạo ảnh AI (fal.ai, BFL/FLUX), và tạo video AI (Sora 2).

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
| Thinking Modes | Instant (nhanh), Think (chuỗi suy nghĩ), Deep Think (DeepSeek R1), Multi-Think (4-Agents) |
| Voice (STT) | Whisper API — transcribe audio sang text |
| OCR | Vision API — đọc nội dung ảnh/PDF |
| RAG | MongoDB Atlas — lưu & tìm kiếm memory theo ngữ nghĩa |
| **Web Search** | **SerpAPI** (Google, Bing, Baidu) + Google CSE fallback — tự động khi cần |
| **Reverse Image** | **Google Lens** → Google Reverse Image → Yandex Images (cascade tự động) |
| **SauceNAO** | Tìm nguồn gốc ảnh anime/illustration qua SauceNAO API |
| **Image Search** | SerpAPI google_images — tìm kiếm ảnh theo query |
| **Image Gen** | fal.ai (FLUX) + BFL/Black Forest Labs — tạo ảnh AI chất lượng cao |
| Image Storage | ImgBB + MongoDB + Firebase RTDB cho ảnh được tạo bởi AI |
| **Video AI** | **OpenAI Sora 2** — tạo video từ text (4/8/12s, 720p/1080p) |
| Streaming | Server-Sent Events (SSE) |
| Swagger UI | Tài liệu API tự động tại `/docs` |

### Thinking Modes

| Mode | Mô tả |
| --- | --- |
| `instant` | Trả lời ngay, không reasoning (mặc định) |
| `think` | Chuỗi suy nghĩ nội tại trước khi trả lời |
| `deep-think` | DeepSeek R1 extended reasoning |
| `multi-thinking` | 4 Agents phối hợp: Analyst + Creative + Critic + Synthesizer |

### Search Tools UI

Các nút công cụ có sẵn trong chat UI:

| Nút | Tool | Mô tả |
| --- | --- | --- |
| 🔍 Web Search | `google-search` | SerpAPI Google (tự động fallback Google CSE) |
| Lens | `serpapi-reverse-image` | Google Lens → Reverse Image → Yandex cascade |
| Bing | `serpapi-bing` | SerpAPI Bing search |
| Baidu | `serpapi-baidu` | SerpAPI Baidu search |
| Img Search | `serpapi-images` | SerpAPI Google Images |
| SauceNAO | `saucenao` | Tìm nguồn gốc ảnh anime |

Web search cũng **tự động kích hoạt** khi câu hỏi chứa từ khóa thời gian thực (giá vàng, thời tiết, tin tức, v.v.).

### API Video (Sora 2)

```text
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

### 2) Chạy Chatbot (Flask mode — mặc định)

```bash
# Windows
cd services\chatbot
python chatbot_main.py

# Linux/Mac
cd services/chatbot
python chatbot_main.py
```

### 2b) Chạy Chatbot (FastAPI mode — tùy chọn)

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
MONGODB_DB_NAME=chatbot_db

# Shared env profile
env=dev
```

Biến thường dùng thêm cho chatbot:

```env
# Image Generation (fal.ai + BFL/FLUX)
FAL_API_KEY=                        # fal.ai — FLUX.1, FLUX Pro, Recraft, Ideogram
BFL_API_KEY=                        # Black Forest Labs — FLUX Pro raw

# Web Search
SERPAPI_API_KEY=                    # SerpAPI — Google, Bing, Baidu, Lens, Images
GOOGLE_SEARCH_API_KEY_1=            # Google CSE key 1 (fallback)
GOOGLE_SEARCH_API_KEY_2=            # Google CSE key 2 (fallback)
GOOGLE_CSE_ID=                      # Google Custom Search Engine ID (fallback)

# Reverse Image Search
SAUCENAO_API_KEY=                   # SauceNAO — tìm nguồn gốc ảnh anime

# Chọn database đích cho chat + image storage
MONGODB_DB_NAME=chatbot_db

# Optional X.509 auth cho MongoDB Atlas
MONGODB_X509_ENABLED=false
MONGODB_X509_URI=
MONGODB_X509_CERT_PATH=

# Firebase RTDB fallback cho gallery ảnh
FIREBASE_RTDB_URL=
FIREBASE_DB_SECRET=

# Google Drive upload qua service account
GOOGLE_DRIVE_ENABLED=false
GOOGLE_DRIVE_SA_JSON_PATH=config/google-drive-sa.json
GOOGLE_DRIVE_FOLDER_ID=
```

Lưu ý vận hành:

- Chatbot app mới dùng `MONGODB_DB_NAME`; nếu không khai báo sẽ mặc định là `chatbot_db`.
- Luồng image storage cũng dùng explicit DB name, không còn phụ thuộc default database trong connection string.
- Google Drive bằng service account thường không upload được vào personal Drive do giới hạn quota; nên dùng Shared Drive hoặc tắt Drive upload.

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
  chatbot/              # Multi-model AI Chatbot (Flask, FastAPI optional)
    chatbot_main.py     #   Entry point Flask — endpoint /chat
    run.py              #   Entry point FastAPI (USE_FASTAPI=true)
    routes/
      stream.py         #   Flask SSE endpoint /chat/stream (primary)
      main.py           #   Các route phụ
    core/
      config.py         #   Load tất cả API keys từ .env
      tools.py          #   Tool functions: web search, image search, SauceNAO, SerpAPI
    fastapi_app/        #   App factory, routers, models (FastAPI optional)
    src/                #   Core logic: chatbot, video_generation, OCR, STT
    templates/          #   Chat UI (index.html)
  stable-diffusion/     # Image generation (SDXL)
  edit-image/           # ComfyUI-based image editing
  mcp-server/           # Model Context Protocol server
tests/             # Test suite
private/           # Dữ liệu/submodule nội bộ
  archived-services/    # Dịch vụ đã ngả hưu (speech2text, text2sql, ...)
```

## Kiến trúc tích hợp

```text
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

## Lưu trữ ảnh

Luồng lưu ảnh hiện tại:

1. Tạo ảnh qua provider router.
2. Lưu file local trong chatbot storage.
3. Upload ImgBB để lấy public URL.
4. Ghi metadata vào MongoDB nếu kết nối được.
5. Ghi thêm vào Firebase RTDB như fallback/index cho gallery.
6. Nếu bật Google Drive và service account hợp lệ, thử upload thêm lên Drive.

Các endpoint liên quan:

```text
POST /api/save-generated-image     # Lưu ảnh generated + upload cloud/db
POST /api/gallery/upload-db        # Đồng bộ ảnh local từ gallery lên cloud/db
GET  /api/image-gen/images/{id}    # Serve ảnh đã tạo
GET  /api/image-gen/meta/{id}      # Metadata ảnh
POST /api/image-gen/save/{id}      # Re-upload một ảnh đã có lên cloud/db
```

Ghi chú:

- Nếu ImgBB thành công nhưng MongoDB lỗi, ảnh vẫn có thể có cloud URL nhưng `saved_to_mongodb=false`.
- Nếu Firestore Admin SDK không có service account, hệ thống vẫn có thể lưu qua Firebase RTDB.
- Google Drive là nhánh best-effort; lỗi Drive không chặn luồng lưu ảnh chính.

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
