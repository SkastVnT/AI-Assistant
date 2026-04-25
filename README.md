# AI-Assistant

Nền tảng microservices Python tích hợp các dịch vụ AI: chatbot đa mô hình LLM, image generation đa provider, video generation (Sora 2), và MCP server.

---

## Dịch vụ

| Service | Port | Entry Point | venv |
|---|---|---|---|
| **ChatBot** | **5000** | `services/chatbot/run.py` | `venv-core` |
| **MCP Server** | **stdio** (FastMCP) | `services/mcp-server/server.py` | `venv-core` |
| **Stable Diffusion** | **7861** | `services/stable-diffusion/` | `venv-image` |
| **Edit Image (ComfyUI)** | **8100** | `services/edit-image/` | `venv-image` |

> Image services (`Stable Diffusion`, `Edit Image`) tự động khởi động cùng chatbot khi `AUTO_START_IMAGE_SERVICES=true` (mặc định bật trong `run.py`).

---

## Chatbot Startup Modes

`services/chatbot/run.py` là dispatcher cho 3 mode:

| Env Flag | Mode | Engine |
|---|---|---|
| `USE_FASTAPI=true` | **FastAPI** (khuyến nghị) | uvicorn + ASGI |
| `USE_NEW_STRUCTURE=true` | Flask modular | App factory pattern |
| *(không set)* | Flask monolith | `chatbot_main.py` (legacy) |

Tất cả đều listen trên port `FLASK_PORT` (default `5000`).

---

## Tính năng Chatbot

| Tính năng | Mô tả |
|---|---|
| Đa LLM provider | OpenAI, Grok (xAI), DeepSeek, Qwen, OpenRouter, StepFun, BloomVN (HF), Gemini, Ollama local |
| Thinking modes | UI: `Instant` / `4-Agents` (default) |
| Multi-thinking council | 4-agent: Planner → Researcher → Critic → Synthesizer |
| Skill system | 12 built-in personas, auto-route theo nội dung tin nhắn |
| Image generation | 7 provider router với fallback chain |
| Video AI | OpenAI Sora 2 (yêu cầu unlock qua admin) |
| Web search | SerpAPI (Google/Bing/Baidu) → Google CSE fallback, auto-trigger theo từ khoá |
| Reverse image | Google Lens → Google Reverse → Yandex (cascade) |
| OCR | Vision APIs cho ảnh / PDF |
| STT | Whisper API (audio → text) |
| RAG | MongoDB Atlas + embeddings cho semantic memory |
| MCP integration | Truy cập file/folder local qua MCP stdio |
| User auth + quota | Đăng ký / đăng nhập, quota tin nhắn / ảnh, video unlock |
| Admin panel | Quản lý user, session, ảnh, memory, logs, payments |
| QR Payment | VietQR — mở khoá video generation |
| SSE streaming | Real-time token streaming cho cả Flask và FastAPI |
| URL routing | `/c/<conversation_id>` per-conversation URL (ChatGPT-style) |
| Conversation CRUD | Tạo / xoá / archive / switch / generate title |

---

## Thinking Modes

UI chỉ expose **2 mode**:

| Mode | UI Label | Default | Mô tả |
|---|---|---|---|
| `instant` | Instant | | Trả lời trực tiếp một agent, không reasoning pipeline |
| `multi-thinking` | **4-Agents** | ✓ | Kích hoạt 4-agent council (Planner → Researcher → Critic → Synthesizer) |

Khi user ở `instant` mà muốn nghiêm túc hơn: nhấn nút **“Think Harder”** trong response actions → gửi lại tin nhắn cuối với `multi-thinking`.

> Backend (`core/skills/applicator.py`, `routes/stream.py`, các test) vẫn nhận các giá trị `thinking` / `deep` / `auto` cho mục đích nội bộ (skill overrides, tương thích ngược). Người dùng cuối chỉ chọn 2 mode trên.

---

## 4-Agent Council (`multi-thinking` mode)

```
Planner      → Phân tích câu hỏi, chia thành task list
   ↓
Researcher   → Thu thập bằng chứng (web search, RAG, MCP)
   ↓
Critic       → Đánh giá, quyết định cần thêm round không
   ↓
Synthesizer  → Tổng hợp câu trả lời cuối
```

