# AI-Assistant

Nền tảng microservices Python: chatbot đa LLM, image generation đa provider, video (Sora 2), và MCP server. Surface chính là Electron desktop (frameless + tray); browser mode vẫn chạy được.

---

## Dịch vụ

| Service | Port | Entry | venv |
|---|---|---|---|
| **ChatBot** | `5000` | `services/chatbot/run.py` | `venv-core` |
| **MCP Server** | stdio (FastMCP) | `services/mcp-server/server.py` | `venv-core` |
| **Stable Diffusion** | `7861` | `services/stable-diffusion/` | `venv-image` |
| **Edit Image (ComfyUI)** | `8100` | `services/edit-image/` | `venv-image` |

`AUTO_START_IMAGE_SERVICES=true` (mặc định) → `run.py` tự spawn SD + Edit Image.

---

## Khởi động nhanh

**Desktop (khuyến nghị):**

```powershell
cd desktop\electron
npm install
npm run dev          # frameless window + tray + auto-spawn backend
```

**Browser:**

```powershell
cd services\chatbot
python run.py        # http://127.0.0.1:5000
```

> Chỉ còn Flask monolith. `USE_FASTAPI`, `USE_NEW_STRUCTURE`, package `fastapi_app/`, blueprints `auth`/`admin`/`qr_payment` đã bị bỏ trong Electron Phase 1 (May 2026). Electron giả định một single trusted local user — không có login.

**Electron shortcuts:** `F12` DevTools · `F5` reload · `Ctrl+Shift+R` restart backend · `Ctrl+Shift+A` toggle window.

---

## Tính năng Chatbot

| Nhóm | Chi tiết |
|---|---|
| LLM providers | OpenAI, Grok (xAI), DeepSeek, Qwen, Gemini, OpenRouter, StepFun, BloomVN (HF), Ollama local |
| Thinking modes | UI: `Instant` / `4-Agents` (default). Backend còn nhận `thinking`/`deep`/`auto` cho skill overrides |
| 4-Agent council | Planner → Researcher → Critic → Synthesizer (`core/agentic/`) |
| Skill system | 12 built-in YAML personas, auto-route theo nội dung message |
| Image generation | 7 provider router + fallback chain |
| Reasoning image pipeline | Local ComfyUI multi-panel — opt-in `REASONING_PIPELINE=true` |
| Video AI | OpenAI Sora 2 |
| Web search | SerpAPI (Google/Bing/Baidu) → Google CSE fallback, auto-trigger theo từ khoá realtime |
| Reverse image | Google Lens → Google Reverse → Yandex |
| OCR / STT | Vision APIs / Whisper |
| RAG | MongoDB Atlas + embeddings |
| MCP | Truy cập file/folder local qua stdio |
| Streaming | SSE realtime (`POST /chat/stream`) |
| URL routing | `/c/<conversation_id>` per-conversation (ChatGPT-style) |
| Conversation CRUD | Tạo / xoá / archive / switch / generate title |

---

## Thinking Modes

| Mode (UI) | Backend value | Hành vi |
|---|---|---|
| Instant | `instant` | Trả lời trực tiếp một agent |
| **4-Agents** (default) | `multi-thinking` | 4-agent council |

Nút **Think Harder** trong response actions: gửi lại tin cuối cùng với `multi-thinking`.

```
Planner    → Phân tích, chia task list
Researcher → Web search / RAG / MCP
Critic     → Đánh giá, quyết định round mới
Synthesizer→ Tổng hợp câu trả lời
```

Source: `services/chatbot/core/agentic/{agents/*,orchestrator.py,blackboard.py}`. SSE qua `routes/stream.py`.

---

## LLM Providers

