# AI-Assistant

Nền tảng microservices Python tích hợp nhiều dịch vụ AI: chatbot đa mô hình, stable diffusion, image editing (ComfyUI), và MCP server.

## Dịch vụ đang hoạt động

| Service | Port | Entry Point | Mô tả |
|---|---|---|---|
| **ChatBot** | **5000** | `services/chatbot/run.py` | AI Chat + Voice + OCR + Image Gen + Video + Tools |
| **Stable Diffusion** | **7861** | `services/stable-diffusion/` | Image generation (SDXL) |
| **Edit Image** | **8100** | `services/edit-image/` | AI image editing (ComfyUI backend) |
| **MCP Server** | **stdio** | `services/mcp-server/server.py` | Model Context Protocol tools |

> Chatbot hỗ trợ 3 chế độ khởi động: Flask monolith (mặc định), Flask modular (`USE_NEW_STRUCTURE=true`), FastAPI (`USE_FASTAPI=true`).

---

## Tính năng Chatbot

| Tính năng | Mô tả |
|---|---|
| **Đa mô hình LLM** | Grok (xAI), OpenAI GPT-4, DeepSeek, Gemini (pool 4 key), Qwen, OpenRouter, StepFun |
| **Thinking Modes** | Instant / Think / Deep-Think / Multi-Thinking (4 Agents) |
| **Skill System** | 11 built-in personas tự động route theo nội dung tin nhắn |
| **Image Generation** | 7 provider: fal.ai, BFL/FLUX, Replicate, StepFun, OpenAI DALL-E, Together AI, ComfyUI |
| **Anime Pipeline** | 7-stage layered anime generation — Vision → Plan → Compose → Structure → Beauty → Critique → Upscale |
| **Video AI** | OpenAI Sora 2 — text-to-video 4/8/12s, 720p/1080p |
| **Web Search** | SerpAPI (Google, Bing, Baidu) + Google CSE fallback — tự động kích hoạt |
| **Reverse Image** | Google Lens → Google Reverse Image → Yandex (cascade) |
| **Image Search** | SerpAPI google_images — tìm ảnh theo query |
| **SauceNAO** | Tìm nguồn gốc ảnh anime/illustration |
| **Voice (STT)** | Whisper API — transcribe audio thành text |
| **OCR** | Vision APIs — đọc nội dung ảnh và PDF |
| **RAG** | MongoDB Atlas — lưu và tìm kiếm memory theo ngữ nghĩa |
| **MCP Integration** | Truy cập file/folder local, đọc code, grep — qua MCP server (stdio) |
| **Memory System** | Lưu trữ memory theo session + semantic search |
| **User Auth** | Đăng ký/đăng nhập, quota tin nhắn/ảnh, video unlock |
| **Admin Panel** | Quản lý user, session, ảnh, memory, logs, payment |
| **QR Payment** | VietQR — mở khóa tính năng video generation |
| **Streaming** | Server-Sent Events (SSE) — streaming thời gian thực |
| **Image Storage** | ImgBB + MongoDB + Firebase RTDB + Google Drive |
| **Conversation CRUD** | Tạo / xóa / archive / switch conversation |
| **Swagger UI** | Tài liệu API tự động tại `/docs` (FastAPI mode) |

---

## Thinking Modes

| Mode | Mô tả |
|---|---|
| `instant` | Trả lời ngay, không reasoning — nhanh nhất |
| `think` | Chuỗi suy nghĩ nội tại trước khi trả lời |
| `deep-think` | DeepSeek R1 extended reasoning — phân tích sâu |
| `multi-thinking` | Research Council 5 thành viên, 2 phase: Logic Architect / Research Lead / Creative Strategist / Optimization Engineer / DevOps QA Critic |

---

## LLM Providers

