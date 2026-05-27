# Chatbot Service Architecture â€” P1 Snapshot

This document captures the canonical state of the chatbot service after the
P1 roadmap wave.  It is the authoritative reference for new contributors.

---

## Entry points

| Surface | Command | Notes |
|---|---|---|
| Browser | `python services/chatbot/run.py` | Flask monolith on port 5000 |
| Desktop | `cd app/electron && npm run dev` | Frameless Electron, auto-spawns backend |

---

## Application factory

```
services/chatbot/app_factory.py   â† canonical create_app() â€” NEW (P1.5)
services/chatbot/app/__init__.py  â† legacy compat shim (delegates to app_factory)
services/chatbot/chatbot_main.py  â† Flask monolith (owns all routes + blueprints)
```

`app_factory.create_app()` is the single stable import boundary. Tests,
tooling, and the Electron desktop all go through this entry point.

---

## Environment loading

```
services/shared_env.py â†’ load_shared_env(__file__)
```

Called **once** per process in `chatbot_main.py` (and fallback-called in
`core/config.py` for standalone script usage). Never add a second
`load_dotenv()` call that overrides the shared env.

`run.py` additionally loads `services/chatbot/.env` **without override** for
chatbot-local keys (FAL_API_KEY, STEPFUN_API_KEY, etc.).

---

## Configuration

| Module | Purpose |
|---|---|
| `core/config.py` | Global constants from env vars â€” primary config |
| `core/settings.py` | Typed `Settings` dataclass â€” new preferred import path (P1.6) |
| `config/mongodb_config.py` | MongoDB client setup and collection helpers |
| `config/features.json` | Feature flag defaults |

For new code, prefer `from core.settings import settings` over importing
individual constants from `core.config`.

---

## Route surface

See [docs/route-contract.md](route-contract.md) for the complete route table.

Summary:
- **70+ inline routes** on `app` defined in `chatbot_main.py`
- **20 blueprints** registered at the bottom of `chatbot_main.py`
- **Primary SSE endpoint**: `POST /chat/stream` (stream_bp â†’ routes/stream.py)
- **Route contract test**: `tests/test_route_contract.py`

Blueprint inventory is in `routes/__init__.py::REGISTERED_BLUEPRINTS`.

---

## MongoDB persistence

```
core/mongo_store.py   â† fail-safe wrapper, all save/update ops
core/settings.py      â† provider keys (no mongo URI here)
config/mongodb_config.py â† client setup, collection references
```

New in P1.7:
- `mongo_store.health_check()` â€” ping-based health dict, used by `/api/db-health`
- `mongodb_config.py` now explains why `load_shared_env()` is kept even though it's a no-op in normal startup

---

## Testing

```
cd services/chatbot
pytest tests/ -v -m "not integration and not image and not rag and not hermes and not mongo and not slow and not agentic"
```

Or use the shortcut gate:
```powershell
app/scripts/verify-local.ps1
```

Key test files:
- `tests/test_p0_trust_boundary.py` â€” P0 security boundary
- `tests/test_mcp_guard.py` â€” MCP path-traversal guard
- `tests/test_route_contract.py` â€” Route existence regression (P1.4)
- `tests/conftest.py` â€” Fixtures (uses `app_factory.create_app()` via `app/__init__.py`)

---

## Sidecar services (opt-in)

| Sidecar | Port | Flag |
|---|---|---|
| Hermes Agent | 8080 | `HERMES_ENABLED=true` |
| SAA character picker | 51028 | `CHARACTER_SELECT_ENABLED=true` |

Both are disabled by default. The chatbot degrades gracefully when they are unreachable.

---

## Dependency profiles

| Profile | venv | Requirements |
|---|---|---|
| Core (chatbot + MCP) | `venv-core` | `app/requirements/profile_core_services.txt` |
| Image AI | `venv-image` | `app/requirements/profile_image_ai_services.txt` |

Never install image packages into `venv-core`.

---

## Docker

Build context is the **repo root** (not the service subdirectory):

```bash
docker compose build chatbot
docker compose up chatbot
```

The Dockerfile at `services/chatbot/Dockerfile` uses `python:3.11-slim` and
runs as a non-root user (`appuser`, uid 1000).

See [docs/DEPLOYMENT.md](DEPLOYMENT.md) for the full deployment guide.

---

## CI

Workflows: `.github/workflows/tests.yml`, `ci-cd.yml`, `security-scan.yml`

Gates:
1. **P0 gate** â€” `test_p0_trust_boundary.py + test_mcp_guard.py` run first, block on failure
2. **Default gate** â€” all tests excluding the marker-excluded set
3. **Electron test** â€” `npm test` in `app/electron/` (payload-filter + preload-contract)
4. **Security scan** â€” bandit (severity HIGH), pip-audit against `profile_core_services.txt`

Python version: **3.11** across all CI jobs.
