# AI-Assistant

Nền tảng microservices Python tích hợp các dịch vụ AI: chatbot đa mô hình LLM, image generation đa provider, video generation, và MCP server.

---

## Dịch vụ đang hoạt động

| Service | Port | Entry Point | Mô tả |
|---|---|---|---|
| **ChatBot** | **5000** | `services/chatbot/run.py` | AI Chat + Voice + OCR + Image Gen + Video + Tools |
| **Stable Diffusion** | **7861** | `services/stable-diffusion/` | Image generation (SDXL backend) |
| **Edit Image** | **8100** | `services/edit-image/` | AI image editing (ComfyUI backend) |
| **MCP Server** | **stdio** | `services/mcp-server/server.py` | Model Context Protocol tools |

> Chatbot hỗ trợ 3 chế độ khởi động: Flask monolith (mặc định), Flask modular (`USE_NEW_STRUCTURE=true`), FastAPI (`USE_FASTAPI=true`).

---

## Tính năng Chatbot

| Tính năng | Mô tả |
|---|---|
| **Đa mô hình LLM** | Grok, OpenAI, DeepSeek, Gemini, Qwen, OpenRouter, Ollama local |
| **Thinking Modes** | Instant / Think / Deep-Think / Multi-Thinking (4-agent council) |
| **Skill System** | 12 built-in personas tự động route theo nội dung tin nhắn |
| **Image Generation** | 7 provider: fal.ai, Black Forest Labs, Replicate, StepFun, OpenAI DALL-E, Together AI, ComfyUI |
| **Video AI** | OpenAI Sora 2 — text-to-video (yêu cầu unlock) |
| **Web Search** | SerpAPI (Google, Bing, Baidu) + Google CSE fallback, tự động kích hoạt |
| **Reverse Image** | Google Lens → Google Reverse Image → Yandex (cascade) |
| **SauceNAO** | Tìm nguồn gốc ảnh |
| **Voice (STT)** | Whisper API — transcribe audio |
| **OCR** | Vision APIs — đọc ảnh và PDF |
| **RAG** | MongoDB Atlas — memory theo ngữ nghĩa |
| **MCP Integration** | Truy cập file/folder local qua MCP server (stdio) |
| **User Auth** | Đăng ký / đăng nhập, quota, video unlock qua admin |
| **SSE Streaming** | Server-Sent Events — streaming token thời gian thực |
| **URL Routing** | `/c/<conversation_id>` per-conversation URL (ChatGPT-style) |

---

## Thinking Modes

| Mode | Mô tả |
|---|---|
| `instant` | Trả lời ngay, không reasoning — nhanh nhất |
| `think` | Chuỗi suy nghĩ nội tại trước khi trả lời |
| `deep-think` | Extended reasoning — phân tích sâu |
| `multi-thinking` | 4-agent council: Planner → Researcher → Critic → Synthesizer |

---

## LLM Providers

| Provider | Env Key | Ghi chú |
|---|---|---|
| xAI Grok | `GROK_API_KEY` | Grok-2, Grok-3 |
| OpenAI | `OPENAI_API_KEY` | GPT-4o, o1; bắt buộc cho Sora 2 + DALL-E + Whisper |
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek-V3, R1 |
| Google Gemini | `GEMINI_API_KEY_1..4` | Pool 4 key, tự động rotation |
| Alibaba Qwen | `QWEN_API_KEY` | Qwen-2.5, Qwen-VL |
| OpenRouter | `OPENROUTER_API_KEY` | Multi-model proxy |
| Local (Ollama) | — | Qwen, Llama qua Ollama / llama.cpp |

---

## Image Generation Providers