| Provider | Env Key | Ghi chú |
|---|---|---|
| xAI Grok | `GROK_API_KEY` / `XAI_API_KEY` | Grok-2, Grok-3 |
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-4, o1; bắt buộc để dùng Sora 2 + DALL-E |
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek-V3, R1 reasoning |
| Google Gemini | `GEMINI_API_KEY_1..4` | Pool 4 key, rotation tự động |
| Alibaba Qwen | `QWEN_API_KEY` / `DASHSCOPE_API_KEY` | Qwen-2.5, Qwen-VL |
| OpenRouter | `OPENROUTER_API_KEY` | Multi-model proxy |
| StepFun | `STEPFUN_API_KEY` | Step-1X (Chinese LLM) |
| HuggingFace | `HUGGINGFACE_API_KEY` / `HUGGINGFACE_TOKEN` | Inference API |
| Local (Ollama) | — | Qwen, Llama qua Ollama/llama.cpp |

---

## Image Generation Providers

| Provider | Env Key | Ưu tiên | Đặc điểm |
|---|---|---|---|
| **fal.ai** | `FAL_API_KEY` | 90 | FLUX.1, FLUX Pro, Recraft, Ideogram |
| **Black Forest Labs** | `BFL_API_KEY` | 85 | FLUX Pro raw |
| **Replicate** | `REPLICATE_API_KEY` | 80 | Nhiều model, marketplace |
| **StepFun** | `STEPFUN_API_KEY` | 75 | Step-1X Flash |
| **OpenAI DALL-E** | `OPENAI_API_KEY` | 70 | DALL-E 3 |
| **Together AI** | `TOGETHER_API_KEY` | 60 | FLUX Schnell, distributed inference |
| **ComfyUI** | `SD_API_URL` | 10 | Local GPU, miễn phí, cần cài ComfyUI |

Tự động dùng những provider nào có API key. Fallback chain: nếu provider lỗi, thử provider tiếp theo theo thứ tự ưu tiên.

---

## Skill System

Runtime Skill System cho phép chatbot tự động chọn persona phù hợp với yêu cầu, hoặc người dùng kích hoạt thủ công qua UI.

### Luồng xử lý

```
resolve_skill()    Ưu tiên: explicit > session > auto-route > none
  explicit         Request body có trường "skill": "coding-assistant"
  session          Người dùng đã kích hoạt skill qua /api/skills/activate
  auto-route       SkillRouter chấm điểm từ khóa trong tin nhắn (ngưỡng 1.05)
        ↓
apply_skill_overrides()   Merge cấu hình skill vào request
  → model, thinking_mode, system_prompt, tools, context_window
```

### 11 Skill Built-in

| Skill ID | Trigger tự động | Mô tả |
|---|---|---|
| `realtime-search` | today, news, price, weather | Tìm kiếm web, sự kiện hiện tại |
| `code-expert` | architecture, design pattern, algorithm | Review code, kiến trúc hệ thống |
| `coding-assistant` | code, debug, function, bug, refactor | Hỗ trợ code từng bước |
| `research-analyst` | analyze, compare, evaluate, report | Nghiên cứu chuyên sâu |
| `repo-analyzer` | repository, codebase, project structure | Phân tích repository |
| `research-web` | search, find, look up, research | Nghiên cứu web |
| `prompt-engineer` | prompt, system prompt, instruction | Tối ưu image prompt |
| `mcp-file-helper` | file, folder, read file, MCP | Thao tác file qua MCP |
| `creative-writer` | write, story, poem, creative, essay | Sáng tạo, viết lách |
| `shopping-advisor` | buy, price, recommend, product | Tư vấn mua sắm |
| `counselor` | stress, anxiety, feeling, advice | Tư vấn tâm lý, hỗ trợ cảm xúc |

### SSE Metadata

`POST /chat/stream` phát event `metadata` kèm thông tin skill đang được dùng:

```json
{
  "skill_id": "coding-assistant",
  "skill_source": "auto",
  "auto_score": 2.1,
  "auto_keywords": ["code", "debug"]
}
```

`skill_source`: `"explicit"` | `"session"` | `"auto"` | `"none"`

### YAML Skill Schema

```yaml
id: my-skill
name: My Skill
description: Mô tả skill
enabled: true
priority: 8
tags: [coding, tools]
trigger_keywords:
  - keyword: "example"
    weight: 1.0
overrides:
  model: "gpt-4o"
  thinking_mode: "think"       # instant / think / deep-think
  context_window: 8192
  system_prompt: "You are..."  # prepend vào system prompt
  blocked_tools: ["web_search"]
  preferred_tools: ["mcp"]
```

