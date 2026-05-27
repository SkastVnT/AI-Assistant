# Integration Plan: Hermes Agent + last30days-skill â†’ AI-Assistant

> **Status**: All phases complete (Phase 1â€“4). Ready for review and merge.
> **Created**: 2026-04-13
> **Updated**: 2026-04-14 â€” Phase 4 completed (tests, guardrails, logging, release checklist, final cleanup)
> **Author**: GitHub Copilot survey
> **References**:
> - https://github.com/NousResearch/hermes-agent (v0.8.0, 72.8kâ˜…)
> - https://github.com/mvanhorn/last30days-skill (v3.0.0, 21.3kâ˜…)
> - AI-Assistant repo: https://github.com/SkastVnT/AI-Assistant

---

## 1. Kiáº¿n trÃºc hiá»‡n táº¡i cá»§a AI-Assistant

### 1.1 Service Map

| Service | Port | Entry point | venv | Tráº¡ng thÃ¡i |
|---|---|---|---|---|
| ChatBot (Flask default) | 5000 | `services/chatbot/chatbot_main.py` | `venv-core` | Active, primary |
| ChatBot (all modes) | 5000 | `services/chatbot/run.py` | `venv-core` | Active |
| MCP Server | stdio | `services/mcp-server/server.py` | `venv-core` | Active |
| Stable Diffusion | 7861 | `services/stable-diffusion/` | `venv-image` | Active, READ-ONLY |
| Edit Image (ComfyUI) | 8100 | `services/edit-image/` | `venv-image` | Active, READ-ONLY |

### 1.2 Startup Modes (chatbot)

| Env flag | Mode | Entry |
|---|---|---|
| *(none)* | Flask monolith | `run.py` |

`USE_NEW_STRUCTURE` and `USE_FASTAPI` were removed in May 2026. Do not add FastAPI parity files without a separate migration task.

### 1.3 Request Path (Primary â€” Flask SSE)

```
Client POST /chat/stream
  â†’ routes/stream.py (stream_bp)
    â”œâ”€ resolve_skill() â†’ SkillOverrides           [skill system]
    â”œâ”€ apply_skill_overrides() â†’ AppliedSkill      [model/tool/prompt merge]
    â”œâ”€ inject_code_context()                       [MCP local file context]
    â”œâ”€ _needs_web_search() â†’ inline tool dispatch
    â”‚   â”œâ”€ _run_web_search() (SerpAPI â†’ Google CSE fallback)
    â”‚   â”œâ”€ saucenao_search_tool()
    â”‚   â”œâ”€ serpapi_reverse_image()
    â”‚   â””â”€ serpapi_image_search()
    â”œâ”€ Tool results â†’ appended to message text (augmented context)
    â””â”€ chatbot_v2.get_chatbot() â†’ streaming via ModelRegistry
        â””â”€ SSE events: metadata â†’ chunk â†’ complete
```

### 1.4 Tool System hiá»‡n táº¡i

**Pattern**: Plain functions trong `core/tools.py`, **khÃ´ng cÃ³ tool registry**. Dispatch báº±ng `if tool_name in tools:` trong `routes/stream.py`.

| Tool function | API Key | Purpose |
|---|---|---|
| `google_search_tool()` | `GOOGLE_SEARCH_API_KEY_1/2` | Google CSE |
| `github_search_tool()` | `GITHUB_TOKEN` | GitHub repo search |
| `saucenao_search_tool()` | `SAUCENAO_API_KEY` | SauceNAO reverse image |
| `serpapi_web_search()` | `SERPAPI_API_KEY` | Multi-engine web search |
| `serpapi_reverse_image()` | `SERPAPI_API_KEY` | 3-tier reverse image cascade |
| `serpapi_image_search()` | `SERPAPI_API_KEY` | Image search |
| `reverse_image_search()` | Multiple | Comprehensive reverse image |

### 1.5 Skill System hiá»‡n táº¡i