| Provider | Env Key | Ưu tiên | Đặc điểm |
|---|---|---|---|
| **fal.ai** | `FAL_API_KEY` | 90 | FLUX.1, FLUX Pro, Recraft, Ideogram |
| **Black Forest Labs** | `BFL_API_KEY` | 85 | FLUX Pro raw |
| **Replicate** | `REPLICATE_API_KEY` | 80 | Marketplace nhiều model |
| **StepFun** | `STEPFUN_API_KEY` | 75 | Step-1X Flash |
| **OpenAI DALL-E** | `OPENAI_API_KEY` | 70 | DALL-E 3 |
| **Together AI** | `TOGETHER_API_KEY` | 60 | FLUX Schnell, distributed inference |
| **ComfyUI** | `SD_API_URL` | 10 | Local GPU, miễn phí, cần cài ComfyUI |

Tự động dùng provider nào có API key. Fallback chain: nếu provider lỗi, thử provider tiếp theo theo thứ tự ưu tiên.

---

## Skill System

Runtime Skill System cho phép chatbot tự động chọn persona phù hợp với yêu cầu, hoặc người dùng kích hoạt thủ công qua UI.

### Luồng xử lý

```
resolve_skill()    Ưu tiên: explicit > session > auto-route > none
  explicit         Request body có trường "skill": "coding-assistant"
  session          Người dùng đã kích hoạt skill qua /api/skills/activate
  auto-route       SkillRouter chấm điểm từ khoá trong tin nhắn (ngưỡng 1.05)
        ↓
apply_skill_overrides()   Merge cấu hình skill vào request
  → model, thinking_mode, system_prompt, tools, context_window
```

### 12 Skill Built-in

| Skill ID | Trigger tự động | Mô tả |
|---|---|---|
| `realtime-search` | today, news, price, weather | Tìm kiếm web, sự kiện hiện tại |
| `code-expert` | architecture, design pattern, algorithm | Review code, kiến trúc hệ thống |
| `coding-assistant` | code, debug, function, bug, refactor | Hỗ trợ code từng bước |
| `research-analyst` | analyze, compare, evaluate, report | Nghiên cứu chuyên sâu |
| `repo-analyzer` | repository, codebase, project structure | Phân tích repository |
| `research-web` | search, find, look up, research | Nghiên cứu web |
| `social-research` | reddit, twitter, x, youtube, hackernews | Tổng hợp dữ liệu social media (qua last30days nếu bật) |
| `prompt-engineer` | prompt, system prompt, instruction | Tối ưu prompt |
| `mcp-file-helper` | file, folder, read file, MCP | Thao tác file qua MCP |
| `creative-writer` | write, story, poem, creative, essay | Sáng tạo, viết lách |
| `shopping-advisor` | buy, price, recommend, product | Tư vấn mua sắm |
| `counselor` | stress, anxiety, feeling, advice | Tư vấn tâm lý, hỗ trợ cảm xúc |

### SSE Metadata

`POST /chat/stream` phát event `metadata` kèm thông tin skill đang dùng:

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
4-agent council (Planner → Researcher → Critic → Synthesizer)
  Planner      → Phân tích câu hỏi, chia nhỏ thành task list
  Researcher   → Thu thập bằng chứng (web search, RAG, MCP)
  Critic       → Đánh giá kết quả, quyết định cần làm thêm hay không
  Synthesizer  → Tổng hợp câu trả lời cuối cùng
