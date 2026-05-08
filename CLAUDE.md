# CLAUDE.md — AI-Assistant

Behavioral guidelines for Claude Code. Merged from project-specific rules and Karpathy engineering principles.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

---

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

The test: Every changed line should trace directly to the user's request.

**For this repo** — trace the path before editing:
1. UI / assets / templates
2. Flask/FastAPI route entry point
3. Core router / provider / tool code
4. Response formatting
5. Docs / tests / workflows

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

When behavior changes, update docs and identify the smallest sufficient validation plan.

---

## Project rules (project-specific, override nothing above)

**Service scope for chatbot tasks:** only edit `services/chatbot/`, `services/shared_env.py`, `services/mcp-server/`, `app/config/`, `app/src/`. Never touch `ComfyUI/`, `image_pipeline/`, `services/stable-diffusion/`, `services/edit-image/`.

**Env loading:** `services/shared_env.py` → `load_shared_env(__file__)` once per service. Never add a second `load_dotenv` that overrides it.

**Primary streaming endpoint:** `routes/stream.py` → `POST /chat/stream`. The Flask monolith is the **only** path — `fastapi_app/` was removed in May 2026. Login/admin/QR-payment blueprints were removed too; Electron is the canonical surface.

**MCP transport:** `stdio` (FastMCP). Do not add HTTP listeners.

**Secrets:** always read from env vars. Never hardcode API keys, ports, or paths.

**After behavior changes:** update `README.md` and relevant docs. See `.github/skills/docs-drift-sync/SKILL.md`.

**Run tests:** `cd services/chatbot && pytest tests/ -v` (venv-core activated).

## Sidecar services (opt-in, do not touch for chatbot-only tasks)

| Sidecar | Flag | Port | Entry |
|---|---|---|---|
| Hermes Agent | `HERMES_ENABLED=true` | 8080 | separate process — `NousResearch/hermes-agent` |
| SAA character picker | `CHARACTER_SELECT_ENABLED=true` | 51028 | `character_select_stand_alone_app-main/` — `npm start` |

**Hermes ↔ Reasoning pipeline are separate paths by default.** `POST /api/hermes/chat` is a chat proxy. `POST /api/reasoning-image-gen/generate` is a ComfyUI multi-panel pipeline (opt-in: `REASONING_PIPELINE=true`). A bridge (`core/image_intent.py`) activates only when **both** `HERMES_ENABLED=true` and `REASONING_PIPELINE=true` — it classifies the message and redirects image requests to the reasoning pipeline. Fails-safe: any import or classification error falls through to Hermes.

---

## Standard response shape

After making or proposing a change:

- **Goal** — what was requested
- **Findings** — what was discovered
- **Files touched** — changed files
- **Risks** — what could break
- **Verification** — minimum steps to confirm
- **Doc sync** — which docs need updating
