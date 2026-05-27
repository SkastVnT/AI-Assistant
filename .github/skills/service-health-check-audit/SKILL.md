---
name: service-health-check-audit
description: "Debug startup failures, port drift, and service health for the core chatbot stack. Use when: a service fails to start, a health check returns unexpected results, ports or entry points are mismatched across scripts and docs, dependency profiles need verification, Docker or CI startup assumptions need checking, or runtime behavior no longer matches documentation."
---

# Service Health Check Audit

## When to use this skill

- A chatbot or MCP service fails to start or returns errors on health endpoints.
- Port numbers, entry points, or startup commands appear inconsistent across files.
- A change to startup behavior needs verification against scripts, Docker, and CI.
- You suspect a dependency profile mismatch (`venv-core` vs `venv-image`).
- You need to reconcile docs with actual runtime behavior.
- A health check script reports a service down when it should be running (or vice versa).

Do **not** use this skill for ComfyUI, Stable Diffusion, or image pipeline issues unless the failing path actually reaches those services.

---

## Canonical service facts

| Service | Port | Entry point | Health endpoint | venv | Transport |
|---|---|---|---|---|---|
| ChatBot | **5000** | `services/chatbot/run.py` or `chatbot_main.py` | `GET /health` | `venv-core` | HTTP |
| MCP Server | **stdio** | `services/mcp-server/server.py` | *(none â€” stdio)* | `venv-core` | stdio |
| Stable Diffusion | **7861** | `services/stable-diffusion/` | `GET /sdapi/v1/options` | `venv-image` | HTTP |
| Edit Image | **8100** | `services/edit-image/` | varies | `venv-image` | HTTP |

**Known stale references** (do not trust):

| Source | Claims | Actual |
|---|---|---|
| `app/scripts/README.md` | SD = 7860, Edit = 7861 | SD = 7861, Edit = 8100 |
| `app/scripts/health-check-all.sh` | MCP = 8000 (HTTP) | MCP = stdio (no port) |
| `app/scripts/start-mcp-server.sh` | MCP = 8000 (HTTP) | MCP = stdio |
| `app/config/config.yml` | MCP = 8000, ComfyUI = 8189 | MCP = stdio, ComfyUI = 8188 |
| Various scripts | `speech2text` (5001), `text2sql` (5002) | Archived â€” no longer in `services/` |

**Authoritative source for ports**: `README.md` service table.

---

## Chatbot startup modes

| Env flag | Mode | Entry | Port env var |
|---|---|---|---|
| *(none)* | Flask monolith | `run.py` or `chatbot_main.py` | `FLASK_PORT` / `CHATBOT_PORT` (default 5000) |

Note: `run.py` is the canonical dispatcher and starts the Flask monolith only.

---

## Health check endpoints (chatbot)

| Endpoint | Location | Purpose |
|---|---|---|
| `GET /health` | `chatbot_main.py` or `app/main.py` | Basic liveness |
| `GET /api/v1/health` | `chatbot_main.py` | External API health |
| `GET /api/db-health` | `app/routes/legacy_routes.py` | MongoDB + collection counts |
| `GET /api/sd-health` | `chatbot_main.py` | Stable Diffusion reachability |
| `GET /api/health/databases` | `routes/main.py` | MongoDB/Redis status |

Docker healthcheck uses: `curl -f http://localhost:5000/health`

---

## Startup debug sequence

When a service fails to start, follow this sequence exactly. Do not skip steps.

### Step 1 â€” Verify the environment

```
Check                                   How
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Python version                          python --version (expect 3.10+)
Active venv                             which python / where python
Correct venv for service                venv-core for chatbot/MCP, venv-image for SD/edit
Required packages installed             pip list | grep flask (or mcp, etc.)
Shared env file exists                  ls app/config/.env or .env_dev
Startup env vars set                    echo $FLASK_PORT, echo $CHATBOT_PORT
```

### Step 2 â€” Verify the entry point

```
Check                                   How
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Entry file exists                       ls services/chatbot/run.py
Entry file is syntactically valid       python -m py_compile services/chatbot/run.py
Shared env import works                 python -c "from services.shared_env import load_shared_env"
Core config imports cleanly             cd services/chatbot && python -c "from core.config import *"
```

### Step 3 â€” Attempt a controlled start

```
# Local (Flask monolith)
cd services/chatbot && python chatbot_main.py

# Docker
docker-compose -f app/config/docker-compose.yml up chatbot
```

Watch for:
- `ImportError` / `ModuleNotFoundError` â†’ wrong venv or missing package.
- `Address already in use` â†’ port 5000 already occupied.
- `KeyError` or missing env var â†’ shared env not loaded or variable missing from `.env`.
- `ConnectionRefusedError` to MongoDB/Redis â†’ database not running.

### Step 4 â€” Verify health

```
# HTTP health check
curl http://localhost:5000/health

# Database health
curl http://localhost:5000/api/db-health

# Expected healthy response
{"status": "healthy", "service": "chatbot"}
```

### Step 5 â€” Report findings

Use the output format below.

---

## MCP server health check

The MCP server uses **stdio**, not HTTP. It has no port and no `/health` endpoint.

### Verify MCP

```
# Check the module imports cleanly
cd services/mcp-server && python -c "from server import mcp; print('OK')"

# Check FastMCP is installed
pip show mcp

# Run interactively (stdio â€” will wait for input)
cd services/mcp-server && python server.py
```

If scripts or docs reference MCP on port 8000, that is stale. Do not add HTTP listeners.

---

