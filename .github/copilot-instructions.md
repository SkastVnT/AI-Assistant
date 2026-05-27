# GitHub Copilot Instructions — AI-Assistant

## Repository identity

Python microservices platform. Four active services: **ChatBot (5000)**, MCP Server (stdio), Stable Diffusion (7861), Edit Image/ComfyUI (8100). The chatbot is the primary development area. Image workflow services are functional and should not be touched for chatbot-only tasks.

## Default focus

Unless a task explicitly targets image generation, stable diffusion, or ComfyUI workflows, stay inside:

- `services/chatbot/`
- `services/shared_env.py`
- `services/mcp-server/`
- `app/config/`
- `app/src/`

Do **not** edit `ComfyUI/`, `app/image_pipeline/`, `services/stable-diffusion/`, or `services/edit-image/` for chatbot tasks.

## Entry points

| Service | Port | Entry point |
|---|---|---|
| ChatBot (Flask default) | 5000 | `services/chatbot/chatbot_main.py` |
| ChatBot (all modes) | 5000 | `services/chatbot/run.py` |
| MCP Server | stdio | `services/mcp-server/server.py` |
| Stable Diffusion | 7861 | `services/stable-diffusion/` |
| Edit Image | 8100 | `services/edit-image/` |

Chatbot startup:
- `python services/chatbot/run.py` → Flask monolith on port 5000 (the only supported mode since May 2026; `USE_FASTAPI` / `USE_NEW_STRUCTURE` were removed).
- `cd app/electron && npm run dev` → Frameless Electron desktop (tray, single-instance, auto-spawns backend).

## Environment loading contract

**One loader, one call per service.** `services/shared_env.py` → `load_shared_env(__file__)`.

- Loads `app/config/.env_{env}` (env defaults to `dev`) or falls back to `app/config/.env`.
- Never add a second `load_dotenv` call that overrides shared env values in any service file.
- `run.py` additionally loads `services/chatbot/.env` without override for chatbot-local keys.

## Chatbot architecture

```
routes/stream.py        PRIMARY: SSE endpoint POST /chat/stream
routes/main.py          /, /chat, /clear, /history, /api/generate-title
routes/image_gen.py     /api/image-gen/* — multi-provider image gen
routes/stable_diffusion.py  SD proxy routes
routes/skills.py        /api/skills/* — runtime skill CRUD + session activation
routes/characters.py    /api/characters/* — character registry + SAA augment
routes/character_select.py  /api/character-select/* + /api/local-image-gen/*
routes/jobs.py          /api/jobs/* — local image job queue
routes/anime_pipeline.py    /api/anime-pipeline/* — 7-agent ComfyUI pipeline
routes/reasoning_image_gen.py  /api/reasoning-image-gen/* — multi-panel pipeline (REASONING_PIPELINE=true)
routes/hermes.py        /api/hermes/chat — Hermes sidecar proxy (HERMES_ENABLED=true)
routes/last30days.py    /api/tools/last30days — social research (LAST30DAYS_ENABLED=true)
core/chatbot.py         ChatbotAgent v1 — if/elif model routing
core/chatbot_v2.py      ChatbotAgent v2 — ModelRegistry-based
core/tools.py           Tool functions: web search, reverse image, SauceNAO
core/config.py          All API keys and configuration constants
core/thinking_generator.py  Thinking modes + ThinkTagParser
core/stream_contract.py SSE complete-event payload builder
core/agentic/           Multi-thinking pipeline (4-agent council)
core/image_gen/         Multi-provider image gen router
core/character_registry.py  CharacterRegistry singleton — searchable alias-aware DB
core/character_select_adapter.py  HTTP probe to SAA sidecar (CHARACTER_SELECT_ENABLED)
core/job_queue.py       JobQueue singleton — local image job lifecycle
core/hermes_adapter.py  HTTP proxy to Hermes Agent sidecar (HERMES_ENABLED)
config/                 Service-level MongoDB config, model presets, features.json
database/               Repository pattern DB access, query caching
src/handlers/           Multimodal handler, advanced image gen handler
src/utils/              Utility modules (imgbb, SD client, MCP integration)
src/rag/                RAG subsystem (ingest, embeddings, retrieval)
app/                    Nested Flask modular helper (services + middleware only)
app/electron/           Frameless Electron desktop wrapper (tray, IPC, single-instance)
```

**Warning — two config layers:** `core/config.py` (API keys from env) vs `config/mongodb_config.py` + `config/mongodb_helpers.py` (MongoDB setup, imported by `chatbot_main.py` via importlib). Do not confuse `services/chatbot/config/` with `app/config/`.

The parallel FastAPI implementation (`fastapi_app/`) and the auth/admin/qr_payment blueprints were removed in May 2026 (Electron overhaul Phase 1). The Flask SSE path (`routes/stream.py`) is now the single canonical entry. Do not re-introduce a parallel framework; raise it as a separate task.

