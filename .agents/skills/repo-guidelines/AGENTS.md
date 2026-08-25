# AGENTS.md — AI-Assistant

Repository: https://github.com/SkastVnT/AI-Assistant  
Language: Python microservices  
Primary focus: **Core chatbot, tool routing, shared env, MCP integration**

---

## What this repo is

A Python microservices platform with four active services. The chatbot is the primary development area. Image workflow services exist and are functional — do not touch them for chatbot-only tasks.

---

## Service map

| Service | Port | Entry point | venv profile |
|---|---|---|---|
| ChatBot | **5000** | `services/chatbot/chatbot_main.py` (Flask default) or `run.py` (all modes) | `venv-core` |
| MCP Server | **stdio** | `services/mcp-server/server.py` | `venv-core` |
| Stable Diffusion | **7861** | `services/stable-diffusion/` | `venv-image` |
| Edit Image (ComfyUI) | **8100** | `services/edit-image/` | `venv-image` |

---

## Startup

| Mode | Command | Notes |
|---|---|---|
| Browser (default) | `python services/chatbot/run.py` | Single Flask monolith on port 5000 |
| Desktop (Electron) | `cd desktop/electron && npm run dev` | Frameless + tray, auto-spawns the backend |

`run.py` is the universal dispatcher. `chatbot_main.py` is the Flask monolith and also works as a direct entry point. The previous `USE_FASTAPI` and `USE_NEW_STRUCTURE` modes (and the `fastapi_app/` package) were removed in May 2026 — only the Flask monolith remains.

---

## Environment loading — single contract

**Authoritative loader: `services/shared_env.py` → `load_shared_env(__file__)`**

- Resolves `app/config/.env_{env}` where `env` defaults to `"dev"`.
- Falls back to `app/config/.env`.
- **Never** duplicate `load_dotenv` calls across service files or hardcode `.env` paths.
- `run.py` additionally loads `services/chatbot/.env` **without override** for service-local keys (FAL_API_KEY, STEPFUN_API_KEY, etc.) that are not in the shared env.
- Call `load_shared_env(__file__)` **once**, early, before any module that reads env at import time.

---

## Dependency profiles

| Profile | venv | Requirements |
|---|---|---|
| core-services | `venv-core` | `app/requirements/profile_core_services.txt` |
| image-ai-services | `venv-image` | `app/requirements/profile_image_ai_services.txt` |

Chatbot and MCP work → `venv-core`. Image generation workflows → `venv-image`. Do not mix.

---

## File map

### Safe to edit for chatbot tasks