**Pattern**: YAML-defined overrides, loaded from `core/skills/builtins/*.yaml`.

**Resolution chain**: explicit (request) â†’ session (sticky) â†’ auto-route (keyword match) â†’ none

**11 builtin skills**: `code_expert`, `coding_assistant`, `counselor`, `creative_writer`, `mcp_file_helper`, `prompt_engineer`, `realtime_search`, `repo_analyzer`, `research_analyst`, `research_web`, `shopping_advisor`

**Key classes**:
- `SkillDefinition` â†’ id, name, description, prompt_fragments, preferred_tools, trigger_keywords, etc.
- `SkillRegistry` â†’ in-memory dict, load from YAML
- `SkillRouter` â†’ keyword scoring, auto-match
- `SkillOverrides` â†’ merge output for stream.py

### 1.6 MCP Server (stdio)

**6 tools** registered via `@mcp.tool()` decorator: `search_files`, `read_file_content`, `list_directory`, `get_project_info`, `search_logs`, `calculate`.

**Chatbot-side MCP**: `src/utils/mcp_integration.py` â†’ `MCPClient` class (local file access, NOT connecting to stdio server).

### 1.7 Config Layers

| Layer | File | Concern |
|---|---|---|
| Shared env | `services/shared_env.py` | `.env` loading, one call per service |
| API keys | `core/config.py` | `os.getenv()` for all keys |
| MongoDB | `config/mongodb_config.py` | DB connection |
| Features | `config/features.json` | Feature flags |
| Model presets | `config/model_presets.py` | SD model configs |

---

## 2. Äiá»ƒm mÃ³c Ä‘á»ƒ thÃªm tool má»›i (last30days)

### 2.1 CÃ¡ch last30days hoáº¡t Ä‘á»™ng

**last30days** lÃ  má»™t Python CLI tool (`scripts/last30days.py`) cháº¡y multi-source research:
- **Sources**: Reddit, X/Twitter, YouTube, TikTok, Instagram, HN, Polymarket, GitHub, Bluesky, Web
- **Output**: Compact research report (JSON/markdown) vá»›i scored results
- **Dependencies**: `requests>=2.32`, Python 3.12+, optional: `yt-dlp`, Node.js (vendored Bird client for X)
- **Config**: `~/.config/last30days/.env` (API keys per source)
- **Execution**: `python scripts/last30days.py "topic" --emit=compact --plan 'JSON'`

### 2.2 Integration hook points

**Hook A â€” New tool function** trong `core/tools.py`:

```python
def last30days_research(topic, query_type="general", depth="default", days=30):
    """Run last30days research engine and return structured results."""
    # Subprocess call to last30days.py with --emit=compact --agent
    # Parse JSON output, return structured dict
```

**Hook B â€” New builtin skill** `core/skills/builtins/social_research.yaml`:

```yaml
id: social_research
name: Social Research (last30days)
trigger_keywords: [last30days, trending, social media, reddit says, twitter says, what people think, recent trends, public opinion]
preferred_tools: [last30days-research]
```

**Hook C â€” Tool dispatch** trong `routes/stream.py`:

ThÃªm case `last30days-research` vÃ o inline tool dispatch block (tÆ°Æ¡ng tá»± `google-search`, `deep-research`).

**Hook D â€” UI tool selector** trong `static/js/modules/` vÃ  `templates/index.html`:

ThÃªm option "Social Research" vÃ o tool dropdown.

**Hook E â€” MCP server tool** (optional â€” Phase 2):

Expose `last30days_research` qua `@mcp.tool()` trong `services/mcp-server/server.py`.

### 2.3 Chiáº¿n lÆ°á»£c tÃ­ch há»£p last30days

**Approach: Subprocess wrapper** (khÃ´ng import trá»±c tiáº¿p, trÃ¡nh dependency conflict)

