---
name: core-chatbot-routing-audit
description: "Audit and safely edit the core chatbot request path: route registration, blueprint wiring, provider routing, tool dispatch, SSE streaming, and UI-to-backend wiring. Use when adding or changing a chat route, modifying provider selection, wiring a new tool into the UI, debugging broken streaming, or reviewing blueprint registration."
---

# Core Chatbot Routing Audit

## When to use this skill

- Adding, removing, or renaming a chatbot route or endpoint.
- Changing provider routing or model selection logic.
- Wiring a new tool (search, image, MCP) into the chat pipeline.
- Debugging broken SSE streaming or missing UI controls.
- Confirming changes stay on the Flask monolith path.
- Reviewing blueprint registration order or URL prefix conflicts.
- Verifying that a frontend JS call still matches its backend endpoint.

## Mandatory first step

**Trace the real request path before editing anything.** Identify:
1. Which Flask blueprint handles the request.
2. Which core module processes it (chatbot.py, tools.py, thinking_generator.py).
3. Which UI element triggers it (template HTML, static JS module).
4. What response shape the frontend expects (JSON, SSE events, redirect).

---

## File map â€” likely touch points

### Entry points

| File | Role |
|---|---|
| `services/chatbot/chatbot_main.py` | Flask monolith â€” registers blueprints, starts app |
| `services/chatbot/run.py` | Dispatcher for the Flask monolith |

### Flask blueprints â€” `services/chatbot/routes/`

| File | Blueprint | Key routes |
|---|---|---|
| `routes/stream.py` | `stream_bp` | **`POST /chat/stream`** (SSE primary), `GET /chat/stream/models`, `GET /chat/stream/metrics` |
| `routes/main.py` | `main_bp` | `GET /`, `POST /chat`, `POST /clear`, `GET /history`, `POST /api/generate-title`, `POST /api/extract-file-text` |
| `routes/conversations.py` | `conversations_bp` | Conversation CRUD |
| `routes/mcp.py` | `mcp_bp` | `/api/mcp/*` â€” enable, disable, list-files, add-folder, fetch-url, ocr-extract |
| `routes/image_gen.py` | `image_gen_bp` | `/api/image-gen/*` â€” generate, edit, gallery, providers, styles |
| `routes/images.py` | `images_bp` | `/images/*` â€” storage and retrieval |
| `routes/memory.py` | `memory_bp` | `/memory/*` â€” AI memory management |
| `routes/models.py` | `models_bp` | Model list and status |
| `routes/auth.py` | `auth_bp` | Auth endpoints |
| `routes/stable_diffusion.py` | `sd_bp` | SD proxy routes |
| `routes/admin.py` | `admin_bp` | `/admin` â€” admin panel, user management |
| `routes/user_auth.py` | `user_auth_bp` | Login, register, quota endpoints |
| `routes/qr_payment.py` | `qr_bp` | QR payment routes (VietQR) |
| `routes/skills.py` | `skills_bp` | `/api/skills/*` â€” skill list, get, activate, deactivate |
| `routes/async_routes.py` | `async_bp` | `/chat/async` â€” async SSE streaming |

### Retired parallel API path

The parallel API package was removed in May 2026. Do not add compatibility shims or reintroduce a second runtime path while editing routes.

### Core logic â€” `services/chatbot/core/`

| File | Role |
|---|---|
| `core/chatbot.py` | `ChatbotAgent.chat()` â€” provider dispatch, tool routing |
| `core/tools.py` | Tool implementations: `google_search_tool`, `serpapi_web_search`, `serpapi_reverse_image`, `serpapi_image_search`, `saucenao_search_tool`, `reverse_image_search` |
| `core/config.py` | All API keys and constants (read from env) |
| `core/thinking_generator.py` | Thinking mode logic (instant/think/deep-think/multi-thinking) |
| `core/streaming.py` | SSE stream helpers and event formatting |
| `core/extensions.py` | Flask extensions shared across blueprints |
| `core/error_handler.py` | Centralized error handling |

### UI layer

