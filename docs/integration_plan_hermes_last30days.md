# Integration Plan: Hermes Agent + last30days-skill → AI-Assistant

> **Status**: All phases complete (Phase 1–4). Ready for review and merge.
> **Created**: 2026-04-13
> **Updated**: 2026-04-14 — Phase 4 completed (tests, guardrails, logging, release checklist, final cleanup)
> **Author**: GitHub Copilot survey
> **References**:
> - https://github.com/NousResearch/hermes-agent (v0.8.0, 72.8k★)
> - https://github.com/mvanhorn/last30days-skill (v3.0.0, 21.3k★)
> - AI-Assistant repo: https://github.com/SkastVnT/AI-Assistant

---

## 1. Kiến trúc hiện tại của AI-Assistant

### 1.1 Service Map

| Service | Port | Entry point | venv | Trạng thái |
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

### 1.3 Request Path (Primary — Flask SSE)

```
Client POST /chat/stream
  → routes/stream.py (stream_bp)
    ├─ resolve_skill() → SkillOverrides           [skill system]
    ├─ apply_skill_overrides() → AppliedSkill      [model/tool/prompt merge]
    ├─ inject_code_context()                       [MCP local file context]
    ├─ _needs_web_search() → inline tool dispatch
    │   ├─ _run_web_search() (SerpAPI → Google CSE fallback)
    │   ├─ saucenao_search_tool()
    │   ├─ serpapi_reverse_image()
    │   └─ serpapi_image_search()
    ├─ Tool results → appended to message text (augmented context)
    └─ chatbot_v2.get_chatbot() → streaming via ModelRegistry
        └─ SSE events: metadata → chunk → complete
```

### 1.4 Tool System hiện tại

**Pattern**: Plain functions trong `core/tools.py`, **không có tool registry**. Dispatch bằng `if tool_name in tools:` trong `routes/stream.py`.

| Tool function | API Key | Purpose |
|---|---|---|
| `google_search_tool()` | `GOOGLE_SEARCH_API_KEY_1/2` | Google CSE |
| `github_search_tool()` | `GITHUB_TOKEN` | GitHub repo search |
| `saucenao_search_tool()` | `SAUCENAO_API_KEY` | SauceNAO reverse image |
| `serpapi_web_search()` | `SERPAPI_API_KEY` | Multi-engine web search |
| `serpapi_reverse_image()` | `SERPAPI_API_KEY` | 3-tier reverse image cascade |
| `serpapi_image_search()` | `SERPAPI_API_KEY` | Image search |
| `reverse_image_search()` | Multiple | Comprehensive reverse image |

### 1.5 Skill System hiện tại

**Pattern**: YAML-defined overrides, loaded from `core/skills/builtins/*.yaml`.

**Resolution chain**: explicit (request) → session (sticky) → auto-route (keyword match) → none

**11 builtin skills**: `code_expert`, `coding_assistant`, `counselor`, `creative_writer`, `mcp_file_helper`, `prompt_engineer`, `realtime_search`, `repo_analyzer`, `research_analyst`, `research_web`, `shopping_advisor`

**Key classes**:
- `SkillDefinition` → id, name, description, prompt_fragments, preferred_tools, trigger_keywords, etc.
- `SkillRegistry` → in-memory dict, load from YAML
- `SkillRouter` → keyword scoring, auto-match
- `SkillOverrides` → merge output for stream.py

### 1.6 MCP Server (stdio)

**6 tools** registered via `@mcp.tool()` decorator: `search_files`, `read_file_content`, `list_directory`, `get_project_info`, `search_logs`, `calculate`.

**Chatbot-side MCP**: `src/utils/mcp_integration.py` → `MCPClient` class (local file access, NOT connecting to stdio server).

### 1.7 Config Layers

| Layer | File | Concern |
|---|---|---|
| Shared env | `services/shared_env.py` | `.env` loading, one call per service |
| API keys | `core/config.py` | `os.getenv()` for all keys |
| MongoDB | `config/mongodb_config.py` | DB connection |
| Features | `config/features.json` | Feature flags |
| Model presets | `config/model_presets.py` | SD model configs |

