---
name: zoom-out
description: Get broader context and a higher-level perspective before editing unfamiliar code. Use when entering an unknown module, when a change feels risky but scope is unclear, or when asked to refactor a section without a clear plan.
---

# Zoom Out

Before touching unfamiliar code, get a mental model of the surrounding system. Prevents the "surgical change that broke three things" failure mode.

## When to use

- About to edit a module you haven't read before
- Change feels risky but you're not sure why
- Asked to refactor without a clear plan
- Bug is in a subsystem you don't have a model for

## Steps

### 1. Identify the module's role

Read the relevant section of `AGENTS.md` file map first. Answer:
- What is this module responsible for?
- What calls it? What does it call?
- What does it NOT do (boundaries)?

### 2. Map the data flow

For chatbot tasks, trace the real path:
```
UI (static/js/) → route (routes/) → core logic (core/) → tool/provider → response
```

Sketch the path on paper or in a comment before editing.

### 3. Check contracts

- **Response shapes**: does this module have a defined output contract? (`tool-response-contract` skill)
- **Env dependencies**: what env vars does it read? (`core/config.py`)
- **Blueprint registration**: where is this blueprint registered? (`chatbot_main.py`)

### 4. Find the test coverage

```
cd services/chatbot && pytest tests/ -v --collect-only 2>&1 | grep <module_name>
```

If there are tests, read them — they describe intended behavior better than docs.

### 5. Identify blast radius

Before changing anything, list:
- Files that import this module
- Routes that call this function  
- Frontend JS that depends on this response shape

Use grep: `grep -r "from core.X import\|import core.X" services/chatbot/`

### 6. State your model

In a comment or to the user, state:
> "This module does X. It is called by Y. It must return Z. I plan to change W, which affects A and B."

If you can't complete that sentence, zoom out further before touching code.

## Common zoom-out targets in this project

| Module | Key thing to understand before touching |
|---|---|
| `core/chatbot.py` | The if/elif model routing chain — adding a provider breaks the chain if not inserted correctly |
| `routes/stream.py` | SSE generator lifecycle — `yield` order matters for client state |
| `core/stream_contract.py` | `complete` event payload shape — frontend depends on exact field names |
| `core/tools.py` | Auto-trigger keywords and fallback order — changing keywords affects routing |
| `chatbot_main.py` | Blueprint registration order — later blueprints can shadow earlier ones |
| `fastapi_app/` | Parallel to Flask — changes here do NOT affect Flask mode and vice versa |
| `services/shared_env.py` | Loaded once per process — side effects at import time can cause hard-to-debug failures |
