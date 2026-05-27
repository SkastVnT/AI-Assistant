# Final Summary: last30days + Hermes Integration

> **Date**: 2026-04-14
> **Branch**: master
> **Status**: Ready for review and merge

---

## What was integrated

### 1. last30days â€” Social Media Research Tool

A subprocess-isolated wrapper around the [last30days-skill](https://github.com/mvanhorn/last30days-skill) CLI engine. Collects and synthesizes data from Reddit, X/Twitter, YouTube, TikTok, Hacker News, and other platforms.

**Access paths:**
- `/last30days <topic>` slash command in chat (SSE stream)
- `POST /api/tools/last30days` standalone API (JSON)
- Auto-routed via `social-research` skill (keyword detection)
- UI "Social Research" tool button

### 2. Hermes Agent â€” AI Sidecar Proxy

An HTTP proxy adapter to the [Hermes Agent](https://github.com/NousResearch/hermes-agent) sidecar service. Hermes runs as a separate process with its own venv to avoid dependency conflicts.

**Access paths:**
- `POST /api/hermes/chat` API endpoint (JSON)
- Flask + FastAPI parity

### 3. Infrastructure

- Root `docker-compose.yml` with profile-based service selection
- Dockerfile fix (port 5000, entrypoint `run.py`)
- Vendor setup scripts (Windows + Linux)
- Comprehensive env variable configuration

### 4. Quality

- 59 unit tests (mock-only, no network)
- Input validation and guardrails on all new endpoints
- Standardized `[TAG]` logging with elapsed time tracking
- Regression safety tests for existing functionality

---

## Changed files (grouped by module)

### Core modules (`services/chatbot/core/`)

| File | Lines | Change |
|---|---|---|
| `config.py` | +12 | Added `LAST30DAYS_*` and `HERMES_*` env vars |
| `last30days_tool.py` | 300 | **New** â€” subprocess wrapper + `parse_research_params()` |
| `hermes_adapter.py` | 158 | **New** â€” HTTP proxy to Hermes sidecar |
| `skills/builtins/social_research.yaml` | 40 | **New** â€” skill definition with 25+ trigger keywords |

### Flask routes (`services/chatbot/routes/`)

| File | Lines | Change |
|---|---|---|
| `stream.py` | +25 | `/last30days` command detection + tool dispatch (uses `parse_research_params`) |
| `last30days.py` | 76 | **New** â€” `POST /api/tools/last30days` blueprint |
| `hermes.py` | 47 | **New** â€” `POST /api/hermes/chat` blueprint |

### FastAPI routers (`services/chatbot/fastapi_app/`)

| File | Lines | Change |
|---|---|---|
| `__init__.py` | +4 | Registered last30days + hermes routers |
| `routers/last30days.py` | 79 | **New** â€” Pydantic-validated last30days endpoint |
| `routers/hermes.py` | 51 | **New** â€” Pydantic-validated hermes endpoint |

### Blueprint registration (`services/chatbot/chatbot_main.py`)

| Change | Pattern |
|---|---|
| +`last30days_bp` | `try/except ImportError` (existing convention) |
| +`hermes_bp` | `try/except ImportError` (existing convention) |

### UI (`services/chatbot/templates/` + `static/`)

| File | Change |
|---|---|
| `templates/index.html` | Added "Social Research" tool button |
| `static/js/modules/api-service.js` | Added `last30days-research` tool ID |

### Tests (`services/chatbot/tests/`)

| File | Tests | Coverage |
|---|---|---|
| `test_last30days.py` | 23 | Tool wrapper, route, output parser |
| `test_hermes.py` | 14 | Adapter, route |
| `test_regression_safety.py` | 22 | Core imports, routes, search tools, image gen, skills, env |

### Infrastructure (root)

| File | Change |
|---|---|
| `docker-compose.yml` | **New** â€” MongoDB + chatbot + last30days-setup + hermes + redis |
| `Dockerfile` | Fixed port 5001â†’5000, entrypoint app.pyâ†’run.py |

### Config / Env

| File | Change |
|---|---|
| `app/config/.env.example` | Added `LAST30DAYS_*` and `HERMES_*` variables |
| `services/chatbot/.env.example` | Added `LAST30DAYS_*` and `HERMES_*` variables |

### Vendor

| File | Change |
|---|---|
| `vendor/last30days/setup.ps1` | **New** â€” Windows clone script |
| `vendor/last30days/setup.sh` | **New** â€” Linux/macOS clone script |

### Documentation

| File | Change |
|---|---|
| `docs/integration_plan_hermes_last30days.md` | Master plan (Phase 1-2 âœ…, Phase 3 â³) |
| `docs/deployment_last30days_hermes.md` | Deployment, health checks, troubleshooting, rollback |
| `docs/release_checklist_last30days_hermes.md` | Pre-merge and post-merge checklists |
| `services/chatbot/docs/last30days_integration.md` | Service-level integration docs |
| `README.md` | Updated tools table, Docker section |

---

## How to run

```bash
# Activate venv
source venv-core/bin/activate  # Linux
.\venv-core\Scripts\Activate.ps1  # Windows

# Start chatbot (default Flask mode)
cd services/chatbot
python chatbot_main.py

# With Docker
docker compose up -d                      # Core only
docker compose --profile tools up -d      # + last30days setup
docker compose --profile hermes up -d     # + Hermes sidecar
```

### Enable last30days

```bash
# 1. Clone engine
cd services/chatbot/vendor/last30days && ./setup.sh

# 2. Set env
export LAST30DAYS_ENABLED=true
export LAST30DAYS_PYTHON_PATH=python3.12

# 3. Test
curl -X POST http://localhost:5000/api/tools/last30days \
  -H 'Content-Type: application/json' \
  -d '{"topic": "AI trends", "depth": "quick"}'
```

### Enable Hermes

```bash
# 1. Start Hermes sidecar on port 8080
# 2. Set env
export HERMES_ENABLED=true
export HERMES_API_URL=http://localhost:8080

# 3. Test
curl -X POST http://localhost:5000/api/hermes/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "hello"}'
```

---

## How to test

```bash
cd services/chatbot

# New tests only
pytest tests/test_last30days.py tests/test_hermes.py tests/test_regression_safety.py -v

# Full suite
pytest tests/ -v --tb=short
```

All 59 new tests use mocks â€” no network calls, no external dependencies.

---

## Major architectural decisions

| Decision | Rationale |
|---|---|
| **Subprocess isolation** for last30days | Avoids Python 3.12+ / Node.js dependency in venv-core |
| **Sidecar pattern** for Hermes | Hermes has ~100+ deps; HTTP proxy keeps venvs clean |
| **Feature flags default to `false`** | Zero impact on existing deployments until explicitly enabled |
| **Separate tool module** (not in `core/tools.py`) | Keeps the 300-line wrapper self-contained; `tools.py` stays for search tools |
| **`parse_research_params()` extracted** | Single source of truth for `--deep/--quick/--days/--sources` parsing (used by stream.py) |
| **Flask + FastAPI parity** | Both startup modes get identical endpoints |
| **try/except blueprint registration** | Follows existing pattern â€” graceful degradation if import fails |

---

## Known limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| last30days research can take 1-5 min | Blocks SSE stream during research | Use `depth=quick` for faster results |
| Hermes sidecar must be started separately | Extra operational step | Docker compose profile; future: auto-start |
| No caching of research results | Repeat queries re-run full research | Phase 3: MongoDB cache |
| No MCP tool exposure | Can't use last30days/Hermes via MCP | Phase 3: MCP tool registration |
| No Hermes SSE streaming proxy | Response is full JSON, not streamed | Phase 3: SSE pass-through |
| No `hermes-agent` skill YAML | Hermes not auto-routed by keyword | Phase 3: skill + stream.py dispatch |
| `HERMES_AUTO_START` not implemented | Referenced in plan but not coded | Removed from config; add in Phase 3 |

---

## Next steps (recommended PRs)

| PR | Priority | Description |
|---|---|---|
| **Phase 3a**: MongoDB cache | Medium | Cache last30days results by topic+depth+days hash |
| **Phase 3b**: MCP tools | Medium | Expose `last30days_research` and `hermes_chat` via `@mcp.tool()` |
| **Phase 3c**: Hermes skill | Low | `hermes_agent.yaml` skill + stream.py tool dispatch |
| **Phase 3d**: Hermes auto-start | Low | `run.py` auto-launches sidecar process |
| **Phase 3e**: SSE streaming proxy | Low | Pass Hermes SSE events through to client |
| **Phase 3f**: Context compression | Low | Extract Hermes context compression into chatbot core |