---

## 2. Điểm móc để thêm tool mới (last30days)

### 2.1 Cách last30days hoạt động

**last30days** là một Python CLI tool (`scripts/last30days.py`) chạy multi-source research:
- **Sources**: Reddit, X/Twitter, YouTube, TikTok, Instagram, HN, Polymarket, GitHub, Bluesky, Web
- **Output**: Compact research report (JSON/markdown) với scored results
- **Dependencies**: `requests>=2.32`, Python 3.12+, optional: `yt-dlp`, Node.js (vendored Bird client for X)
- **Config**: `~/.config/last30days/.env` (API keys per source)
- **Execution**: `python scripts/last30days.py "topic" --emit=compact --plan 'JSON'`

### 2.2 Integration hook points

**Hook A — New tool function** trong `core/tools.py`:

```python
def last30days_research(topic, query_type="general", depth="default", days=30):
    """Run last30days research engine and return structured results."""
    # Subprocess call to last30days.py with --emit=compact --agent
    # Parse JSON output, return structured dict
```

**Hook B — New builtin skill** `core/skills/builtins/social_research.yaml`:

```yaml
id: social_research
name: Social Research (last30days)
trigger_keywords: [last30days, trending, social media, reddit says, twitter says, what people think, recent trends, public opinion]
preferred_tools: [last30days-research]
```

**Hook C — Tool dispatch** trong `routes/stream.py`:

Thêm case `last30days-research` vào inline tool dispatch block (tương tự `google-search`, `deep-research`).

**Hook D — UI tool selector** trong `static/js/modules/` và `templates/index.html`:

Thêm option "Social Research" vào tool dropdown.

**Hook E — MCP server tool** (optional — Phase 2):

Expose `last30days_research` qua `@mcp.tool()` trong `services/mcp-server/server.py`.

### 2.3 Chiến lược tích hợp last30days

**Approach: Subprocess wrapper** (không import trực tiếp, tránh dependency conflict)

```
User request → stream.py
  ├─ skill resolve → "social_research" (keyword match hoặc explicit)
  ├─ tool = "last30days-research"
  ├─ subprocess.run(["python", "scripts/last30days.py", topic, "--emit=compact", "--agent"])
  ├─ Parse compact output → structured dict
  ├─ Append results to message context
  └─ LLM synthesizes based on research data
```

**Lý do chọn subprocess**: last30days yêu cầu Python 3.12+ và Node.js runtime (vendored Bird client), có thể conflict với venv-core. Subprocess cách ly hoàn toàn.

---

## 3. Điểm móc để thêm service Hermes

### 3.1 Cách Hermes Agent hoạt động

**Hermes Agent** là full-featured AI agent với closed learning loop:
- **Core**: `run_agent.py` → `AIAgent` class (~9200 lines)
- **Tool system**: Registry pattern, 20+ tool modules, OpenAI function calling format
- **Features**: Skill creation/improvement, persistent memory, session search (FTS5), subagent delegation, context compression
- **Gateway**: Multi-platform messaging (Telegram, Discord, Slack, etc.) with SSE streaming
- **Entry points**: CLI (`hermes`), Gateway API (`gateway/platforms/api_server.py`), ACP adapter

### 3.2 Integration approaches

#### Option 1: Sidecar service via Gateway API (RECOMMENDED)

Hermes có sẵn `gateway/platforms/api_server.py` — HTTP API với SSE streaming. Dùng làm sidecar:

```
AI-Assistant chatbot → HTTP → Hermes Gateway API → AIAgent → response (SSE)
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

**Hook A — New route** `routes/hermes.py`:

```python
hermes_bp = Blueprint('hermes', __name__)

@hermes_bp.route('/api/hermes/chat', methods=['POST'])
def hermes_chat():
    """Proxy to Hermes sidecar for advanced agent tasks."""
    # Forward to Hermes Gateway API