Skill files đặt tại `services/chatbot/core/skills/builtins/`. Có thể đăng ký thêm skill qua Python API.

---

## Agentic Pipeline (Multi-Thinking)

Kích hoạt bằng thinking mode `multi-thinking`. Dùng cho các câu hỏi phức tạp cần nhiều góc nhìn.

```
Research Council (5 thành viên, 2 phase)
  Phase 1 (song song):
    Logic Architect        → Phân tích logic, kiến trúc, thuật toán
    Research Lead          → Thu thập và đánh giá dữ liệu web
    Creative Strategist    → Góc nhìn sáng tạo, phá vỡ convention
    Optimization Engineer  → Tối ưu hiệu năng, trade-offs
    DevOps / QA Critic     → Bảo mật, edge cases, production readiness
  Phase 2 (top 3 thảo luận nhóm):
    Top 3 trajectories tranh luận, phản biện lẫn nhau
  Synthesis:
    Tổng hợp kết quả tốt nhất từ toàn bộ council
```

Mỗi agent dùng LLMAdapter riêng (model cấu hình độc lập). Dữ liệu chia sẻ qua `Blackboard` (in-memory hoặc Redis). SSE streaming tại `/council/stream` (FastAPI).

**xAI Native Research mode**: endpoint `xai-native/stream` — dùng xAI Live Search để làm giàu context trước khi trả lời.

---

## Search Tools

### Tự động kích hoạt

Web search tự động khi tin nhắn chứa từ khóa thời gian thực: giá vàng, thời tiết, tin tức, tỷ giá, v.v.

### Cascade Reverse Image Search

```
Google Lens → Google Reverse Image → Yandex Images
```

| Tool ID | Mô tả |
|---|---|
| `google-search` | SerpAPI Google Search — fallback sang Google CSE nếu hết quota |
| `serpapi-bing` | SerpAPI Bing Search |
| `serpapi-baidu` | SerpAPI Baidu Search |
| `serpapi-reverse-image` | Google Lens → Reverse Image → Yandex (cascade tự động) |
| `serpapi-images` | SerpAPI Google Images |
| `saucenao` | SauceNAO — tìm nguồn gốc ảnh anime/illustration |

---

## Video Generation (Sora 2)

Yêu cầu `OPENAI_API_KEY`. Người dùng cần **unlock** qua luồng QR payment trước khi dùng.

```
POST /api/video/generate          Gửi job, trả về ngay (async)
POST /api/video/generate-sync     Chờ hoàn thành (blocking)
GET  /api/video/status/{id}       Tiến độ 0-100%
GET  /api/video/download/{id}     Tải file MP4
GET  /api/video/list              Danh sách video đã tạo
```

Pricing: `sora-2` $0.10/s · `sora-2-pro` $0.30/s · Thời lượng: 4, 8, 12 giây · Độ phân giải: 720p / 1080p.

---

## Anime Pipeline

7-stage layered anime image generation chạy qua ComfyUI backend. Yêu cầu ComfyUI đang chạy tại `ANIME_PIPELINE_COMFYUI_URL` (mặc định `http://localhost:8188`). Gated bởi feature flag `IMAGE_PIPELINE_V2`.

```
Prompt → Vision Analysis → Layer Planning → Composition Pass
       → Structure Lock (lineart/depth/canny) → Beauty Pass
       → Critique Loop (Gemini / GPT-4o-mini vision)
       → Upscale → Output Manifest
```

Tất cả stage phát SSE events với prefix `anime_pipeline_*`. Chi tiết kiến trúc: [image_pipeline/anime_pipeline/README.md](image_pipeline/anime_pipeline/README.md).

### Env vars