```

Mỗi agent dùng LLMAdapter riêng. Dữ liệu chia sẻ qua `Blackboard`. SSE streaming tại `/council/stream` (FastAPI).

**xAI Native Research mode**: endpoint `xai-native/stream` — dùng xAI Live Search để làm giàu context trước khi trả lời.

---

## Search Tools

### Tự động kích hoạt

Web search tự động khi tin nhắn chứa từ khoá thời gian thực: giá vàng, thời tiết, tin tức, tỷ giá, v.v.

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
| `saucenao` | SauceNAO — tìm nguồn gốc ảnh |

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

## URL Routing & Conversation State (ChatGPT-style)

Mỗi cuộc trò chuyện có URL riêng:

| Hành động | URL |
|---|---|
| Mở `localhost:5000` lần đầu | Tự đổi thành `/c/chat_<id>` (replaceState) |
| Click chat khác trong sidebar | URL đổi sang `/c/<id chat đó>` (pushState) |
| Bấm Back / Forward browser | Quay lại / tiến tới chat trước (popstate) |
| Bấm "+ New chat" | URL đổi sang `/c/chat_<timestamp mới>` |
| Paste link `/c/<id>` | Khôi phục đúng cuộc trò chuyện đó |

Backend route: `GET /c/<conversation_id>` (chatbot_main.py) — validate ID khớp regex `[A-Za-z0-9_\-]{1,64}`, trả về cùng `index.html`. Frontend khôi phục state từ `localStorage.chatSessions[id]`.

Stream payload (`POST /chat/stream`) gửi kèm `conversation_id` và 3 ảnh gen gần nhất (`generated_images[]`) để LLM có context về ảnh đã tạo trong cuộc trò chuyện.

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

### Trang HTML

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/` | Trang chủ chat |
| `GET` | `/c/<conversation_id>` | Trang chat với cuộc trò chuyện cụ thể |
| `GET` | `/new` | Tạo session mới rồi redirect về `/` |
| `GET` | `/mobile` | Layout di động |
| `GET` | `/desktop` | Layout máy tính |
| `GET` | `/login` | Trang đăng nhập |
| `GET` | `/admin` | Admin dashboard |

### Conversations

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/conversations` | Danh sách conversations (tối đa 50) |
| `GET` | `/conversations/<id>` | Chi tiết conversation + messages |
| `DELETE` | `/conversations/<id>` | Xoá conversation |
| `POST` | `/conversations/<id>/archive` | Archive conversation |
| `POST` | `/conversations/new` | Tạo conversation mới |
| `POST` | `/conversations/<id>/switch` | Chuyển sang conversation |
| `POST` | `/clear` | Xoá history session hiện tại |
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
| `POST` | `/api/image-gen/edit` | Edit / transform ảnh có sẵn |

### Image Storage & Gallery

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/save-generated-image` | Lưu ảnh + upload cloud / DB |
| `POST` | `/api/gallery/upload-db` | Đồng bộ ảnh local lên cloud / DB |
| `GET` | `/api/gallery/images` | Danh sách ảnh trong gallery |
| `GET` | `/api/gallery/cloud` | Gallery links từ cloud storage |
| `GET` | `/api/gallery/image-info` | Metadata ảnh |
| `GET` | `/storage/images/<filename>` | Serve ảnh đã lưu |
| `DELETE` | `/api/delete-image/<filename>` | Xoá ảnh |
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
| `DELETE` | `/memory/delete/<id>` | Xoá memory |
| `PUT` | `/memory/update/<id>` | Cập nhật memory |
| `GET` | `/memory/search` | Tìm kiếm memory theo keyword |

### MCP Proxy

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/mcp/enable` | Bật MCP integration |
| `POST` | `/api/mcp/disable` | Tắt MCP |
| `POST` | `/api/mcp/add-folder` | Thêm folder vào scope MCP |
| `POST` | `/api/mcp/remove-folder` | Xoá folder khỏi scope |
| `GET` | `/api/mcp/list-files` | Danh sách files trong scope |
| `GET` | `/api/mcp/search-files` | Tìm file theo tên / pattern |
| `GET` | `/api/mcp/read-file` | Đọc nội dung file |
| `GET` | `/api/mcp/grep` | Grep pattern trong files |
| `POST` | `/api/mcp/ocr-extract` | OCR từ file |
| `POST` | `/api/mcp/warm-cache` | Warm cache cho MCP scope |
| `GET` | `/api/mcp/status` | MCP server health |

### Models

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/models` | Danh sách model khả dụng |
| `GET` | `/api/models/<id>` | Chi tiết model + capabilities |
| `GET` | `/api/models/health` | Provider health status |
| `GET` | `/api/models/contexts` | Context window theo model |
| `POST` | `/api/models/recommend` | Gợi ý model cho task |
| `GET` | `/api/local-models-status` | Trạng thái Ollama / llama.cpp |