```
User request â†’ stream.py
  â”œâ”€ skill resolve â†’ "social_research" (keyword match hoáº·c explicit)
  â”œâ”€ tool = "last30days-research"
  â”œâ”€ subprocess.run(["python", "scripts/last30days.py", topic, "--emit=compact", "--agent"])
  â”œâ”€ Parse compact output â†’ structured dict
  â”œâ”€ Append results to message context
  â””â”€ LLM synthesizes based on research data
```

**LÃ½ do chá»n subprocess**: last30days yÃªu cáº§u Python 3.12+ vÃ  Node.js runtime (vendored Bird client), cÃ³ thá»ƒ conflict vá»›i venv-core. Subprocess cÃ¡ch ly hoÃ n toÃ n.

---

## 3. Äiá»ƒm mÃ³c Ä‘á»ƒ thÃªm service Hermes

### 3.1 CÃ¡ch Hermes Agent hoáº¡t Ä‘á»™ng

**Hermes Agent** lÃ  full-featured AI agent vá»›i closed learning loop:
- **Core**: `run_agent.py` â†’ `AIAgent` class (~9200 lines)
- **Tool system**: Registry pattern, 20+ tool modules, OpenAI function calling format
- **Features**: Skill creation/improvement, persistent memory, session search (FTS5), subagent delegation, context compression
- **Gateway**: Multi-platform messaging (Telegram, Discord, Slack, etc.) with SSE streaming
- **Entry points**: CLI (`hermes`), Gateway API (`gateway/platforms/api_server.py`), ACP adapter

### 3.2 Integration approaches

#### Option 1: Sidecar service via Gateway API (RECOMMENDED)

Hermes cÃ³ sáºµn `gateway/platforms/api_server.py` â€” HTTP API vá»›i SSE streaming. DÃ¹ng lÃ m sidecar:

```
AI-Assistant chatbot â†’ HTTP â†’ Hermes Gateway API â†’ AIAgent â†’ response (SSE)
```

**Pros**: Zero code change to Hermes, clean separation, independent scaling
**Cons**: Extra process, network latency, session management cross-service

#### Option 2: Library import (AIAgent as dependency)

```python
from hermes_agent.run_agent import AIAgent
agent = AIAgent(model="...", enabled_toolsets=["web", "file"], quiet_mode=True)
result = agent.run_conversation(user_message="...", conversation_history=[...])
```

**Pros**: Tight integration, no network hop
**Cons**: Heavy dependency (~100+ packages), venv conflict risk, version lock

#### Option 3: Selective extraction (cherry-pick patterns)

Extract specific Hermes patterns into AI-Assistant:
- Tool registry pattern (`tools/registry.py`)
- Context compression (`agent/context_compressor.py`)
- Delegate/subagent pattern (`agent/delegate_tool.py`)

**Pros**: Minimal footprint, no external dependency
**Cons**: Maintenance burden, won't get Hermes updates

### 3.3 Recommended: Option 1 (Sidecar) + selective extraction

1. **Phase 1**: Run Hermes as sidecar service, expose via internal API
2. **Phase 2**: Extract useful patterns (context compression, tool registry) as needed
3. **Phase 3**: Optional deeper integration based on usage patterns

### 3.4 Hook points for Hermes sidecar

**Hook A â€” New route** `routes/hermes.py`:

```python
hermes_bp = Blueprint('hermes', __name__)

@hermes_bp.route('/api/hermes/chat', methods=['POST'])
def hermes_chat():
    """Proxy to Hermes sidecar for advanced agent tasks."""
    # Forward to Hermes Gateway API
```

**Hook B â€” Config** `core/config.py`:

```python
HERMES_API_URL = os.getenv("HERMES_API_URL", "http://localhost:8080")
HERMES_API_KEY = os.getenv("HERMES_API_KEY")
HERMES_ENABLED = os.getenv("HERMES_ENABLED", "false").lower() == "true"
```

**Hook C â€” Skill** `core/skills/builtins/hermes_agent.yaml`:

```yaml
id: hermes_agent
name: Hermes Advanced Agent
trigger_keywords: [hermes, advanced agent, delegate, deep task, complex task]
preferred_tools: [hermes-delegate]
```

**Hook D â€” Blueprint registration** `chatbot_main.py`:

```python
try:
    from routes.hermes import hermes_bp
    app.register_blueprint(hermes_bp)
except ImportError:
    logger.warning("Hermes routes not available")
```

**Hook E â€” UI** (optional):

New mode selector option "Hermes Agent" hoáº·c tool button "Delegate to Hermes".

---

## 4. Danh sÃ¡ch file tháº­t sá»± nÃªn touch

### Phase 1: last30days integration (tool + skill)

| File | Action | Layer | Risk |
|---|---|---|---|
| `services/chatbot/core/tools.py` | **EDIT** â€” add `last30days_research()` function | Tool | Low |
| `services/chatbot/core/config.py` | **EDIT** â€” add `LAST30DAYS_*` env vars | Config | Low |
| `services/chatbot/routes/stream.py` | **EDIT** â€” add tool dispatch case | Route | Medium |
| `services/chatbot/core/skills/builtins/social_research.yaml` | **CREATE** â€” new builtin skill | Skill | Low |
| `services/chatbot/templates/index.html` | **EDIT** â€” add tool option in dropdown | UI | Low |
| `services/chatbot/static/js/modules/api-service.js` | **EDIT** â€” add tool ID to known tools | UI | Low |
| `app/config/.env` (or `.env_dev`) | **EDIT** â€” add `LAST30DAYS_*` key placeholders | Config | Low |
| `services/chatbot/tests/test_tools.py` | **EDIT** â€” add last30days tool tests | Test | Low |
| `README.md` | **EDIT** â€” update tools table | Docs | Low |

### Phase 2: Hermes sidecar integration

| File | Action | Layer | Risk |
|---|---|---|---|
| `services/chatbot/routes/hermes.py` | **CREATE** â€” new blueprint | Route | Low |
| `services/chatbot/core/config.py` | **EDIT** â€” add `HERMES_*` env vars | Config | Low |
| `services/chatbot/core/skills/builtins/hermes_agent.yaml` | **CREATE** â€” new builtin skill | Skill | Low |
| `services/chatbot/chatbot_main.py` | **EDIT** â€” register `hermes_bp` | Blueprint reg | Medium |
| `services/chatbot/run.py` | **EDIT** â€” optional auto-start Hermes sidecar | Startup | Medium |
| `services/chatbot/routes/stream.py` | **EDIT** â€” add hermes-delegate tool dispatch | Route | Medium |
| `services/chatbot/templates/index.html` | **EDIT** â€” add Hermes mode/tool option | UI | Low |
| `services/chatbot/static/js/modules/api-service.js` | **EDIT** â€” add hermes tool ID | UI | Low |
| `app/config/.env` | **EDIT** â€” add `HERMES_*` key placeholders | Config | Low |
| `services/chatbot/tests/test_hermes_integration.py` | **CREATE** â€” integration tests | Test | Low |
| `README.md` | **EDIT** â€” update service table, tools | Docs | Low |

### READ-ONLY services (KHÃ”NG touch)

| Service/Path | Reason |
|---|---|
| `services/stable-diffusion/` | Image workflow â€” hoáº¡t Ä‘á»™ng á»•n, khÃ´ng liÃªn quan |
| `services/edit-image/` | ComfyUI â€” hoáº¡t Ä‘á»™ng á»•n, khÃ´ng liÃªn quan |
| `ComfyUI/` | External dependency â€” khÃ´ng modify |
| `app/image_pipeline/` | Image pipeline internals |
| `venv-core/`, `venv-image/` | Generated venvs |

---

## 5. Rá»§i ro tÆ°Æ¡ng thÃ­ch

