---
name: tool-response-contract
description: "Define and enforce response-shape contracts for every tool function, route handler, SSE event, and MCP tool in the chatbot stack. Use when: adding or modifying a tool function return type, changing a route's JSON response, adding or changing an SSE event payload, modifying an MCP tool's return schema, debugging frontend crashes from missing response fields, reviewing backward compatibility of response changes, or tracing how a response shape flows from backend to frontend."
---

# Tool Response Contract

## When to use this skill

- Adding, renaming, or removing a field in any tool function return value.
- Changing a route handler's `jsonify()` response structure or HTTP status codes.
- Adding or modifying an SSE event type or its payload keys.
- Changing an MCP tool's `Dict[str, Any]` return schema.
- Debugging frontend `Cannot read property X of undefined` errors.
- Reviewing backward compatibility before deploying a response-shape change.
- Tracing a response field from backend origin → SSE wire → frontend consumer.

---

## Contract-first workflow

**Every response-shape change MUST follow this sequence:**

```
1. IDENTIFY the output surface being changed  (tool function / route / SSE event / MCP tool)
2. TRACE all consumers                        (stream.py injection, frontend callback, MCP client)
3. ASSESS impact                              (additive? breaking? optional field?)
4. IMPLEMENT change                           (prefer additive, backward-compatible)
5. VERIFY checklist                           (Section 10 below)
6. DOCUMENT in response impact summary        (Section 9 below)
```

**Rule — trace before edit:** Before changing *any* return shape, you MUST identify every consumer of that output. Search downstream: if a tool function → find where stream.py reads it; if an SSE event → find the frontend callback; if a route → find the JS fetch call. Do NOT modify a response shape without confirming the consumer list.

---

## Safe-touch and avoid zones

### Safe to edit (with contract trace)

| Layer | Files | Notes |
|-------|-------|-------|
| Tool functions | `services/chatbot/core/tools.py` | Return type must stay `str` (except `reverse_image_search` → `dict`) |
| Stream contract | `services/chatbot/core/stream_contract.py` | `build_complete_event_payload()` — add fields only, never remove |
| SSE emitter | `services/chatbot/routes/stream.py` | `_emit()` helper and all `yield _emit(...)` call sites |
| Route handlers | `services/chatbot/routes/*.py` | Follow the existing pattern for that route module |
| MCP tools | `services/mcp-server/server.py` | All `@mcp.tool()` functions return `Dict[str, Any]` |
| Frontend parser | `services/chatbot/static/js/modules/api-service.js` | SSE callback dispatch |

### Avoid zones (do not touch for response-contract tasks)

| Zone | Why |
|------|-----|
| `ComfyUI/`, `app/image_pipeline/` | Image services — separate response contracts |
| `services/stable-diffusion/`, `services/edit-image/` | Image services |
| Flask route response shapes | Preserve the monolith contract consumed by the UI |
| `services/chatbot/core/chatbot.py` model dispatch | Provider routing, not response contracts |

---

## Response type registry

### Tool functions (core/tools.py)

**Rule:** All search functions return `str` (markdown-formatted). Only `reverse_image_search()` returns `dict`.

| Function | Return | Success shape | Error shape |
|----------|--------|---------------|-------------|
| `google_search_tool()` | `str` | Markdown `"🔍 **Kết quả...**\n..."` | `"❌ API Key không được cấu hình"` |
| `github_search_tool()` | `str` | Markdown string | `"❌ Lỗi: {e}"` |
| `saucenao_search_tool()` | `str` | Markdown string | `"❌ Lỗi: {e}"` |
| `serpapi_web_search()` | `str` | Markdown string | `"❌ ..."` or empty `""` |
| `serpapi_reverse_image()` | `str` | Markdown string (cascades engines) | `"❌ ..."` |
| `serpapi_image_search()` | `str` | Markdown string | `"❌ ..."` |
| `reverse_image_search()` | `dict` | `{"sources": [...], "similar": [...], "knowledge": str\|None, "summary": str}` | `{"error": "message"}` |

**How tool results reach the frontend:** Search results are **injected into the user message** as text before sending to the LLM:

```python
# stream.py — search result injection
if search_results:
    message = f"{message}\n\n---\n📋 DỮ LIỆU THỰC TẾ TỪ WEB:\n{search_results}\n---\n"
```

Tool results are **NOT** sent as separate SSE events. The model sees them in context and incorporates them into its response.

### reverse_image_search() detailed contract

