﻿# ChatBot Service

Flask monolith chatbot — port 5000. Entry point: `run.py`.

---

## Khởi động

```powershell
# Browser
python services/chatbot/run.py
# mở http://127.0.0.1:5000

# Desktop (Recommended) — Electron frameless + tray
cd app/electron
npm install
npm run dev
```

Chế độ `USE_FASTAPI` / `USE_NEW_STRUCTURE` đã bỏ từ tháng 5/2026 — chỉ còn Flask monolith.

---

## Kiến trúc

```
routes/
  stream.py           PRIMARY: POST /chat/stream (SSE)
  main.py             /, /chat, /clear, /history, /api/generate-title
  conversations.py    CRUD conversations
  image_gen.py        /api/image-gen/*
  images.py           /images/*
  memory.py           /memory/*
  mcp.py              /api/mcp/*
  skills.py           /api/skills/*
  characters.py       /api/characters/*
  character_select.py /api/character-select/*, /api/local-image-gen/*
  jobs.py             /api/jobs/*
  stable_diffusion.py SD proxy
  anime_pipeline.py   /api/anime-pipeline/*
  reasoning_image_gen.py  /api/reasoning-image-gen/* (REASONING_PIPELINE=true)
  hermes.py           /api/hermes/chat (HERMES_ENABLED=true)
  last30days.py       /api/tools/last30days (LAST30DAYS_ENABLED=true)
  async_routes.py     /chat/async, /chat/async/stream, /chat/async/batch

core/
  config.py           API keys & constants (từ env)
  chatbot.py          ChatbotAgent v1 (if/elif routing)
  chatbot_v2.py       ChatbotAgent v2 (ModelRegistry)
  tools.py            Web search, reverse image, SauceNAO
  thinking_generator.py  Thinking modes + ThinkTagParser
  stream_contract.py  SSE complete-event payload builder
  agentic/            4-agent council (Planner->Researcher->Critic->Synthesizer)
  image_gen/          Multi-provider image gen router (7 providers)
  skills/             SkillRegistry, SkillRouter, resolver, applicator, session
    builtins/         12 YAML skill definitions
  character_registry.py  CharacterRegistry singleton
  job_queue.py        JobQueue singleton
  hermes_adapter.py   Hermes sidecar HTTP proxy

config/               mongodb_config.py, model_presets.py, features.json
database/             Repository pattern DB access
src/
  audio_transcription.py  STT (Whisper)
  ocr_integration.py      OCR (Vision API)
  video_generation.py     Sora 2 video
  handlers/               Multimodal + image gen handlers
  utils/                  imgbb, SD client, MCP integration
  rag/                    RAG subsystem (ingest, embeddings, retrieval)
templates/            index.html (sole template)
static/
  css/                app.css + component CSS
  js/main.js          Orchestration + event bindings
  js/modules/         api-service, chat-manager, message-renderer,
                      image-gen-v2, video-gen, skill-manager,
                      file-handler, export-handler, electron-bridge,
                      right-sidebar, character-picker, job-queue-panel, ...
tests/                pytest (venv-core)
```

---

## LLM Providers

| Provider | Env key | Model mặc định |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Grok (xAI) | `GROK_API_KEY` | `grok-3` |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| Qwen | `QWEN_API_KEY` | `qwen-turbo` |
| Gemini | `GEMINI_API_KEY_1..4` | `gemini-2.0-flash` |
| OpenRouter | `OPENROUTER_API_KEY` | `stepfun/step-3.5-flash:free` |
| StepFun | `STEPFUN_API_KEY` | `step-2-16k` |
| BloomVN (HF) | `HUGGINGFACE_API_KEY` | `BlossomsAI/BloomVN-8B-chat` |
| Ollama local | — | user-chosen |

---

## Thinking Modes

| Mode | Label UI | Mô tả |
|---|---|---|
| `instant` | Instant | Trả lời trực tiếp, không pipeline |
| `multi-thinking` | 4-Agents (default) | 4-agent council: Planner->Researcher->Critic->Synthesizer |

---

## Image Generation

Router `core/image_gen/router.py` (`ImageGenerationRouter`) đăng ký provider theo env key có sẵn. Provider chọn theo **priority giảm dần** + `QualityMode`, fallback xuống provider thấp hơn khi lỗi.

8 providers tại `core/image_gen/providers/`:

| Provider | Priority | Env key | Models tiêu biểu |
|---|---|---|---|
| fal.ai | 90 | `FAL_API_KEY` | FLUX.2, nano-banana(-pro/-2), seedream5, recraft-v4 |
| Black Forest Labs | 85 | `BFL_API_KEY` | FLUX.2 pro/dev/max, FLUX1 pro |
| Replicate | 80 | `REPLICATE_API_TOKEN` | grok-imagine, FLUX.2, kontext, sdxl-lightning |
| StepFun | 75 | `STEPFUN_API_KEY` | step1x turbo/medium/edit/fill |
| OpenAI | 70 | `OPENAI_API_KEY` | gpt-image-1, DALL-E 3 |
| Together AI | 60 | `TOGETHER_API_KEY` | FLUX1 schnell/dev/kontext/redux |
| ComfyUI Fast | 15 | `COMFYUI_URL`/`SD_API_URL` | local single-pass (~10s, SAA-style) |
| ComfyUI | 10 | `COMFYUI_URL`/`SD_API_URL` | local multi-pass workflow |