### 5.1 last30days risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Python version**: last30days yÃªu cáº§u 3.12+, venv-core cÃ³ thá»ƒ dÃ¹ng 3.10/3.11 | Medium | Subprocess isolation â€” cháº¡y báº±ng python system hoáº·c venv riÃªng |
| **Node.js dependency**: vendored Bird client cho X search cáº§n Node.js | Medium | Optional â€” skip X source náº¿u khÃ´ng cÃ³ Node.js |
| **Subprocess timeout**: research cÃ³ thá»ƒ máº¥t 1-5 phÃºt | Medium | Set timeout (300s), stream progress events vá» client |
| **Config conflict**: `~/.config/last30days/.env` vs `app/config/.env` | Low | TÃ¡ch rÃµ: last30days dÃ¹ng config riÃªng, chatbot chá»‰ pass topic |
| **SSE blocking**: long-running research blocks SSE stream | High | Run research async (background thread/process), stream partial results |
| **API key management**: last30days cáº§n riÃªng SCRAPECREATORS_API_KEY, XAI_API_KEY, etc. | Low | Load tá»« shared env hoáº·c last30days tá»± Ä‘á»c config riÃªng |

### 5.2 Hermes risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Heavy dependency**: Hermes kÃ©o ~100+ packages (anthropic, openai, rich, etc.) | High | Sidecar pattern â€” Hermes cháº¡y trong venv riÃªng, giao tiáº¿p qua HTTP |
| **Port conflict**: Hermes Gateway API cáº§n port riÃªng | Low | Config `HERMES_PORT` env var, default 8080 |
| **API key overlap**: Hermes vÃ  chatbot share `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Medium | Hermes Ä‘á»c tá»« `~/.hermes/config.yaml`, chatbot tá»« `app/config/.env` â€” tÃ¡ch rÃµ |
| **Session management**: Hermes cÃ³ SQLite sessions, chatbot dÃ¹ng MongoDB | Medium | Keep separate â€” Hermes session cho Hermes, MongoDB cho chatbot |
| **Resource consumption**: Hermes agent loop + tools tiÃªu tá»‘n RAM/CPU | Medium | Lazy start Hermes khi cáº§n, timeout idle sessions |
| **Model cost**: Hermes cÃ³ thá»ƒ gá»i nhiá»u LLM calls (tool loops, subagents) | High | Rate limit, max_iterations config, cost tracking |

### 5.3 Cross-cutting risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Image services disruption** | CRITICAL | KhÃ´ng touch `services/stable-diffusion/`, `services/edit-image/`, `venv-image` |
| **Streaming regression** | High | Regression test: SSE `metadataâ†’chunkâ†’complete` flow váº«n hoáº¡t Ä‘á»™ng |
| **OCR/multimodal regression** | Medium | Test reverse image search, OCR flows unaffected |
| **Blueprint registration failure** | Medium | Try/except wrapper (existing pattern) |
| **Environment loading order** | Medium | Verify `load_shared_env()` váº«n lÃ  single call Ä‘áº§u tiÃªn |

---

## 6. Thá»© tá»± triá»ƒn khai an toÃ n

### Phase 1: last30days as chatbot tool âœ… DONE

**Step 1.1** â€” CÃ i Ä‘áº·t last30days engine
- Clone `mvanhorn/last30days-skill` vÃ o `services/chatbot/vendor/last30days/` (hoáº·c install as submodule)
- Verify Python 3.12+ available trÃªn machine
- Test standalone: `python scripts/last30days.py "AI agents" --emit=compact --agent`

**Step 1.2** â€” Tool wrapper function
- ThÃªm `last30days_research()` vÃ o `core/tools.py`
- Subprocess wrapper vá»›i timeout, JSON output parsing
- Error handling: timeout, missing dependencies, empty results

**Step 1.3** â€” Config vÃ  env vars
- ThÃªm `LAST30DAYS_ENABLED`, `LAST30DAYS_PYTHON_PATH`, `LAST30DAYS_SCRIPT_PATH` vÃ o `core/config.py`
- ThÃªm placeholders vÃ o `app/config/.env_dev`

**Step 1.4** â€” Skill definition
- Táº¡o `core/skills/builtins/social_research.yaml` vá»›i trigger keywords
- Test auto-route: "what are people saying about..." â†’ activates social_research skill

**Step 1.5** â€” Route integration
- ThÃªm `last30days-research` dispatch case vÃ o `routes/stream.py`
- Research results â†’ append to message context â†’ LLM synthesizes
- Handle async: research cháº¡y background, stream progress events

**Step 1.6** â€” UI wiring
- ThÃªm "Social Research" tool option vÃ o dropdown
- (Optional) ThÃªm "ðŸ” Researching..." indicator during long-running research

**Step 1.7** â€” Tests
- Unit test cho `last30days_research()` wrapper
- Integration test cho tool dispatch flow
- Regression test cho existing search tools (SerpAPI, CSE, reverse image)

**Step 1.8** â€” Docs
- Update README.md tools table
- Update search cascade docs

### Phase 2: Hermes sidecar service âœ… DONE

**Step 2.1** â€” Hermes environment setup
- Install Hermes Agent (`pip install hermes-agent[all]`) trong venv riÃªng hoáº·c Docker
- Configure `~/.hermes/config.yaml` vá»›i model provider
- Test standalone: `hermes` CLI hoáº¡t Ä‘á»™ng

**Step 2.2** â€” Gateway API startup
- Configure Hermes Gateway API server trÃªn port 8080
- Test: `curl http://localhost:8080/api/health`
- Document startup command

