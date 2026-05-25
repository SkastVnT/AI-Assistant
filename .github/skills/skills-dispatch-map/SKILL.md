---
name: skills-dispatch-map
description: "Choose which repository skill to activate for a given task. Use when: starting any chatbot, MCP, config, or docs task to determine the best skill or skill combination; reviewing whether the right skills were applied; or deciding whether to combine multiple skills for a cross-cutting change."
---

# Skills Dispatch Map

## Purpose

This skill is a router. It tells you which of the 14 repository skills to activate for a given task. Read this **before** reading any other skill, so you pick the right one (or the right combination) on the first try.

## Default scope

All skills below target the **core chatbot and tools stack** — `services/chatbot/`, `services/mcp-server/`, `services/shared_env.py`, `app/config/`, `app/src/`. Do not apply these skills to ComfyUI, Stable Diffusion, or image pipeline work unless the task explicitly requires it.

**Line-number references:** Several skills cite specific line numbers (e.g., `stream.py` L258). These are approximate landmarks from when the skill was written. Search for the described content or function name rather than jumping to the exact line — the code evolves.

---

## Skill registry

| # | Skill | One-line scope |
|---|-------|---------------|
| 1 | **core-chatbot-routing-audit** | Route registration, blueprint wiring, provider routing, tool dispatch, SSE streaming, Flask monolith contract |
| 2 | **shared-env-contract** | Env variable loading, `.env` file hierarchy, hardcoded secrets/ports, cross-service config |
| 3 | **service-health-check-audit** | Startup failures, port drift, health endpoints, Docker/CI startup assumptions |
| 4 | **search-tool-cascade** | Search tool functions, fallback order, auto-trigger keywords, reverse image flows |
| 5 | **mcp-tool-authoring** | MCP server tools/resources/prompts, stdio transport, chatbot-side MCP routes |
| 6 | **thinking-mode-routing** | Thinking mode selection, SSE thinking events, agentic pipeline, mode parity |
| 7 | **provider-env-matrix** | LLM provider config, API keys, model registry, fallback chains, vision routing |
| 8 | **tool-response-contract** | Return shapes for tool functions, route handlers, SSE events, MCP tools |
| 9 | **chat-ui-sync** | Frontend ↔ backend wiring: tool selectors, mode selectors, SSE rendering, payload field names |
| 10 | **observability-log-hygiene** | Log levels, tags, error handling, secret leakage, bare `except:` blocks |
| 11 | **requirements-profile-selection** | Dependency profiles, `venv-core` vs `venv-image`, package classification, CI install sync |
| 12 | **workflow-impact-guard** | CI/CD impact assessment, test assumptions, security scan triggers, env in workflows |
| 13 | **docs-drift-sync** | README/docs alignment after any runtime behavior change |
| 14 | **test-impact-mapper** | Map changed files to the smallest sufficient test set |

---

## Task-to-skill routing matrix

### Routing / Endpoints

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a new chat route | core-chatbot-routing-audit | chat-ui-sync, tool-response-contract |
| Change SSE event payload | core-chatbot-routing-audit | tool-response-contract, chat-ui-sync |
| Fix broken streaming | core-chatbot-routing-audit | observability-log-hygiene |
| Check Flask route contract | core-chatbot-routing-audit | — |
| Wire a new tool button in UI | core-chatbot-routing-audit | chat-ui-sync, search-tool-cascade (if search tool) |

### Providers / Models

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a new LLM provider | provider-env-matrix | shared-env-contract, docs-drift-sync |
| Change model defaults or fallback | provider-env-matrix | core-chatbot-routing-audit |
| Debug "API key not configured" | provider-env-matrix | shared-env-contract |
| Add a model to the model selector | provider-env-matrix | chat-ui-sync |

### Search / Tools

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a new search tool | search-tool-cascade | tool-response-contract, chat-ui-sync |
| Change fallback order | search-tool-cascade | observability-log-hygiene |
| Edit auto-search keywords | search-tool-cascade | — |
| Debug tool returning no results | search-tool-cascade | observability-log-hygiene, provider-env-matrix (if API key issue) |
| Change a tool's return shape | tool-response-contract | chat-ui-sync (if UI renders it) |

