# xAI Native Multi-Agent Research — API & Architecture

> **Version**: v1 (beta)
> **Base path**: `services/chatbot/`
> **Feature flag**: `XAI_NATIVE_MULTI_AGENT_ENABLED=true`

---

## Overview

A **separate execution path** that delegates multi-agent research to xAI's
server-side infrastructure via the [Responses API](https://docs.x.ai/developers/rest-api-reference/inference/chat#create-new-response).

| Aspect | Council mode | xAI Native mode |
|---|---|---|
| Agent orchestration | Internal (4 agents, local) | Server-side (xAI multi-agent) |
| Model | Any registered model | `grok-4.20-multi-agent` |
| Agent count | Always 4 | 4 or 16 (via `reasoning_effort`) |
| Tools | Local: web search, RAG, MCP | Server-side: `web_search`, `x_search` |
| Streaming events | `council_event` / `council_result` | `xai_native_event` / `xai_native_chunk` / `xai_native_result` |
| Feature flag | `AGENTIC_V1_ENABLED` | `XAI_NATIVE_MULTI_AGENT_ENABLED` |

### When to use which

- **Council**: Full control over agent behaviour, custom prompts per role,
  local RAG/MCP integration, detailed step-by-step trace.
- **xAI Native**: Deep multi-source web research, higher-quality synthesis
  for factual/comparative queries, less latency tuning needed.

---

## Endpoints

### POST /chat (JSON — non-streaming)

Set `agent_mode` to `"grok_native_research"`:

```json
{
  "message": "Research the latest breakthroughs in quantum computing",
  "agent_mode": "grok_native_research",
  "reasoning_effort": "high",
  "enable_web_search": true,
  "enable_x_search": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `agent_mode` | `string` | `"off"` | Set to `"grok_native_research"` |
| `reasoning_effort` | `string` | `"high"` | `"low"` / `"medium"` → 4 agents; `"high"` → 16 agents |
| `enable_web_search` | `bool` | `true` | Enable server-side web search |
| `enable_x_search` | `bool` | `false` | Enable server-side X/Twitter search |

**Response** (`ChatResponse`):

```json
{
  "response": "## Quantum Computing Breakthroughs...",
  "model": "grok-native",
  "context": "casual",
  "deep_thinking": true,
  "thinking_process": "xAI multi-agent research completed in 12.3s...",
  "citations": [
    {"url": "https://...", "title": "Source", "source": "xai_web_search"}
  ],
  "agent_run_id": "e7fd6e3f-0a77-9948-99a9-b40ba7c1c6f1",
  "agent_trace_summary": {
    "response_id": "e7fd6e3f-...",
    "model": "grok-4.20-multi-agent",
    "status": "completed",
    "reasoning_effort": "high",
    "total_tokens": 12500,
    "reasoning_tokens": 8000,
    "sources_used": 15,
    "server_tool_calls": 8,
    "elapsed_seconds": 12.3
  }
}
```

### POST /chat/xai-native/stream (SSE streaming)

Same request body as `/chat`. Returns SSE events:

| Event | Payload | Description |
|---|---|---|
| `xai_native_event` | `{"stage": "starting", "model": "...", "reasoning_effort": "..."}` | Pipeline started |
| `xai_native_event` | `{"stage": "thinking", "reasoning_tokens": 500}` | Reasoning progress |
| `xai_native_chunk` | `{"text": "partial text..."}` | Content delta |
| `xai_native_result` | Full `ChatResponse` dict | Final result |
| `xai_native_error` | `{"error": "message"}` | On failure |

---

## Architecture

```
ChatRequest (agent_mode="grok_native_research")
    │
    ├── chat.py: _do_chat() ──→ run_xai_native()
    │                               │
    │                               ├── XaiNativeConfig
    │                               ├── _build_system_prompt()
    │                               └── XaiResponsesAdapter.call()
    │                                       │
    │                                       └── POST https://api.x.ai/v1/responses
    │
    └── xai_native_stream.py ──→ run_xai_native_stream()
                                    │
                                    └── XaiResponsesAdapter.stream()
                                            │
                                            └── POST (stream=true) → SSE events
```

### File layout

```
core/agentic/xai_native/
├── __init__.py       # Public exports
├── adapter.py        # HTTP client for xAI Responses API
├── contracts.py      # XaiNativeConfig, XaiNativeResult, XaiUsage, etc.
└── entrypoint.py     # run_xai_native(), run_xai_native_stream()

fastapi_app/routers/
├── chat.py           # Updated: grok_native_research branch
└── xai_native_stream.py  # SSE streaming endpoint
```

---

## Configuration

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROK_API_KEY` | Yes | — | xAI API key (shared with existing grok model) |
| `XAI_NATIVE_MULTI_AGENT_ENABLED` | No | `false` | Feature flag to enable the mode |

### Reasoning effort → Agent count

| `reasoning_effort` | Agent count | Best for |
|---|---|---|
| `"low"` / `"medium"` | 4 | Quick research, focused queries |
| `"high"` | 16 | Deep research, complex multi-faceted topics |

---

## Security

- **No hidden reasoning exposed**: Sub-agent internal state and encrypted
  reasoning content are never returned to the client.
- **Safe trace metadata only**: `agent_trace_summary` contains operational
  metrics (tokens, elapsed time, sources count) — not internal prompts or
  intermediate agent outputs.
- **API key isolation**: Uses the existing `GROK_API_KEY` — no new secrets needed.
- **Store disabled**: `store: false` is sent to xAI, so queries are not
  persisted on xAI's side.

---

## Limitations (xAI multi-agent beta)

- **No client-side function calling**: Custom tools / function calling not
  supported by the multi-agent model. Only built-in tools (web_search,
  x_search) are available.
- **No Chat Completions API**: Must use Responses API (handled by adapter).
- **No `max_tokens` control**: Not supported by the multi-agent model.
- **Higher token usage**: Multiple agents running in parallel consume
  significantly more tokens than single-agent requests.

---

## Tests

```bash
cd services/chatbot
python -m pytest tests/test_xai_native.py -v
```

46 tests covering contracts, adapter payload/parsing, HTTP calls (mocked),
entrypoint helpers, feature flag, streaming, and error handling.