```env
ANIME_PIPELINE_COMFYUI_URL=http://localhost:8188   # ComfyUI URL
ANIME_PIPELINE_VRAM_PROFILE=normalvram             # lowvram / normalvram / highvram / auto
ANIME_PIPELINE_COMPOSITION_MODEL=animagine-xl-4.0-opt.safetensors
ANIME_PIPELINE_BEAUTY_MODEL=noobai-xl-1.1.safetensors
ANIME_PIPELINE_QUALITY_THRESHOLD=0.70              # 0.0-1.0 (critique pass threshold)
ANIME_PIPELINE_MAX_REFINE_ROUNDS=3
ANIME_PIPELINE_DEBUG=false                         # Lưu workflow JSON + intermediate images
```

Vision critique dùng `GEMINI_API_KEY` (primary) → `OPENAI_API_KEY` (fallback). Không cần package riêng — gọi API qua httpx.

Config đầy đủ: [configs/anime_pipeline_example.yaml](configs/anime_pipeline_example.yaml).

---

## MCP Server

Transport: **stdio** (FastMCP). Không dùng HTTP. Entry point: `services/mcp-server/server.py`.

**10 Advanced Tools** (`tools/advanced_tools.py`):

| Tool | Mô tả |
|---|---|
| `git_status` | Trạng thái git repository |
| `git_log` | Lịch sử commit (N gần nhất) |
| `git_branch_info` | Thông tin branch hiện tại |
| `query_sqlite_database` | Chạy SQL query trên SQLite |
| `list_database_tables` | Schema database |
| `analyze_python_file` | AST analysis: functions, classes, imports |
| `find_todos_in_code` | Tìm TODO/FIXME trong code |
| `fetch_github_repo_info` | GitHub API — repo metadata, contributors, stars |
| `search_stackoverflow` | Tìm kiếm StackOverflow |
| `count_lines_in_project` | LOC theo extension |

---

## API Endpoint Reference

### Chat & Streaming

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/chat/stream` | **Primary** — SSE streaming chat |
| `GET` | `/chat/stream/models` | Danh sách model khả dụng |
| `GET` | `/chat/stream/metrics` | Stream performance metrics |
| `GET` | `/chat/stream/skills` | Skill đang active trong session |
| `POST` | `/chat` | Legacy JSON chat (không stream) |
| `POST` | `/chat/async` | Async SSE chat |
| `POST` | `/chat/async/batch` | Batch async requests |

### Conversations

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/conversations` | Danh sách conversations (tối đa 50) |
| `GET` | `/conversations/<id>` | Chi tiết conversation + messages |
| `DELETE` | `/conversations/<id>` | Xóa conversation |
| `POST` | `/conversations/<id>/archive` | Archive conversation |
| `POST` | `/conversations/new` | Tạo conversation mới |
| `POST` | `/conversations/<id>/switch` | Chuyển sang conversation |
| `POST` | `/clear` | Xóa history session hiện tại |
| `GET` | `/history` | History session hiện tại |
| `POST` | `/api/generate-title` | Tạo tên conversation bằng LLM |

### Skills

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/skills` | Danh sách skills (`?tag=X`) |
| `GET` | `/api/skills/<id>` | Chi tiết một skill |
| `POST` | `/api/skills/activate` | Kích hoạt skill cho session |
| `POST` | `/api/skills/deactivate` | Tắt skill của session |
| `GET` | `/api/skills/active` | Skill đang active |

### Image Generation

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/image-gen/generate` | Tạo ảnh (multi-provider) |
| `POST` | `/api/image-gen/stream` | Stream image generation (SSE) |
| `POST` | `/api/image-gen/edit` | Edit/transform ảnh có sẵn |

### Image Storage & Gallery

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/save-generated-image` | Lưu ảnh + upload cloud/db |
| `POST` | `/api/gallery/upload-db` | Đồng bộ ảnh local lên cloud/db |
| `GET` | `/api/gallery/images` | Danh sách ảnh trong gallery |
| `GET` | `/api/gallery/cloud` | Gallery links từ cloud storage |
| `GET` | `/api/gallery/image-info` | Metadata ảnh |
| `GET` | `/storage/images/<filename>` | Serve ảnh đã lưu |
| `DELETE` | `/api/delete-image/<filename>` | Xóa ảnh |
| `POST` | `/api/upload-imgbb` | Upload ảnh lên ImgBB |

### Video

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/video/generate` | Gửi job video (async) |
| `POST` | `/api/video/generate-sync` | Gửi + chờ hoàn thành |
| `GET` | `/api/video/status/<id>` | Tiến độ 0-100% |
| `GET` | `/api/video/download/<id>` | Tải MP4 |
| `GET` | `/api/video/list` | Danh sách video |