Source: `services/chatbot/core/agentic/agents/{planner,researcher,critic,synthesizer}.py` + `orchestrator.py`. Dữ liệu chia sẻ qua `Blackboard`. SSE streaming tại `/council/stream` (FastAPI).

**xAI Native Research**: endpoint `/xai-native/stream` dùng xAI Live Search.

---

## LLM Providers

| Provider | Env Key | Model mặc định | Streaming | Vision |
|---|---|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | ✓ | ✓ |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` | ✓ | ✗ |
| Grok (xAI) | `GROK_API_KEY` | `grok-3` | ✓ | ✗ |
| Qwen | `QWEN_API_KEY` | `qwen-turbo` | ✓ | ✗ |
| Gemini | `GEMINI_API_KEY_1..4` | `gemini-2.0-flash` | ✓ | ✓ |
| OpenRouter | `OPENROUTER_API_KEY` | `stepfun/step-3.5-flash:free` | ✓ | ✗ |
| StepFun | `STEPFUN_API_KEY` | `step-2-16k` | ✓ | ✗ |
| BloomVN (HF) | `HUGGINGFACE_API_KEY` | `BlossomsAI/BloomVN-8B-chat` | ✗ | ✗ |
| Ollama local | — | (model do user chọn) | ✓ | (tuỳ model) |

> **Lưu ý**: Gemini có thể bị disable trong `chatbot_main.py` nếu quota cạn. Fallback chains được wire trong `core/chatbot_v2.py` ModelRegistry.

---

## Image Generation

7 provider router tại `services/chatbot/core/image_gen/providers/`:

| Provider | File | Models tiêu biểu |
|---|---|---|
| **fal.ai** | `fal_provider.py` | FLUX.2, FLUX.1, nano-banana, seedream5 |
| Black Forest Labs | `bfl_provider.py` | FLUX Pro |
| Replicate | `replicate_provider.py` | Marketplace |
| OpenAI | `openai_provider.py` | DALL-E 3 |
| StepFun | `stepfun_provider.py` | Step image models |
| Together AI | `together_provider.py` | Open-source models |
| ComfyUI | `comfyui_provider.py` | Local workflow engine |

Provider được chọn theo API key có sẵn + priority chain. Fallback tự động khi provider lỗi.

---

## Skill System

12 built-in YAML skills tại `services/chatbot/core/skills/builtins/`:

| Skill ID | Trigger tự động |
|---|---|
| `code-expert` | code, bug, lỗi code, lập trình, docker, CI/CD |
| `coding-assistant` | code, debug, function, refactor |
| `realtime-search` | today, news, price, weather |
| `research-analyst` | analyze, compare, evaluate |
| `repo-analyzer` | repository, codebase, project structure |
| `research-web` | search, find, look up, research |
| `social-research` | reddit, twitter, x, youtube, hackernews |
| `prompt-engineer` | prompt, system prompt, instruction |
| `mcp-file-helper` | file, folder, read file, MCP |
| `creative-writer` | write, story, poem, essay |
| `shopping-advisor` | buy, price, recommend, product |
| `counselor` | stress, anxiety, advice |

### Resolve order

```
explicit skill   (request.skill = "...")
  → session skill   (POST /api/skills/activate)
    → auto-route    (SkillRouter scoring, threshold 1.05)
      → none
```

Skill overrides: `model`, `thinking_mode`, `system_prompt`, `tools`, `context_window`.

---

## MCP Server

Transport: **stdio** (FastMCP). Không có HTTP listener.

Entry: `services/mcp-server/server.py`. Tools (`@mcp.tool()`):

| Tool | Mô tả |
|---|---|
| `search_files` | Tìm file theo query / file_type / max_results |
| `read_file_content` | Đọc nội dung file (giới hạn max_lines) |
| `list_directory` | List directory contents |
| `get_project_info` | Project metadata tổng quan |
| `search_logs` | Tìm trong service logs |
| `calculate` | Safe math expression evaluation |

Plus `@mcp.resource()` (config, docs) và `@mcp.prompt()` (code review, debug, explain templates).

Chatbot proxy qua `routes/mcp.py` (Flask) hoặc `fastapi_app/routers/mcp.py` (FastAPI).

---

## API Endpoints (chính)

### Chat & Streaming
| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/chat/stream` | **Primary** — SSE streaming chat |
| `POST` | `/chat/async` | Async SSE |
| `POST` | `/council/stream` | Multi-thinking council SSE (FastAPI) |
| `POST` | `/xai-native/stream` | xAI Live Search streaming (FastAPI) |
| `GET` | `/c/<conversation_id>` | Trang chat với conversation cụ thể |

