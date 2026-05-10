# Agentic Council — API Reference

> **Version**: v1
> **Base path**: `services/chatbot/`

---

## Endpoints

### POST /chat (JSON — non-streaming)

Existing endpoint, extended with council support.

**Request body** (`ChatRequest`):

```json
{
  "message": "Compare Python and Rust",
  "model": "grok",
  "agent_mode": "council",
  "max_agent_iterations": 2,
  "preferred_planner_model": "openai",
  "preferred_researcher_model": "gemini",
  "preferred_critic_model": "grok",
  "preferred_synthesizer_model": "stepfun"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `message` | `string` | **required** | User question (min 1 char) |
| `model` | `string` | `"grok"` | Base model (used for non-council path) |
| `agent_mode` | `string` | `"off"` | `"off"` / `"council"` / `"grok_native_research"` |
| `max_agent_iterations` | `int` | `2` | Max Planner→Critic rounds (1-5) |
| `preferred_planner_model` | `string?` | `null` | Override planner model |
| `preferred_researcher_model` | `string?` | `null` | Override researcher model |
| `preferred_critic_model` | `string?` | `null` | Override critic model |
| `preferred_synthesizer_model` | `string?` | `null` | Override synthesizer model |

**Response** (`ChatResponse`):

```json
{
  "response": "Python excels at rapid prototyping while Rust...",
  "model": "council",
  "context": "casual",
  "deep_thinking": true,
  "thinking_process": "Council completed in 1 round(s), 4 LLM calls, 3.2s.\nExit reason: approved.\nQuality score: 8/10.",
  "citations": null,
  "agent_run_id": "a1b2c3d4e5f6...",
  "agent_trace_summary": {
    "rounds": 1,
    "agents_used": ["planner", "researcher", "synthesizer", "critic"],
    "total_llm_calls": 4,
    "total_tokens": 3200,
    "elapsed_seconds": 3.2,
    "decision": {
      "approved": true,
      "iterations_used": 1,
      "iterations_max": 2,
      "final_quality_score": 8,
      "exit_reason": "approved",
      "warnings": []
    }
  }
}
```

| Field | Type | Description |
|---|---|---|
| `response` | `string` | Final synthesized answer (Markdown) |
| `model` | `string` | Always `"council"` for council mode |
| `deep_thinking` | `bool` | Always `true` for council mode |
| `thinking_process` | `string` | Human-readable summary of the critic loop |
| `agent_run_id` | `string?` | UUID for log correlation (null when disabled) |
| `agent_trace_summary` | `object?` | Trace metadata (null when disabled) |

---

### POST /chat/council/stream (SSE — streaming)

Streams progress events as the council pipeline executes.

**Request body**: Same as `/chat`.

**Response**: `text/event-stream` with two event types:

#### Event: `council_event` (progress updates)

```
event: council_event
data: {"run_id":"abc123","stage":"planning","role":"planner","status":"started","round":1,"timestamp":"2026-04-03T10:00:00Z","short_message":"Decomposing task into sub-questions"}
```

| Field | Type | Values |
|---|---|---|
| `run_id` | `string` | Council run ID |
| `stage` | `string` | `planning` / `researching` / `synthesizing` / `critiquing` / `retrying` / `completed` / `failed` |
| `role` | `string` | `planner` / `researcher` / `synthesizer` / `critic` / `orchestrator` |
| `status` | `string` | `started` / `progress` / `completed` / `skipped` |
| `round` | `int` | Current iteration (1-based) |
| `timestamp` | `string` | ISO 8601 UTC |
| `short_message` | `string` | Human-readable note (max 300 chars, no raw reasoning) |

#### Event: `council_result` (final response)

```
event: council_result
data: { ... same as ChatResponse JSON ... }
```

#### Event: `council_error` (pipeline failure)

```
event: council_error
data: {"error": "Pipeline failed: ...", "run_id": "abc123"}
```

---

### POST /chat/upload (multipart — with files)

Existing endpoint, extended with `agent_mode` form field.

```
POST /chat/upload
Content-Type: multipart/form-data

message=Compare these documents
model=grok
agent_mode=council
file=@document.pdf
```

---

## Model Resolution

Each agent role has a fallback chain. The first available model wins:

| Role | Chain |
|---|---|
| Planner | openai → deepseek → grok → gemini |
| Researcher | gemini → grok → openai → deepseek |
| Critic | grok → deepseek → openai → gemini |
| Synthesizer | stepfun → step-flash → openai → grok → gemini |

**Override priority**: `preferred_*_model` > role chain > global fallback > `"grok"`.

---

## Configuration

### CouncilConfig

| Field | Type | Default | Range | Description |
|---|---|---|---|---|
| `max_rounds` | `int` | `2` | 1-5 | Max Planner→Critic iterations |
| `quality_threshold` | `int` | `7` | 1-10 | Score to auto-approve |
| `planner_model` | `string` | `"openai"` | — | Model for Planner |
| `researcher_model` | `string` | `"gemini"` | — | Model for Researcher |
| `critic_model` | `string` | `"grok"` | — | Model for Critic |
| `synthesizer_model` | `string` | `"stepfun"` | — | Model for Synthesizer |
| `enable_tools` | `bool` | `true` | — | Allow Researcher tool calls |
| `enable_rag` | `bool` | `true` | — | Allow RAG queries |
| `enable_mcp` | `bool` | `true` | — | Allow MCP file context |

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGENTIC_V1_ENABLED` | `false` | Kill-switch for the council pipeline |
| `BLACKBOARD_BACKEND` | `memory` | `"memory"` or `"redis"` |

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Feature flag off | Returns graceful message, no pipeline execution |
| Agent raises exception | Orchestrator catches, returns degraded `FinalDecision` with `exit_reason="error"` |
| LLM returns invalid JSON | Agent uses fallback output (safe defaults) |
| All models unavailable | Falls back to `"grok"` as absolute last resort |
| Unknown `agent_mode` | Falls through to standard chatbot path |