### Memory

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/memory/save` | Lưu memory entry |
| `GET` | `/memory/list` | Danh sách memory |
| `GET` | `/memory/get/<id>` | Chi tiết memory |
| `DELETE` | `/memory/delete/<id>` | Xóa memory |
| `PUT` | `/memory/update/<id>` | Cập nhật memory |
| `GET` | `/memory/search` | Tìm kiếm memory theo keyword |

### MCP Proxy

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/mcp/enable` | Bật MCP integration |
| `POST` | `/api/mcp/disable` | Tắt MCP |
| `POST` | `/api/mcp/add-folder` | Thêm folder vào scope MCP |
| `POST` | `/api/mcp/remove-folder` | Xóa folder khỏi scope |
| `GET` | `/api/mcp/list-files` | Danh sách files trong scope |
| `GET` | `/api/mcp/search-files` | Tìm file theo tên/pattern |
| `GET` | `/api/mcp/read-file` | Đọc nội dung file |
| `GET` | `/api/mcp/grep` | Grep pattern trong files |
| `POST` | `/api/mcp/ocr-extract` | OCR từ file |
| `GET` | `/api/mcp/status` | MCP server health |

### Models

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/models` | Danh sách model khả dụng |
| `GET` | `/api/models/<id>` | Chi tiết model + capabilities |
| `GET` | `/api/models/health` | Provider health status |
| `GET` | `/api/models/contexts` | Context window theo model |
| `POST` | `/api/models/recommend` | Gợi ý model cho task |
| `GET` | `/api/local-models-status` | Trạng thái Ollama/llama.cpp |

### User Auth & Quota

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/login` | Trang đăng nhập |
| `POST` | `/api/auth/login` | Đăng nhập (username/password) |
| `GET` | `/logout` | Đăng xuất |
| `POST` | `/api/auth/register` | Đăng ký tài khoản |
| `GET` | `/api/auth/me` | Thông tin user hiện tại |
| `POST` | `/api/auth/change-password` | Đổi mật khẩu |
| `GET` | `/api/auth/quota` | Quota tin nhắn/ảnh còn lại |
| `POST` | `/api/auth/update-profile` | Cập nhật display name, avatar, bio |
| `GET` | `/api/features` | Feature flags theo user |
| `POST` | `/api/auth/request-video-unlock` | Yêu cầu mở khóa video generation |

### Admin Panel

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/admin` | Admin dashboard (HTML) |
| `GET` | `/api/admin/stats` | Thống kê tổng quan |
| `GET` | `/api/admin/users` | Danh sách user |
| `POST` | `/api/admin/users` | Tạo user mới |
| `POST` | `/api/admin/users/<u>/toggle` | Bật/tắt tài khoản |
| `POST` | `/api/admin/users/<u>/password` | Reset mật khẩu |
| `POST` | `/api/admin/users/<u>/quota/reset` | Reset quota |
| `POST` | `/api/admin/users/<u>/video/unlock` | Cấp quyền video |
| `POST` | `/api/admin/users/<u>/video/lock` | Thu hồi quyền video |
| `GET` | `/api/admin/sessions` | Danh sách active session |
| `GET` | `/api/admin/sessions/<id>` | Chi tiết session + messages |
| `GET` | `/api/admin/images` | Kho ảnh đã tạo |
| `GET` | `/api/admin/memory` | AI memory log |
| `GET` | `/api/admin/logs` | System logs |
| `GET` | `/api/admin/payments` | Yêu cầu thanh toán |
| `POST` | `/api/admin/payments/<id>/approve` | Duyệt mở khóa video |
| `POST` | `/api/admin/payments/<id>/reject` | Từ chối thanh toán |

### Payment (VietQR)

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/payment/info` | Thông tin tài khoản nhận tiền |
| `POST` | `/api/payment/qr` | Tạo QR code VietQR |

