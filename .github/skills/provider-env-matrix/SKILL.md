---
name: provider-env-matrix
description: "Work safely with provider configuration, API keys, model routing, and environment dependencies for the core chatbot. Use when: adding or changing an LLM provider, modifying API key loading, changing model defaults or fallback chains, debugging missing-key errors, reviewing config drift across .env files, or checking whether a provider change affects tools or docs."
---

# Provider-Env Matrix

## When to use this skill

- Adding a new LLM provider or model.
- Changing an API key variable name, default, or rotation logic.
- Modifying model fallback chains or vision model selection.
- Debugging "API key not configured" errors at runtime.
- Reviewing whether .env files, config.py, and README.md are aligned.
- Checking whether a provider change also affects tool dispatch or MCP.

## Source of truth

| Fact | Authoritative file | Copies to check |
|---|---|---|
| Env variable names and defaults | `services/chatbot/core/config.py` lines 23-59 | `services/chatbot/.env.example`, `app/config/.env`, `README.md` env table |
| Model registry (names, IDs, base URLs, fallbacks) | `core/chatbot_v2.py` lines 54-182 (`ModelRegistry`) | `core/chatbot.py` (v1 if/elif chain) |
| Shared env loading contract | `services/shared_env.py` | `services/chatbot/run.py` (secondary load) |
| Tool API key requirements | `core/tools.py` lines 13-16 (imports) | `core/config.py`, `.env.example` |
| Search key usage in stream route | `routes/stream.py` lines 75-152 (`_run_web_search`) | `core/tools.py` (parallel code path) |
| Documented env vars | `README.md` lines 142-186 | `app/scripts/README.md`, `.claude/skills/repo-guidelines/AGENTS.md` |

## Provider registry

### LLM providers (chatbot_v2.py ModelRegistry)

| Model name | Env key | Model ID | Base URL | Vision | Fallback | Streaming |
|---|---|---|---|---|---|---|
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | *(default OpenAI)* | ✓ | `deepseek` | ✓ |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` | `https://api.deepseek.com/v1` | ✗ | `openai` | ✓ |
| `grok` | `GROK_API_KEY` | `grok-3` | `https://api.x.ai/v1` | ✗ | `deepseek` | ✓ |
| `qwen` | `QWEN_API_KEY` | `qwen-turbo` | *(Aliyun)* | ✗ | `deepseek` | ✓ |
| `bloomvn` | `HUGGINGFACE_API_KEY` | `BlossomsAI/BloomVN-8B-chat` | *(HF API)* | ✗ | `qwen` | ✗ |
| `step-flash` | `OPENROUTER_API_KEY` | `stepfun/step-3.5-flash:free` | `https://openrouter.ai/api/v1` | ✗ | `deepseek` | ✓ |
| `gemini` | `GEMINI_API_KEYS[0]` | `gemini-2.0-flash` | `https://generativelanguage.googleapis.com/v1beta/openai/` | ✓ | `grok` | ✓ |
| `stepfun` | `STEPFUN_API_KEY` | `step-2-16k` | `https://api.stepfun.com/v1` | ✗ | `step-flash` | ✓ |

**Vision fallback chain** (`chatbot_v2.py` line 199): `gemini` → `openai`.

**Gemini key rotation**: `GEMINI_API_KEY_1` through `_4` collected into `GEMINI_API_KEYS` list; first available key is used.

### Tool providers (tools.py + stream.py)

| Tool | Env key(s) | Fallback |
|---|---|---|
| Web search (SerpAPI primary) | `SERPAPI_API_KEY` | Google CSE via `GOOGLE_SEARCH_API_KEY_1/2` + `GOOGLE_CSE_ID` |
| Web search (Google CSE) | `GOOGLE_SEARCH_API_KEY_1`, `GOOGLE_CSE_ID` | `GOOGLE_SEARCH_API_KEY_2` on 429 |
| Reverse image (SerpAPI) | `SERPAPI_API_KEY` | *(none — SerpAPI required)* |
| SauceNAO | `SAUCENAO_API_KEY` | *(none)* |
| GitHub search | `GITHUB_TOKEN` | *(none)* |

### Image generation providers (chatbot-local keys)

| Provider | Env key | Loaded from |
|---|---|---|
| fal.ai | `FAL_API_KEY` | `services/chatbot/.env` only (not in shared env) |
| Black Forest Labs | `BFL_API_KEY` | `services/chatbot/.env` only |
| Replicate | `REPLICATE_API_TOKEN` | `services/chatbot/.env` only |
| Together | `TOGETHER_API_KEY` | `services/chatbot/.env` only |
| StepFun | `STEPFUN_API_KEY` | `services/chatbot/.env` only |
| OpenRouter | `OPENROUTER_API_KEY` | `services/chatbot/.env` only |

### Infrastructure

| Variable | Default | Purpose |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017` | Database |
| `MONGODB_DB_NAME` | `chatbot_db` | Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache |
| `SD_API_URL` | `http://127.0.0.1:7861` | Stable Diffusion endpoint |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI endpoint |
| `env` | `dev` | Selects `.env_{name}` file |

## Env loading chain

```
1. services/shared_env.py → load_shared_env(__file__)
   Loads: app/config/.env_dev  (or .env fallback)
   Scope: process-wide, all services

2. services/chatbot/run.py → load_dotenv(services/chatbot/.env)
   Mode: NO override — shared env values win on conflict
   Purpose: chatbot-only keys (FAL_API_KEY, STEPFUN_API_KEY, etc.)

3. services/chatbot/core/config.py → os.getenv(...)
   Reads all keys at import time into module-level constants
   Imported by: chatbot.py, chatbot_v2.py, tools.py, stream.py
```

