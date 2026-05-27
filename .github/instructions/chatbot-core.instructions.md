---
applyTo: "services/chatbot/**,services/shared_env.py,services/mcp-server/**,app/config/**,app/src/**"
---

# Chatbot Core — Development Instructions

These instructions apply to all chatbot, shared env, MCP server, and shared config work.

## Scope

You are working inside the core chatbot layer. The image pipeline, Stable Diffusion, and ComfyUI stacks are out of scope unless the task explicitly names them.

## File map — what each file owns

### Entry points

| File | Responsibility |
|---|---|
| `services/chatbot/chatbot_main.py` | Flask legacy monolith entry point |
| `services/chatbot/run.py` | Dispatcher for the Flask monolith |

### Core modules — `services/chatbot/core/`

| File | Responsibility |
|---|---|
| `core/config.py` | All API keys and config constants (read from env) |
| `core/chatbot.py` | `ChatbotAgent` v1 — if/elif model routing, tool dispatch |
| `core/chatbot_v2.py` | `ChatbotAgent` v2 — `ModelRegistry`-based dispatch |
| `core/tools.py` | Tool functions: web search, reverse image, SauceNAO, image search |
| `core/streaming.py` | SSE / streaming helpers and `StreamEvent` |
| `core/stream_contract.py` | `build_complete_event_payload()` — SSE complete event shape |
| `core/stream_metrics.py` | Stream timing and metrics tracking |
| `core/thinking_generator.py` | Thinking mode logic + `ThinkTagParser` |
| `core/base_chat.py` | `ModelConfig`, `ModelProvider`, `ChatContext` base classes |
| `core/async_chat.py` | `AsyncChatbotAgent` for async routes |
| `core/extensions.py` | Flask extensions shared across blueprints (MongoDB, logger) |
| `core/db_helpers.py` | MongoDB access helpers |
| `core/error_handler.py` | Centralized error handling |
| `core/feature_flags.py` | Runtime feature flags |
| `core/user_auth.py` | User auth logic (passwords, quotas, admin seeding) |
| `core/http_logging.py` | HTTP request/response logging |
| `core/agentic/` | Multi-thinking pipeline: orchestrator, agents, contracts, blackboard |
| `core/image_gen/` | Image gen orchestration: multi-provider router, intent detection |

### Flask routes — `services/chatbot/routes/`

| File | Responsibility |
|---|---|
| `routes/stream.py` | **Primary**: `POST /chat/stream` (SSE) |
| `routes/main.py` | `/`, `/chat`, `/clear`, `/history`, `/api/generate-title` |
| `routes/conversations.py` | Conversation CRUD endpoints |
| `routes/mcp.py` | `/api/mcp/*` — MCP proxy routes |
| `routes/image_gen.py` | `/api/image-gen/*` — multi-provider image generation |
| `routes/images.py` | `/images/*` — image storage routes |
| `routes/memory.py` | `/memory/*` — AI memory routes |
| `routes/models.py` | Model list and status |
| `routes/auth.py` | Auth endpoints |
| `routes/stable_diffusion.py` | SD proxy routes (`sd_bp`) |
| `routes/admin.py` | `/admin` — admin panel, user management |
| `routes/user_auth.py` | Login, register, quota endpoints |
| `routes/qr_payment.py` | QR payment routes (VietQR) |
| `routes/skills.py` | `/api/skills/*` — runtime skill management |
| `routes/async_routes.py` | `/chat/async` — async SSE streaming |

### Other key directories

| Path | Responsibility |
|---|---|
| `services/chatbot/config/` | Service-level config: `mongodb_config.py`, `mongodb_helpers.py`, `model_presets.py`, `features.json` |
| `services/chatbot/database/` | Repository pattern DB access, query caching |
| `services/chatbot/src/video_generation.py` | OpenAI Sora 2 video generation |
| `services/chatbot/src/audio_transcription.py` | Whisper STT |
| `services/chatbot/src/ocr_integration.py` | Vision API OCR |
| `services/chatbot/src/handlers/` | Multimodal handler, advanced image gen handler |
| `services/chatbot/src/utils/` | Utility modules (imgbb, SD client, MCP integration, etc.) |
| `services/chatbot/src/rag/` | RAG subsystem (ingest, embeddings, retrieval, service) |
| `services/chatbot/app/` | Legacy modular Flask helpers that may still be imported by the monolith |
| `services/chatbot/templates/` | `index.html` (chat UI) |
| `services/chatbot/static/js/modules/` | JS modules: api-service, chat-manager, message-renderer, image-gen-v2, video-gen, etc. |
| `services/shared_env.py` | Shared env loader — do not duplicate its logic |
| `services/mcp-server/server.py` | FastMCP server (stdio) |
| `services/mcp-server/tools/advanced_tools.py` | MCP tool implementations |

**Warning — two config layers exist:**
- `core/config.py` reads API keys from env. This is the primary config.
- `config/mongodb_config.py` + `config/mongodb_helpers.py` handle MongoDB setup. Imported directly by `chatbot_main.py` using `importlib`.
- Do not confuse `services/chatbot/config/` with `app/config/` (root-level shared config).