### Anime Pipeline

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/anime-pipeline/health` | ComfyUI health + feature flag status |
| `POST` | `/api/anime-pipeline/stream` | **Primary** — 7-stage SSE streaming generation |
| `POST` | `/api/anime-pipeline/generate` | Blocking generation (chờ hoàn thành) |

### Stable Diffusion Proxy

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/sd-health` | SD service health |
| `GET` | `/api/sd-models` | Danh sách SD models |
| `POST` | `/api/sd-change-model` | Đổi SD model |
| `GET` | `/api/sd-presets` | SD generation presets |
| `GET` | `/api/sd-samplers` | Samplers khả dụng |
| `GET` | `/api/sd-loras` | LoRA models |
| `GET` | `/api/sd-vaes` | VAE models |
| `POST` | `/api/generate-image` | Text-to-image qua SD |
| `POST` | `/api/img2img` | Image-to-image qua SD |

### Health & Utilities

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/api/health/databases` | Database connectivity |
| `POST` | `/api/extract-file-text` | OCR/STT từ file upload |

---

## Chạy nhanh

### 1. Clone

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

### 2. Chạy bằng menu (khuyến nghị)

```bash
# Windows
menu.bat

# Linux/Mac
./menu.sh
```

### 3. Chạy Chatbot thủ công

```bash
# Flask mode (mặc định)
cd services/chatbot
python chatbot_main.py

# Flask modular app factory
set USE_NEW_STRUCTURE=true    # Windows
python run.py

# FastAPI + uvicorn
set USE_FASTAPI=true           # Windows
python run.py
```

### 4. Chạy bằng script (Windows)

```bat
app\scripts\start-chatbot.bat
app\scripts\start-stable-diffusion.bat
app\scripts\start-edit-image.bat
app\scripts\start-mcp.bat

rem Khởi động tất cả
app\scripts\start-all.bat
```

### 5. Docker

```bash
# Core services (chatbot + MongoDB)
docker compose up -d

# Với optional tools
docker compose --profile tools up -d    # + last30days
docker compose --profile hermes up -d   # + Hermes agent

curl http://localhost:5000/health
```

Chi tiết: [docs/deployment_last30days_hermes.md](docs/deployment_last30days_hermes.md)

---

## Cấu hình môi trường

```bash
cp app/config/.env.example app/config/.env
```

Cơ chế tải: `services/shared_env.py` → `load_shared_env(__file__)` → tìm `app/config/.env_{env}` rồi fallback `app/config/.env`. Mỗi service gọi **một lần** khi khởi động.

### Biến bắt buộc tối thiểu

```env
# Chọn ít nhất 1 LLM provider
GROK_API_KEY=
OPENAI_API_KEY=      # Bắt buộc cho Sora 2, DALL-E, Whisper STT
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=

# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=chatbot_db

# Shared env profile
env=dev
```

### Biến tùy chọn thường dùng

```env
# LLM providers
QWEN_API_KEY=               # Alibaba Qwen (alias: DASHSCOPE_API_KEY)
OPENROUTER_API_KEY=         # Multi-model proxy
STEPFUN_API_KEY=            # StepFun + image gen
GEMINI_API_KEY_1=           # Gemini key rotation (1-4)
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_API_KEY_4=

# Image generation
FAL_API_KEY=                # fal.ai — FLUX.1, FLUX Pro, Recraft
BFL_API_KEY=                # Black Forest Labs — FLUX Pro raw
REPLICATE_API_KEY=          # Replicate marketplace
TOGETHER_API_KEY=           # Together AI — FLUX Schnell
SD_API_URL=http://127.0.0.1:7861  # Stable Diffusion WebUI

# Web search
SERPAPI_API_KEY=            # SerpAPI — Google, Bing, Baidu, Lens, Images
GOOGLE_SEARCH_API_KEY_1=   # Google CSE fallback key 1
GOOGLE_SEARCH_API_KEY_2=   # Google CSE fallback key 2
GOOGLE_CSE_ID=              # Google Custom Search Engine ID

