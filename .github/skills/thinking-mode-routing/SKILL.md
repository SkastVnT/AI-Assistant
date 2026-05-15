---
name: thinking-mode-routing
description: "Reason about chatbot thinking modes and route requests to the correct mode. Use when adding or changing a thinking mode, modifying mode selection UI, changing how mode affects backend routing or tool dispatch, debugging broken thinking/reasoning display, or reviewing SSE event flow for thinking modes."
---

# Thinking-Mode Routing

## When to use this skill

- Adding a new thinking mode or renaming an existing one.
- Changing how the UI selects or displays a mode.
- Changing how the backend interprets the `thinking_mode` parameter.
- Modifying SSE event types or payload shapes for thinking events.
- Debugging broken reasoning display (steps not showing, mode mismatch).
- Editing the agentic pipeline (Planner → Researcher → Critic → Synthesizer).
- Reviewing whether a change to chatbot or streaming code preserves the Flask SSE contract.

## Mode registry

| Mode string | UI label | `deep_thinking` | Behavior |
|---|---|---|---|
| `instant` | Instant ⚡ | `False` | No thinking display; direct model response |
| `auto` | *(default when mode omitted)* | `False` | Parses native `<think>` tags from model output; does not force reasoning |
| `thinking` | *(alias used in backend mapping)* | `True` | Standard thinking with step display |
| `deep` | *(alias used in backend mapping)* | `True` | Same as `thinking` — both set `deep_thinking=True` |
| `multi-thinking` | 4-Agents 🧠 | `True` | 4-agent council: Planner → Researcher → Critic → Synthesizer |

**UI exposes two options** in the dropdown (`templates/index.html` lines 648–662):
- `instant` (default, active on load)
- `multi-thinking` (4-Agents)

**Backend also accepts** `thinking`, `deep`, and `auto` via the API even though the UI does not surface them directly.

## Request path — mode selection to rendered response

```
1. UI: user clicks thinking-mode dropdown
   → templates/index.html: .thinking-mode-option[data-mode="..."]
   → sets #thinkingModeValue hidden input
   → window.getThinkingMode() returns the value

2. JS: sendStreamMessage() reads thinkingMode
   → static/js/modules/api-service.js line 22-75
   → POST /chat/stream body: { thinking_mode: "instant"|"multi-thinking"|... }

3. Flask route: routes/stream.py line 258-264
   → thinking_mode = data.get('thinking_mode', 'auto')
   → if thinking_mode in ('thinking', 'deep', 'multi-thinking'): deep_thinking = True
   → if thinking_mode in ('instant', 'auto'): deep_thinking = False

4. Branching: routes/stream.py line 491-493
   → use_thinking = thinking_mode != 'instant'
   → is_multi_thinking = thinking_mode == 'multi-thinking'

5a. Multi-thinking path: routes/stream.py line 497+
    → reasoning_service.coordinate_reasoning_sync()
    → streams thinking events from progress queue
    → on failure: fallback_used = True, falls through to standard path

5b. Standard path: routes/stream.py line 615+
    → chatbot.chat_stream(deep_thinking=deep_thinking, ...)
    → ThinkTagParser parses <think>...</think> tags (if use_thinking)
    → emits thinking_start / thinking / thinking_end / chunk / complete

6. UI rendering: static/js/main.js lines 1127-1175
   → onThinkingStart: show thinking container
   → onThinking: append step text
   → onThinkingEnd: display summary + duration
   → onChunk: stream response content
   → onComplete: finalize with metadata
```

## SSE event contract by mode