### Conversations
| Method | Path |
|---|---|
| `GET` / `DELETE` | `/conversations[/<id>]` |
| `POST` | `/conversations/new`, `/conversations/<id>/switch`, `/conversations/<id>/archive` |
| `POST` | `/clear`, `/api/generate-title` |

### Skills
| Method | Path |
|---|---|
| `GET` | `/api/skills`, `/api/skills/<id>`, `/api/skills/active` |
| `POST` | `/api/skills/activate`, `/api/skills/deactivate` |

### Image Generation
| Method | Path |
|---|---|
| `POST` | `/api/image-gen/generate`, `/api/image-gen/stream`, `/api/image-gen/edit` |

### Reasoning Image Pipeline (opt-in, `REASONING_PIPELINE=true`)
| Method | Path |
|---|---|
| `GET`  | `/api/reasoning-image-gen/status` |
| `POST` | `/api/reasoning-image-gen/generate` |

Local nano-banana-style multi-panel pipeline backed by ComfyUI. Disabled
by default; the route is not registered when the flag is unset, so the
URL map is byte-identical to the legacy runtime.

When the flag is on, the existing `POST /api/image-gen/generate` endpoint
also accepts `use_reasoning_pipeline: true` in its JSON payload — that
opt-in toggle short-circuits the regular provider router and returns the
assembled comic via the standard image-gen response shape (`provider:
"reasoning"`, `model: "comic-pipeline"`). The toggle is exposed in the
chat UI's Image Gen v2 modal as **🧠 Use Reasoning Pipeline**.

### Video (Sora 2)
| Method | Path |
|---|---|
| `POST` | `/api/video/generate`, `/api/video/generate-sync` |
| `GET` | `/api/video/status/<id>`, `/api/video/download/<id>`, `/api/video/list` |

### Memory
| Method | Path |
|---|---|
| `POST/GET/PUT/DELETE` | `/memory/{save,list,get/<id>,update/<id>,delete/<id>,search}` |

### MCP Proxy
| Method | Path |
|---|---|
| `POST` | `/api/mcp/{enable,disable,add-folder,remove-folder,ocr-extract,warm-cache}` |
| `GET` | `/api/mcp/{list-files,search-files,read-file,grep,status}` |

### Auth & Quota
| Method | Path |
|---|---|
| `POST` | `/api/auth/{login,register,change-password,update-profile,request-video-unlock}` |
| `GET` | `/api/auth/{me,quota}`, `/api/features` |

### Admin
| Method | Path |
|---|---|
| `GET` | `/admin`, `/api/admin/{stats,users,sessions,images,memory,logs,payments}` |
| `POST` | `/api/admin/users/<u>/{toggle,password,quota/reset,video/unlock,video/lock}` |
| `POST` | `/api/admin/payments/<id>/{approve,reject}` |

### Stable Diffusion Proxy
| Method | Path |
|---|---|
| `GET` | `/api/sd-{health,models,presets,samplers,vaes}` |
| `POST` | `/api/sd-change-model`, `/api/generate-image`, `/api/img2img` |

### Health
| Method | Path |
|---|---|
| `GET` | `/health`, `/api/health/databases` |

> Flask blueprints (19 tổng) tại `services/chatbot/routes/`. FastAPI routers tại `services/chatbot/fastapi_app/routers/` — **parallel implementations**, không merge.

---

## URL Routing (ChatGPT-style)

```
GET /                       → Homepage, redirect/replace sang /c/<id>
GET /c/<conversation_id>    → Chat page với conversation cụ thể (validate regex [A-Za-z0-9_\-]{1,64})
GET /new                    → Tạo session mới rồi redirect /
```

Frontend (`static/js/modules/chat-manager.js`):
- `_syncUrl(id, replace=false)` → `history.pushState/replaceState`
- `popstate` listener → switch session khi user Back/Forward
- URL-first restore on page load → đọc `/c/<id>` → restore từ `localStorage.chatSessions[id]`

Stream payload include `conversation_id` + 3 ảnh gen gần nhất (`generated_images[]`) để LLM có context về ảnh đã tạo.