### User Auth & Quota

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/login` | Trang đăng nhập |
| `POST` | `/api/auth/login` | Đăng nhập (username / password) |
| `GET` | `/logout` | Đăng xuất |
| `POST` | `/api/auth/register` | Đăng ký tài khoản |
| `GET` | `/api/auth/me` | Thông tin user hiện tại |
| `POST` | `/api/auth/change-password` | Đổi mật khẩu |
| `GET` | `/api/auth/quota` | Quota tin nhắn / ảnh còn lại |
| `POST` | `/api/auth/update-profile` | Cập nhật display name, avatar, bio |
| `GET` | `/api/features` | Feature flags theo user |
| `POST` | `/api/auth/request-video-unlock` | Yêu cầu mở khoá video generation |

### Admin Panel

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/admin` | Admin dashboard (HTML) |
| `GET` | `/api/admin/stats` | Thống kê tổng quan |
| `GET` | `/api/admin/users` | Danh sách user |
| `POST` | `/api/admin/users` | Tạo user mới |
| `POST` | `/api/admin/users/<u>/toggle` | Bật / tắt tài khoản |
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
| `POST` | `/api/admin/payments/<id>/approve` | Duyệt mở khoá video |
| `POST` | `/api/admin/payments/<id>/reject` | Từ chối thanh toán |

### Payment (VietQR)

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/payment/info` | Thông tin tài khoản nhận tiền |
| `POST` | `/api/payment/qr` | Tạo QR code VietQR |

### Stable Diffusion Proxy

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/api/sd-health` | SD service health |
| `GET` | `/api/sd-models` | Danh sách SD models |
| `POST` | `/api/sd-change-model` | Đổi SD model |
| `GET` | `/api/sd-presets` | SD generation presets |
| `GET` | `/api/sd-samplers` | Samplers khả dụng |
| `GET` | `/api/sd-vaes` | VAE models |
| `POST` | `/api/generate-image` | Text-to-image qua SD |
| `POST` | `/api/img2img` | Image-to-image qua SD |

### Health & Utilities

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/api/health/databases` | Database connectivity |
| `POST` | `/api/extract-file-text` | OCR / STT từ file upload |

---

## Chạy nhanh

### 1. Clone

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

### 2. Chạy Chatbot thủ công

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

### 3. Chạy bằng script (Windows)

```bat
app\scripts\start-chatbot.bat
app\scripts\start-stable-diffusion.bat
app\scripts\start-edit-image.bat
app\scripts\start-mcp.bat

rem Khởi động tất cả
app\scripts\start-all.bat
```

### 4. Docker

```bash
# Core services (chatbot + MongoDB)
docker compose up -d

# Với optional sidecars
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

### Biến tuỳ chọn thường dùng

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
GOOGLE_SEARCH_API_KEY_1=    # Google CSE fallback key 1
GOOGLE_SEARCH_API_KEY_2=    # Google CSE fallback key 2
GOOGLE_CSE_ID=              # Google Custom Search Engine ID

# Reverse image
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