**Step 2.3** â€” Chatbot proxy route
- Táº¡o `routes/hermes.py` blueprint
- Endpoints: `/api/hermes/chat` (SSE proxy), `/api/hermes/status`
- HTTP client (httpx/requests) gá»i Hermes Gateway

**Step 2.4** â€” Config
- ThÃªm `HERMES_*` env vars vÃ o `core/config.py`
- Feature flag: `HERMES_ENABLED` (default: false)

**Step 2.5** â€” Skill + tool dispatch
- Táº¡o `core/skills/builtins/hermes_agent.yaml`
- ThÃªm `hermes-delegate` tool dispatch vÃ o `routes/stream.py`

**Step 2.6** â€” Blueprint registration
- ÄÄƒng kÃ½ `hermes_bp` trong `chatbot_main.py` (with try/except)
- Do not add FastAPI parity without a separate migration task.

**Step 2.7** â€” Auto-start (optional)
- ThÃªm Hermes auto-start vÃ o `run.py` (tÆ°Æ¡ng tá»± pattern ComfyUI auto-start)
- Config: `AUTO_START_HERMES=true`

**Step 2.8** â€” UI integration
- ThÃªm "Hermes Agent" mode trong UI
- (Optional) Hermes-specific response rendering

**Step 2.9** â€” Tests
- Integration test cho Hermes proxy with mock server
- Regression test cho existing chat flow
- Test graceful fallback khi Hermes unavailable

**Step 2.10** â€” Docs
- Update README.md service table (Hermes sidecar)
- Document startup, config, usage

### Phase 3: Advanced integration â³ OPEN (post-merge)

- last30days results cached trong MongoDB
- Hermes context compression pattern extracted vÃ o chatbot core
- Cross-session memory sharing giá»¯a chatbot vÃ  Hermes
- MCP tool exposure cho both last30days vÃ  Hermes delegate
- Unified tool registry (migrate from plain functions sang registry pattern)

---

## 7. Acceptance criteria

### Phase 1: last30days tool âœ…