## Docker health check sequence

```
# Start stack
docker-compose -f app/config/docker-compose.yml up -d

# Check container status
docker-compose -f app/config/docker-compose.yml ps

# Check chatbot health
docker exec ai-chatbot curl -f http://localhost:5000/health

# Check logs for startup errors
docker-compose -f app/config/docker-compose.yml logs chatbot --tail 50

# Verify depends_on services
docker-compose -f app/config/docker-compose.yml logs mongodb --tail 20
docker-compose -f app/config/docker-compose.yml logs redis --tail 20
```

Docker healthcheck config (from `docker-compose.yml`):
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

---

## CI / workflow considerations

When changing startup behavior, verify these workflow files still work:

| Workflow | File | What it does |
|---|---|---|
| Tests | `.github/workflows/tests.yml` | `pytest tests/ -v` in `./services/chatbot` with `TESTING=True`, `MONGODB_ENABLED=False` |
| CI/CD | `.github/workflows/ci-cd.yml` | Lint (`services/ app/src/`), then same test job |
| Security | `.github/workflows/security-scan.yml` | CodeQL + dependency review |

**CI assumptions to preserve**:
- Working directory: `./services/chatbot`
- Python version: 3.10
- Dependencies: `tests/requirements-test.txt` + `requirements.txt`
- `TESTING=True` disables live service connections
- `MONGODB_ENABLED=False` uses mocks instead of real DB
- No actual service startup â€” tests run against imported modules

**If you change any of these, update the workflow file**:
- Entry point file name or location
- `requirements.txt` path or name
- Test directory path
- Env vars the test suite checks

---

## Where ports are defined (drift risk map)

Port 5000 (chatbot) appears in **20+ files**. When changing the chatbot port, all of these must be updated:

| Category | Files |
|---|---|
| Runtime | `chatbot_main.py`, `run.py` (reads `CHATBOT_PORT` / `FLASK_PORT`) |
| Config | `app/config/.env`, `app/config/.env.example`, `app/config/config.yml`, `app/config/model_config.py` |
| Docker | `app/config/docker-compose.yml`, `docker-compose.light.yml` |
| Scripts | `app/scripts/start-chatbot.bat`, `start-chatbot.sh`, `start-all.bat`, `start-core-services-parallel.bat`, `expose-public.bat`, `expose-public.sh`, `deploy_public.py` |
| Health checks | `app/scripts/health_check.py`, `health-check-all.sh`, `health-check-all.bat` |
| Docs | `README.md` service table |
| Tunnel | `app/config/public_urls.py` |

This is why ports must not be hardcoded in new code. Read from env: `int(os.getenv('CHATBOT_PORT', '5000'))`.

---

## Dependency profile verification

```
# Check chatbot deps (venv-core)
venv-core/Scripts/python -m pip check

# Check for image-ai leakage into core
venv-core/Scripts/pip list | findstr /i "torch diffusers transformers"
# Should return nothing â€” these belong in venv-image

# Check profile file exists
ls app/requirements/profile_core_services.txt
ls app/requirements/profile_image_ai_services.txt
```

---

## Docs-sync reminder

After resolving any startup or health issue, check:

- [ ] `README.md` service table â€” ports, entry points, and commands still match reality.
- [ ] `app/scripts/README.md` â€” if you touched a script, update the script docs.
- [ ] `app/config/config.yml` â€” if ports changed, update the YAML.
- [ ] `app/config/model_config.py` â€” `ServiceConfig` port values match.
- [ ] Docker healthcheck URLs â€” if the health endpoint path changed.

**Main `README.md` is authoritative.** If `app/scripts/README.md` conflicts, `README.md` wins.

---

## Do not touch unless the failing path reaches them

- `ComfyUI/` and `app/ComfyUI/` â€” external dependency subtree.
- `app/image_pipeline/` â€” image pipeline internals.
- `services/stable-diffusion/` â€” unless SD is the actual failing service.
- `services/edit-image/` â€” unless edit-image is the actual failing service.
- `venv-core/` or `venv-image/` â€” generated, never edit manually.

---

## Required output format

After every health check or startup debug session, report:

1. **Observed behavior** â€” what actually happened (error message, HTTP status, log output).
2. **Expected behavior** â€” what should have happened instead.
3. **Root cause guess** â€” most likely explanation, with supporting evidence.
4. **Files affected** â€” which files contribute to the problem.
5. **Fix applied** â€” what was changed (if anything).
6. **Next verification step** â€” how to confirm the fix works.
7. **Docs impact** â€” whether any docs need updating after the fix.

---

## Pre-fix checklist

Before applying a fix to a startup or health issue:

- [ ] Confirmed the Flask monolith startup path is being used.
- [ ] Confirmed which venv is active (`venv-core` for chatbot/MCP).
- [ ] Confirmed the shared env file loads successfully.
- [ ] Checked whether the issue reproduces in Docker, local scripts, or both.
- [ ] Verified the fix does not change behavior for unaffected startup modes.

## Post-fix checklist

After applying a fix:

- [ ] The service starts without errors in the affected mode.
- [ ] `GET /health` returns `{"status": "healthy"}`.
- [ ] `pytest services/chatbot/tests/ -v` passes.
- [ ] If a port or entry point changed: all files in the drift risk map above are updated.
- [ ] If a startup env var changed: `.env.example` and `README.md` are updated.
- [ ] If a workflow assumption changed: the `.github/workflows/` files are updated.
- [ ] No image-pipeline or ComfyUI files were modified for a chatbot-only fix.
