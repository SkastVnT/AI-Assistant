# Agentic Council — Trace & Observability Guide

> **Version**: v1
> **Audience**: Developers debugging council runs

---

## 1. Run ID

Every council execution receives a unique `run_id` (UUID hex, 32 chars).
This ID appears in:

- All log messages: `[Council] run_id=abc123 | ...`
- Agent-level logs: `[Planner] run_id=abc123 | ...`
- SSE events: `{"run_id": "abc123", ...}`
- API response: `agent_run_id` field
- Trace summary: `agent_trace_summary.decision`

Use `run_id` to correlate a single request across all log sources.

---

## 2. CouncilTrace

Attached to every `CouncilResult` (and exposed via `agent_trace_summary`):

```json
{
  "run_id": "a1b2c3d4e5f6...",
  "rounds": 2,
  "agents_used": ["planner", "researcher", "synthesizer", "critic", "researcher", "synthesizer", "critic"],
  "total_llm_calls": 7,
  "total_tokens": 5400,
  "elapsed_seconds": 8.3,
  "steps": [
    {
      "agent": "planner",
      "round": 1,
      "input_summary": "Explain recursion in Python...",
      "output_summary": "3 tasks, complexity=4",
      "tool_calls": null,
      "tokens": 800,
      "elapsed_ms": 1200
    }
  ]
}
```

### Fields

| Field | Description |
|---|---|
| `rounds` | Total iterations completed (1 = single pass) |
| `agents_used` | Ordered list of agent invocations (may repeat on retry) |
| `total_llm_calls` | Cumulative LLM API calls |
| `total_tokens` | Cumulative token usage |
| `elapsed_seconds` | Wall-clock time for the entire pipeline |
| `steps` | Detailed per-agent step trace |

### CouncilStep

Each step captures:

| Field | Description |
|---|---|
| `agent` | `planner` / `researcher` / `critic` / `synthesizer` |
| `round` | Which iteration this step belongs to |
| `input_summary` | Truncated input (max 500 chars) — safe for logs |
| `output_summary` | Truncated output summary — safe for logs |
| `tool_calls` | List of tool names used (e.g., `["web_search", "rag_query"]`) |
| `tokens` | Tokens consumed by this step |
| `elapsed_ms` | Wall-clock time for this step |

---

## 3. FinalDecision

Every run produces a `FinalDecision` regardless of success or failure:

```json
{
  "approved": true,
  "iterations_used": 1,
  "iterations_max": 2,
  "final_quality_score": 8,
  "exit_reason": "approved",
  "warnings": []
}
```

### Exit reasons

| Reason | Meaning |
|---|---|
| `approved` | Critic gave `pass` verdict |
| `quality_threshold` | Score met `quality_threshold` config (even with `needs_work` verdict) |
| `first_pass` | Single-iteration mode (no critic) |
| `budget_exhausted` | All `max_rounds` used, critic still unsatisfied |
| `circuit_breaker` | Score did not improve between consecutive rounds |
| `error` | Pipeline exception (agent crash, LLM failure, etc.) |

### Warnings

When `approved=false`, the `warnings` list contains unresolved issues from
the last critic evaluation, formatted as `"[severity] description"`.

---

## 4. Log Format

All council logs follow a structured key=value format for easy parsing:

```
[Council] run_id=abc123 | Starting council pipeline | max_rounds=2 | models: planner=openai researcher=gemini critic=grok synthesizer=stepfun
[Council] run_id=abc123 | round=1 | stage=planning
[Planner] run_id=abc123 | round=1 | model=openai | tasks=3 complexity=4
[Council] run_id=abc123 | round=1 | stage=researching
[Researcher] run_id=abc123 | round=1 | model=gemini | evidence=8 (pre=3, llm=5) | tools=none
[Council] run_id=abc123 | round=1 | stage=synthesizing
[Synthesizer] run_id=abc123 | model=stepfun | chars=1200 confidence=0.85
[Council] run_id=abc123 | round=1 | stage=critiquing
[Critic] run_id=abc123 | round=1 | model=grok | quality=8 verdict=pass issues=0
[Council] run_id=abc123 | Finished | exit=approved approved=True quality=8 rounds=1 llm_calls=4 tokens=3200 elapsed=3.20s
```

### Filtering by run_id

```bash
grep "run_id=abc123" logs/chatbot.log
```

### Log levels used

| Level | What |
|---|---|
| `INFO` | Pipeline lifecycle, stage transitions, agent outputs, retry decisions |
| `DEBUG` | LLM call metadata (model, tokens, elapsed), feature flag checks |
| `WARNING` | Model fallbacks to global chain |
| `ERROR` | Pipeline failures, model resolution failures, adapter creation failures |

---

## 5. SSE Event Sequence

A typical council run produces this event sequence on `/chat/council/stream`:

```
event: council_event
data: {"run_id":"abc","stage":"planning","role":"planner","status":"started","round":1,"short_message":"Decomposing task"}

event: council_event
data: {"run_id":"abc","stage":"planning","role":"planner","status":"completed","round":1,"short_message":"3 sub-tasks created"}

event: council_event
data: {"run_id":"abc","stage":"researching","role":"researcher","status":"started","round":1,"short_message":"Collecting evidence"}

event: council_event
data: {"run_id":"abc","stage":"researching","role":"researcher","status":"completed","round":1,"short_message":"8 evidence items gathered"}

event: council_event
data: {"run_id":"abc","stage":"synthesizing","role":"synthesizer","status":"started","round":1,"short_message":"Composing initial response"}

event: council_event
data: {"run_id":"abc","stage":"synthesizing","role":"synthesizer","status":"completed","round":1,"short_message":"Initial response ready"}

event: council_event
data: {"run_id":"abc","stage":"critiquing","role":"critic","status":"started","round":1,"short_message":"Reviewing answer quality"}

event: council_event
data: {"run_id":"abc","stage":"critiquing","role":"critic","status":"completed","round":1,"short_message":"Score 8/10 — verdict: pass"}

event: council_event
data: {"run_id":"abc","stage":"completed","role":"orchestrator","status":"completed","round":1,"short_message":"Finished — approved"}

event: council_result
data: {"response":"...","model":"council","agent_run_id":"abc",...}
```

### Retry sequence (round 2+):

```
event: council_event
data: {"stage":"retrying","role":"orchestrator","status":"started","round":2,"short_message":"Retrying both (round 2)"}

event: council_event
data: {"stage":"researching","role":"researcher","status":"started","round":2,...}
...
```

---

## 6. Debugging Checklist

| Symptom | Check |
|---|---|
| "Council mode is not enabled" | `AGENTIC_V1_ENABLED` env var is `false` or unset |
| Empty response | Check `exit_reason` in trace — may be `error` |
| Low quality score | Review critic issues in `warnings` |
| Pipeline timeout | Check `elapsed_seconds` and individual step `elapsed_ms` |
| Unexpected model used | Check `models:` line in startup log vs `preferred_*_model` params |
| No retry when expected | `max_rounds=1` means no retry; check `max_agent_iterations` |
| Circuit breaker triggered | Score did not improve — check consecutive quality scores in logs |