```

**Hook B — Config** `core/config.py`:

```python
HERMES_API_URL = os.getenv("HERMES_API_URL", "http://localhost:8080")
HERMES_API_KEY = os.getenv("HERMES_API_KEY")
HERMES_ENABLED = os.getenv("HERMES_ENABLED", "false").lower() == "true"
```

**Hook C — Skill** `core/skills/builtins/hermes_agent.yaml`:

```yaml
id: hermes_agent
name: Hermes Advanced Agent
trigger_keywords: [hermes, advanced agent, delegate, deep task, complex task]
preferred_tools: [hermes-delegate]
```

**Hook D — Blueprint registration** `chatbot_main.py`:

```python
try:
    from routes.hermes import hermes_bp
    app.register_blueprint(hermes_bp)
except ImportError:
    logger.warning("Hermes routes not available")
```

**Hook E — UI** (optional):

New mode selector option "Hermes Agent" hoặc tool button "Delegate to Hermes".

---

## 4. Danh sách file thật sự nên touch

### Phase 1: last30days integration (tool + skill)

| File | Action | Layer | Risk |
|---|---|---|---|
| `services/chatbot/core/tools.py` | **EDIT** — add `last30days_research()` function | Tool | Low |
| `services/chatbot/core/config.py` | **EDIT** — add `LAST30DAYS_*` env vars | Config | Low |
| `services/chatbot/routes/stream.py` | **EDIT** — add tool dispatch case | Route | Medium |
| `services/chatbot/core/skills/builtins/social_research.yaml` | **CREATE** — new builtin skill | Skill | Low |
| `services/chatbot/templates/index.html` | **EDIT** — add tool option in dropdown | UI | Low |
| `services/chatbot/static/js/modules/api-service.js` | **EDIT** — add tool ID to known tools | UI | Low |
| `app/config/.env` (or `.env_dev`) | **EDIT** — add `LAST30DAYS_*` key placeholders | Config | Low |
| `services/chatbot/tests/test_tools.py` | **EDIT** — add last30days tool tests | Test | Low |
| `README.md` | **EDIT** — update tools table | Docs | Low |

### Phase 2: Hermes sidecar integration

| File | Action | Layer | Risk |
|---|---|---|---|
| `services/chatbot/routes/hermes.py` | **CREATE** — new blueprint | Route | Low |
| `services/chatbot/core/config.py` | **EDIT** — add `HERMES_*` env vars | Config | Low |
| `services/chatbot/core/skills/builtins/hermes_agent.yaml` | **CREATE** — new builtin skill | Skill | Low |
| `services/chatbot/chatbot_main.py` | **EDIT** — register `hermes_bp` | Blueprint reg | Medium |
| `services/chatbot/run.py` | **EDIT** — optional auto-start Hermes sidecar | Startup | Medium |
| `services/chatbot/routes/stream.py` | **EDIT** — add hermes-delegate tool dispatch | Route | Medium |
| `services/chatbot/templates/index.html` | **EDIT** — add Hermes mode/tool option | UI | Low |
| `services/chatbot/static/js/modules/api-service.js` | **EDIT** — add hermes tool ID | UI | Low |
| `app/config/.env` | **EDIT** — add `HERMES_*` key placeholders | Config | Low |
| `services/chatbot/tests/test_hermes_integration.py` | **CREATE** — integration tests | Test | Low |
| `README.md` | **EDIT** — update service table, tools | Docs | Low |

### READ-ONLY services (KHÔNG touch)

| Service/Path | Reason |
|---|---|
| `services/stable-diffusion/` | Image workflow — hoạt động ổn, không liên quan |
| `services/edit-image/` | ComfyUI — hoạt động ổn, không liên quan |
| `ComfyUI/` | External dependency — không modify |
| `image_pipeline/` | Image pipeline internals |
| `venv-core/`, `venv-image/` | Generated venvs |

---

## 5. Rủi ro tương thích

### 5.1 last30days risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Python version**: last30days yêu cầu 3.12+, venv-core có thể dùng 3.10/3.11 | Medium | Subprocess isolation — chạy bằng python system hoặc venv riêng |
| **Node.js dependency**: vendored Bird client cho X search cần Node.js | Medium | Optional — skip X source nếu không có Node.js |
| **Subprocess timeout**: research có thể mất 1-5 phút | Medium | Set timeout (300s), stream progress events về client |
| **Config conflict**: `~/.config/last30days/.env` vs `app/config/.env` | Low | Tách rõ: last30days dùng config riêng, chatbot chỉ pass topic |
| **SSE blocking**: long-running research blocks SSE stream | High | Run research async (background thread/process), stream partial results |
| **API key management**: last30days cần riêng SCRAPECREATORS_API_KEY, XAI_API_KEY, etc. | Low | Load từ shared env hoặc last30days tự đọc config riêng |

### 5.2 Hermes risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Heavy dependency**: Hermes kéo ~100+ packages (anthropic, openai, rich, etc.) | High | Sidecar pattern — Hermes chạy trong venv riêng, giao tiếp qua HTTP |
| **Port conflict**: Hermes Gateway API cần port riêng | Low | Config `HERMES_PORT` env var, default 8080 |
| **API key overlap**: Hermes và chatbot share `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Medium | Hermes đọc từ `~/.hermes/config.yaml`, chatbot từ `app/config/.env` — tách rõ |
| **Session management**: Hermes có SQLite sessions, chatbot dùng MongoDB | Medium | Keep separate — Hermes session cho Hermes, MongoDB cho chatbot |
| **Resource consumption**: Hermes agent loop + tools tiêu tốn RAM/CPU | Medium | Lazy start Hermes khi cần, timeout idle sessions |
| **Model cost**: Hermes có thể gọi nhiều LLM calls (tool loops, subagents) | High | Rate limit, max_iterations config, cost tracking |