### MCP

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a new MCP tool | mcp-tool-authoring | tool-response-contract |
| Change MCP tool response shape | mcp-tool-authoring | tool-response-contract |
| Debug MCP tool not discovered | mcp-tool-authoring | observability-log-hygiene |
| Update chatbot-side MCP route | mcp-tool-authoring | core-chatbot-routing-audit |

### Thinking Modes

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a new thinking mode | thinking-mode-routing | chat-ui-sync, core-chatbot-routing-audit |
| Fix broken reasoning display | thinking-mode-routing | chat-ui-sync, tool-response-contract |
| Change agentic pipeline | thinking-mode-routing | observability-log-hygiene |
| Debug mode mismatch | thinking-mode-routing | core-chatbot-routing-audit |

### UI / Frontend

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add or rename a UI control | chat-ui-sync | core-chatbot-routing-audit |
| Debug dead button or missing state | chat-ui-sync | tool-response-contract |
| Fix rendering of search results | chat-ui-sync | search-tool-cascade, tool-response-contract |
| Change model/tool selector options | chat-ui-sync | provider-env-matrix (models) or search-tool-cascade (tools) |

### Config / Environment

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a new env variable | shared-env-contract | docs-drift-sync, workflow-impact-guard |
| Change `.env` file loading logic | shared-env-contract | service-health-check-audit |
| Debug missing env value at runtime | shared-env-contract | provider-env-matrix (if API key) |
| Check for hardcoded secrets | shared-env-contract | observability-log-hygiene |

### Dependencies

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a Python package | requirements-profile-selection | workflow-impact-guard |
| Debug ImportError in CI | requirements-profile-selection | workflow-impact-guard |
| Audit cross-profile leakage | requirements-profile-selection | — |
| Upgrade a dependency | requirements-profile-selection | workflow-impact-guard, docs-drift-sync (if major version) |

### Startup / Health

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Service won't start | service-health-check-audit | shared-env-contract, observability-log-hygiene |
| Port mismatch in docs vs runtime | service-health-check-audit | docs-drift-sync |
| CI test job fails on startup | service-health-check-audit | workflow-impact-guard |

### Logging / Error Handling

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Add a log statement | observability-log-hygiene | — |
| Fix bare `except:` block | observability-log-hygiene | — |
| Debug silent failure | observability-log-hygiene | core-chatbot-routing-audit (if route-level) |
| Audit secret leakage in logs | observability-log-hygiene | shared-env-contract |

### CI / Workflows

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Assess CI impact of a code change | workflow-impact-guard | test-impact-mapper |
| Debug CI failure | workflow-impact-guard | requirements-profile-selection (if install step), service-health-check-audit (if startup) |
| Add a new workflow job | workflow-impact-guard | — |
| Check if PR needs security review | workflow-impact-guard | — |

### Docs

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Update docs after a code change | docs-drift-sync | (depends on what changed) |
| Verify README matches runtime | docs-drift-sync | service-health-check-audit |
| Fix stale port in scripts README | docs-drift-sync | — |

### Testing

| Task | Primary skill | Also load |
|------|--------------|-----------|
| Decide which tests to run | test-impact-mapper | — |
| Review PR test coverage | test-impact-mapper | workflow-impact-guard |
| Justify skipping tests | test-impact-mapper | — |

---

## Multi-skill escalation

Some tasks require 3+ skills. These are the most common multi-skill patterns:

### Pattern A: New feature end-to-end

**Example:** Add a new search tool with UI button, API key, and tests.

| Order | Skill | Why |
|-------|-------|-----|
| 1 | search-tool-cascade | Tool function, fallback position |
| 2 | provider-env-matrix | New API key config |
| 3 | shared-env-contract | Env variable loading |
| 4 | tool-response-contract | Return shape |
| 5 | chat-ui-sync | UI button wiring |
| 6 | test-impact-mapper | Which tests to add/run |
| 7 | docs-drift-sync | README search tools table |

### Pattern B: New provider + model

**Example:** Add Anthropic provider with Claude model.

| Order | Skill | Why |
|-------|-------|-----|
| 1 | provider-env-matrix | Model registry, API key |
| 2 | shared-env-contract | Env loading |
| 3 | core-chatbot-routing-audit | Provider routing in chatbot.py |
| 4 | chat-ui-sync | Model selector update |
| 5 | workflow-impact-guard | CI env assumptions |
| 6 | docs-drift-sync | README provider table |