```python
# Success — guaranteed keys:
{
    "sources": [
        {"title": str, "author": str|None, "url": str,
         "thumbnail": str|None, "similarity": float|None,
         "source_engine": str},  # "saucenao", "google_lens", etc.
    ],
    "similar": [  # same schema as sources
    ],
    "knowledge": str | None,    # Knowledge panel text
    "summary": str,             # Always present, even if "no results"
}
# Error:
{"error": "message"}
```

---

## SSE event catalog

**Wire format:** All events use `StreamEvent(event=type, data=json.dumps(payload)).format()` from `core/streaming.py`.

**Emitter helper:** `_emit(event, payload)` in `stream.py` wraps payload with `with_request_id()`.

### Event 1: `metadata` — emitted first

```python
{
    "model": str,                      # e.g. "grok"
    "context": str,                    # e.g. "casual"
    "deep_thinking": bool,
    "thinking_mode": str,              # "instant"|"think"|"deep-think"|"multi-thinking"|"auto"
    "stream_backend": "flask",
    "stream_contract_version": "v2",
    "web_search": bool,               # True if auto-search triggered
    "streaming": bool,                 # Always true
    "timestamp": str,                  # ISO format
}
```
**Consumer:** Not explicitly handled by a named callback in current frontend — sent for informational/debug use.

### Event 2: `thinking_start`

```python
{
    "category": str,                   # detect_category() result
    "timestamp": str,                  # ISO format
    "mode": str,                       # OPTIONAL — "multi-thinking" only
    "label": str,                      # OPTIONAL — "4-Agents Reasoning"
}
```
**Consumer:** `callbacks.onThinkingStart(data)`

### Event 3: `thinking` (streamed multiple times)

```python
{
    "step": str,                       # Reasoning text chunk
    "step_index": int,                 # Sequential number
    "category": str,
    "is_reasoning_chunk": bool,        # True if from model native reasoning
    "trajectory_id": str,              # OPTIONAL — multi-thinking only
}
```
**Consumer:** `callbacks.onThinking(data)`

### Event 4: `thinking_end`

```python
{
    "summary": str,                    # Human-readable reasoning summary
    "steps": list[str],               # All thinking steps
    "category": str,
    "duration_ms": int,
    "rounds": int,                     # OPTIONAL — multi-thinking only
    "trajectories": int,              # OPTIONAL — multi-thinking only
}
```
**Consumer:** `callbacks.onThinkingEnd(data)`

### Event 5: `chunk` (streamed many times)

```python
{
    "content": str,                    # Text segment
    "chunk_index": int,                # Sequential number
}
```
**Consumer:** `callbacks.onChunk(data)`

### Event 6: `complete` — emitted last (final event)

Payload built by `build_complete_event_payload()` in `core/stream_contract.py`:

```python
{
    "response": str,                   # Full assembled response text
    "model": str,
    "context": str,
    "deep_thinking": bool,
    "thinking_mode": str,
    "total_chunks": int,
    "thinking_summary": str,
    "thinking_steps": list[str],
    "thinking_duration_ms": int,
    "timestamp": str,                  # ISO format
    "elapsed_time": float,             # Seconds, 3 decimals
    "tokens": int,
    "max_tokens": int,
    "request_id": str,                 # UUID hex[:12]
    "time_to_first_chunk": float,      # OPTIONAL
}
```
**Consumer:** `callbacks.onComplete(data)` — result stored as final response.

### Event 7: `error`

```python
{
    "error": str,                      # Error message
    "request_id": str,                 # OPTIONAL — if available
}
```
**Consumer:** `callbacks.onError(data)`

### Event 8: `suggestions` — placeholder (not yet implemented)

```python
{}  # Structure TBD
```
**Consumer:** `callbacks.onSuggestions(data)` — registered but not triggered.

### Keepalive

SSE comment line `": keepalive\n\n"` — not a named event.

---

## Route response patterns

### Pattern summary by module

| Module | Success pattern | Error pattern | Notes |
|--------|----------------|---------------|-------|
| `conversations.py` | Bare dict or `{"conversations": [...]}` | `{"error": "..."}, 4xx/5xx` | No `success` field |
| `mcp.py` | `{"success": true, ...}` | `{"success": false, "error": "..."}, 4xx/5xx` | Always has `success` |
| `image_gen.py` | `{"success": true, "image_id": ..., ...}` | `{"error": "..."}, 400/403/429` | `success` only on success |
| `memory.py` | `{"success": true, "memory": ...}` or `{"memories": [...]}` | `{"error": "..."}, 4xx/5xx` | Mixed — some have `success`, some don't |
| `main.py` (`/chat`) | `{"success": true, "response": ..., ...}` | `{"error": "..."}, 500` | Always has `success` |
| `models.py` | `MODEL_CATALOG` dict | — | Static data |