### 5.3 Cross-cutting risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Image services disruption** | CRITICAL | Không touch `services/stable-diffusion/`, `services/edit-image/`, `venv-image` |
| **Streaming regression** | High | Regression test: SSE `metadata→chunk→complete` flow vẫn hoạt động |
| **OCR/multimodal regression** | Medium | Test reverse image search, OCR flows unaffected |
| **Blueprint registration failure** | Medium | Try/except wrapper (existing pattern) |
| **Environment loading order** | Medium | Verify `load_shared_env()` vẫn là single call đầu tiên |

---

## 6. Thứ tự triển khai an toàn

### Phase 1: last30days as chatbot tool ✅ DONE

**Step 1.1** — Cài đặt last30days engine
- Clone `mvanhorn/last30days-skill` vào `services/chatbot/vendor/last30days/` (hoặc install as submodule)
- Verify Python 3.12+ available trên machine
- Test standalone: `python scripts/last30days.py "AI agents" --emit=compact --agent`

**Step 1.2** — Tool wrapper function
- Thêm `last30days_research()` vào `core/tools.py`
- Subprocess wrapper với timeout, JSON output parsing
- Error handling: timeout, missing dependencies, empty results

**Step 1.3** — Config và env vars
- Thêm `LAST30DAYS_ENABLED`, `LAST30DAYS_PYTHON_PATH`, `LAST30DAYS_SCRIPT_PATH` vào `core/config.py`
- Thêm placeholders vào `app/config/.env_dev`

**Step 1.4** — Skill definition
- Tạo `core/skills/builtins/social_research.yaml` với trigger keywords
- Test auto-route: "what are people saying about..." → activates social_research skill

**Step 1.5** — Route integration
- Thêm `last30days-research` dispatch case vào `routes/stream.py`
- Research results → append to message context → LLM synthesizes
- Handle async: research chạy background, stream progress events

**Step 1.6** — UI wiring
- Thêm "Social Research" tool option vào dropdown
- (Optional) Thêm "🔍 Researching..." indicator during long-running research

**Step 1.7** — Tests
- Unit test cho `last30days_research()` wrapper
- Integration test cho tool dispatch flow
- Regression test cho existing search tools (SerpAPI, CSE, reverse image)

**Step 1.8** — Docs
- Update README.md tools table
- Update search cascade docs