| Provider | Env key | Default model | Stream | Vision |
|---|---|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | ✓ | ✓ |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` | ✓ | – |
| Grok (xAI) | `GROK_API_KEY` | `grok-3` | ✓ | – |
| Qwen | `QWEN_API_KEY` | `qwen-turbo` | ✓ | – |
| Gemini | `GEMINI_API_KEY_1..4` | `gemini-2.0-flash` | ✓ | ✓ |
| OpenRouter | `OPENROUTER_API_KEY` | `stepfun/step-3.5-flash:free` | ✓ | – |
| StepFun | `STEPFUN_API_KEY` | `step-2-16k` | ✓ | – |
| BloomVN (HF) | `HUGGINGFACE_API_KEY` | `BlossomsAI/BloomVN-8B-chat` | – | – |
| Ollama | – | (user chọn) | ✓ | tuỳ model |

Fallback chain wired tại `core/chatbot_v2.py` (ModelRegistry).

---

## Image Generation

7 provider tại `services/chatbot/core/image_gen/providers/`:

| Provider | File | Models tiêu biểu |
|---|---|---|
| **fal.ai** | `fal_provider.py` | FLUX.2 / FLUX.1 / nano-banana / seedream5 |
| Black Forest Labs | `bfl_provider.py` | FLUX Pro |
| Replicate | `replicate_provider.py` | Marketplace |
| OpenAI | `openai_provider.py` | DALL-E 3 |
| StepFun | `stepfun_provider.py` | Step image |
| Together AI | `together_provider.py` | Open-source |
| ComfyUI | `comfyui_provider.py` | Local workflow |

Chọn theo API key + priority; fallback tự động khi provider lỗi.

---

## Skill System

12 built-in YAML skills tại `services/chatbot/core/skills/builtins/`:

`code-expert`, `coding-assistant`, `realtime-search`, `research-analyst`, `repo-analyzer`, `research-web`, `social-research`, `prompt-engineer`, `mcp-file-helper`, `creative-writer`, `shopping-advisor`, `counselor`.

**Resolve order:** explicit (`request.skill`) → session (`POST /api/skills/activate`) → auto-route (SkillRouter, threshold `1.05`) → none.

Skill có thể override: `model`, `thinking_mode`, `system_prompt`, `tools`, `context_window`.

---

## MCP Server

Transport **stdio** (FastMCP). Không có HTTP listener. Entry: `services/mcp-server/server.py`. Chatbot proxy qua `routes/mcp.py`.

| Tool | Mô tả |
|---|---|
| `search_files` | Tìm file theo query / file_type |
| `read_file_content` | Đọc file (giới hạn `max_lines`) |
| `list_directory` | List directory |
| `get_project_info` | Project metadata |
| `search_logs` | Search trong service logs |
| `calculate` | Safe math eval |

Plus `@mcp.resource()` (config, docs) và `@mcp.prompt()` (code review, debug, explain).

---

## API Endpoints

### Chat & conversations
| Method | Path |
|---|---|
| `POST` | `/chat/stream` (**primary**, SSE), `/chat/async` |
| `GET` | `/c/<conversation_id>` |
| `GET`/`DELETE` | `/conversations[/<id>]` |
| `POST` | `/conversations/new`, `/conversations/<id>/{switch,archive}`, `/clear`, `/api/generate-title` |

### Skills
| Method | Path |
|---|---|
| `GET` | `/api/skills`, `/api/skills/<id>`, `/api/skills/active` |
| `POST` | `/api/skills/{activate,deactivate}` |

### Image / Video / Reasoning
| Method | Path |
|---|---|
| `POST` | `/api/image-gen/{generate,stream,edit}` |
| `POST`/`GET` | `/api/video/{generate,generate-sync,status/<id>,download/<id>,list}` |
| `GET`/`POST` | `/api/reasoning-image-gen/{status,generate}` (`REASONING_PIPELINE=true`) |

Khi `REASONING_PIPELINE=true`, cả `POST /api/image-gen/generate` và `POST /api/image-gen/stream` accept `use_reasoning_pipeline: true` trong payload — short-circuit provider router, trả về cùng response shape (`provider: "reasoning"`, `model: "comic-pipeline"`). Stream phát chuỗi event quen thuộc `status` → `provider_try` → `provider_success` → `result` → `saved`. Image Gen v2 modal exposes nút **🧠 Use Reasoning Pipeline** và lưu `localStorage`.

### Memory / MCP / SD / Health
| Method | Path |
|---|---|
| `POST`/`GET`/`PUT`/`DELETE` | `/memory/{save,list,get/<id>,update/<id>,delete/<id>,search}` |
| `POST` | `/api/mcp/{enable,disable,add-folder,remove-folder,ocr-extract,warm-cache}` |
| `GET` | `/api/mcp/{list-files,search-files,read-file,grep,status}` |
| `GET` | `/api/sd-{health,models,presets,samplers,vaes}` |
| `POST` | `/api/sd-change-model`, `/api/generate-image`, `/api/img2img` |
| `GET` | `/health`, `/api/health/databases` |

Blueprints tại `services/chatbot/routes/`. Auth/admin/qr-payment đã bỏ.

---

## URL Routing

```
GET /                       → Tạo / restore session, replace sang /c/<id>
GET /c/<conversation_id>    → Conversation cụ thể (regex [A-Za-z0-9_\-]{1,64})
GET /new                    → New session rồi redirect /
```

Frontend (`static/js/modules/chat-manager.js`): `_syncUrl()` dùng `history.pushState/replaceState`, `popstate` listener cho Back/Forward, URL-first restore từ `localStorage.chatSessions[id]`. Stream payload kèm `conversation_id` + 3 ảnh gen gần nhất (`generated_images[]`) làm context.

---

## Cài đặt

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant

# Core (chatbot + MCP)
python -m venv venv-core
venv-core\Scripts\activate                          # Windows
# source venv-core/bin/activate                     # Linux/Mac
pip install -r app/requirements/profile_core_services.txt

# Image (chỉ khi cần local SD/ComfyUI)
python -m venv venv-image
pip install -r app/requirements/profile_image_ai_services.txt

# Env
cp app/config/.env.example app/config/.env
# Sửa app/config/.env, set ít nhất 1 LLM key (OpenRouter cho fallback đa dạng)
```