---

## Cài đặt & Chạy

### 1. Clone

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

### 2. Setup venv

```bash
# Core services (chatbot + MCP)
python -m venv venv-core
venv-core\Scripts\activate          # Windows
source venv-core/bin/activate        # Linux/Mac
pip install -r app/requirements/profile_core_services.txt

# Image services (SD + ComfyUI) — chỉ cần nếu chạy local image gen
python -m venv venv-image
pip install -r app/requirements/profile_image_ai_services.txt
```

### 3. Cấu hình env

```bash
cp app/config/.env.example app/config/.env
# Sửa app/config/.env, set ít nhất 1 LLM API key
```

Loader: `services/shared_env.py` → `load_shared_env(__file__)` → tìm `app/config/.env_{env}` rồi fallback `app/config/.env`. Mỗi service gọi **một lần** khi khởi động.

### 4. Chạy chatbot

```powershell
# FastAPI mode (khuyến nghị)
$env:USE_FASTAPI="true"
cd services\chatbot
python run.py

# Flask modular
$env:USE_NEW_STRUCTURE="true"
python run.py

# Flask monolith (mặc định)
python run.py
# hoặc trực tiếp:
python chatbot_main.py
```

### 5. Scripts (Windows / Linux)

`app/scripts/` chứa các script khởi động:

```bat
app\scripts\start-chatbot.bat
app\scripts\start-stable-diffusion.bat
app\scripts\start-edit-image.bat
app\scripts\start-mcp.bat
app\scripts\start-all.bat
app\scripts\stop-all.bat
app\scripts\health-check-all.bat
```

### 6. Docker

```bash
# Core (MongoDB + ChatBot)
docker compose up -d

# + last30days sidecar
docker compose --profile tools up -d

# + Hermes sidecar
docker compose --profile hermes up -d

# + Character Select picker
docker compose --profile character-select up -d

# Tất cả
docker compose --profile all up -d

curl http://localhost:5000/health
```

> Image services (Stable Diffusion, ComfyUI) **không có trong docker-compose** — chạy local vì cần GPU.

---

## Biến môi trường

```env
# ── LLM (chọn ít nhất 1) ──
OPENAI_API_KEY=
GROK_API_KEY=
DEEPSEEK_API_KEY=
QWEN_API_KEY=
GEMINI_API_KEY_1=
OPENROUTER_API_KEY=
STEPFUN_API_KEY=
HUGGINGFACE_API_KEY=

# ── Database ──
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=chatbot_db

# ── Image generation ──
FAL_API_KEY=
BFL_API_KEY=
REPLICATE_API_KEY=
TOGETHER_API_KEY=
SD_API_URL=http://127.0.0.1:7861

# ── Web search ──
SERPAPI_API_KEY=
GOOGLE_SEARCH_API_KEY_1=
GOOGLE_SEARCH_API_KEY_2=
GOOGLE_CSE_ID=

# ── Reverse image ──
SAUCENAO_API_KEY=

# ── Image cloud storage ──
IMGBB_API_KEY=
FIREBASE_RTDB_URL=
FIREBASE_DB_SECRET=

# ── Optional sidecars ──
LAST30DAYS_ENABLED=false
LAST30DAYS_SCRIPT_PATH=
HERMES_ENABLED=false
HERMES_API_URL=http://localhost:8080
HERMES_API_KEY=
CHARACTER_SELECT_ENABLED=false
CHARACTER_SELECT_URL=http://localhost:51028
CHARACTER_SELECT_PORT=51028
CHARACTER_SELECT_AUTO_START=false

# ── Runtime flags ──
USE_FASTAPI=true                     # Khuyến nghị
USE_NEW_STRUCTURE=false
AUTO_START_IMAGE_SERVICES=true       # Auto-launch SD + Edit Image
FLASK_PORT=5000
env=dev                              # Chọn .env_dev / .env_prod
```

---

## Cấu trúc thư mục

