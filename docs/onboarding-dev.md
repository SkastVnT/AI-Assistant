# Developer Onboarding Guide

Step-by-step setup for new contributors to the AI-Assistant chatbot stack.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | **3.11.9** | Pinned in `.python-version` at repo root and per-service. Do NOT use 3.10 or 3.12. |
| Git | 2.40+ | Standard |
| Node.js | 20 LTS | Required only for Electron desktop wrapper (`desktop/electron/`) |
| npm | 10+ | Comes with Node.js 20 |

Confirm Python version:
```powershell
python --version    # must print Python 3.11.9
```

If you manage multiple Python versions, use `pyenv-win` (Windows) or `pyenv` (Linux/macOS):
```powershell
pyenv install 3.11.9
pyenv global 3.11.9
```

---

## Clone and initial setup

```powershell
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

---

## Two-venv model

This project uses **two isolated virtual environments**. Do NOT mix them.

| venv | Purpose | Requirements file |
|---|---|---|
| `venv-core` | Chatbot + MCP server | `app/requirements/profile_core_services.txt` |
| `venv-image` | Stable Diffusion + ComfyUI | `app/requirements/profile_image_ai_services.txt` |

For chatbot-only work, you only need `venv-core`.

---

## Setting up venv-core (chatbot + MCP)

```powershell
python -m venv venv-core
venv-core\Scripts\activate               # Windows
# source venv-core/bin/activate          # Linux/macOS

pip install --upgrade pip
pip install -r app/requirements/profile_core_services.txt
pip install -r services/chatbot/tests/requirements-test.txt
```

> Do NOT run `pip install -r requirements.txt` (root) — that file is a legacy reference that
> includes the full RAG + Firebase + torch stack. Always use the profile files.

---

## Setting up venv-image (image services — optional)

Only needed when working on Stable Diffusion or ComfyUI integrations:

```powershell
python -m venv venv-image
venv-image\Scripts\activate

pip install --upgrade pip
pip install -r app/requirements/profile_image_ai_services.txt
```

---

## Environment config

```powershell
# Copy the example and fill in at least one LLM API key
Copy-Item app\config\.env.example app\config\.env
notepad app\config\.env
```

Minimum required key to start: any one of `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROK_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY_1`.

The env loader (`services/shared_env.py`) looks for `app/config/.env_dev` first, then falls back to `app/config/.env`. You don't need to rename the file.

---

## Running the chatbot (browser mode)

```powershell
# Terminal 1 — activate venv-core
venv-core\Scripts\activate
cd services\chatbot
python run.py
# → http://127.0.0.1:5000
```

---

## Running the desktop wrapper (Electron)

```powershell
# Terminal 1 — activate venv-core, start backend
venv-core\Scripts\activate
cd services\chatbot
python run.py

# Terminal 2 — start Electron
cd desktop\electron
npm install
npm run dev
```

The Electron wrapper auto-spawns the backend unless it's already running. In production/dev mode the window is frameless with a system tray icon.

---

## Running tests

```powershell
# Default gate — runs only fast, offline tests
venv-core\Scripts\activate
cd services\chatbot
..\..\venv-core\Scripts\python.exe -m pytest tests/ `
  -m "not integration and not image and not rag and not hermes and not mongo and not slow and not agentic" `
  -q --no-header --tb=line
```

Or use the convenience script from the repo root:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-local.ps1
```

Expected output: all tests pass, no failures. **Run this before every commit.**

### Marker reference

| Marker | What it skips |
|---|---|
| `integration` | Tests that call live external services |
| `mongo` | Tests that require a running MongoDB |
| `rag` | RAG subsystem tests (needs MongoDB + embeddings) |
| `hermes` | Tests that require Hermes sidecar |
| `image` | Image generation tests |
| `slow` | Tests that take >10s |
| `agentic` | Async multi-agent tests (require `pytest-asyncio`) |

---

## Branch and commit conventions

| Branch prefix | Use for |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `refactor/` | Refactoring without behavior change |
| `docs/` | Documentation-only changes |
| `chore/` | Dependency bumps, CI changes |

Commit message format: `<type>(<scope>): <short description>`

Example: `feat(stream): add conversation_id to SSE complete payload`

---

## Architecture quick reference

- Primary chat endpoint: `POST /chat/stream` (SSE) in `services/chatbot/routes/stream.py`
- Flask monolith entry: `services/chatbot/chatbot_main.py` (started via `run.py`)
- API keys and constants: `services/chatbot/core/config.py` (reads from env — never hardcode)
- MongoDB setup: `services/chatbot/config/mongodb_config.py` (separate from `core/config.py`)
- Env loader: `services/shared_env.py` → call `load_shared_env(__file__)` once per service

Full architecture: [AGENTS.md](../AGENTS.md)

---

## Common issues

### `ModuleNotFoundError` at startup
You're using the wrong venv or haven't installed dependencies.
```powershell
venv-core\Scripts\activate
pip install -r app/requirements/profile_core_services.txt
```

### Tests fail with `AttributeError: module 'pytest' has no attribute 'mark.asyncio'`
`pytest-asyncio` is not installed. Those tests are marked `agentic` and excluded from the default gate — you don't need them for normal development.

### Port 5000 already in use
```powershell
netstat -ano | findstr :5000
taskkill /F /PID <pid>
```

### `FLASK_SECRET_KEY` error in production
Set `FLASK_SECRET_KEY` in `app/config/.env`. In `env=dev` an ephemeral key is generated automatically.

### MongoDB connection errors
The chatbot runs without MongoDB in `MONGODB_ENABLED=False` mode (tests use this). For local development with MongoDB:
```powershell
docker compose up -d mongodb
```