# Reverse image / anime
SAUCENAO_API_KEY=

# GitHub (dùng cho MCP tools)
GITHUB_TOKEN=

# Image cloud storage
IMGBB_API_KEY=
FIREBASE_RTDB_URL=
FIREBASE_DB_SECRET=

# Google Drive (best-effort, optional)
GOOGLE_DRIVE_ENABLED=false
GOOGLE_DRIVE_SA_JSON_PATH=config/google-drive-sa.json
GOOGLE_DRIVE_FOLDER_ID=

# MongoDB X.509 (Atlas)
MONGODB_X509_ENABLED=false
MONGODB_X509_URI=
MONGODB_X509_CERT_PATH=
```

---

## Cấu trúc thư mục chính

```
services/
  shared_env.py              Bộ tải env dùng chung — gọi 1 lần per service
  chatbot/
    chatbot_main.py          Entry point Flask monolith (14 blueprints)
    run.py                   Dispatcher cho Flask modular + FastAPI
    core/
      config.py              API keys, system prompts, storage paths
      chatbot.py             ChatbotAgent v1 (if/elif routing)
      chatbot_v2.py          ChatbotAgent v2 (ModelRegistry)
      tools.py               Web search, reverse image, SauceNAO
      thinking_generator.py  Thinking modes + ThinkTagParser
      stream_contract.py     SSE payload contract
      agentic/               CouncilOrchestrator (Planner/Researcher/Critic/Synthesizer)
      image_gen/             ImageOrchestrator + 7 providers
      skills/                SkillRegistry, Router, Resolver, Session (11 YAML builtins)
    routes/                  Flask blueprints (~95 endpoints / 15 files)
    fastapi_app/             FastAPI routers (~40 endpoints / 9 files)
    src/
      audio_transcription.py  Whisper STT
      ocr_integration.py      Vision OCR
      video_generation.py     Sora 2 video
      handlers/               Multimodal + advanced image handlers
      utils/                  imgbb, sd_client, mcp_integration, cache, ...
      rag/                    RAG subsystem (ingest, embeddings, retrieval)
    templates/               index.html, admin.html, login.html
    static/js/modules/       15 JS modules (skill-manager, image-gen-v2, video-gen, ...)
    config/                  mongodb_config.py, model_presets.py, features.json
    tests/                   40+ test modules, 275+ tests
  mcp-server/
    server.py                FastMCP stdio server
    tools/advanced_tools.py  10 advanced MCP tools
  stable-diffusion/          SDXL image generation service (port 7861)
  edit-image/                ComfyUI-based image editing service (port 8100)

app/
  config/                    .env, config.yml, model_config.py, rate_limiter.py
  requirements/              profile_core_services.txt, profile_image_ai_services.txt
  scripts/                   start/stop/health-check scripts
  src/                       Shared modules (utils, database, cache, security)

ComfyUI/                     ComfyUI installation (image editing backend)
image_pipeline/
  anime_pipeline/            7-stage anime pipeline (agents, config, schemas, orchestrator)
    agents/                  VisionAnalyst, LayerPlanner, CompositionPass, StructureLock, BeautyPass, Critique, Upscale
    examples/                request_payload.json, output_manifest.json
    README.md                Developer docs
    MIGRATION.md             Migration notes
configs/
  anime_pipeline.yaml        Runtime config (VRAM, model slots, thresholds)
  anime_pipeline_example.yaml  Template config với comments đầy đủ
rag/                         Standalone RAG service (separate stack)
private/                     Dữ liệu nội bộ / submodule
```

---

## Dependency Profiles

| Profile | venv | Requirements |
|---|---|---|
| core-services | `venv-core` | `app/requirements/profile_core_services.txt` |
| image-ai-services | `venv-image` | `app/requirements/profile_image_ai_services.txt` |

Chatbot và MCP dùng `venv-core`. Image generation workflows dùng `venv-image`. Không trộn lẫn.

---

## Kiến trúc tích hợp

```
services/shared_env.py  <-  các service gọi load_shared_env(__file__)
         |
     app/config/
         .env / .env_dev      Biến môi trường
         config.yml           Port/host config
         model_config.py      ServiceConfig dataclasses
         rate_limiter.py      Gemini/OpenAI rate limiting
         response_cache.py    LLM response caching
         public_urls.py       Cloudflare tunnel URL manager
         logging_config.py    Centralized logging setup