Loader: `services/shared_env.py` → `load_shared_env(__file__)` → tìm `app/config/.env_{env}` rồi fallback `app/config/.env`. Mỗi service gọi **một lần** khi khởi động.

---

## Docker

```bash
docker compose up -d                                  # Mongo + ChatBot
docker compose --profile tools up -d                  # + last30days
docker compose --profile hermes up -d                 # + Hermes
docker compose --profile character-select up -d       # + Character Select
docker compose --profile all up -d                    # tất cả

curl http://localhost:5000/health
```

> SD + ComfyUI **không** trong docker-compose (cần GPU local).

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
MONGODB_DB_NAME=ai_assistant_v2

# ── Image generation ──
FAL_API_KEY=
BFL_API_KEY=
REPLICATE_API_KEY=
TOGETHER_API_KEY=
SD_API_URL=http://127.0.0.1:7861

# ── Search ──
SERPAPI_API_KEY=
GOOGLE_SEARCH_API_KEY_1=
GOOGLE_CSE_ID=
SAUCENAO_API_KEY=

# ── Storage ──
IMGBB_API_KEY=
FIREBASE_RTDB_URL=
FIREBASE_DB_SECRET=

# ── Optional sidecars ──
LAST30DAYS_ENABLED=false
HERMES_ENABLED=false
HERMES_API_URL=http://localhost:8080
CHARACTER_SELECT_ENABLED=false
CHARACTER_SELECT_URL=http://localhost:51028
CHARACTER_SELECT_AUTO_START=false
REASONING_PIPELINE=false