## MCP server

- Transport: `stdio` (FastMCP). Not HTTP. Port 8000 in some older docs is a legacy artifact.
- Active server: `services/mcp-server/server.py`.
- Tools: `services/mcp-server/tools/advanced_tools.py`.

## Dependency profiles

- `venv-core` + `app/requirements/profile_core_services.txt` → chatbot, MCP server.
- `venv-image` + `app/requirements/profile_image_ai_services.txt` → image/video services.

Never install image-ai packages into `venv-core` and vice versa.

## Tests and CI

- Run chatbot tests: `cd services/chatbot && pytest tests/ -v` (activate `venv-core`).
- CI lint scope: `services/ app/src/` — ComfyUI, private, venv excluded.
- Workflow files: `.github/workflows/tests.yml`, `ci-cd.yml`, `security-scan.yml`.

## Doc-sync rule

After changing **ports, entry points, runtime commands, or env variable names**, update `README.md` service table and any affected script READMEs. The main `README.md` is authoritative where script docs conflict.

## Known inconsistencies (do not propagate)

- `app/scripts/README.md` lists Stable Diffusion on 7860 and Edit Image on 7861 — both are wrong. Correct ports: SD=7861, Edit Image=8100.
- `speech2text` (5001) and `text2sql` (5002) are in archived scripts only; these services no longer exist in `services/`.
- MCP port 8000 in `app/scripts/README.md` is stale; server uses stdio.

## Search tool cascade (do not break)

Web search: SerpAPI (Google/Bing/Baidu) → Google CSE fallback.  
Reverse image: Google Lens → Google Reverse Image → Yandex.  
Auto-trigger: activated when query contains real-time keywords (price, weather, news, etc.).

## Working style

### Think Before Coding
Before implementing: state assumptions explicitly. If multiple interpretations exist, present them — don't pick silently. If something is unclear, stop, name what's confusing, and ask.

### Simplicity First
Minimum code that solves the problem. No speculative features, abstractions for single-use code, or "configurability" that wasn't requested.

### Surgical Changes
For chatbot tasks, trace the real request path before editing:
1. UI / assets / templates
2. Flask/FastAPI route entry point
3. Core router / provider / tool code
4. Response formatting
5. Docs / tests / workflows

Touch only what's needed. Every changed line must trace directly to the user's request. Prefer minimal, reversible edits.

### Goal-Driven Execution
For multi-step tasks, state a plan with verifiable steps:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```
Include verification steps. Note likely impacted workflows.

## Skill system

This repository has 16 skills in `.github/skills/`. **Before starting work, read the matching skill file at `.github/skills/{name}/SKILL.md`.** Skills contain file monitors, checklists, and rules — not just descriptions.

| Task category | Read this skill first |
|---|---|
| Routing / streaming | `core-chatbot-routing-audit` |
| Env / config | `shared-env-contract` |
| Provider / model | `provider-env-matrix` |
| Search / reverse image | `search-tool-cascade` |
| MCP tools | `mcp-tool-authoring` |
| Thinking modes | `thinking-mode-routing` |
| Response shapes | `tool-response-contract` |
| UI wiring | `chat-ui-sync` |
| Logging / errors | `observability-log-hygiene` |
| Dependencies | `requirements-profile-selection` |
| CI / workflows | `workflow-impact-guard` |
| Startup / health | `service-health-check-audit` |
| Docs drift | `docs-drift-sync` |
| Test scope | `test-impact-mapper` |
| Character picker, job queue, SAA | `character-picker-integration` |
| Reasoning pipeline, anime pipeline | `character-picker-integration` + `core-chatbot-routing-audit` |
| Bug, hard failure, silent error | `diagnose` |
| Building feature/fix test-first | `tdd` |
| Entering unfamiliar module | `zoom-out` |
| Uncertain | `skills-dispatch-map` |

**Mandatory secondary skills:** After any behavior change, also read `docs-drift-sync` and `test-impact-mapper`. For cross-cutting changes, combine skills in the order listed by `skills-dispatch-map`.

## What Copilot must not do

- Do not hardcode API keys, ports, or file paths. Read from env.
- Do not touch image pipeline or ComfyUI for chatbot-only tasks.
- Do not add a `load_dotenv` call that overrides the shared env loader.
- Do not add HTTP transport to the MCP server.
- Do not merge the Flask SSE path with any other framework. The previous parallel FastAPI implementation was removed; do not re-introduce one.
- Do not update only code without updating docs when runtime behavior changes.
- Do not bypass the Hermes↔Reasoning bridge contract: `core/image_intent.py` is the single import boundary between chatbot code and `image_pipeline.reasoning`. Do not add additional direct imports of `image_pipeline` anywhere else in `services/chatbot/`.