```
services/chatbot/
  chatbot_main.py           Flask entry point (legacy monolith)
  run.py                    Dispatcher for all startup modes
  core/
    config.py               All API keys and config constants (reads env)
    chatbot.py              ChatbotAgent class (v1, if/elif routing)
    chatbot_v2.py           ChatbotAgent v2 (ModelRegistry-based)
    tools.py                Tool functions: web search, reverse image, SauceNAO
    streaming.py            SSE / streaming helpers
    stream_contract.py      SSE complete-event payload builder
    stream_metrics.py       Stream timing and metrics
    thinking_generator.py   Thinking mode logic + ThinkTagParser
    base_chat.py            Base chat class (ModelConfig, ChatContext)
    async_chat.py           AsyncChatbotAgent for async routes
    extensions.py           Flask extensions (MongoDB, cache, logger)
    db_helpers.py           Database helpers
    error_handler.py        Centralized error handling
    feature_flags.py        Runtime feature flags
    http_logging.py         HTTP request/response logging
    private_logger.py       Private activity logger
    image_storage.py        Image storage helpers
    google_drive_service.py Google Drive integration
    rag_settings.py         RAG settings
    agentic/                Multi-thinking pipeline
      orchestrator.py       CouncilOrchestrator (4-agent loop)
      agents/               Planner, Researcher, Critic, Synthesizer
      contracts.py          AgentRole, RunStatus, CouncilResult
      blackboard.py         Shared state between agents
      config.py             Agentic-specific config
      xai_native/           xAI native research mode
    image_gen/              Image generation orchestration
      orchestrator.py       Multi-provider image gen router
      providers/            fal.ai, BFL, Replicate, StepFun, etc.
      intent.py             Image request detection
    skills/                 Runtime skill system
      registry.py           SkillDefinition, SkillRegistry, builtin YAML loader
      router.py             SkillRouter — auto-detect best skill (keyword + threshold)
      resolver.py           resolve_skill() — explicit > session > auto-route
      applicator.py         apply_skill_overrides() — merge skill into request
      session.py            SkillSessionStore (in-memory per-session binding)
      builtins/             12 built-in YAML skill definitions
    character_registry.py   CharacterRegistry singleton — searchable alias-aware DB
    character_select_adapter.py  HTTP probe to SAA sidecar (status, reachability)
    job_queue.py            JobQueue singleton — local image job lifecycle (queued→done)
    image_pipeline_link.py  Bridge: enriches LLM asset records with live JobQueue state
    hermes_adapter.py       HTTP proxy to Hermes Agent sidecar (POST /chat)
    last30days_tool.py      Subprocess wrapper for last30days social-research CLI
  routes/
    stream.py               PRIMARY: POST /chat/stream (SSE)
    main.py                 /, /chat, /clear, /history, /api/generate-title
    conversations.py        Conversation CRUD
    mcp.py                  /api/mcp/* — MCP proxy routes
    image_gen.py            /api/image-gen/* — multi-provider image gen
    images.py               /images/* — image storage
    memory.py               /memory/* — AI memory
    stable_diffusion.py     SD proxy routes (sd_bp)
    skills.py               /api/skills/* — runtime skill management
    characters.py           /api/characters/* — character registry search + SAA augment
    character_select.py     /api/character-select/* + /api/local-image-gen/* — SAA sidecar
    jobs.py                 /api/jobs/* — local image job queue (status, cancel, manifest)
    anime_pipeline.py       /api/anime-pipeline/* — local ComfyUI 7-agent pipeline
    reasoning_image_gen.py  /api/reasoning-image-gen/* — multi-panel reasoning pipeline (REASONING_PIPELINE=true)
    hermes.py               /api/hermes/chat — Hermes sidecar proxy (HERMES_ENABLED=true)
    last30days.py           /api/tools/last30days — social research (LAST30DAYS_ENABLED=true)
  config/                   Service-level config (NOT core/config.py)
    mongodb_config.py       MongoDB client setup
    mongodb_helpers.py      ConversationDB, MessageDB, MemoryDB, FileDB
    mongodb_schema.py       Schema definitions
    model_presets.py        SD model presets and categories
    features.json           Feature flag defaults
  database/                 Database abstraction layer
    repositories/           Repository pattern for DB access
    helpers.py              DB utility functions
    cache/                  Query caching
  src/
    audio_transcription.py  STT via Whisper API
    ocr_integration.py      OCR via Vision APIs
    video_generation.py     OpenAI Sora 2 video
    handlers/               Multimodal + advanced image gen handlers
    utils/                  Utility modules (imgbb, SD client, MCP, etc.)
    rag/                    RAG subsystem (ingest, embeddings, service, etc.)
  app/                      Nested Flask app (services + middleware only after Phase 1 cleanup)
    middleware/             auth.py (require_login is a no-op pass-through), rate_limiter.py
    services/               Service layer
  templates/
    index.html              Chat UI — sole template (login/admin removed May 2026)
  static/
    css/app.css             Main stylesheet
    css/image-gen-v2.css    Image gen modal styles
    js/main.js              Orchestration, event bindings
    js/mcp.js               MCP sidebar
    js/language-switcher.js Language toggle
    js/modules/             api-service, chat-manager, message-renderer,
                            image-gen-v2, video-gen, memory-manager,
                            skill-manager, ui-utils, file-handler,
                            export-handler, etc.
  tests/                    Unit + integration tests

services/shared_env.py      Shared environment loader
services/mcp-server/
  server.py                 Active MCP server (FastMCP, stdio)
  server_enhanced.py        Enhanced variant (additional tools)
  server_v2_memory.py       V2 with memory tools
  tools/advanced_tools.py   MCP tool implementations

app/config/                 Centralized config (.env, config.yml, model_config.py,
                            rate_limiter.py, response_cache.py, firebase_config.py)
app/src/                    Shared modules (utils, database, cache, security, health)

app/image_pipeline/         Local multi-stage image pipeline (image-only tasks)
  reasoning/                Reasoning library: capability_router, prompt_parser,
                            prompt_revision, schemas, state/, execution/
  anime_pipeline/           7-agent ComfyUI anime pipeline (orchestrator, agents,
                            lora_manager, saa_character_db, character_parser, ...)
  workflow/                 Workflow orchestrator (ImageJob dataclass, stage runner)
  evaluator/                LLM-as-judge scorer
  planner/                  PromptLayerEngine
  BLUEPRINT.md              Architecture reference (locked stack decisions)

app/character_select_stand_alone_app-main/   SAA — Electron character picker sidecar
  data/wai_characters.csv               5149 verified WAI SDXL characters
  data/danbooru_e621_merged.csv         Tag autocomplete vocabulary
  data/wai_character_thumbs.json        Character thumbnail index
  (webserver runs on port 51028)

app/storage/character_db/   Local character registry JSON (editable seed data)
  characters.json           Registry entries (key, display_name, series, tags...)
  series_aliases.json       Series key aliases (GI→genshin_impact, HSR→...)
```

