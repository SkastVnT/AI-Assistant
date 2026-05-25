---
name: shared-env-contract
description: "Audit and enforce the shared environment loading contract across all services. Use when: adding, renaming, or removing an environment variable; changing config loading logic; debugging missing env values at runtime; adding a new service or dependency profile; reviewing whether a change affects chatbot only, MCP only, or multiple services; or checking for hardcoded ports, URLs, or secrets."
---

# Shared Environment Contract

## When to use this skill

- Adding, renaming, or removing an environment variable.
- Changing how or where `.env` files are loaded.
- Debugging a service that cannot find an expected env value.
- Adding a new API key, provider, or external service URL.
- Reviewing whether a config change is scoped to one service or crosses boundaries.
- Checking for hardcoded ports, URLs, or secrets that should come from env.
- Changing dependency profiles (`venv-core` vs `venv-image`).

---

## Source of truth — configuration files

| File | Role | Authority |
|---|---|---|
| `services/shared_env.py` | **Authoritative loader** — `load_shared_env(__file__)` | How env is loaded |
| `app/config/.env` | Shared env values (production/dev) | Runtime values |
| `app/config/.env_{env}` | Environment-specific override (e.g. `.env_dev`) | Runtime values (preferred when exists) |
| `app/config/.env.example` | Shared variable template | What variables exist |
| `services/chatbot/.env` | Chatbot-local overrides (loaded without override by `run.py`) | Service-local keys only |
| `services/chatbot/.env.example` | Chatbot variable template | What chatbot-specific vars exist |
| `services/chatbot/core/config.py` | Reads all env vars via `os.getenv()` | What the chatbot actually uses |
| `app/config/config.yml` | Service ports, hosts, logging, cache settings | Static config reference |
| `app/config/model_config.py` | `HubConfig`, `ServiceConfig` dataclasses | Service registry and hub config |

---

## Environment loading architecture

```
Process start
  │
  ├─ services/chatbot/run.py (universal dispatcher)
  │    ├─ load_shared_env(__file__)          ← loads app/config/.env_{env} or .env
  │    └─ load_dotenv(services/chatbot/.env) ← WITHOUT OVERRIDE, local-only keys
  │
  ├─ services/chatbot/chatbot_main.py (Flask legacy)
  │    └─ load_shared_env(__file__)          ← same shared loader
  │
  ├─ services/chatbot/core/config.py (imported by either entry point)
  │    └─ load_shared_env(__file__)          ← safe re-call (dotenv is idempotent)
  │
  └─ services/mcp-server/server.py
       └─ (no explicit env loading — reads os.environ directly)
```

### Key rules

1. **One loader function**: `services/shared_env.py` → `load_shared_env(__file__)`.
2. **One shared env file**: `app/config/.env_{env}` (preferred) or `app/config/.env` (fallback).
3. **One allowed local override**: `run.py` loads `services/chatbot/.env` **without override** — shared values always win.
4. **Never** add a second `load_dotenv(override=True)` anywhere in `services/`.
5. **MCP server** does not call `load_shared_env` — it inherits from the process environment or is launched with env already set.

---

## Variable registry — what the chatbot reads

### LLM provider keys (core/config.py)

| Variable | Provider | Required |
|---|---|---|
| `GROK_API_KEY` | xAI Grok (default model) | Yes (for default) |
| `OPENAI_API_KEY` | OpenAI GPT + Sora 2 video | For OpenAI/video |
| `DEEPSEEK_API_KEY` | DeepSeek Chat | For DeepSeek |
| `QWEN_API_KEY` | Qwen (Alibaba) | For Qwen |
| `GEMINI_API_KEY_1` … `_4` | Google Gemini (rotation pool) | For Gemini |
| `HUGGINGFACE_API_KEY` | HuggingFace models | For local models |
| `OPENROUTER_API_KEY` | OpenRouter multi-model | Optional |
| `STEPFUN_API_KEY` | StepFun image gen | Optional |

### Search and tool keys

| Variable | Tool | Required |
|---|---|---|
| `SERPAPI_API_KEY` | SerpAPI (Google/Bing/Baidu/Lens/Images) | For web search |
| `GOOGLE_SEARCH_API_KEY_1`, `_2` | Google CSE fallback | For CSE fallback |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | For CSE fallback |
| `SAUCENAO_API_KEY` | SauceNAO reverse image | For anime source |
| `GITHUB_TOKEN` | GitHub API | For GitHub search |

### Image generation keys (chatbot-local .env)

| Variable | Provider | Loaded from |
|---|---|---|
| `FAL_API_KEY` | fal.ai FLUX | `services/chatbot/.env` |
| `BFL_API_KEY` | Black Forest Labs | `services/chatbot/.env` |
| `IMGBB_API_KEY` | ImgBB image hosting | `services/chatbot/.env` |
| `REPLICATE_API_TOKEN` | Replicate | `services/chatbot/.env` |

### Infrastructure

| Variable | Purpose | Default |
|---|---|---|
| `env` | Environment name | `dev` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Database name | `chatbot_db` |
| `MONGODB_TLS_ALLOW_INVALID_CERTIFICATES` | Allow invalid MongoDB TLS certificates | `false` |
| `REDIS_URL` | Redis cache URL | — |
| `SD_API_URL` | Stable Diffusion WebUI | `http://127.0.0.1:7861` |
| `FLASK_SECRET_KEY` | Flask session secret | required outside dev/test |