### Conversations (conversations.py)

| Endpoint | Method | Success (200) | Error |
|----------|--------|---------------|-------|
| `/conversations` | GET | `{"conversations": [...], "count": int}` | `{"error": "..."}, 503/500` |
| `/conversations/<id>` | GET | Full conversation dict | `{"error": "..."}, 404/500` |
| `/conversations/<id>` | DELETE | `{"message": "..."}` | `{"error": "..."}, 503/500` |
| `/conversations/<id>/archive` | POST | `{"message": "..."}` | `{"error": "..."}, 503/500` |
| `/conversations/new` | POST | New conversation dict | `{"error": "..."}, 500` |
| `/conversations/<id>/switch` | POST | `{"message": "...", "conversation": {...}}` | `{"error": "..."}, 404/500` |

### MCP routes (mcp.py)

| Endpoint | Success | Error |
|----------|---------|-------|
| `GET /grep` | `{"success": true, "pattern": str, "results": [...], "count": int}` | `{"success": false, "error": "..."}, 400/500` |
| `POST /enable` | `{"success": true\|false, "status": {...}}` | `{"success": false, "error": "..."}, 500` |
| `POST /disable` | `{"success": true, "status": {...}}` | Same |
| `POST /add-folder` | `{"success": true\|false, "status": {...}}` | `{"success": false, "error": "..."}, 400/500` |
| `POST /remove-folder` | Same as add-folder | Same |

### Image generation (image_gen.py)

| Endpoint | Success | Error |
|----------|---------|-------|
| `POST /api/image-gen/generate` | `{"success": true, "image_id": str, "images": [...], "provider": str, "model": str, "prompt": str, "timestamp": str}` | `{"error": "..."}, 400/403/429` or `{"error": "...", "quota_exceeded": true}, 403` |
| `GET /api/image-gen/health` | Health status dict | — |
| `GET /api/image-gen/providers` | Provider list dict | — |
| `GET /api/image-gen/styles` | Styles dict | — |

### Memory (memory.py)

| Endpoint | Success | Error |
|----------|---------|-------|
| `POST /save` | `{"success": true, "memory": {...}, "message": "..."}` | `{"error": "..."}, 400/500` |
| `GET /list` | `{"memories": [...]}` | `{"error": "..."}, 500` |
| `GET /get/<id>` | `{"memory": {...}}` | `{"error": "..."}, 404/500` |
| `DELETE /delete/<id>` | `{"success": true, "message": "..."}` | `{"error": "..."}, 404/500` |
| `PUT /update/<id>` | `{"success": true, "memory": {...}}` | `{"error": "..."}, 404/500` |
| `GET /search` | `{"memories": [...]}` | `{"error": "..."}, 500` |

### Main routes (main.py)

| Endpoint | Success | Error |
|----------|---------|-------|
| `POST /chat` | `{"success": true, "response": str, "model": str, "context": str, "deep_thinking": bool, "thinking_process": str, "tools": [...], "timestamp": str}` | `{"error": "..."}, 500` |
| `GET /api/health/databases` | `{"ok": bool, ...}, 200\|503` | — |

### HTTP status code reference

| Code | When | Example |
|------|------|---------|
| 200 | Success | Memory saved, conversation listed |
| 400 | Validation | Missing required field, bad input |
| 403 | Forbidden / quota | Image gen quota exceeded |
| 404 | Not found | Conversation / memory not found |
| 429 | Rate limited | Too many image gen requests |
| 500 | Server error | Unhandled exception |
| 503 | Service unavailable | MongoDB not enabled |

---

## MCP tool return schemas

All `@mcp.tool()` functions in `services/mcp-server/server.py` return `Dict[str, Any]`. Error case always uses `{"error": "..."}`.

### search_files()

```python
# Success:
{"query": str, "file_type": str, "total_found": int,
 "results": [{"filename": str, "path": str, "full_path": str, "size": int}]}
# Error:
{"error": "File không tồn tại: {file_path}"}
```

### read_file_content()

```python
# Success:
{"file_path": str, "total_lines": int, "lines_read": int, "truncated": bool, "content": str}
# Error:
{"error": "Lỗi đọc file: {e}"}
```

### list_directory()

```python
{"directory": str, "total_items": int,
 "folders": [{"name": str, "size": None, "modified": str}],
 "files":   [{"name": str, "size": int,  "modified": str}]}
```

### get_project_info()