### Pattern C: Dependency upgrade with CI impact

**Example:** Upgrade `openai` SDK major version.

| Order | Skill | Why |
|-------|-------|-----|
| 1 | requirements-profile-selection | Profile classification |
| 2 | workflow-impact-guard | CI install impact |
| 3 | provider-env-matrix | API client changes |
| 4 | tool-response-contract | Response shape changes from new SDK |
| 5 | test-impact-mapper | Which tests cover affected code |

### Pattern D: Debug a CI failure

**Example:** Tests pass locally, fail in CI.

| Order | Skill | Why |
|-------|-------|-----|
| 1 | workflow-impact-guard | Understand CI env and install steps |
| 2 | requirements-profile-selection | Missing package? |
| 3 | service-health-check-audit | Startup failure in CI? |
| 4 | shared-env-contract | Missing env var default? |

### Pattern E: New MCP tool with chatbot integration

**Example:** Add an MCP tool that the chatbot calls via proxy route.

| Order | Skill | Why |
|-------|-------|-----|
| 1 | mcp-tool-authoring | Tool registration, response shape |
| 2 | core-chatbot-routing-audit | Chatbot-side MCP proxy route |
| 3 | tool-response-contract | Wire formats |
| 4 | chat-ui-sync | If UI exposes the tool |
| 5 | docs-drift-sync | MCP tool documentation |

---

## Dispatch decision tree

```
START → What is the primary object of the change?

├── Route / endpoint / blueprint  → core-chatbot-routing-audit
├── LLM provider / model / API key → provider-env-matrix
├── Search tool / reverse image   → search-tool-cascade
├── MCP tool / resource / prompt  → mcp-tool-authoring
├── Thinking mode / agentic pipe  → thinking-mode-routing
├── UI control / selector / render → chat-ui-sync
├── Env variable / .env loading   → shared-env-contract
├── Python package / requirements  → requirements-profile-selection
├── Startup / port / health        → service-health-check-audit
├── Log statement / error handler  → observability-log-hygiene
├── CI workflow / test runner      → workflow-impact-guard
├── Documentation / README         → docs-drift-sync
├── Test scope decision            → test-impact-mapper
└── Return shape / payload field   → tool-response-contract

THEN → Does the change cross into another domain?
  YES → Load the additional skill(s) from the routing matrix above.
  NO  → Proceed with the primary skill only.

FINALLY → Does the change affect runtime behavior?
  YES → Also load docs-drift-sync (for docs) + test-impact-mapper (for tests).
  NO  → Skip.
```

---

## Skills that are almost always secondary

These skills rarely lead a task but are frequently loaded alongside a primary skill:

| Skill | When to add as secondary |
|-------|-------------------------|
| **docs-drift-sync** | Any change to ports, commands, env vars, entry points, or service responsibilities |
| **test-impact-mapper** | Any code change that might affect test outcomes |
| **workflow-impact-guard** | Any change that adds dependencies, changes env, or modifies startup |
| **observability-log-hygiene** | Any change that adds error handling or touches exception paths |
| **tool-response-contract** | Any change that modifies what data flows from backend to frontend |

---

## Skills that should NOT be combined

| Combination | Why not |
|-------------|---------|
| Any chatbot skill + image pipeline work | Different venv, different services, different concerns. If the task is image-only, none of these 14 skills apply. |
| mcp-tool-authoring + thinking-mode-routing | MCP tools and thinking modes are independent systems. A change to one does not affect the other unless the task explicitly bridges them. |

---

## Dispatch checklist

Before starting any chatbot/core task:

- [ ] **Primary skill identified** — one skill that matches the main object of the change
- [ ] **Secondary skills checked** — routing matrix consulted for additional skills
- [ ] **Scope confirmed as core** — change does not require image pipeline skills
- [ ] **Multi-skill order planned** — if 3+ skills, read them in the order listed in the escalation patterns
- [ ] **docs-drift-sync considered** — does the change alter runtime behavior that docs describe?
- [ ] **test-impact-mapper considered** — does the change require running or adding tests?
- [ ] **workflow-impact-guard considered** — does the change affect CI assumptions?