**Structural warning — two config directories:**

- `services/chatbot/core/config.py` — API keys and constants (read from env). This is the primary config.
- `services/chatbot/config/` — MongoDB setup, model presets, feature flags. Legacy but actively imported by `chatbot_main.py`.

**Structural warning — nested `app/` inside chatbot:**
`services/chatbot/app/` contains legacy modular Flask helpers (middleware and service-layer code) that may still be imported by the monolith. It is not a startup mode. Do not confuse it with the root `app/` directory.

### Do not touch for chatbot-only tasks

```
ComfyUI/                    External dependency subtree — do not modify
app/image_pipeline/         Image pipeline internals
services/stable-diffusion/  SDXL stack
services/edit-image/        ComfyUI-based image editing
venv-core/                  Generated — never edit manually
venv-image/                 Generated — never edit manually
private/                    Internal data/submodule
```

---

## Operational rules

1. **Chatbot-only task** → edit only `services/chatbot/`, `services/shared_env.py`, `services/mcp-server/`, `app/config/`, `app/src/`. Do not touch image service files.

2. **Shared env** is loaded once per process. Do not add a second `load_dotenv` that overrides it. The one allowed exception is `run.py` loading `services/chatbot/.env` without override.

3. **Primary streaming endpoint**: `routes/stream.py` → `POST /chat/stream`. The Flask monolith is now the **only** path — the parallel `fastapi_app/` package was removed in May 2026 (Phase 1 of the Electron overhaul). If you need an API-first variant, raise it as a separate task; do not silently re-introduce a parallel framework.

   **Removed blueprints (May 2026):** `auth`, `models` (already removed earlier), `async_routes`, `user_auth`, `admin`, `qr_payment`. Login / admin / QR-payment routes and templates are gone. Electron is the canonical surface and assumes a single trusted local user; `app/middleware/auth.require_login` is a no-op pass-through.

4. **Adding a new tool**: update `core/tools.py`, `core/config.py` (for any new API key), tool-routing in `core/chatbot.py` or the relevant route handler, and the search tools table in `README.md`.

5. **Adding a new MCP tool**: update `services/mcp-server/server.py` or `tools/advanced_tools.py`. MCP transport is `stdio` — do not add HTTP listeners.

6. **Run tests**: `cd services/chatbot && pytest tests/ -v` (activate `venv-core` first).

7. **CI lint scope**: `services/ app/src/` — ComfyUI, private, and venv directories are excluded.

8. **After changing ports, entry points, or commands**: update `README.md` service table to match.

9. **Secrets and keys**: always read from env vars. Never hardcode API keys, URLs, or ports.

---

## Known doc inconsistencies

- `app/scripts/README.md` lists Stable Diffusion on 7860 and Edit Image on 7861. Main `README.md` says 7861 and 8100. **Main README is authoritative.**
- Older scripts reference `speech2text` (5001) and `text2sql` (5002) — these are archived services no longer in `services/`.
- MCP port 8000 appears in `app/scripts/README.md` but the server uses `stdio`. Do not add HTTP transport.

---

## Skill dispatch

Skills live in `.github/skills/{name}/SKILL.md`. **Read the matching skill file before editing code.** Each skill contains file monitors, checklists, and domain-specific rules.

| Task involves… | Read `.github/skills/{name}/SKILL.md` |
|---|---|
| Route, blueprint, SSE, Flask monolith | `core-chatbot-routing-audit` |
| Env vars, `.env` loading, secrets | `shared-env-contract` |
| Startup failure, port drift, health | `service-health-check-audit` |
| Search tool, fallback, auto-trigger | `search-tool-cascade` |
| MCP tool, resource, prompt | `mcp-tool-authoring` |
| Thinking mode, agentic pipeline | `thinking-mode-routing` |
| LLM provider, API key, model registry | `provider-env-matrix` |
| Return shape, SSE payload, response contract | `tool-response-contract` |
| UI control, selector, frontend wiring | `chat-ui-sync` |
| Log statement, error handling, bare except | `observability-log-hygiene` |
| Python package, profile, venv | `requirements-profile-selection` |
| CI impact, workflow, security scan | `workflow-impact-guard` |
| Docs vs runtime drift | `docs-drift-sync` |
| Which tests to run | `test-impact-mapper` |
| Bug, hard failure, silent error | `diagnose` |
| Building feature/fix test-first | `tdd` |
| Entering unfamiliar module | `zoom-out` |
| Uncertain which skill | `skills-dispatch-map` |