## Request path — Flask primary (SSE)

```
Client POST /chat/stream
  → routes/stream.py
    → core/chatbot.py (ChatbotAgent)
      → model selection (config.py keys)
      → tool dispatch (tools.py)
        → web search: SerpAPI → Google CSE
        → reverse image: Google Lens → Google Reverse → Yandex
        → SauceNAO
      → thinking_generator.py (if think/deep-think/multi-thinking)
    → SSE response stream
```

## Environment loading rules

- Call `load_shared_env(__file__)` exactly once per process, before importing modules that read env at import time.
- `core/config.py` reads all keys via `os.getenv(...)`. Never hardcode values there.
- If adding a new API key: add it to `core/config.py`, document the variable name in `README.md`, and add a placeholder line to `app/config/.env.example`.

## Adding a new chat tool

1. Implement the tool function in `core/tools.py`.
2. Add the API key reference to `core/config.py`.
3. Register the tool in `core/chatbot.py` routing logic.
4. If the tool has a UI button, update `templates/index.html` and the search tools table in `README.md`.
5. Add at least one unit test in `tests/`.

## Adding a new MCP tool

1. Add the function to `services/mcp-server/tools/advanced_tools.py` and decorate with `@mcp.tool()`.
2. Registration is auto-discovered by FastMCP via `server.py`.
3. MCP transport is **stdio only**. Do not add HTTP listeners or routes.
4. Document the tool name, arguments, and return shape in `services/mcp-server/README.md`.

## Thinking modes

| Mode | Behavior |
|---|---|
| `instant` | No reasoning chain, direct answer |
| `think` | Internal chain-of-thought before responding |
| `deep-think` | DeepSeek R1 extended reasoning |
| `multi-thinking` | 4-agent pipeline: Analyst + Creative + Critic + Synthesizer |

Logic lives in `core/thinking_generator.py`. Do not inline thinking mode branching into route handlers.

## Search tool cascade — do not break

**Web search**: SerpAPI Google → Bing/Baidu options → Google CSE fallback  
**Reverse image**: Google Lens → Google Reverse Image → Yandex  
**Auto-trigger**: activates when user query contains real-time keywords (price, weather, news, etc.)

Fallback order is intentional. If SerpAPI is unavailable, the CSE fallback must still work independently.

## Flask-only runtime path

- Flask SSE path: `routes/stream.py` is **canonical**. Always keep it working.
- The parallel API implementation was removed in May 2026. Do not add compatibility shims or reintroduce a second runtime path.

## Verification checklist after chatbot changes

- [ ] `pytest services/chatbot/tests/ -v` passes (activate `venv-core`).
- [ ] `/chat/stream` still returns SSE events.
- [ ] Thinking mode still works for at least `instant` and `think`.
- [ ] If any env var name changed: `core/config.py`, `.env.example`, and `README.md` updated.
- [ ] If a new route was added: blueprint registration in app factory confirmed.
- [ ] If a new tool was added: tool name matches what the UI sends, fallback behavior is defined.

## Doc-sync triggers

| What changed | What to update |
|---|---|
| New env variable | `core/config.py`, `README.md` env table, `app/config/.env.example` |
| New route | Route docstring, `README.md` or API docs |
| Port change | `README.md` service table, `app/config/config.yml`, any health-check script |
| New tool | `README.md` search tools table, `core/tools.py` comment header |
| New MCP tool | `services/mcp-server/README.md` |

## Skill activation for chatbot work

**Before editing chatbot code, read the matching skill at `.github/skills/{name}/SKILL.md`.** Each skill has file monitors and checklists — follow them.

| Changing… | Read first (`.github/skills/{name}/SKILL.md`) |
|---|---|
| `routes/`, blueprints, SSE events | `core-chatbot-routing-audit` + `tool-response-contract` |
| `core/tools.py`, search cascade | `search-tool-cascade` |
| `core/chatbot.py`, model selection | `provider-env-matrix` + `core-chatbot-routing-audit` |
| `core/thinking_generator.py` | `thinking-mode-routing` |
| `core/config.py`, env vars | `shared-env-contract` + `provider-env-matrix` |
| `templates/`, `static/`, UI controls | `chat-ui-sync` |
| Error handling, log calls | `observability-log-hygiene` |
| `requirements.txt`, packages | `requirements-profile-selection` + `workflow-impact-guard` |
| MCP server files | `mcp-tool-authoring` |
| Startup failure, port drift, health | `service-health-check-audit` |

**After any behavior change:** also read `docs-drift-sync` (docs) and `test-impact-mapper` (tests). When uncertain which skill applies, start with `skills-dispatch-map`.

## What not to do

- Do not import from `services/stable-diffusion/` or `services/edit-image/`.
- Do not add a `load_dotenv` call that could override values already loaded by `shared_env.py`.
- Do not hardcode `localhost`, port numbers, or file paths; read from env or derive from `Path(__file__)`.
- Do not add compatibility shims or a second runtime path.
- Do not modify `.claude/skills/repo-guidelines/AGENTS.md` or `.github/copilot-instructions.md` as part of a feature task — those are meta files.