```python
{"project_name": "AI-Assistant", "base_directory": str,
 "services": [str],
 "structure": {"config": bool, "services": bool, "tests": bool,
               "docs": bool, "resources": bool, "local_data": bool},
 "description": str}
```

### search_logs()

```python
{"service_filter": str, "level_filter": str, "logs_found": int,
 "data": [{"service": str, "file": str, "total_lines": int, "entries": [str]}]}
```

### calculate()

```python
# Success:
{"expression": str, "result": float|int|complex, "type": str}
# Error:
{"expression": str, "error": str}
```

---

## Frontend consumer map

**File:** `services/chatbot/static/js/modules/api-service.js` (lines ~96–205)

### SSE callback dispatch

```javascript
switch (currentEvent) {
    case 'thinking_start': callbacks.onThinkingStart(data);  break;
    case 'thinking':       callbacks.onThinking(data);       break;
    case 'thinking_end':   callbacks.onThinkingEnd(data);    break;
    case 'chunk':          callbacks.onChunk(data);          break;
    case 'complete':       result = data; callbacks.onComplete(data); break;
    case 'suggestions':    callbacks.onSuggestions(data);    break;
    case 'error':          callbacks.onError(data);          break;
}
```

### Callback → required data keys

| Callback | Required keys | Optional keys |
|----------|---------------|---------------|
| `onThinkingStart` | `category`, `timestamp` | `mode`, `label` |
| `onThinking` | `step`, `step_index`, `category`, `is_reasoning_chunk` | `trajectory_id` |
| `onThinkingEnd` | `summary`, `steps`, `category`, `duration_ms` | `rounds`, `trajectories` |
| `onChunk` | `content`, `chunk_index` | — |
| `onComplete` | All 14 fields from `build_complete_event_payload()` | `time_to_first_chunk` |
| `onError` | `error` | `request_id` |
| `onSuggestions` | — | TBD (not implemented) |

### Non-SSE API consumers

| JS call | Backend endpoint | Expected response keys |
|---------|-----------------|----------------------|
| `sendMessage()` | `POST /chat` | `success`, `response`, `model`, `context`, `deep_thinking`, `thinking_process`, `tools`, `timestamp` |
| `saveMemory()` | `POST /memory/save` | `success`, `memory`, `message` |
| `listMemories()` | `GET /memory/list` | `memories` |

---

## Monitor: success, partial success, and failure outcomes

When modifying a response shape, assess impact across three outcome categories:

### Success path

The happy path works end-to-end: backend returns expected shape → SSE events carry all required keys → frontend callback processes without error → UI renders correctly.

**Monitor points:**
- Tool function returns correct type (`str` or `dict` per registry)
- `build_complete_event_payload()` receives all required kwargs
- All SSE events include required keys per catalog above
- Frontend callback receives data with all expected keys
- HTTP status is 200

### Partial success path

The request completes but with degraded output: optional fields are `null`, search returns empty, thinking mode falls back to simpler mode.

**Monitor points:**
- Optional SSE fields (`trajectory_id`, `rounds`, `mode`, `label`) may be absent — frontend must not crash
- `time_to_first_chunk` in complete event may be `None`
- Tool function returns `""` (empty string) on search failure — message injection is skipped (this is correct)
- `reverse_image_search()` returns `{"sources": [], "similar": [], "knowledge": null, "summary": "no results"}` — valid partial success

### Failure path

An error terminates the request or stream.

**Monitor points:**
- Tool functions: return error string `"❌ ..."` (6 functions) or `{"error": "..."}` (1 function)
- Routes: return `jsonify({"error": "..."}), 4xx/5xx`
- SSE stream: emit `error` event with `{"error": str, "request_id": str|null}`, then stop
- MCP tools: return `{"error": "..."}` — never raise exceptions to the client
- Frontend: `onError(data)` callback fires — must handle gracefully

---

## Response impact summary template

After every response-shape change, append this to your PR description or commit message:

```
### Response Impact Summary

**Surface changed:** [tool function | route handler | SSE event | MCP tool]
**File(s) modified:** [list files]
**Change type:** [additive | modification | removal]
**Backward compatible:** [yes | no — if no, explain migration]

**Consumers affected:**
- [ ] stream.py injection (tool functions only)
- [ ] Frontend callback: [callback name]
- [ ] MCP client
- [ ] Other route consumer: [endpoint]

**Fields added:** [list new fields, or "none"]
**Fields removed:** [list removed fields, or "none"]
**Fields modified:** [list changed fields with old→new type, or "none"]

**Tested:** [how verified — unit test, manual SSE check, frontend console]
```

