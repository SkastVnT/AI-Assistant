# last30days Integration — AI-Assistant Chatbot

## Overview

The [last30days-skill](https://github.com/mvanhorn/last30days-skill) engine is integrated as a **subprocess-isolated tool** for multi-platform social media research. It collects and synthesizes data from Reddit, X/Twitter, YouTube, TikTok, Hacker News, and other sources.

## Architecture

### Three access paths

```
Path 1 — SSE streaming (primary chat):
  User → POST /chat/stream (message + tool "last30days-research")
    → command detection: /last30days <topic> → auto-add tool
    → skill auto-route: "social-research" (keyword match)
    → tool dispatch: "last30days-research"
    → core/last30days_tool.py::run_last30days_research()
    → append results to message context → LLM synthesizes → SSE

Path 2 — Standalone API (Flask):
  Client → POST /api/tools/last30days { topic, depth?, days?, sources? }
    → routes/last30days.py → run_last30days_research()
    → JSON { success, result, metadata, error }

Path 3 — Standalone API (FastAPI):
  Client → POST /api/tools/last30days { topic, depth?, days?, sources? }
    → fastapi_app/routers/last30days.py → run_last30days_research()
    → JSON { success, result, metadata, error }
```

**Subprocess boundary**: last30days runs in a separate Python process because it requires Python 3.12+ and optional Node.js (for X/Twitter via vendored Bird client). This avoids dependency conflicts with `venv-core`.

## Files

| File | Purpose |
|---|---|
| `vendor/last30days/setup.ps1` | Clone the last30days repo (Windows) |
| `vendor/last30days/setup.sh` | Clone the last30days repo (Linux/macOS) |
| `vendor/last30days/repo/` | Cloned engine (git-ignored) |
| `core/last30days_tool.py` | Subprocess wrapper — `run_last30days_research()` |
| `routes/last30days.py` | Flask blueprint — `POST /api/tools/last30days` |
| `fastapi_app/routers/last30days.py` | FastAPI router — `POST /api/tools/last30days` |
| `core/config.py` | `LAST30DAYS_*` env vars |
| `core/skills/builtins/social_research.yaml` | Skill definition with trigger keywords |
| `routes/stream.py` | Tool dispatch case (`last30days-research`) |

## Setup

### 1. Clone the engine

```powershell
cd services/chatbot/vendor/last30days
.\setup.ps1
```

### 2. Configure environment

Add to `app/config/.env` (or `.env_dev`):

```env
LAST30DAYS_ENABLED=true
LAST30DAYS_PYTHON_PATH=python    # or path to Python 3.12+ exe
LAST30DAYS_SCRIPT_PATH=          # auto-detected from vendor dir
LAST30DAYS_TIMEOUT=180           # seconds
```

### 3. Configure last30days API keys

Follow the [last30days configuration guide](https://github.com/mvanhorn/last30days-skill#configuration) to set up `~/.config/last30days/.env` with per-source API keys.

### 4. Verify

1. Test CLI: `python vendor/last30days/repo/scripts/last30days.py "AI trends" --emit=compact --agent`
2. Start chatbot: `python run.py`
3. Send message with tool `last30days-research` or type a trigger phrase like "what people think about..."

## Usage

### Explicit tool selection (UI button)

Click the **"Social Research"** tool button in the tools dropdown, or include `last30days-research` in the tools array:

```json
{
  "message": "What do people think about Claude 4?",
  "tools": ["last30days-research"]
}
```

### Slash command

Type directly in the chat input:

```
/last30days AI agent trends
/last30days Claude vs GPT --deep --days=7
/last30days Rust programming --sources=reddit,youtube --quick
```

Supported flags: `--deep`, `--quick`, `--days=N`, `--sources=x,y`

### Auto-route via skill

The skill auto-activates when the message matches trigger keywords:
- "social media", "reddit says", "twitter says", "trending on", "public opinion", "dư luận", "xu hướng", etc.

### Standalone API endpoint

```bash
# Basic
curl -X POST http://localhost:5000/api/tools/last30days \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI agent trends"}'

# With options
curl -X POST http://localhost:5000/api/tools/last30days \
  -H "Content-Type: application/json" \
  -d '{"topic": "Rust vs Go", "depth": "quick", "days": 7, "sources": "reddit,youtube"}'
```

Response:
```json
{
  "success": true,
  "result": "## 🔍 Social Research: AI agent trends\n...",
  "metadata": {"topic": "AI agent trends", "depth": "default", "days": 30, "elapsed_s": 12.5},
  "error": null
}
```

### Parameters

The wrapper defaults are suitable for most queries. For advanced use, the function signature:

```python
run_last30days_research(
    topic="AI trends",
    query_type="general",   # general, sentiment, trend, deep
    depth="default",        # quick, default, deep
    days=30,                # 1-90
    sources="reddit,youtube" # optional filter
)
```

## Rollback

To disable without removing code:

1. Set `LAST30DAYS_ENABLED=false` in env → tool returns error message, no subprocess call
2. Or remove `last30days-research` from the UI tool selector

To fully remove:

1. Delete `vendor/last30days/` directory
2. Remove `core/last30days_tool.py`
3. Remove `social_research.yaml` from `core/skills/builtins/`
4. Remove dispatch block from `routes/stream.py` (the `last30days-research` block + `/last30days` command detection)
5. Remove `routes/last30days.py` (Flask blueprint)
6. Remove `fastapi_app/routers/last30days.py` (FastAPI router)
7. Remove blueprint registration from `chatbot_main.py` and `fastapi_app/__init__.py`
8. Remove tool button from `templates/index.html` and JS binding
9. Remove `LAST30DAYS_*` vars from `core/config.py`

## Risks

| Risk | Mitigation |
|---|---|
| Long execution (1-5 min) | Timeout at 180s default; use `depth=quick` |
| Missing Python 3.12+ | Clear error message; feature flag gates execution |
| Missing Node.js (X/Twitter) | Graceful skip; other sources still work |
| SSE blocking | Research completes before streaming; acceptable for sync flow |
| Bad request to API endpoint | Pydantic validation (FastAPI) / manual validation (Flask); 400 response |
| Upstream subprocess error | Captured with non-zero exit code; returned as 422 with error detail |
