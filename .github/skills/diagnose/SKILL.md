---
name: diagnose
description: Disciplined 6-phase debug loop for hard bugs and performance regressions. Use when a bug is reported, something is broken/throwing/failing, or a performance regression is described.
---

# Diagnose

A discipline for hard bugs and silent failures in the chatbot stack. Skip phases only when explicitly justified.

Before each phase, consult the relevant domain skill (`core-chatbot-routing-audit`, `tool-response-contract`, etc.) to understand the module being debugged.

## Phase 1 — Build a feedback loop

**This is the most important step.** If you have a fast, deterministic, agent-runnable pass/fail signal, you will find the cause. If you don't, no amount of staring at code will.

Try in this order:
1. **Failing test** at whatever seam reaches the bug (unit, integration, e2e in `tests/`)
2. **Curl / HTTP script** against the running chatbot at `POST /chat/stream`
3. **CLI invocation** with fixture input, diff stdout against known-good snapshot
4. **Replay captured payload** — save a real SSE request/response to disk and replay it
5. **Throwaway harness** — minimal Python script exercising only the failing path
6. **Property loop** — if bug is "sometimes wrong output", run 100 random inputs

For SSE bugs specifically: capture the raw event stream, not just the final response.

Do not proceed to Phase 2 without a loop you believe in.

## Phase 2 — Reproduce

Run the loop. Confirm:
- [ ] Failure matches what the **user** described — not a nearby different failure
- [ ] Reproducible across multiple runs (or high rate for non-deterministic bugs)
- [ ] Exact symptom captured (error message, wrong SSE event, missing field)

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any.

Each must be falsifiable:
> "If X is the cause, then changing Y will make the bug disappear."

**Show the ranked list before testing.** Users often have domain knowledge that re-ranks instantly. Cheap checkpoint, big time saver.

For chatbot bugs, common hypothesis categories:
- Route/blueprint not registered
- SSE event missing required field (`stream_contract.py`)
- Env key missing / wrong profile
- Tool response shape mismatch
- Flask/FastAPI path divergence

## Phase 4 — Instrument

Each probe maps to one hypothesis from Phase 3. Change one variable at a time.

- Prefer debugger/REPL breakpoints over logs
- For targeted logs: use prefix `[DEBUG-<tag>]` (e.g. `[DEBUG-a4f2]`) — easy to grep and clean up
- Never "log everything and grep"
- For perf regressions: establish baseline timing first, then bisect

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only at a correct seam (one that exercises the real bug pattern, not a nearby proxy).

If no correct seam exists, that is the finding. Note it. Do not write a test that gives false confidence.

If a seam exists:
1. Write failing test
2. Watch it fail
3. Apply fix
4. Watch it pass
5. Re-run Phase 1 loop against original scenario

## Phase 6 — Cleanup

Required before declaring done:
- [ ] Original repro no longer reproduces
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` logs removed (`grep "[DEBUG-"`)
- [ ] Throwaway harnesses deleted
- [ ] Hypothesis that was correct stated in commit message

**Then ask:** what would have prevented this? If architectural (no test seam, tangled callers), hand off to `improve-codebase-architecture` after the fix is in.

## File monitors for chatbot bugs

| Symptom | Check first |
|---|---|
| SSE stream broken / missing fields | `core/stream_contract.py`, `routes/stream.py` |
| Tool not triggering | `core/chatbot.py` or `chatbot_v2.py` routing |
| Response shape wrong | `core/tools.py`, `tool-response-contract` skill |
| Env key missing at runtime | `core/config.py`, `services/shared_env.py` |
| Blueprint 404 | `chatbot_main.py` blueprint registration |
| FastAPI path broken | `fastapi_app/routers/` |