---

## Backward compatibility rules

1. **Prefer additive changes.** Adding a new field to a response dict is always safe if the frontend ignores unknown keys (it does — `JSON.parse` keeps extra fields).
2. **Never remove a field** that a frontend callback reads without updating the frontend first.
3. **Never change a field's type** (e.g. `str` → `dict`, `int` → `str`) without updating all consumers.
4. **Never change a field's name** (`thinking_steps` → `thinkingSteps`) — frontend keys are case-sensitive.
5. **Never change a tool function's return type** from `str` to `dict` (or vice versa) — stream.py injection expects strings.
6. **New optional fields** must default to `None`/`null` and be documented in the SSE catalog above.
7. **MCP tools** must always return `Dict[str, Any]` — never raise exceptions to the transport.

---

## Response-shape validation checklist

Before merging any response-shape change:

- [ ] **Return type matches contract** — tool function returns `str` (or `dict` for `reverse_image_search` only)
- [ ] **All required SSE keys present** — cross-reference callback → required keys table above
- [ ] **HTTP status code correct** — 200 for success, 4xx for client error, 5xx for server error
- [ ] **`request_id` propagated** — via `with_request_id(payload, request_id)` in stream events
- [ ] **Field names exact case** — `thinking_steps` not `thinkingSteps`, `elapsed_time` not `elapsedTime`
- [ ] **Optional fields marked** — new optional fields default to `None` and are noted in this skill
- [ ] **Frontend callback tested** — verify the JS callback parses the changed event without error
- [ ] **Error shape consistent** — routes: `{"error": "..."}` with proper HTTP code; tools: error string; MCP: `{"error": "..."}`
- [ ] **Search results injected correctly** — tool results go into message context, NOT as separate SSE events
- [ ] **`build_complete_event_payload` kwargs match** — if adding a field to complete event, update both the function and the call site
- [ ] **Backward compatible** — no field removals, no type changes, no renames without consumer updates
- [ ] **Response impact summary written** — template in Section 9 above, filled in PR/commit

---

## Known inconsistencies (do not propagate)

| Issue | Where | Correct behavior |
|-------|-------|-----------------|
| Routes use mixed patterns for success (`success: true` vs bare dict) | `conversations.py` vs `mcp.py` | New routes should include `success` field for clarity. Do not refactor existing routes unless asked. |
| `reverse_image_search()` is the only tool returning `dict` | `core/tools.py` | Keep it as-is — `stream.py` handles both `str` and `dict` returns from this function |
| `metadata` SSE event has no named frontend callback | `api-service.js` | Informational event — frontend may handle it later |
| `suggestions` event type registered but not implemented | `stream.py` / `api-service.js` | Placeholder — do not emit until schema is defined |
| Error messages in Vietnamese (`"❌ Lỗi..."`, `"File không tồn tại"`) | `tools.py`, `server.py` | Existing convention — do not change to English unless refactoring i18n |

---

## File reference

| File | Purpose | Key locations |
|------|---------|---------------|
| `services/chatbot/core/tools.py` | Tool functions | ~21, ~119, ~176, ~287, ~330, ~444, ~488 |
| `services/chatbot/core/stream_contract.py` | Complete event builder | ~23 (`build_complete_event_payload`) |
| `services/chatbot/core/streaming.py` | StreamEvent dataclass | ~12 |
| `services/chatbot/routes/stream.py` | SSE streaming, `_emit()`, search injection | ~336, ~462, ~469+, ~735 |
| `services/chatbot/routes/conversations.py` | Conversation CRUD responses | ~19+ |
| `services/chatbot/routes/mcp.py` | MCP proxy responses | ~26+ |
| `services/chatbot/routes/image_gen.py` | Image gen responses | ~152 |
| `services/chatbot/routes/memory.py` | Memory CRUD responses | ~18+ |
| `services/chatbot/routes/main.py` | `/chat`, health responses | ~119, ~413 |
| `services/chatbot/routes/models.py` | Model catalog | ~31 |
| `services/mcp-server/server.py` | MCP tool return schemas | ~119, ~213, ~257, ~319, ~361, ~420 |
| `services/chatbot/static/js/modules/api-service.js` | Frontend SSE parser + API consumers | ~96–205 |

---

## Related skills

- **search-tool-cascade** — tool selection and fallback order
- **core-chatbot-routing-audit** — request path and tool dispatch wiring
- **mcp-tool-authoring** — MCP tool registration and return contracts
- **thinking-mode-routing** — thinking event lifecycle
- **docs-drift-sync** — update docs when response schemas change