| # | Criterion | Verification |
|---|---|---|
| 1.1 | `last30days_research("AI agents")` tráº£ vá» structured dict vá»›i â‰¥1 source | Unit test |
| 1.2 | Skill auto-route: "what people say about X" â†’ `social_research` skill | Unit test |
| 1.3 | `POST /chat/stream` vá»›i tool=`last30days-research` â†’ SSE research results | Integration test |
| 1.4 | UI hiá»‡n "Social Research" option trong tool dropdown | Manual verify |
| 1.5 | Existing search tools (SerpAPI, CSE, reverse image) váº«n hoáº¡t Ä‘á»™ng | Regression test |
| 1.6 | Image generation (`/api/image-gen/*`) khÃ´ng bá»‹ áº£nh hÆ°á»Ÿng | Regression test |
| 1.7 | OCR, multimodal handler khÃ´ng bá»‹ áº£nh hÆ°á»Ÿng | Regression test |
| 1.8 | SSE streaming (`metadataâ†’chunkâ†’complete`) váº«n Ä‘Ãºng contract | Regression test |
| 1.9 | Research timeout â‰¤5 phÃºt, graceful error náº¿u timeout | Unit test |
| 1.10 | README.md updated vá»›i tools table má»›i | Manual verify |

### Phase 2: Hermes sidecar âœ…

| # | Criterion | Verification |
|---|---|---|
| 2.1 | Hermes sidecar start/stop khÃ´ng áº£nh hÆ°á»Ÿng chatbot main | Manual verify |
| 2.2 | `POST /api/hermes/chat` â†’ SSE response tá»« Hermes | Integration test |
| 2.3 | Hermes unavailable â†’ graceful fallback (503 + message) | Unit test |
| 2.4 | `HERMES_ENABLED=false` â†’ route returns 503, no sidecar started | Unit test |
| 2.5 | Existing chat flow (`POST /chat/stream`) tá»‘c Ä‘á»™ khÃ´ng giáº£m | Performance test |
| 2.6 | Image services (SD 7861, ComfyUI 8100) khÃ´ng bá»‹ áº£nh hÆ°á»Ÿng | Regression test |
| 2.7 | All 14 existing blueprints váº«n register thÃ nh cÃ´ng | Startup test |
| 2.8 | `shared_env.py` váº«n load má»™t láº§n duy nháº¥t | Code review |
| 2.9 | Flask mode hoáº¡t Ä‘á»™ng | Manual verify `python run.py` |
| 2.10 | README.md updated vá»›i Hermes service entry | Manual verify |

### Phase 3: Advanced â³ OPEN

| # | Criterion | Verification |
|---|---|---|
| 3.1 | last30days results cached â†’ repeat research nhanh hÆ¡n | Performance test |
| 3.2 | MCP tool `last30days_research` accessible via MCP client | MCP Inspector test |
| 3.3 | Context compression reduces token usage â‰¥30% cho long conversations | Metrics |

---

## Appendix A: File map thá»±c táº¿ (verified)