### Phase 2: Hermes sidecar service ✅ DONE

**Step 2.1** — Hermes environment setup
- Install Hermes Agent (`pip install hermes-agent[all]`) trong venv riêng hoặc Docker
- Configure `~/.hermes/config.yaml` với model provider
- Test standalone: `hermes` CLI hoạt động

**Step 2.2** — Gateway API startup
- Configure Hermes Gateway API server trên port 8080
- Test: `curl http://localhost:8080/api/health`
- Document startup command

**Step 2.3** — Chatbot proxy route
- Tạo `routes/hermes.py` blueprint
- Endpoints: `/api/hermes/chat` (SSE proxy), `/api/hermes/status`
- HTTP client (httpx/requests) gọi Hermes Gateway

**Step 2.4** — Config
- Thêm `HERMES_*` env vars vào `core/config.py`
- Feature flag: `HERMES_ENABLED` (default: false)

**Step 2.5** — Skill + tool dispatch
- Tạo `core/skills/builtins/hermes_agent.yaml`
- Thêm `hermes-delegate` tool dispatch vào `routes/stream.py`

**Step 2.6** — Blueprint registration
- Đăng ký `hermes_bp` trong `chatbot_main.py` (with try/except)
- Do not add FastAPI parity without a separate migration task.

**Step 2.7** — Auto-start (optional)
- Thêm Hermes auto-start vào `run.py` (tương tự pattern ComfyUI auto-start)
- Config: `AUTO_START_HERMES=true`

**Step 2.8** — UI integration
- Thêm "Hermes Agent" mode trong UI
- (Optional) Hermes-specific response rendering

**Step 2.9** — Tests
- Integration test cho Hermes proxy with mock server
- Regression test cho existing chat flow
- Test graceful fallback khi Hermes unavailable

**Step 2.10** — Docs
- Update README.md service table (Hermes sidecar)
- Document startup, config, usage

### Phase 3: Advanced integration ⏳ OPEN (post-merge)

- last30days results cached trong MongoDB
- Hermes context compression pattern extracted vào chatbot core
- Cross-session memory sharing giữa chatbot và Hermes
- MCP tool exposure cho both last30days và Hermes delegate
- Unified tool registry (migrate from plain functions sang registry pattern)

---

## 7. Acceptance criteria

### Phase 1: last30days tool ✅

| # | Criterion | Verification |
|---|---|---|
| 1.1 | `last30days_research("AI agents")` trả về structured dict với ≥1 source | Unit test |
| 1.2 | Skill auto-route: "what people say about X" → `social_research` skill | Unit test |
| 1.3 | `POST /chat/stream` với tool=`last30days-research` → SSE research results | Integration test |
| 1.4 | UI hiện "Social Research" option trong tool dropdown | Manual verify |
| 1.5 | Existing search tools (SerpAPI, CSE, reverse image) vẫn hoạt động | Regression test |
| 1.6 | Image generation (`/api/image-gen/*`) không bị ảnh hưởng | Regression test |
| 1.7 | OCR, multimodal handler không bị ảnh hưởng | Regression test |
| 1.8 | SSE streaming (`metadata→chunk→complete`) vẫn đúng contract | Regression test |
| 1.9 | Research timeout ≤5 phút, graceful error nếu timeout | Unit test |
| 1.10 | README.md updated với tools table mới | Manual verify |

### Phase 2: Hermes sidecar ✅

| # | Criterion | Verification |
|---|---|---|
| 2.1 | Hermes sidecar start/stop không ảnh hưởng chatbot main | Manual verify |
| 2.2 | `POST /api/hermes/chat` → SSE response từ Hermes | Integration test |
| 2.3 | Hermes unavailable → graceful fallback (503 + message) | Unit test |
| 2.4 | `HERMES_ENABLED=false` → route returns 503, no sidecar started | Unit test |
| 2.5 | Existing chat flow (`POST /chat/stream`) tốc độ không giảm | Performance test |
| 2.6 | Image services (SD 7861, ComfyUI 8100) không bị ảnh hưởng | Regression test |
| 2.7 | All 14 existing blueprints vẫn register thành công | Startup test |
| 2.8 | `shared_env.py` vẫn load một lần duy nhất | Code review |
| 2.9 | Flask mode hoạt động | Manual verify `python run.py` |
| 2.10 | README.md updated với Hermes service entry | Manual verify |