**Rule**: `config.py` must call `load_shared_env(__file__)` before any `os.getenv`. It does so at line 23. Never add a second `load_dotenv` that overrides shared values.

## Scope classification

Before making any provider change, classify it:

| Scope | What it means | Files to touch |
|---|---|---|
| **Chatbot-only** | New LLM provider or model change | `config.py`, `chatbot.py` or `chatbot_v2.py`, `.env.example`, `README.md` |
| **Tool-related** | New or changed search/image tool key | `config.py`, `tools.py`, `stream.py` (if auto-trigger changes), `.env.example`, `README.md` |
| **MCP-related** | MCP server needs a new env var | `services/mcp-server/server.py`, `services/mcp-server/README.md`, `README.md` |
| **Multi-service** | Shared env var or port change | `shared_env.py`, `app/config/.env*`, all affected `.env*`, `README.md`, `.claude/skills/repo-guidelines/AGENTS.md` |

## Good patterns

```python
# ✅ Read from env in config.py, use the constant everywhere
# config.py
NEW_PROVIDER_API_KEY = os.getenv('NEW_PROVIDER_API_KEY')

# chatbot_v2.py
from core.config import NEW_PROVIDER_API_KEY
if NEW_PROVIDER_API_KEY:
    self._configs['new-provider'] = ModelConfig(
        name='new-provider',
        api_key=NEW_PROVIDER_API_KEY,
        ...
        fallback_model='deepseek'
    )
```

```python
# ✅ Graceful missing-key handling
def chat_with_new_provider(self, message, ...):
    if not NEW_PROVIDER_API_KEY:
        return "❌ NEW_PROVIDER_API_KEY not configured"
    ...
```

```python
# ✅ Single source for base URLs
# config.py
NEW_PROVIDER_BASE_URL = os.getenv('NEW_PROVIDER_BASE_URL', 'https://api.example.com/v1')
```

## Bad patterns

```python
# ❌ Hardcoded key
client = OpenAI(api_key="sk-proj-abc123...")

# ❌ Inline os.getenv in routing code instead of config.py
def some_route():
    key = os.getenv('OPENAI_API_KEY')  # Should import from config.py

# ❌ Duplicate base URL in multiple files
# chatbot_v2.py
base_url='https://api.deepseek.com/v1'
# stream.py
DEEPSEEK_URL = 'https://api.deepseek.com/v1'  # duplicate!

# ❌ Override shared env
load_dotenv('services/chatbot/.env', override=True)  # breaks shared contract

# ❌ Missing fallback model in ModelConfig
self._configs['new'] = ModelConfig(
    ...,
    fallback_model=None  # if key is missing, model silently fails
)
```

## Missing-key behavior audit

| Model | Key check | Behavior when missing |
|---|---|---|
| `grok` | `if not GROK_API_KEY` | Returns error string ✓ |
| `qwen` | `if not QWEN_API_KEY` | Returns error string ✓ |
| `bloomvn` | `if not HUGGINGFACE_API_KEY` | Returns error string ✓ |
| `openai` | *(no explicit check in v1)* | Client creation fails at runtime ✗ |
| `deepseek` | *(no explicit check in v1)* | Client creation fails at runtime ✗ |
| `gemini` | Guarded by `if GEMINI_API_KEYS:` in v2 | Not registered → fallback chain ✓ |
| `step-flash` | Guarded by `if OPENROUTER_API_KEY:` in v2 | Not registered → fallback chain ✓ |
| `stepfun` | Guarded by `if STEPFUN_API_KEY:` in v2 | Not registered → fallback chain ✓ |

**Note**: v2 `ModelRegistry` only registers a model if its key exists, so missing keys cause graceful fallback. v1 `chatbot.py` has inconsistent error handling — some models check, some don't.

## Config impact summary format

After any provider or env change, report:

```
Config Impact Summary
─────────────────────
Scope:        chatbot-only | tool-related | MCP-related | multi-service
Variable:     NEW_VARIABLE_NAME
Default:      (value or None)
Read in:      config.py line N
Used by:      [list of modules]
Fallback:     (what happens if missing)
.env updated: .env.example, app/config/.env.example
Docs updated: README.md env table
```

## Provider-change checklist

- [ ] **Variable in config.py**: new env var added to `core/config.py` with `os.getenv()`, no hardcoded default for secrets.
- [ ] **No duplicate reads**: variable is read once in `config.py` and imported elsewhere — not re-read via `os.getenv` in routing code.
- [ ] **Missing-key guard**: provider method returns a clear error string when key is `None`.
- [ ] **ModelRegistry entry** (if LLM): `chatbot_v2.py` registers model only when key is present; `fallback_model` is set.
- [ ] **v1 parity** (if LLM): `chatbot.py` if/elif chain also handles the new model name.
- [ ] **No hardcoded secrets or URLs**: base URLs read from env with sensible defaults.
- [ ] **.env.example updated**: placeholder line added for the new variable.
- [ ] **README.md env table updated**: variable documented with description.
- [ ] **Shared env contract preserved**: no second `load_dotenv` with override; chatbot-only keys go in `services/chatbot/.env`.
- [ ] **Tool impact reviewed**: if the change affects search/image tools, verify `tools.py` and `stream.py` still work.
- [ ] **Config impact summary included** in the response.