# ── Runtime ──
AUTO_START_IMAGE_SERVICES=true
FLASK_PORT=5000
env=dev                    # → .env_dev / .env_prod
```

---

## Optional Sidecars

| Component | Type | Activation | Mô tả |
|---|---|---|---|
| **last30days** | Subprocess | `LAST30DAYS_ENABLED=true` hoặc `--profile tools` | Multi-source social research (Reddit, X, YouTube, HN, …) |
| **Hermes Agent** | HTTP (port 8080) | `HERMES_ENABLED=true` hoặc `--profile hermes` | AI agent với tool registry, memory, subagent delegation |
| **Character Select** | Electron + WS (51028) | `CHARACTER_SELECT_ENABLED=true` (+ `_AUTO_START=true`) hoặc `--profile character-select` | Character picker UI cho image gen. Status: `GET /api/character-select/status`. Source: [mirabarukaso/character_select_stand_alone_app](https://github.com/mirabarukaso/character_select_stand_alone_app) |

Khi cả `HERMES_ENABLED` và `REASONING_PIPELINE` cùng bật, một bridge tại `core/image_intent.py` classify message và redirect image-gen sang reasoning pipeline (fail-safe: lỗi import/classify → fall through Hermes nguyên vẹn).

---

## Cấu trúc thư mục

```
services/
  shared_env.py                       Bộ tải env dùng chung
  chatbot/
    chatbot_main.py                   Flask monolith entry
    run.py                            Dispatcher + sidecar autostart
    core/
      config.py                       API keys, system prompts
      chatbot_v2.py                   ModelRegistry agent
      tools.py                        Web search, reverse image, SauceNAO
      thinking_generator.py
      stream_contract.py              SSE payload contract
      agentic/                        4-agent council
      image_gen/                      7 providers + orchestrator
      skills/{registry,router,resolver,session,builtins/}
      character_registry.py, job_queue.py, image_intent.py
    routes/                           Flask blueprints
    src/
      audio_transcription.py          Whisper STT
      ocr_integration.py              Vision OCR
      video_generation.py             Sora 2
      handlers/, utils/, rag/
    templates/index.html              Single template
    static/{css,js/modules}/          UI assets
    config/                           mongodb_config, model_presets, features.json
    tests/
  mcp-server/server.py                FastMCP stdio
  stable-diffusion/                   SDXL (7861)
  edit-image/                         ComfyUI (8100)

desktop/electron/                     Frameless wrapper (tray, IPC, single-instance)
app/
  config/                             .env, config.yml, model_config.py
  requirements/                       profile_{core,image_ai}_services.txt
  scripts/                            start/stop/health-check
  src/                                Shared utils, db, cache, security
ComfyUI/                              ComfyUI upstream (vendored)
character_select_stand_alone_app-main/
configs/                              YAML pipeline configs
docs/
docker-compose.yml
menu.bat / menu.sh
```

---

## Tests

```powershell
venv-core\Scripts\Activate.ps1
cd services/chatbot
pytest tests/ -v --tb=short
```

CI (`.github/workflows/tests.yml`) chạy với `TESTING=True`, `MONGODB_ENABLED=False`, timeout 60s.

---

## Tài liệu

- [AGENTS.md](AGENTS.md) — Architecture conventions cho AI coding assistants
- [CLAUDE.md](CLAUDE.md) — Behavioural rules
- [docs/](docs/) — Deployment guides, integration plans
- [services/chatbot/README.md](services/chatbot/README.md) — Chatbot service detail
- [.github/skills/](.github/skills/) — Skill files cho Copilot

---

## Known Issues

- `menu.sh` ghi sai port: SD=7860 (đúng `7861`), Edit Image=7861 (đúng `8100`), MCP=8000 (đúng stdio). Dùng `menu.bat` hoặc scripts trực tiếp.
- Gemini có thể bị disable trong `chatbot_main.py` khi quota cạn — fallback dùng provider khác.
- Tồn tại nhiều venv (`venv/`, `venv-core/`, `venv-image/`); chatbot active mặc định trên `venv-core`.