| File | Role |
|---|---|
| `templates/index.html` | Chat UI â€” fetch calls, EventSource, form submission |
| `static/js/modules/api-service.js` | Core API client â€” `sendMessage()`, `sendStreamMessage()` |
| `static/js/modules/image-gen-v2.js` | Image gen API calls |
| `static/js/mcp.js` | MCP panel API calls |
| `static/js/main.js` | Video gen, gallery, title gen, file extract calls |

---

## Provider routing â€” how model selection works

```
Client sends { model: "grok" | "openai" | "deepseek" | "qwen" | "gemini" | "<name>-local" }
  â†’ ChatbotAgent.chat()
    â†’ model == "grok"     â†’ chat_with_grok()     [GROK_API_KEY, xAI API]
    â†’ model == "openai"   â†’ chat_with_openai()   [OPENAI_API_KEY]
    â†’ model == "deepseek" â†’ chat_with_deepseek()  [DEEPSEEK_API_KEY]
    â†’ model == "qwen"     â†’ chat_with_qwen()     [QWEN_API_KEY]
    â†’ model == "gemini"   â†’ chat_with_gemini()   [GOOGLE_API_KEY]
    â†’ model.endswith("-local") â†’ chat_with_local_model()
```

Default model: `grok` (configured in `core/config.py`).

---

## Tool dispatch â€” how tools are triggered

### Explicit tool selection (UI button â†’ `tools` parameter)

| UI button | Tool ID | Function |
|---|---|---|
| ðŸ” Web Search | `google-search` | `google_search_tool()` or `serpapi_web_search()` |
| Lens | `serpapi-reverse-image` | `serpapi_reverse_image()` â†’ cascade |
| Bing | `serpapi-bing` | `serpapi_web_search(engine="bing")` |
| Baidu | `serpapi-baidu` | `serpapi_web_search(engine="baidu")` |
| Img Search | `serpapi-images` | `serpapi_image_search()` |
| SauceNAO | `saucenao` | `saucenao_search_tool()` |

### Auto-trigger (realtime keyword detection in `routes/stream.py`)

Vietnamese patterns: giÃ¡, tá»· giÃ¡, thá»i tiáº¿t, tin tá»©c, hÃ´m nay, bitcoin, vÃ ng, chá»©ng khoÃ¡nâ€¦
English patterns: price, weather, news, latest, today, stock, bitcoin, crypto, goldâ€¦

When detected â†’ auto-injects `google_search_tool()` results into context.

### Search cascade order (do not break)

- **Web**: SerpAPI Google â†’ SerpAPI Bing/Baidu â†’ Google CSE fallback
- **Reverse image**: Google Lens â†’ Google Reverse Image â†’ Yandex

---

## SSE streaming contract

`POST /chat/stream` returns `text/event-stream` with these event types:

| Event | Payload | When |
|---|---|---|
| `thinking_start` | `{}` | Thinking mode activated |
| `thinking` | `{ content }` | Each thinking token/step |
| `thinking_end` | `{}` | Thinking complete |
| `chunk` | `{ content }` | Response text fragment |
| `complete` | `{ full_response, metadata }` | Final response + model info |
| `suggestions` | `{ suggestions: [...] }` | Follow-up suggestions |
| `error` | `{ error, message }` | Error occurred |

**Frontend contract**: `static/js/modules/api-service.js` â†’ `sendStreamMessage()` parses these events. Changing event names or payload shapes **will break the UI**.

---

## UI-to-backend endpoint map

