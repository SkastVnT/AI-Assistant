# Council Streaming — SSE Event Sequence

## Endpoint

```
POST /chat/council/stream
Content-Type: application/json
```

Request body: same as `/chat` with `agent_mode: "council"`.

## Event types

| SSE event name    | Meaning                              |
|-------------------|--------------------------------------|
| `council_event`   | Agent progress update (safe status)  |
| `council_result`  | Final ChatResponse-compatible JSON   |
| `council_error`   | Pipeline failure                     |

## `council_event` schema

```json
{
  "run_id":        "a1b2c3d4e5f6...",
  "stage":         "planning | researching | synthesizing | critiquing | retrying | completed | failed",
  "role":          "planner | researcher | synthesizer | critic | orchestrator",
  "status":        "started | progress | completed | skipped",
  "round":         1,
  "timestamp":     "2026-04-03T12:00:00.123456+00:00",
  "short_message": "Decomposing task into sub-questions"
}
```

## Example: single-round run (approved on first pass)

```
event: council_event
data: {"run_id":"a1b2c3d4","stage":"planning","role":"planner","status":"started","round":1,"timestamp":"2026-04-03T12:00:00.100Z","short_message":"Decomposing task into sub-questions"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"planning","role":"planner","status":"completed","round":1,"timestamp":"2026-04-03T12:00:01.200Z","short_message":"3 sub-tasks created"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"researching","role":"researcher","status":"started","round":1,"timestamp":"2026-04-03T12:00:01.210Z","short_message":"Collecting evidence"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"researching","role":"researcher","status":"completed","round":1,"timestamp":"2026-04-03T12:00:03.500Z","short_message":"5 evidence items gathered"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"synthesizing","role":"synthesizer","status":"started","round":1,"timestamp":"2026-04-03T12:00:03.510Z","short_message":"Composing initial response"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"synthesizing","role":"synthesizer","status":"completed","round":1,"timestamp":"2026-04-03T12:00:05.100Z","short_message":"Initial response ready"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"critiquing","role":"critic","status":"started","round":1,"timestamp":"2026-04-03T12:00:05.110Z","short_message":"Reviewing answer quality"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"critiquing","role":"critic","status":"completed","round":1,"timestamp":"2026-04-03T12:00:06.800Z","short_message":"Score 8/10 — verdict: pass"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"completed","role":"orchestrator","status":"completed","round":1,"timestamp":"2026-04-03T12:00:06.810Z","short_message":"Finished — approved"}

event: council_result
data: {"response":"The synthesized answer…","model":"council","context":"casual","deep_thinking":true,"thinking_process":"Council completed in 1 round(s), 4 LLM calls, 6.8s.\nExit reason: approved.\nQuality score: 8/10.","citations":null,"agent_run_id":"a1b2c3d4","agent_trace_summary":{"rounds":1,"agents_used":["planner","researcher","synthesizer","critic"],"total_llm_calls":4,"total_tokens":3200,"elapsed_seconds":6.8,"decision":{"approved":true,"iterations_used":1,"iterations_max":2,"final_quality_score":8,"exit_reason":"approved","warnings":[]}}}

```

## Example: two-round run (retry then approved)

The extra events for round 2:

```
event: council_event
data: {"run_id":"a1b2c3d4","stage":"retrying","role":"orchestrator","status":"started","round":2,"timestamp":"…","short_message":"Retrying both (round 2)"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"researching","role":"researcher","status":"started","round":2,"timestamp":"…","short_message":"Re-collecting evidence based on critic feedback"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"researching","role":"researcher","status":"completed","round":2,"timestamp":"…","short_message":"Evidence updated"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"synthesizing","role":"synthesizer","status":"started","round":2,"timestamp":"…","short_message":"Re-composing response with new evidence"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"synthesizing","role":"synthesizer","status":"completed","round":2,"timestamp":"…","short_message":"Response updated"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"critiquing","role":"critic","status":"started","round":2,"timestamp":"…","short_message":"Re-reviewing answer"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"critiquing","role":"critic","status":"completed","round":2,"timestamp":"…","short_message":"Score 9/10 — verdict: pass"}

event: council_event
data: {"run_id":"a1b2c3d4","stage":"completed","role":"orchestrator","status":"completed","round":2,"timestamp":"…","short_message":"Finished — approved"}

event: council_result
data: {…}
```

## Frontend rendering guide

Map `stage` to UI elements:

| stage           | Icon suggestion | Display text                          |
|-----------------|-----------------|---------------------------------------|
| `planning`      | 📋              | "Planner is decomposing task"         |
| `researching`   | 🔍              | "Researcher is collecting evidence"   |
| `synthesizing`  | ✍️              | "Synthesizer is composing response"   |
| `critiquing`    | 🔎              | "Critic is reviewing answer"          |
| `retrying`      | 🔄              | "Refining answer (round N)"          |
| `completed`     | ✅              | "Done"                                |
| `failed`        | ❌              | "Pipeline error"                      |

Use `short_message` for the subtitle / secondary text.