**How to use skills:**

1. Match the task to the table above. Most tasks need 1–2 skills.
2. Read the SKILL.md file **before** writing any code.
3. Follow the skill's checklist and monitor table — they list which files to verify.
4. After any behavior change, also read `docs-drift-sync` and `test-impact-mapper`.
5. For multi-domain tasks, load skills in the order given by `skills-dispatch-map`.

---

## Working style

### 1. Think Before Coding
Before implementing: state assumptions explicitly. If multiple interpretations exist, present them — don't pick silently. If something is unclear, stop, name what's confusing, and ask.

### 2. Simplicity First
Minimum code that solves the problem. No speculative features, abstractions for single-use code, or "configurability" that wasn't requested. Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
Trace the full path before editing: UI → route → router/provider/tool → response formatting → docs/tests. Touch only what's needed — don't "improve" adjacent code, comments, or formatting unrelated to the request. Every changed line must trace directly to the user's request. Treat response shapes and env loading as contracts.

### 4. Goal-Driven Execution
For multi-step tasks, state a brief plan with verifiable steps:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```
When behavior changes, update docs and identify verification steps. Always mention risks and affected workflows.

## Standard response shape

After making or proposing a change, summarize using:

- **Goal** — what was requested
- **Findings** — what was discovered
- **Files touched** — changed files
- **Risks** — what could break
- **Verification** — minimum steps to confirm
- **Doc updates** — which docs need syncing

---

## Repository truths (most important)

| Fact | Value |
|---|---|
| Default chatbot port | 5000 |
| Primary chat endpoint | `POST /chat/stream` (SSE) |
| Shared env file | `app/config/.env` or `app/config/.env_dev` |
| Shared env loader | `services/shared_env.py` — one call per service |
| Core venv | `venv-core` |
| Image venv | `venv-image` |
| Desktop wrapper | `desktop/electron/` (frameless, tray, single-instance) |
| Thinking modes | `instant`, `think`, `deep-think`, `multi-thinking` |
| Web search stack | SerpAPI (primary) → Google CSE (fallback) |
| Reverse image stack | Google Lens → Google Reverse → Yandex |
| Image gen providers | fal.ai FLUX + BFL/Black Forest Labs |
| Video gen provider | OpenAI Sora 2 (requires OPENAI_API_KEY) |
| MCP transport | stdio (FastMCP) |
| Flask streaming | SSE via `routes/stream.py` |
| FastAPI mode | Removed in May 2026; Flask monolith only |
| Hermes sidecar | HTTP at `HERMES_API_URL` (default 8080) — opt-in via `HERMES_ENABLED=true` |
| SAA sidecar | Electron app at port 51028 — opt-in via `CHARACTER_SELECT_ENABLED=true` |
| SAA data path | `app/character_select_stand_alone_app-main/data/` — read-only by `saa_character_db.py` |
| Reasoning pipeline | Local ComfyUI multi-panel — opt-in via `REASONING_PIPELINE=true` |
| Reasoning endpoint | `POST /api/reasoning-image-gen/generate` |
| Hermes endpoint | `POST /api/hermes/chat` |
| last30days endpoint | `POST /api/tools/last30days` — opt-in via `LAST30DAYS_ENABLED=true` |

## Sidecar services (opt-in)

| Sidecar | Default port | Enable flag | Entry point |
|---|---|---|---|
| Hermes Agent | 8080 | `HERMES_ENABLED=true` | `NousResearch/hermes-agent` — separate process |
| SAA character picker | 51028 | `CHARACTER_SELECT_ENABLED=true` | `app/character_select_stand_alone_app-main/` — `npm start` |

**Hermes ↔ Reasoning pipeline:** These are **separate, non-overlapping paths** by default. Hermes is a chat AI proxy. The reasoning pipeline is a ComfyUI-backed local image pipeline. A lightweight bridge exists in `core/image_intent.py` and is active only when **both** `HERMES_ENABLED=true` and `REASONING_PIPELINE=true`. When both flags are set, `POST /api/hermes/chat` runs `image_pipeline.reasoning.capability_router.classify()` before forwarding to Hermes; image-generation requests (confidence ≥ 0.75) are redirected to the reasoning pipeline transparently. The bridge fails-safe: if `image_pipeline` is not importable or classification fails, the request falls through to Hermes unchanged.
