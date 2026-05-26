---
name: docs-drift-sync
description: "Keep documentation aligned with runtime behavior. Use when: changing ports, entry points, startup commands, env variables, service responsibilities, or removing/renaming scripts. Requires a runtime-vs-docs comparison before finalizing any change that alters observable behavior."
---

# Docs-Drift-Sync

## When to use this skill

- Any code change that alters a port, entry point, startup command, or env variable name.
- Any change that adds, removes, or renames a service, script, or route.
- Any change where the user asks you to "also update docs" or "keep docs in sync."
- Proactively — after completing a code change, check whether docs still match.

## Authoritative sources

The **main README.md** is the single source of truth. When it conflicts with other docs, main README wins.

| Fact | Authoritative file | Stale copies to check |
|---|---|---|
| Service ports | `README.md` service table | `app/scripts/README.md`, `.claude/skills/repo-guidelines/AGENTS.md`, `.github/copilot-instructions.md`, `services/chatbot/.env*`, Docker compose files |
| Entry points | `README.md` service table | `.claude/skills/repo-guidelines/AGENTS.md`, `.github/copilot-instructions.md`, startup scripts in `app/scripts/` |
| Env variable names | `services/chatbot/core/config.py` | `README.md`, `.env.example`, `app/config/.env*`, `.claude/skills/repo-guidelines/AGENTS.md` |
| MCP transport | `services/mcp-server/server.py` (stdio) | `services/mcp-server/README.md`, `app/scripts/README.md` (stale port 8000) |
| Startup commands | `services/chatbot/run.py` | `README.md`, `app/scripts/README.md` |
| Dependency profiles | `app/requirements/*.txt` | `app/requirements/README.md`, `.claude/skills/repo-guidelines/AGENTS.md` |
| Test commands | `.github/workflows/tests.yml` | `README.md`, `.claude/skills/repo-guidelines/AGENTS.md` |

## Known drift (do not propagate)

| Location | Claim | Correct value |
|---|---|---|
| `app/scripts/README.md` | Stable Diffusion = 7860 | **7861** |
| `app/scripts/README.md` | Edit Image = 7861 | **8100** |
| `app/scripts/README.md` | MCP Server = 8000 (HTTP) | **stdio** (no port) |
| `app/scripts/README.md` | speech2text (5001), text2sql (5002) | **Archived** — no longer in `services/` |
| `app/requirements/README.md` | Lists hub-gateway, speech2text, text2sql, document-intelligence | Only chatbot + mcp-server are active core services |

## When docs must be updated

| Trigger | Docs to update |
|---|---|
| Port changed (code or env default) | `README.md` service table, `.claude/skills/repo-guidelines/AGENTS.md`, `.github/copilot-instructions.md`, affected `.env*` files |
| Entry point changed | `README.md`, `.claude/skills/repo-guidelines/AGENTS.md` |
| New env variable added | `core/config.py`, `README.md` env table, `.env.example` |
| Env variable renamed/removed | Same as above plus search all `.env*` and `.instructions.md` files |
| New route added | Route docstring; `README.md` if user-facing |
| Service added or removed | `README.md` service table, `.claude/skills/repo-guidelines/AGENTS.md`, `.github/copilot-instructions.md`, `app/requirements/README.md` |
| Startup command changed | `README.md` quick-start section, affected script files |
| MCP tool added/changed | `services/mcp-server/README.md` |
| Workflow changed | No doc update unless it changes user-visible behavior |

## Runtime-vs-docs comparison procedure

Before marking a behavioral change as complete, run this comparison:

1. **Identify the changed fact** (port, command, entry point, env var, service name).
2. **Read the authoritative source** and confirm the new value is correct there.
3. **Search stale copies** from the table above. For ports, grep the value across the codebase.
4. **For each stale copy**, decide: update to match, or mark as intentionally different with a comment.
5. **List every file touched** for doc alignment in your response.

## Files most likely to drift

Ordered by frequency of drift:

1. `app/scripts/README.md` — highest drift risk, multiple stale entries already
2. `.claude/skills/repo-guidelines/AGENTS.md` — duplicates the service table
3. `.github/copilot-instructions.md` — duplicates ports and entry points
4. `services/chatbot/.env*` — port defaults may diverge from code defaults
5. `app/requirements/README.md` — lists archived services
6. Docker compose files under `app/config/`

## Mandatory checklist

After any change that alters runtime behavior:

- [ ] The new value is correct in the **authoritative source**.
- [ ] `README.md` service table matches runtime (ports, entry points, transport).
- [ ] `.claude/skills/repo-guidelines/AGENTS.md` service map matches `README.md`.
- [ ] `.github/copilot-instructions.md` entry-point table matches `README.md`.
- [ ] No stale port or command was left in `app/scripts/README.md`.
- [ ] If an env variable changed: `core/config.py`, `.env.example`, and `README.md` are aligned.
- [ ] No doc still references a removed or renamed service/script.
- [ ] Response includes a "Docs updated" section listing every file changed for alignment.