| JS call site | Method | URL | Backend handler |
|---|---|---|---|
| `api-service.js` | POST | `/chat` | `routes/main.py` |
| `api-service.js` | POST | `/chat/stream` | `routes/stream.py` |
| `api-service.js` | GET | `/chat/stream/models` | `routes/stream.py` |
| `main.js` | POST | `/api/generate-title` | `routes/main.py` |
| `main.js` | POST | `/api/extract-file-text` | `routes/main.py` |
| `main.js` | POST | `/api/video/generate` | `routes/main.py` |
| `image-gen-v2.js` | POST | `/api/image-gen/generate` | `routes/image_gen.py` |
| `image-gen-v2.js` | GET | `/api/image-gen/gallery` | `routes/image_gen.py` |
| `image-gen-v2.js` | GET | `/api/image-gen/providers` | `routes/image_gen.py` |
| `mcp.js` | POST | `/api/mcp/enable` | `routes/mcp.py` |
| `mcp.js` | GET | `/api/mcp/list-files` | `routes/mcp.py` |
| `mcp.js` | POST | `/api/mcp/add-folder` | `routes/mcp.py` |
| `mcp.js` | POST | `/api/mcp/fetch-url` | `routes/mcp.py` |

---

## Monitor â€” what can silently break

1. **Blueprint registration order** â€” a new blueprint with an overlapping prefix can shadow existing routes.
2. **SSE event names** â€” renaming events (e.g. `chunk` â†’ `token`) breaks `api-service.js` parsing.
3. **Response shape changes** â€” adding/removing keys in `complete` event payload can break UI rendering.
4. **Tool ID mismatch** â€” UI sends tool IDs from `index.html`; backend matches by string. A rename on either side silently disables the tool.
5. **Auto-search keyword lists** â€” adding/removing patterns in `routes/stream.py` changes when web search fires.
6. **Provider method signature** â€” changing params in `chat_with_grok()` etc. can break the dispatch in `ChatbotAgent.chat()`.
7. **Runtime drift** â€” adding a second route path or compatibility shim creates mode-dependent behavior.
8. **Static file caching** â€” browser-cached JS may call old endpoints after a rename.

---

## Safe to touch

- `services/chatbot/core/` â€” chatbot logic, tools, config, streaming, thinking.
- `services/chatbot/routes/` â€” Flask blueprints.
- `services/chatbot/templates/` â€” Chat UI HTML.
- `services/chatbot/static/js/` â€” Frontend JS modules.
- `services/chatbot/src/` â€” STT, OCR, video gen, RAG helpers.
- `services/chatbot/tests/` â€” Unit tests.

## Do not touch unless the task explicitly requires it

- `services/stable-diffusion/` â€” SDXL stack.
- `services/edit-image/` â€” ComfyUI-based editing.
- `ComfyUI/` and `app/ComfyUI/` â€” External dependency.
- `app/image_pipeline/` â€” Image pipeline internals.
- `services/shared_env.py` â€” Only if env loading logic needs changing.
- `app/config/.env*` â€” Only to add new variable placeholders.

---

## Required output after each change

When using this skill, structure your response with:

1. **Route impact** â€” Which endpoints changed? New, modified, or removed?
2. **UI impact** â€” Does any JS call site need updating? Will the response shape change?
3. **Provider impact** â€” Does this affect model routing or tool dispatch?
4. **Runtime contract** â€” Did the change stay on the Flask monolith path and preserve response shapes?
5. **Verification steps** â€” How to confirm the change works.

---

## Pre-patch checklist

Before making changes:

- [ ] Identified the exact Flask blueprint entry point.
- [ ] Traced the request path from UI â†’ route â†’ core â†’ response.
- [ ] Checked if the endpoint is called from `api-service.js`, `main.js`, `mcp.js`, `image-gen-v2.js`, or `index.html`.
- [ ] Confirmed the current SSE event names and response shapes used by the frontend.
- [ ] Checked for auto-search trigger patterns that may be affected.

## Post-patch checklist

After making changes:

- [ ] `pytest services/chatbot/tests/ -v` passes.
- [ ] `/chat/stream` still returns valid SSE events with correct event names.
- [ ] All JS fetch calls in `static/js/` and `templates/` still match backend route paths.
- [ ] Tool IDs in `index.html` still match what `core/tools.py` and `routes/stream.py` expect.
- [ ] No compatibility shim or second runtime path was introduced.
- [ ] If a new route was added, blueprint registration in `chatbot_main.py` is confirmed.
- [ ] If a response shape changed, `api-service.js` event parsing was updated.
- [ ] No image-pipeline or ComfyUI files were modified for a chatbot-only change.