```
services/
  shared_env.py              Bộ tải env dùng chung
  chatbot/
    chatbot_main.py          Flask monolith entry (legacy)
    run.py                   Dispatcher cho 3 startup modes
    core/
      config.py              API keys, system prompts
      chatbot_v2.py          ModelRegistry-based agent
      tools.py               Web search, reverse image, SauceNAO
      thinking_generator.py  Thinking modes
      stream_contract.py     SSE payload contract
      agentic/               4-agent council
        agents/{planner,researcher,critic,synthesizer}.py
        orchestrator.py
        blackboard.py
      image_gen/             7 providers + orchestrator
      skills/                Registry, Router, Resolver, Session
        builtins/            12 YAML skill definitions
    routes/                  19 Flask blueprints
    fastapi_app/             FastAPI routers (parallel implementation)
      routers/               18 router files
    src/
      audio_transcription.py Whisper STT
      ocr_integration.py     Vision OCR
      video_generation.py    Sora 2
      handlers/, utils/, rag/
    templates/               index.html, admin.html, login.html
    static/js/modules/       Vanilla JS (chat-manager, api-service, ...)
    config/                  mongodb_config.py, model_presets.py
    tests/                   40+ test modules
  mcp-server/
    server.py                FastMCP stdio server
  stable-diffusion/          SDXL service (port 7861)
  edit-image/                ComfyUI-based service (port 8100)

app/
  config/                    .env, config.yml, model_config.py
  requirements/              profile_core_services.txt, profile_image_ai_services.txt
  scripts/                   start/stop/health-check scripts
  src/                       Shared modules (utils, db, cache, security)

ComfyUI/                     ComfyUI upstream (vendored)
character_select_stand_alone_app-main/   Standalone character picker (Electron + Express)
configs/                     YAML pipeline configs
docs/                        Documentation
docker-compose.yml           MongoDB + ChatBot + optional sidecars
menu.bat / menu.sh           Service launcher menu
```

---

## Optional Sidecars & Integrations

| Component | Type | Activation | Mô tả |
|---|---|---|---|
| **last30days** | Subprocess | `LAST30DAYS_ENABLED=true` hoặc `docker compose --profile tools` | Multi-source social media research (Reddit, X, YouTube, HackerNews, ...) |
| **Hermes Agent** | HTTP sidecar (port 8080) | `HERMES_ENABLED=true` hoặc `docker compose --profile hermes` | AI agent với tool registry, memory, subagent delegation |
| **Character Select** | Electron + WS sidecar (port 51028) | `CHARACTER_SELECT_ENABLED=true` (+ `CHARACTER_SELECT_AUTO_START=true` to spawn) hoặc `docker compose --profile character-select` | Character picker UI cho image gen workflow. Status endpoint: `GET /api/character-select/status`. Source: [mirabarukaso/character_select_stand_alone_app](https://github.com/mirabarukaso/character_select_stand_alone_app) |

Tất cả đều **tuỳ chọn** — chatbot chạy bình thường khi không bật.

---

## Dependency Profiles

| Profile | venv | Requirements |
|---|---|---|
| core-services | `venv-core` | `app/requirements/profile_core_services.txt` |
| image-ai-services | `venv-image` | `app/requirements/profile_image_ai_services.txt` |

Chatbot + MCP → `venv-core`. SD + ComfyUI → `venv-image`. **Không trộn lẫn.**

---

## Tests

```bash
venv-core\Scripts\Activate.ps1     # Windows
source venv-core/bin/activate       # Linux/Mac

cd services/chatbot
pytest tests/ -v --tb=short
```

CI: `.github/workflows/tests.yml` — chạy với `TESTING=True`, `MONGODB_ENABLED=False`, timeout 60s.

---

## Tài liệu

- [AGENTS.md](AGENTS.md) — Architecture conventions cho AI coding assistants
- [docs/](docs/) — Deployment guides, integration plans
- [services/chatbot/README.md](services/chatbot/README.md) — Chatbot service detail
- [app/scripts/README.md](app/scripts/README.md) — Script vận hành
- [.github/skills/](.github/skills/) — 17 chuyên môn skill files

---

## Known Issues

- **menu.sh** advertise sai port: SD=7860 (đúng: 7861), Edit Image=7861 (đúng: 8100), MCP=8000 (đúng: stdio). Dùng `menu.bat` hoặc scripts trực tiếp.
- **Gemini** có thể bị disable trong `chatbot_main.py` khi quota cạn — fallback sẽ dùng provider khác.
- **Multiple venvs**: `venv/`, `venv-core/`, `venv-image/` cùng tồn tại. Default active là `venv-core` cho chatbot.