> `nano_banana_provider.py` không đăng ký riêng trong router — các model `nano-banana*` được phục vụ qua fal.ai/Replicate. Surface trực tiếp ở `routes/nano_banana.py` (`/api/nano-banana/*`, gate `NANO_BANANA_ENABLED`, mặc định `true`).

Provider tier `comfyui`/`comfyui_fast` chỉ đăng ký khi runtime profile không bật `skip_comfyui_provider`. AUTO mode gom provider cùng tier (chênh ≤15 điểm) rồi random để phân tải; `FREE` mode ép local; `QUALITY` ưu tiên tier cao.

---

## Skill System

12 built-in YAML skills tại `core/skills/builtins/`. Resolve order:

```
explicit skill -> session skill -> auto-route (SkillRouter, threshold 1.05) -> none
```

---

## API Endpoints (chính)

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/chat/stream` | **Primary** SSE streaming chat |
| `POST` | `/chat/async` | Async SSE |
| `GET` | `/c/<id>` | Chat page với conversation cụ thể |
| `GET/DELETE` | `/conversations[/<id>]` | CRUD conversations |
| `POST` | `/api/generate-title` | Auto-generate title |
| `GET` | `/api/skills` | List skills |
| `POST` | `/api/skills/activate` | Activate skill cho session |
| `POST` | `/api/image-gen/generate` | Image gen (JSON) |
| `POST` | `/api/image-gen/stream` | Image gen (SSE, có event `provider_try`) |
| `POST` | `/api/image-gen/edit` | Edit ảnh gần nhất (img2img) |
| `GET` | `/api/image-gen/providers` | List provider đang bật |
| `GET` | `/api/image-gen/gallery` | Ảnh đã tạo gần đây |
| `GET` | `/api/image-gen/loras` | List LoRA catalog |
| `POST` | `/api/nano-banana/generate` | Gemini Flash Image (gate `NANO_BANANA_ENABLED`) |
| `POST` | `/api/anime-pipeline/stream` | Anime pipeline SSE (gate `IMAGE_PIPELINE_V2`) |
| `POST` | `/api/reasoning-image-gen/stream` | Multi-panel pipeline (gate `REASONING_PIPELINE`) |
| `POST` | `/api/video/generate` | Sora 2 video |
| `POST` | `/memory/save` | Save AI memory |
| `GET` | `/api/jobs` | Job queue status |
| `GET` | `/health` | Service health |

---

## Env Variables

Loader: `services/shared_env.py` -> `load_shared_env(__file__)` đọc `app/config/.env_dev` (hoặc `.env`). Một lần duy nhất mỗi process.

```env
# LLM (chọn ít nhất 1)
OPENAI_API_KEY=
GROK_API_KEY=
DEEPSEEK_API_KEY=
QWEN_API_KEY=
GEMINI_API_KEY_1=
OPENROUTER_API_KEY=
STEPFUN_API_KEY=

# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=ai_assistant_v2

# Image gen
FAL_API_KEY=
BFL_API_KEY=
REPLICATE_API_TOKEN=
TOGETHER_API_KEY=
STEPFUN_API_KEY=
COMFYUI_URL=http://127.0.0.1:8188
SD_API_URL=http://127.0.0.1:7861

# Search
SERPAPI_API_KEY=
GOOGLE_SEARCH_API_KEY_1=
GOOGLE_CSE_ID=

# Optional flags
REASONING_PIPELINE=false
IMAGE_PIPELINE_V2=true
NANO_BANANA_ENABLED=true
HERMES_ENABLED=false
CHARACTER_SELECT_ENABLED=false
LAST30DAYS_ENABLED=false
FLASK_PORT=5000
```

---

## Tests

```bash
# Activate venv-core trước
cd services/chatbot
pytest tests/ -v --tb=short
```

---

## Electron Keyboard Shortcuts

| Phím | Tác dụng |
|---|---|
| `F12` | Bật / tắt DevTools |
| `F5` | Reload trang (renderer) |
| `Ctrl+Shift+R` | Restart Python backend |
| `Ctrl+Shift+A` | Ẩn / hiện cửa sổ (global) |

---

## Cấu trúc thư mục (tóm tắt)

```
services/chatbot/
|-- chatbot_main.py       Flask entry point
|-- run.py                Dispatcher (recommended entry)
|-- core/                 Business logic, providers, tools
|-- routes/               Flask blueprints
|-- config/               MongoDB config, model presets
|-- database/             DB repository layer
|-- src/                  STT, OCR, video, RAG, handlers, utils
|-- templates/            index.html
|-- static/               CSS + JS modules
`-- tests/                pytest test suite
```
