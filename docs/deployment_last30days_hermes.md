# Deployment Guide: last30days + Hermes Agent

> **Scope**: Local development, Docker, and production deployment for the last30days social research tool and Hermes agent sidecar.
>
> **Audience**: Developers and operators of the AI-Assistant platform.
>
> **Prerequisites**: Git, Python 3.10+, Docker (optional), MongoDB.

---

## Table of Contents

1. [Service Matrix](#service-matrix)
2. [Environment Variables](#environment-variables)
3. [Local Development Setup](#local-development-setup)
4. [Docker Setup](#docker-setup)
5. [Health Checks](#health-checks)
6. [Common Failure Modes](#common-failure-modes)
7. [Rollback Procedures](#rollback-procedures)
8. [Architecture Notes](#architecture-notes)

---

## Service Matrix

| Service | Port | Profile | Required | Entry Point |
|---|---|---|---|---|
| ChatBot | 5000 | *(default)* | Yes | `services/chatbot/run.py` |
| MongoDB | 27017 | *(default)* | Yes | docker image `mongo:7` |
| last30days | — (subprocess) | `tools` | No | `vendor/last30days/repo/scripts/last30days.py` |
| Hermes Agent | 8080 | `hermes` | No | `vendor/hermes/repo/gateway/platforms/api_server.py` |
| Redis | 6379 | *(default)* | No (caching) | docker image `redis:7-alpine` |

**Important**: Image generation services (Stable Diffusion on 7861, ComfyUI on 8100) are separate and NOT included in this deployment. They require `venv-image` and optionally GPU access.

---

## Environment Variables

### Shared env (`app/config/.env`)

These variables are loaded by `services/shared_env.py` → `load_shared_env()` for all services.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LAST30DAYS_ENABLED` | No | `false` | Enable last30days tool in chatbot |
| `LAST30DAYS_SCRIPT_PATH` | No | auto-detect | Path to `last30days.py` script |
| `LAST30DAYS_PYTHON_PATH` | No | `python` | Python 3.12+ executable for last30days |
| `LAST30DAYS_TIMEOUT` | No | `180` | Subprocess timeout in seconds |
| `HERMES_ENABLED` | No | `false` | Enable Hermes agent proxy |
| `HERMES_API_URL` | No | `http://localhost:8080` | Hermes Gateway API base URL |
| `HERMES_API_KEY` | No | *(empty)* | API key for Hermes authentication |

### Service-local env (`services/chatbot/.env`)

These are loaded by `run.py` **without override** — they supplement shared env.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LAST30DAYS_ENABLED` | No | `false` | Override per-service (if not in shared env) |
| `HERMES_ENABLED` | No | `false` | Override per-service |

### last30days internal config

last30days reads its own config from `~/.config/last30days/.env` (or the repo's `.env`). The chatbot does NOT pass API keys to it — last30days manages its own credentials.

| Variable (last30days internal) | Description |
|---|---|
| `SCRAPECREATORS_API_KEY` | For Reddit, HN, etc. |
| `XAI_API_KEY` | For X/Twitter via Grok |
| `YOUTUBE_API_KEY` | YouTube Data API |
| `OPENAI_API_KEY` | For synthesis/embedding |

See [last30days configuration guide](https://github.com/mvanhorn/last30days-skill#configuration) for the full list.

---

## Local Development Setup

### Prerequisites

```bash
# Core chatbot
python --version    # 3.10+
git --version

# last30days (optional)
python3.12 --version   # or python3 --version showing 3.12+

# Hermes (optional)
python3 --version      # 3.10+
```

### Step 1 — Clone and activate venv

```bash
cd AI-Assistant
# Windows
.\venv-core\Scripts\activate
# Linux/macOS
source venv-core/bin/activate
```

### Step 2 — Configure environment

```bash
# Copy example env files
cp app/config/.env.example app/config/.env
cp services/chatbot/.env.example services/chatbot/.env

# Edit and fill in API keys
# At minimum: one LLM provider key + MONGODB_URI
```

### Step 3 — Start MongoDB

```bash
# Option A: system MongoDB
mongod --dbpath ./local_data

# Option B: Docker
docker run -d --name ai-mongo -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=changeme \
  mongo:7
```

### Step 4 — Start chatbot

```bash
cd services/chatbot

# Flask monolith
python run.py
```

Verify: `curl http://localhost:5000/health`

### Step 5 — Set up last30days (optional)

```powershell
# Windows
cd services/chatbot/vendor/last30days
.\setup.ps1

# Linux/macOS
cd services/chatbot/vendor/last30days
bash setup.sh
```

Configure:
```bash
# In app/config/.env
LAST30DAYS_ENABLED=true
LAST30DAYS_PYTHON_PATH=python3.12    # must be 3.12+
# LAST30DAYS_SCRIPT_PATH auto-detects if vendor/last30days/repo exists
```

Test standalone:
```bash
python3.12 vendor/last30days/repo/scripts/last30days.py "AI trends" --emit=compact --agent
```

### Step 6 — Set up Hermes Agent (optional)

```bash
# Clone Hermes
mkdir -p vendor/hermes
cd vendor/hermes
git clone https://github.com/NousResearch/hermes-agent.git repo

# Create venv (separate from venv-core!)
cd repo
python -m venv .venv
source .venv/bin/activate    # or .\.venv\Scripts\activate
pip install -r requirements.txt

# Start Gateway API
python -m gateway.platforms.api_server --port 8080
```

Configure:
```bash
# In app/config/.env
HERMES_ENABLED=true
HERMES_API_URL=http://localhost:8080
HERMES_API_KEY=your-secret-key
```

### Local startup commands (summary)

```bash
# Minimum (chatbot + mongo)
mongod --dbpath ./local_data &
cd services/chatbot && python run.py

# With last30days
LAST30DAYS_ENABLED=true python run.py

# With Hermes sidecar
cd vendor/hermes/repo && python -m gateway.platforms.api_server --port 8080 &
HERMES_ENABLED=true python run.py

# With everything
mongod --dbpath ./local_data &
cd vendor/hermes/repo && python -m gateway.platforms.api_server --port 8080 &
cd services/chatbot && LAST30DAYS_ENABLED=true HERMES_ENABLED=true python run.py
```

---

## Docker Setup

### Quick start (chatbot + MongoDB only)

```bash
# Configure env
cp app/config/.env.example app/config/.env
cp services/chatbot/.env.example services/chatbot/.env
# Edit both files with your API keys

# Start
docker compose up -d

# Verify
curl http://localhost:5000/health
```

### With last30days tool

```bash
docker compose --profile tools up -d
```

The `last30days-setup` container clones and configures the engine on first run. Set `LAST30DAYS_ENABLED=true` in `app/config/.env`.

### With Hermes Agent

```bash
# Prerequisite: Hermes Dockerfile must exist at vendor/hermes/Dockerfile
# See "Hermes Docker image" section below

docker compose --profile hermes up -d
```

### Everything

```bash
docker compose --profile all up -d
```

### Container names

| Container | Service | Required |
|---|---|---|
| `ai-assistant-mongodb` | MongoDB 7 | Yes |
| `ai-assistant-chatbot` | ChatBot (Flask) | Yes |
| `ai-assistant-redis` | Redis 7 | Optional (caching) |
| `ai-assistant-last30days-setup` | Engine clone (run-once) | Optional |
| `ai-assistant-hermes` | Hermes Gateway API | Optional |

### Hermes Docker image

Hermes does not ship a Dockerfile. Create one at `vendor/hermes/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
COPY repo/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY repo/ .
EXPOSE 8080
CMD ["python", "-m", "gateway.platforms.api_server", "--port", "8080"]
```

---

## Health Checks

### Chatbot

```bash
# Basic health
curl http://localhost:5000/health
# Expected: {"status": "ok", ...}

# Database connectivity
curl http://localhost:5000/api/health/databases
# Expected: {"mongodb": "connected", ...}

# Model availability
curl http://localhost:5000/api/models/health
```

### last30days

last30days runs as a subprocess — no persistent health endpoint. Verify via:

```bash
# Direct CLI test
python3.12 vendor/last30days/repo/scripts/last30days.py "test" --emit=compact --agent

# Via chatbot API
curl -X POST http://localhost:5000/api/tools/last30days \
  -H "Content-Type: application/json" \
  -d '{"topic": "test query"}'
# Expected: {"success": true, "result": "...", ...} or {"success": false, "error": "..."}
```

### Hermes Agent

```bash
curl http://localhost:8080/health
# Expected: 200 OK (when running)
```

### Docker health

```bash
docker compose ps
# All services should show "healthy" or "running"

docker compose logs chatbot --tail 20
docker compose logs mongodb --tail 20
```

---

## Common Failure Modes

### Chatbot won't start

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Wrong venv or missing deps | `pip install -r requirements.txt` in `venv-core` |
| `ConnectionRefusedError` on MongoDB | MongoDB not running | Start MongoDB first; check `MONGODB_URI` |
| Port 5000 in use | Another process on 5000 | Kill it or set `FLASK_PORT` to another port |
| `KeyError: 'OPENAI_API_KEY'` | Missing env | Check `app/config/.env` has required keys |

### last30days failures

| Symptom | Cause | Fix |
|---|---|---|
| `"❌ last30days tool is not enabled"` | `LAST30DAYS_ENABLED=false` | Set to `true` in env |
| `"❌ last30days script not found"` | Missing repo clone | Run `vendor/last30days/setup.ps1` or `setup.sh` |
| `subprocess.TimeoutExpired` | Research taking too long | Increase `LAST30DAYS_TIMEOUT` or use `depth=quick` |
| `"Python 3.12+ required"` | Wrong Python version | Set `LAST30DAYS_PYTHON_PATH` to a 3.12+ executable |
| Empty results | Missing last30days API keys | Configure `~/.config/last30days/.env` |
| X/Twitter source fails | Missing Node.js | Install Node.js 18+ for vendored Bird client |

### Hermes failures

| Symptom | Cause | Fix |
|---|---|---|
| `"Hermes agent is not enabled"` | `HERMES_ENABLED=false` | Set to `true` in env |
| `ConnectionError` to port 8080 | Hermes not running | Start Hermes sidecar manually or via compose |
| `401 Unauthorized` | Wrong API key | Match `HERMES_API_KEY` between chatbot and Hermes config |
| High memory usage | Hermes agent loops | Set `max_iterations` in Hermes config; monitor with `docker stats` |

### Docker-specific

| Symptom | Cause | Fix |
|---|---|---|
| `ai-assistant-chatbot` unhealthy | Can't reach MongoDB | Check `depends_on` and MongoDB health; `docker compose logs mongodb` |
| `ai-assistant-hermes` won't build | Missing `vendor/hermes/Dockerfile` | Create it per instructions above |
| Env vars not loaded | Missing `.env` files | Copy `.env.example` files and fill in values |
| Port conflict | Host port already bound | Change `CHATBOT_PORT` or `HERMES_PORT` in env |

---

## Rollback Procedures

### Disable last30days (no code change)

```bash
# In app/config/.env
LAST30DAYS_ENABLED=false
```

Restart chatbot. The tool button remains visible but returns an error message. No subprocess calls are made.

### Disable Hermes (no code change)

```bash
# In app/config/.env
HERMES_ENABLED=false
```

Restart chatbot. Hermes routes return 503. The sidecar can be stopped independently:

```bash
docker compose --profile hermes stop
# or kill the local process
```

### Full removal — last30days

1. Set `LAST30DAYS_ENABLED=false`
2. Remove `vendor/last30days/` directory
3. Remove files listed in [last30days integration doc](../services/chatbot/docs/last30days_integration.md#rollback)
4. Remove env vars from `.env` files

### Full removal — Hermes

1. Set `HERMES_ENABLED=false`
2. Remove `vendor/hermes/` directory
3. Remove `routes/hermes.py` (when created)
4. Remove blueprint registration from `chatbot_main.py`
5. Remove env vars from `.env` files

### Docker rollback

```bash
# Stop everything
docker compose --profile all down

# Remove volumes (destructive — loses data)
docker compose --profile all down -v

# Rebuild after code changes
docker compose build chatbot
docker compose up -d
```

---

## Architecture Notes

### Subprocess isolation (last30days)

last30days runs as a **separate Python process** because:
- It requires Python 3.12+ (chatbot venv may be 3.10/3.11)
- It has ~30 internal modules with independent dependencies
- Optional Node.js runtime for X/Twitter via vendored Bird client
- Clean failure boundary — subprocess errors don't crash the chatbot

```
chatbot (venv-core, Python 3.10+)
  └─ subprocess.run(["python3.12", "last30days.py", ...])
       └─ last30days (own deps, Python 3.12+)
            └─ optional: Node.js (Bird client for X)
```

### Sidecar pattern (Hermes)

Hermes runs as an **independent HTTP service** because:
- It has ~100+ package dependencies (would conflict with venv-core)
- It maintains its own SQLite sessions and state
- The Gateway API provides SSE streaming natively
- Independent scaling and lifecycle management

```
chatbot (port 5000)
  └─ HTTP proxy → Hermes Gateway API (port 8080)
                    └─ AIAgent → tools, memory, subagents
```

### What is NOT included

- **Stable Diffusion** (port 7861) — requires `venv-image` + GPU
- **Edit Image / ComfyUI** (port 8100) — requires `venv-image` + GPU
- **MCP Server** — uses stdio transport, runs alongside chatbot process
- **RAG subsystem** — has its own `rag/docker-compose.yml`

### Network topology (Docker)

```
┌─────────────────────────────────────────┐
│  docker compose network                 │
│                                         │
│  ┌──────────┐    ┌─────────────────┐    │
│  │ MongoDB  │◄───│    ChatBot      │    │    host:5000
│  │  :27017  │    │     :5000       │────┼──► http://localhost:5000
│  └──────────┘    └────────┬────────┘    │
│                           │             │
│  ┌──────────┐    ┌────────▼────────┐    │
│  │  Redis   │    │  Hermes (opt)   │    │    host:8080
│  │  :6379   │    │     :8080       │────┼──► http://localhost:8080
│  └──────────┘    └─────────────────┘    │
└─────────────────────────────────────────┘
```

---

## Related Documentation

- [last30days Integration](../services/chatbot/docs/last30days_integration.md) — detailed tool integration docs
- [Integration Plan](./integration_plan_hermes_last30days.md) — master plan with phases and risk matrix
- [Chatbot README](../services/chatbot/docs/README.md) — chatbot service documentation
- [Troubleshooting](../services/chatbot/docs/TROUBLESHOOTING.md) — general chatbot troubleshooting