```
services/chatbot/
â”œâ”€â”€ chatbot_main.py             # Flask monolith entry (~5400 lines)
â”œâ”€â”€ run.py                      # Universal dispatcher
â”œâ”€â”€ core/
â”‚   â”œâ”€â”€ config.py               # API keys from env
â”‚   â”œâ”€â”€ chatbot.py              # ChatbotAgent v1 (if/elif routing)
â”‚   â”œâ”€â”€ chatbot_v2.py           # ChatbotAgent v2 (ModelRegistry)
â”‚   â”œâ”€â”€ tools.py                # Tool functions (plain, no registry)
â”‚   â”œâ”€â”€ streaming.py            # SSE helpers
â”‚   â”œâ”€â”€ stream_contract.py      # SSE complete-event shape
â”‚   â”œâ”€â”€ thinking_generator.py   # Thinking modes
â”‚   â”œâ”€â”€ base_chat.py            # ModelConfig, ChatContext
â”‚   â”œâ”€â”€ extensions.py           # Flask extensions
â”‚   â”œâ”€â”€ skills/
â”‚   â”‚   â”œâ”€â”€ registry.py         # SkillDefinition, SkillRegistry
â”‚   â”‚   â”œâ”€â”€ router.py           # SkillRouter (keyword match)
â”‚   â”‚   â”œâ”€â”€ resolver.py         # resolve_skill() chain
â”‚   â”‚   â”œâ”€â”€ applicator.py       # apply_skill_overrides()
â”‚   â”‚   â”œâ”€â”€ session.py          # SkillSessionStore
â”‚   â”‚   â””â”€â”€ builtins/           # 11 YAML skill definitions
â”‚   â”œâ”€â”€ agentic/                # Multi-thinking pipeline
â”‚   â””â”€â”€ image_gen/              # Image gen orchestration
â”œâ”€â”€ routes/
â”‚   â”œâ”€â”€ stream.py               # PRIMARY: POST /chat/stream
â”‚   â”œâ”€â”€ main.py                 # /, /chat, /clear, /history
â”‚   â”œâ”€â”€ mcp.py                  # /api/mcp/* (MCPClient)
â”‚   â”œâ”€â”€ image_gen.py            # /api/image-gen/*
â”‚   â”œâ”€â”€ skills.py               # /api/skills/*
â”‚   â”œâ”€â”€ conversations.py        # CRUD
â”‚   â”œâ”€â”€ admin.py                # /admin
â”‚   â””â”€â”€ ... (10+ more blueprints)
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ mongodb_config.py       # DB connection
â”‚   â””â”€â”€ mongodb_helpers.py      # ConversationDB, etc.
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ utils/mcp_integration.py # MCPClient (local file access)
â”‚   â”œâ”€â”€ handlers/               # Multimodal, image gen
â”‚   â””â”€â”€ app/rag/                # RAG subsystem
â”œâ”€â”€ templates/index.html        # Chat UI
â”œâ”€â”€ static/js/modules/          # Frontend modules
â”œâ”€â”€ app/                        # Modular Flask mode
â””â”€â”€ tests/                      # Test suite

services/mcp-server/
â”œâ”€â”€ server.py                   # FastMCP (stdio), 6 tools
â””â”€â”€ tools/advanced_tools.py     # Unregistered utility functions

services/shared_env.py          # Single env loader
app/config/                     # .env files, config.yml
```

## Appendix B: Layer classification cho má»—i file dá»± kiáº¿n sá»­a

| Layer | Files |
|---|---|
| **Route** | `routes/stream.py`, `routes/hermes.py` (new) |
| **Service** | `core/tools.py`, `src/utils/hermes_client.py` (new) |
| **Config** | `core/config.py`, `app/config/.env_dev` |
| **Skill** | `core/skills/builtins/social_research.yaml` (new), `hermes_agent.yaml` (new) |
| **UI** | `templates/index.html`, `static/js/modules/api-service.js` |
| **Blueprint** | `chatbot_main.py` (registration only) |
| **Startup** | `run.py` (optional Hermes auto-start) |
| **Test** | `tests/test_tools.py`, `tests/test_hermes_integration.py` (new) |
| **Docs** | `README.md` |
| **Docker** (future) | `docker-compose.yml` cho Hermes sidecar |

## Appendix C: Regression test scope

Sau má»—i phase, cháº¡y regression cho:

| Test area | What to verify | How |
|---|---|---|
| SSE streaming | `metadataâ†’chunkâ†’complete` events Ä‘Ãºng contract | `pytest tests/ -k stream` |
| Search tools | SerpAPI, Google CSE, reverse image váº«n hoáº¡t Ä‘á»™ng | `pytest tests/ -k search` |
| Image generation | `/api/image-gen/*` routes respond correctly | Manual + `pytest tests/ -k image` |
| Skill resolution | Existing 11 skills váº«n resolve Ä‘Ãºng | `pytest tests/ -k skill` |
| Blueprint registration | All blueprints register without error | Startup test |
| OCR / multimodal | Image upload + OCR flow | Manual test |
| MCP integration | `/api/mcp/*` routes work | Manual test |
| Chat history | `/history`, `/clear` routes | Manual test |
| Admin panel | `/admin` accessible | Manual test |