### Phase 3: Advanced ⏳ OPEN

| # | Criterion | Verification |
|---|---|---|
| 3.1 | last30days results cached → repeat research nhanh hơn | Performance test |
| 3.2 | MCP tool `last30days_research` accessible via MCP client | MCP Inspector test |
| 3.3 | Context compression reduces token usage ≥30% cho long conversations | Metrics |

---

## Appendix A: File map thực tế (verified)

```
services/chatbot/
├── chatbot_main.py             # Flask monolith entry (~5400 lines)
├── run.py                      # Universal dispatcher
├── core/
│   ├── config.py               # API keys from env
│   ├── chatbot.py              # ChatbotAgent v1 (if/elif routing)
│   ├── chatbot_v2.py           # ChatbotAgent v2 (ModelRegistry)
│   ├── tools.py                # Tool functions (plain, no registry)
│   ├── streaming.py            # SSE helpers
│   ├── stream_contract.py      # SSE complete-event shape
│   ├── thinking_generator.py   # Thinking modes
│   ├── base_chat.py            # ModelConfig, ChatContext
│   ├── extensions.py           # Flask extensions
│   ├── skills/
│   │   ├── registry.py         # SkillDefinition, SkillRegistry
│   │   ├── router.py           # SkillRouter (keyword match)
│   │   ├── resolver.py         # resolve_skill() chain
│   │   ├── applicator.py       # apply_skill_overrides()
│   │   ├── session.py          # SkillSessionStore
│   │   └── builtins/           # 11 YAML skill definitions
│   ├── agentic/                # Multi-thinking pipeline
│   └── image_gen/              # Image gen orchestration
├── routes/
│   ├── stream.py               # PRIMARY: POST /chat/stream
│   ├── main.py                 # /, /chat, /clear, /history
│   ├── mcp.py                  # /api/mcp/* (MCPClient)
│   ├── image_gen.py            # /api/image-gen/*
│   ├── skills.py               # /api/skills/*
│   ├── conversations.py        # CRUD
│   ├── admin.py                # /admin
│   └── ... (10+ more blueprints)
├── config/
│   ├── mongodb_config.py       # DB connection
│   └── mongodb_helpers.py      # ConversationDB, etc.
├── src/
│   ├── utils/mcp_integration.py # MCPClient (local file access)
│   ├── handlers/               # Multimodal, image gen
│   └── rag/                    # RAG subsystem
├── templates/index.html        # Chat UI
├── static/js/modules/          # Frontend modules
├── app/                        # Modular Flask mode
└── tests/                      # Test suite

services/mcp-server/
├── server.py                   # FastMCP (stdio), 6 tools
└── tools/advanced_tools.py     # Unregistered utility functions

services/shared_env.py          # Single env loader
app/config/                     # .env files, config.yml
```

## Appendix B: Layer classification cho mỗi file dự kiến sửa

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

Sau mỗi phase, chạy regression cho:

| Test area | What to verify | How |
|---|---|---|
| SSE streaming | `metadata→chunk→complete` events đúng contract | `pytest tests/ -k stream` |
| Search tools | SerpAPI, Google CSE, reverse image vẫn hoạt động | `pytest tests/ -k search` |
| Image generation | `/api/image-gen/*` routes respond correctly | Manual + `pytest tests/ -k image` |
| Skill resolution | Existing 11 skills vẫn resolve đúng | `pytest tests/ -k skill` |
| Blueprint registration | All blueprints register without error | Startup test |
| OCR / multimodal | Image upload + OCR flow | Manual test |
| MCP integration | `/api/mcp/*` routes work | Manual test |
| Chat history | `/history`, `/clear` routes | Manual test |
| Admin panel | `/admin` accessible | Manual test |