| Event | `instant` | `auto` (no native tags) | `auto` (model emits `<think>`) | `thinking`/`deep` | `multi-thinking` |
|---|---|---|---|---|---|
| `metadata` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `thinking_start` | ✗ | ✗ | ✓ | ✓ | ✓ (label: "4-Agents Reasoning") |
| `thinking` | ✗ | ✗ | ✓ (parsed tag content) | ✓ (steps) | ✓ (progress events) |
| `thinking_end` | ✗ | ✗ | ✓ | ✓ | ✓ (or fallback summary) |
| `chunk` | ✓ | ✓ | ✓ (after thinking ends) | ✓ (after thinking ends) | ✓ (agent's final answer) |
| `complete` | ✓ | ✓ | ✓ | ✓ | ✓ |

## Key behavioral details

### deep_thinking flag
- The `deep_thinking` bool is derived from `thinking_mode` in `stream.py` line 259-264.
- It controls: `max_tokens` (doubled via `_mc.max_tokens_deep`), temperature (0.5), and system prompt suffix ("Think step-by-step").
- `core/chatbot.py` line 248: `chat()` receives `deep_thinking` as a parameter.

### ThinkTagParser (auto/think/deep modes)
- Located in `core/thinking_generator.py` line 35-76.
- Streaming parser that buffers partial `<think>...</think>` tags across chunks.
- Returns `(is_thinking, text)` tuples.
- Only instantiated when `use_thinking == True` (i.e., mode is not `instant`).

### Multi-thinking fallback
- If the 4-agent council raises an exception (`stream.py` line 602-612):
  - Emits `thinking_end` with `summary: "Fallback to standard"`.
  - Sets `is_multi_thinking = False` and falls through to standard streaming.
  - The user sees a brief thinking indicator, then a normal response.

### Tool dispatch
- Tools execute **independently of thinking_mode**.
- Tool results are prepended to the message before the model sees it.
- No tools are disabled or enabled based on mode.

## Agentic pipeline (multi-thinking only)

| Agent | Role | Module |
|---|---|---|
| Planner | Decomposes query into TaskNode items | `core/agentic/agents/planner.py` |
| Researcher | Gathers evidence for each task | `core/agentic/agents/researcher.py` |
| Critic | Scores quality; verdict = "pass" or "needs_work" | `core/agentic/agents/critic.py` |
| Synthesizer | Produces final answer | `core/agentic/agents/synthesizer.py` |

**Orchestrator**: `core/agentic/orchestrator.py` → `CouncilOrchestrator.run()` / `run_stream()`
- Max rounds: 3 (configurable via `max_rounds`)
- Loop: if Critic says "needs_work", selective retry (re-research or re-synthesize).
- Progress events flow through a thread-safe queue to the SSE generator.

**Contracts**: `core/agentic/contracts.py`
- `AgentRole` enum: `planner`, `researcher`, `critic`, `synthesizer`
- `RunStatus` enum: `planning`, `researching`, `critiquing`, `synthesizing`, `completed`
- `CouncilResult`: `final_answer`, `total_rounds`, `reasoning_time`

## Flask SSE contract

`routes/stream.py` is the canonical thinking-mode entry point. Preserve the existing SSE event names and payload shapes when changing mode behavior.

## File touch map

| Action | Files to touch |
|---|---|
| Add a new mode | `routes/stream.py`, `templates/index.html` (dropdown option), `static/js/modules/api-service.js` (if new default logic), `static/js/main.js` (if new rendering), `README.md` (thinking modes table) |
| Rename a mode | Same as "add" plus grep all references in `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/chatbot-core.instructions.md` |
| Change mode behavior | `routes/stream.py` (branching), `core/thinking_generator.py` (if step generation changes), `core/chatbot.py` (if `deep_thinking` semantics change) |
| Change agentic pipeline | `core/agentic/orchestrator.py`, `core/agentic/agents/*.py`, `core/agentic/contracts.py` |
| Fix broken thinking display | Check `static/js/main.js` callbacks, `routes/stream.py` event emission, `core/thinking_generator.py` ThinkTagParser |

## Safe to touch

- `core/thinking_generator.py` — thinking step logic and ThinkTagParser
- `core/agentic/**` — multi-thinking pipeline
- `routes/stream.py` — thinking-mode branching and SSE events
- `templates/index.html` — mode dropdown
- `static/js/main.js` — thinking display callbacks
- `static/js/modules/api-service.js` — mode wiring in request body

## Avoid unless required

- `core/tools.py` — tools are mode-independent
- `core/chatbot.py` — only touch if `deep_thinking` semantics change
- `core/config.py` — no mode-specific config exists; only touch if adding one
- Image generation routes — not related to thinking modes
- `services/mcp-server/` — MCP is mode-independent

## Monitor section

After any thinking-mode change, check:

- [ ] **Mode string consistency**: the string in the UI `data-mode` attribute, the JS `thinkingMode` variable, the POST body `thinking_mode` field, and the backend `if/elif` mapping all use the same value.
- [ ] **deep_thinking derivation**: `stream.py` line 259-264 correctly maps the new mode to `True` or `False`.
- [ ] **use_thinking flag**: `stream.py` line 491 — does the new mode need `ThinkTagParser`?
- [ ] **is_multi_thinking flag**: `stream.py` line 492 — should the new mode trigger 4-agent council?
- [ ] **SSE events emitted**: correct combination of `thinking_start` / `thinking` / `thinking_end` / `chunk` / `complete` for the new mode.
- [ ] **Fallback path**: if multi-thinking fails, verify standard streaming still works.
- [ ] **Flask SSE contract**: `/chat/stream` handles the mode and keeps event payloads stable.
- [ ] **UI rendering**: `main.js` callbacks handle any new event data fields.
- [ ] **complete event payload**: `_build_complete_event_payload` includes `thinking_mode` in the result.

## Required output format

After using this skill, report:

- **Mode impact**: which modes are affected and how behavior changes.
- **Tool impact**: whether tool dispatch is affected (usually no).
- **UI impact**: whether mode selector, thinking display, or response rendering changed.
- **Files touched**: list with brief reason.
- **Runtime contract**: confirm the Flask path is updated and no parallel route was introduced.
- **Verification steps**: how to confirm the change works.

## Mandatory checklist

### Pre-change

- [ ] Read `routes/stream.py` lines 258-264 (mode mapping) and lines 491-493 (branching).
- [ ] Read `templates/index.html` mode dropdown to confirm current UI options.
- [ ] Read `static/js/modules/api-service.js` `sendStreamMessage()` to confirm how mode reaches the backend.
- [ ] If touching multi-thinking: read `core/agentic/orchestrator.py` and `contracts.py`.

### Post-change

- [ ] Mode string is consistent across UI HTML, JS, and backend `if/elif`.
- [ ] `deep_thinking` and `use_thinking` flags are correct for every mode.
- [ ] SSE event sequence is correct for the changed mode (see event contract table).
- [ ] Multi-thinking fallback still works if the agent pipeline fails.
- [ ] Flask route reflects the change and SSE payloads are unchanged unless explicitly intended.
- [ ] `_build_complete_event_payload` includes the correct `thinking_mode`.
- [ ] UI callbacks in `main.js` handle any new data fields.
- [ ] `pytest tests/test_stream_complete_contract.py tests/test_agentic_agents.py -v` passes.
- [ ] Docs updated if a mode was added, renamed, or removed (`README.md`, `AGENTS.md`, `.github/copilot-instructions.md`).