# Optional sidecars
LAST30DAYS_ENABLED=false
HERMES_ENABLED=false
```

---

## Cấu trúc thư mục chính

```
services/
  shared_env.py              Bộ tải env dùng chung — gọi 1 lần per service
  chatbot/
    chatbot_main.py          Entry point Flask monolith (15 blueprints)
    run.py                   Dispatcher cho Flask modular + FastAPI
    core/
      config.py              API keys, system prompts, storage paths
      chatbot.py             ChatbotAgent v1 (if/elif routing)
      chatbot_v2.py          ChatbotAgent v2 (ModelRegistry)
      tools.py               Web search, reverse image, SauceNAO
      thinking_generator.py  Thinking modes + ThinkTagParser
      stream_contract.py     SSE payload contract
      agentic/               CouncilOrchestrator (5-member research council)
      image_gen/             ImageOrchestrator + 7 providers
      skills/                SkillRegistry, Router, Resolver, Session (12 YAML builtins)
    routes/                  Flask blueprints (15 files)
    fastapi_app/             FastAPI routers (parallel implementation)
    src/
      audio_transcription.py  Whisper STT
      ocr_integration.py      Vision OCR
      video_generation.py     Sora 2 video
      handlers/               Multimodal + advanced image handlers
      utils/                  imgbb, sd_client, mcp_integration, cache, ...
      rag/                    RAG subsystem (ingest, embeddings, retrieval)
    templates/               index.html, admin.html, login.html
    static/js/modules/       Vanilla JS modules (chat-manager, api-service, image-gen-v2, ...)
    config/                  mongodb_config.py, model_presets.py, features.json
    tests/                   40+ test modules
  mcp-server/
    server.py                FastMCP stdio server
    tools/advanced_tools.py  10 advanced MCP tools
  stable-diffusion/          SDXL image generation service (port 7861)
  edit-image/                ComfyUI-based image editing service (port 8100)

app/
  config/                    .env, config.yml, model_config.py, rate_limiter.py
  requirements/              profile_core_services.txt, profile_image_ai_services.txt
  scripts/                   start / stop / health-check scripts
  src/                       Shared modules (utils, database, cache, security)

private/                     Dữ liệu nội bộ / submodule
```

---

## Dependency Profiles

| Profile | venv | Requirements |
|---|---|---|
| core-services | `venv-core` | `app/requirements/profile_core_services.txt` |
| image-ai-services | `venv-image` | `app/requirements/profile_image_ai_services.txt` |

Chatbot và MCP dùng `venv-core`. Image generation backends (Stable Diffusion, ComfyUI) dùng `venv-image`. Không trộn lẫn.

---

## Kiến trúc tích hợp

```
services/shared_env.py  <-  các service gọi load_shared_env(__file__)
         |
     app/config/
         .env / .env_dev      Biến môi trường
         config.yml           Port / host config
         model_config.py      ServiceConfig dataclasses
         rate_limiter.py      Gemini / OpenAI rate limiting
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
5. Ghi vào Firebase RTDB (gallery fallback / index)
6. Upload Google Drive nếu bật (best-effort, lỗi không chặn luồng chính)
```

### Luồng URL routing (frontend)

```
Page load        URL /c/<id>?  -> restore session từ localStorage
                 Else          -> chọn lastActiveChatId hoặc most-recent
                 -> _syncUrl(replace=true) cập nhật URL không reload
newChat()        -> _syncUrl(push) -> URL đổi sang /c/<new_id>
switchChat(id)   -> _syncUrl(push) -> URL đổi sang /c/<id>
deleteChat(id)   -> nếu còn chat: _syncUrl(replace) ; nếu hết: replaceState '/'
popstate event   -> đọc URL, switch session tương ứng (Back/Forward browser)
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

## Optional Sidecars

Các công cụ tuỳ chọn có thể được kích hoạt cùng chatbot:

| Tool | Type | Port | Env flag | Description |
|---|---|---|---|---|
| **last30days** | Subprocess | — | `LAST30DAYS_ENABLED=true` | Multi-source social media research (Reddit, X, YouTube, HackerNews, etc.) |
| **Hermes Agent** | HTTP sidecar | 8080 | `HERMES_ENABLED=true` | Advanced AI agent với tool registry, memory, subagent delegation |
| **Character Select** | Standalone web app | 51028 | — | Character picker UI — chọn/quản lý character cho image gen workflow. Source: [mirabarukaso/character_select_stand_alone_app](https://github.com/mirabarukaso/character_select_stand_alone_app), local copy tại `character_select_stand_alone_app-main/` |

Tất cả đều **tuỳ chọn** — chatbot hoạt động bình thường khi chúng tắt.

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