### Startup flags

| Variable | Effect | Default |
|---|---|---|
| `TESTING` | CI test mode (disables DB) | `False` |
| `MONGODB_ENABLED` | Enable MongoDB | `True` (disabled in CI) |

---

## Dependency profiles — do not mix

| Profile | venv | Requirements | Services |
|---|---|---|---|
| core-services | `venv-core` | `app/requirements/profile_core_services.txt` | Chatbot, MCP server |
| image-ai-services | `venv-image` | `app/requirements/profile_image_ai_services.txt` | Stable Diffusion, Edit Image |

**Rule**: chatbot and MCP work always uses `venv-core`. Never install image-ai packages into `venv-core`.

---

## Good and bad examples

### Good: adding a new API key

```python
# 1. Add to core/config.py — read from env
NEW_SERVICE_API_KEY = os.getenv('NEW_SERVICE_API_KEY')

# 2. Add placeholder to app/config/.env.example
# NEW_SERVICE_API_KEY=your-key-here

# 3. Add actual value to app/config/.env (or .env_dev)
# NEW_SERVICE_API_KEY=sk-abc123

# 4. Document in README.md env table
# 5. Use in code via config import
from core.config import NEW_SERVICE_API_KEY
```

### Bad: hardcoding or duplicating config

```python
# ❌ Hardcoded URL in a route handler
response = requests.get("http://localhost:7861/sdapi/v1/txt2img")

# ✅ Read from config
from core.config import SD_API_URL
response = requests.get(f"{SD_API_URL}/sdapi/v1/txt2img")
```

```python
# ❌ Second load_dotenv that overrides shared env
from dotenv import load_dotenv
load_dotenv("my_custom.env", override=True)  # BREAKS shared contract

# ✅ Use the shared loader
from services.shared_env import load_shared_env
load_shared_env(__file__)
```

```python
# ❌ Hardcoded port in multiple files
app.run(port=5000)           # in chatbot_main.py
PORT = 5000                  # in another file
requests.get("http://localhost:5000/health")  # in health check

# ✅ Single source, read from env or config
PORT = int(os.getenv('CHATBOT_PORT', '5000'))
```

```python
# ❌ Reading env var with wrong name (typo or drift)
key = os.getenv('GROK_KEY')  # Wrong — actual name is GROK_API_KEY

# ✅ Use the canonical name from core/config.py
from core.config import GROK_API_KEY
```

---

## Monitor — what can drift

1. **Variable name mismatch** — `.env.example` says `GROK_API_KEY`, but code reads `GROK_KEY`.
2. **Default value drift** — `config.yml` says port 5000, but `os.getenv('CHATBOT_PORT', '5001')` defaults to 5001.
3. **Orphaned variables** — key removed from code but still in `.env.example`, or vice versa.
4. **Override creep** — a new `load_dotenv(override=True)` call introduced anywhere.
5. **Hardcoded secrets or URLs** — API keys, `localhost:PORT`, or connection strings in source code.
6. **Cross-profile contamination** — image-ai package added to `profile_core_services.txt`.
7. **MCP server env gap** — MCP server expects a variable that only exists in chatbot's local `.env`.
8. **`.env` file proliferation** — new `.env` files created outside the sanctioned locations.

---

## Do not touch unless the task requires it

- `services/shared_env.py` — only if the loading mechanism itself needs changing.
- `app/config/.env` — only to add/remove variable values; never restructure.
- `app/config/config.yml` — only if service ports or infrastructure settings change.
- `services/stable-diffusion/` or `services/edit-image/` — image services have their own env needs.
- `venv-core/` or `venv-image/` — generated; never edit.

---

## Required output — config impact summary

After any change that touches environment variables, configuration files, or env loading logic, include this summary:

1. **Variables affected** — which env vars were added, renamed, removed, or had defaults changed?
2. **Scope** — chatbot only / MCP only / shared (multiple services)?
3. **Loading path** — does the variable come from shared env (`app/config/.env`) or local override (`services/chatbot/.env`)?
4. **Profile impact** — does this change affect `venv-core` dependencies, `venv-image` dependencies, or neither?
5. **Files updated** — list every file that was changed.
6. **Docs updated** — was `README.md`, `.env.example`, or `config.yml` updated to match?
7. **Risk** — could this break another service, override a shared value, or introduce a hardcoded secret?

---

## Verification checklist

After any env-related change:

- [ ] The variable is read via `os.getenv()` in `core/config.py` (not inline in route handlers).
- [ ] The variable name matches exactly between `.env.example`, `core/config.py`, and any docs.
- [ ] No new `load_dotenv(override=True)` was introduced.
- [ ] No API key, URL, or port is hardcoded in source code.
- [ ] If the variable is chatbot-only: it is in `services/chatbot/.env`, not in `app/config/.env`.
- [ ] If the variable is shared: it is in `app/config/.env` and `app/config/.env.example`.
- [ ] `README.md` env table was updated if a new externally-visible variable was added.
- [ ] `pytest services/chatbot/tests/ -v` still passes (activate `venv-core`).
- [ ] No image-ai packages were added to `profile_core_services.txt`.