```

### Luồng chat (Flask SSE)

```
Browser -> POST /chat/stream
  -> routes/stream.py
    -> resolve_skill()           Skill system (auto-route / session / explicit)
    -> ChatbotAgent / ChatbotV2  Model routing
      -> tools.py                Web search / reverse image (auto-trigger nếu cần)
      -> image_gen/              Image generation (nếu là yêu cầu ảnh)
      -> agentic/orchestrator    Multi-thinking council (nếu mode = multi-thinking)
      -> LLM provider            Grok / OpenAI / Gemini / DeepSeek / ...
    <- SSE events: thinking / token / metadata / complete
```

### Luồng lưu ảnh

```
1. Provider router tạo ảnh
2. Lưu file local trong chatbot storage
3. Upload ImgBB -> public URL
4. Ghi metadata vào MongoDB
5. Ghi vào Firebase RTDB (gallery fallback/index)
6. Upload Google Drive nếu bật (best-effort, lỗi không chặn luồng chính)
```

---

## Chạy Tests

```bash
# Activate venv-core
d:\AI-Assistant\venv-core\Scripts\Activate.ps1   # Windows
source venv-core/bin/activate                     # Linux/Mac

# Run toàn bộ chatbot tests
cd services/chatbot
pytest tests/ -v --tb=short

# Bỏ qua một số test nhất định
pytest tests/ -v --tb=short --ignore=tests/test_agentic_router.py
```

CI: `.github/workflows/tests.yml` — `pytest tests/ -v --tb=short --timeout=60` với `TESTING=True`, `MONGODB_ENABLED=False`.

---

## Optional Tools & Sidecars

Hai công cụ tùy chọn có thể được kích hoạt cùng chatbot:

| Tool | Type | Port | Env flag | Description |
|---|---|---|---|---|
| **last30days** | Subprocess | — | `LAST30DAYS_ENABLED=true` | Multi-source social media research (Reddit, X, YouTube, HN, etc.) |
| **Hermes Agent** | HTTP sidecar | 8080 | `HERMES_ENABLED=true` | Advanced AI agent với tool registry, memory, subagent delegation |

Cả hai đều **tùy chọn** — chatbot hoạt động bình thường khi chúng tắt.

### Docker Compose

```bash
# Chatbot + MongoDB only
docker compose up -d

# + last30days
docker compose --profile tools up -d

# + Hermes
docker compose --profile hermes up -d

# Everything
docker compose --profile all up -d
```

📖 Chi tiết đầy đủ: [docs/deployment_last30days_hermes.md](docs/deployment_last30days_hermes.md)

---

## Tài liệu liên quan

- [docs/deployment_last30days_hermes.md](docs/deployment_last30days_hermes.md) — Deployment guide cho last30days + Hermes
- [services/chatbot/docs/last30days_integration.md](services/chatbot/docs/last30days_integration.md) — last30days tool integration
- [services/chatbot/README.md](services/chatbot/README.md) — Chi tiết chatbot service + skill system
- [app/scripts/README.md](app/scripts/README.md) — Script vận hành
- [app/requirements/README.md](app/requirements/README.md) — Dependency profiles
- [SECURITY.md](SECURITY.md) — Security policy
- [AGENTS.md](AGENTS.md) — Agent conventions cho AI coding assistants

---

## Contributing

1. Tạo nhánh mới từ `master`.
2. Commit theo phạm vi thay đổi (chatbot / image / MCP).
3. Mở Pull Request — CI sẽ chạy tests tự động.

## Author & Collaborator

- [SkastVnT](https://github.com/SkastVnT)
- [Sugimo](https://github.com/sug1omyo)

## License

MIT. Xem chi tiết tại [LICENSE](LICENSE).