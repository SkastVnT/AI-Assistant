---
name: workflow-impact-guard
description: "Reason about the impact of chatbot/core changes on GitHub workflows, tests, security scans, and CI behavior. Use when: adding or changing routes, tools, providers, or dependencies; reviewing a PR that might affect CI; debugging CI failures after a chatbot change; checking whether a code change needs a workflow or docs update; or auditing workflow assumptions after startup or env changes."
---

# Workflow Impact Guard

## When to use this skill

- Making a code change in `services/chatbot/`, `services/mcp-server/`, `services/shared_env.py`, or `app/src/` and need to know if CI will break.
- Adding, removing, or upgrading a dependency.
- Changing startup behavior, env variables, ports, or entry points.
- Reviewing a PR for workflow impact before merge.
- Debugging a CI failure that started after a chatbot or tool change.
- Adding a new test file or test fixture.

## Do not use for

- ComfyUI, image pipeline, or Stable Diffusion workflow changes — those are out of scope.
- RAG subsystem changes — `rag-eval.yml` triggers only on `app/rag/**` paths.
- Writing workflow YAML from scratch — this skill is for impact assessment, not authoring.

---

## Workflow map

Six workflows exist under `.github/workflows/`. Each has different triggers, scope, and failure modes.

### 1. `tests.yml` — Service Tests

| Property | Value |
|----------|-------|
| Triggers | push to `master`, `develop`, `feat/**`, `refactor/**`; PRs to `master`, `develop` |
| Jobs | `test-chatbot` |
| Python | 3.10 |
| Installs | `services/chatbot/tests/requirements-test.txt` + `services/chatbot/requirements.txt` |
| Working dir | `./services/chatbot` |
| Env vars | `TESTING=True`, `MONGODB_ENABLED=False` |
| Runs | `pytest tests/ -v --tb=short --timeout=60` |

**What breaks this:** New import that isn't in `services/chatbot/requirements.txt`. New env var read at import time without a default. Test file with syntax error. Fixture added to `conftest.py` that requires a running service.

### 2. `ci-cd.yml` — CI/CD Pipeline

| Property | Value |
|----------|-------|
| Triggers | Same as `tests.yml` |
| Jobs | `lint` → `test-chatbot` (needs lint) → `test-root` (needs lint) → `security` → `build-docker` (needs tests, master only) |
| Lint scope | `python -m compileall services/ app/src/` + `flake8 services/ app/src/ --select=E9,F63,F7` |
| Test deps | Same as `tests.yml` |
| Docker | Builds `services/chatbot/Dockerfile` on master push only |

**What breaks this:**
- **Lint job:** Syntax error anywhere in `services/` or `app/src/`. Import of a module that doesn't exist.
- **Test jobs:** Same as `tests.yml` — these are duplicate test jobs with slightly different timeouts (60s vs 120s).
- **Security job:** Trivy scans `services/` filesystem. Adding a file with a known vulnerable pattern (hardcoded secrets, etc.) triggers alerts.
- **Docker job:** Only runs on master. Changes to `Dockerfile` or files referenced in Docker context can break the build.

### 3. `security-scan.yml` — Security Scanning

| Property | Value |
|----------|-------|
| Triggers | Push/PR (same branches) + weekly cron + manual dispatch |
| Tools | Bandit (Python security linter) + pip-audit |
| Bandit scope | `services/` and `app/src/`, excludes tests |
| pip-audit targets | `services/chatbot/requirements.txt`, `services/stable-diffusion/requirements.txt`, `services/edit-image/requirements.txt`, `services/mcp-server/requirements.txt` |
| PR comment | Posts Bandit issue count as PR comment |

**What breaks this:** Adding a dependency with a known CVE. Introducing code patterns Bandit flags (e.g., `eval()`, `subprocess.call(shell=True)`, hardcoded passwords). Adding a new service-local `requirements.txt` without adding it to the pip-audit loop.

### 4. `codeql-analysis.yml` — CodeQL

| Property | Value |
|----------|-------|
| Triggers | Push to `master`/`develop`, PRs to `master`, weekly cron, manual |
| Language | Python |
| Scanned paths | `services/`, `app/src/` |
| Excluded | `tests/`, `__pycache__/`, `venv*/` |
| Pre-step | Deletes `ComfyUI/`, `app/ComfyUI/`, `private/`, `venv*/` before analysis |

**What breaks this:** Introducing code patterns CodeQL flags as security vulnerabilities (SQL injection, path traversal, SSRF, etc.). CodeQL runs `security-and-quality` queries — a new finding may block merge if GitHub branch protection requires clean CodeQL.

### 5. `dependency-review.yml` — Dependency Review

| Property | Value |
|----------|-------|
| Triggers | PRs to `master`/`develop` that change `**/requirements*.txt`, `**/pyproject.toml`, `app/requirements/**`, or `.github/workflows/**` |
| Action | `actions/dependency-review-action@v4` |
| Fail on | `critical` severity |
| Denied licenses | GPL-3.0, AGPL-3.0 |
| Output | PR comment summary |

**What breaks this:** Adding a dependency with a critical vulnerability. Adding a GPL-3.0 or AGPL-3.0 licensed package. Note: this only runs on PRs that touch requirements or workflow files.

### 6. `rag-eval.yml` — RAG Evaluation

| Property | Value |
|----------|-------|
| Triggers | PRs to `main` or `feat/adv_RAG` that change `app/rag/**` |
| Scope | RAG subsystem only |

**Not affected by chatbot changes.** Ignore for chatbot-only work.

---

## Impact classification

Before committing a chatbot or core change, classify its workflow impact:

### Level 0: No workflow impact

The change does not affect any workflow. Examples:
- Editing a docstring or comment in chatbot code.
- Changing log messages.
- Modifying `templates/index.html` or `static/` assets.

**Action:** None.

### Level 1: Test impact only

The change may cause test failures but does not affect lint, security, or dependency workflows. Examples:
- Changing a route handler's response shape.
- Modifying tool function behavior.
- Adding a new route or blueprint.
- Changing SSE event payload structure.

**Action:** Run `cd services/chatbot && pytest tests/ -v` locally. Check that existing tests still pass. Add tests for new behavior.

**Affected workflows:** `tests.yml`, `ci-cd.yml` (test jobs)

### Level 2: Lint impact

The change may trigger compile or flake8 errors. Examples:
- Adding a new Python file to `services/` or `app/src/`.
- Renaming or deleting a module that other files import.
- Using syntax not supported by Python 3.10.

**Action:** Run `python -m compileall services/ app/src/` and `flake8 services/ app/src/ --select=E9,F63,F7` locally.

**Affected workflows:** `ci-cd.yml` (lint job blocks all downstream jobs)

### Level 3: Dependency impact

The change adds, removes, or upgrades a Python package. Examples:
- Editing `services/chatbot/requirements.txt`.
- Editing any `app/requirements/` chunk or profile file.
- Adding a new import that requires a package not currently installed.

**Action:** Verify the package is in `services/chatbot/requirements.txt` (for CI). Check `pip-audit` for known vulnerabilities. Check license compatibility (no GPL-3.0, no AGPL-3.0).

**Affected workflows:** `tests.yml`, `ci-cd.yml` (install step), `security-scan.yml` (pip-audit), `dependency-review.yml` (if requirements files changed)

### Level 4: Security impact

The change introduces code patterns that security tools flag. Examples:
- Using `eval()`, `exec()`, `subprocess` with `shell=True`.
- Hardcoding a secret or password.
- Introducing a path traversal, SSRF, or injection risk.
- Adding a dependency with a known CVE.

**Action:** Run `bandit -r services/ app/src/ --exclude '**/tests/**' -f txt` locally. Review CodeQL alerts after push.

**Affected workflows:** `security-scan.yml` (Bandit), `codeql-analysis.yml`

### Level 5: Startup / env impact

The change modifies how the service starts, what env vars it reads, or what ports it binds. Examples:
- Changing `load_shared_env()` behavior.
- Adding a new required env var without a default.
- Changing the default port.
- Modifying `run.py` or `chatbot_main.py` startup sequence.

**Action:** Verify CI env assumptions (`TESTING=True`, `MONGODB_ENABLED=False`). Ensure the new env var has a safe default for CI (where no `.env` file exists). Update docs.

**Affected workflows:** `tests.yml`, `ci-cd.yml` (both test jobs rely on env vars)

### Level 6: Workflow file change

The change modifies a `.github/workflows/*.yml` file directly. Examples:
- Adding a new workflow job or step.
- Changing Python version.
- Adding new install steps.

**Action:** Validate YAML syntax. Test in a branch before merging to master. Verify `dependency-review.yml` triggers (it watches workflow file changes).

**Affected workflows:** The modified workflow + `dependency-review.yml`

---

## Env assumptions in CI

Workflows set specific env vars. Code that reads env at import time must have safe defaults for these values.

| Var | Set in CI | Value | Meaning |
|-----|-----------|-------|---------|
| `TESTING` | `tests.yml`, `ci-cd.yml` | `"True"` | Signals test mode — skip real API calls |
| `MONGODB_ENABLED` | `tests.yml`, `ci-cd.yml` | `"False"` | Disables MongoDB connection attempts |

**Vars NOT set in CI** (code must handle their absence):
- All API keys (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `SERPAPI_API_KEY`, etc.)
- `MONGODB_URI`
- `REDIS_URL`
- Removed startup flags or route compatibility shims
- Service-local keys in `services/chatbot/.env`

**Rule:** If you add a new env var that is read at import time, give it a default value or guard it with `os.getenv("VAR", default)`. Otherwise CI will crash with `KeyError` or `None` propagation.

---

## Docs-sync reminder

When a change reaches Level 3 or above, check whether docs need updating:

| Change type | Doc to check |
|-------------|-------------|
| New dependency | `app/requirements/README.md` — is the package in the right profile? |
| New env var | `README.md` — listed in config section? `app/config/.env.example`? |
| Port change | `README.md` service table. `app/scripts/README.md` if scripts reference the port. |
| Startup behavior change | `README.md` startup instructions. `.claude/skills/repo-guidelines/AGENTS.md` service map. |
| New workflow or job | `README.md` CI section if one exists. |
| New service-local requirements file | `security-scan.yml` pip-audit loop. |

---

## Minimum validation plan

For every chatbot/core change, run at least this:

```
Level 0–1: pytest tests/ -v (local)
Level 2:   + python -m compileall services/ app/src/
Level 3:   + verify package in services/chatbot/requirements.txt
Level 4:   + bandit -r services/ app/src/ --exclude '**/tests/**' -f txt
Level 5:   + check env defaults for CI compatibility
Level 6:   + validate YAML, test in branch
```

If you cannot run the full check locally, explicitly note which levels are unverified and flag them for CI review.

---

## Common CI failure patterns

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` in CI | Package missing from `services/chatbot/requirements.txt` | Add the package — check it's not image-only |
| `SyntaxError` in lint job | Python 3.10 incompatibility or typo | Fix syntax; CI uses Python 3.10, not 3.11+ |
| Test timeout (60s / 120s) | Test makes real API call or waits for connection | Mock external calls; check `TESTING` env var |
| Bandit finding on PR | Flagged code pattern (eval, shell=True, etc.) | Refactor to safe pattern or add `# nosec` with justification |
| pip-audit failure | Dependency has known CVE | Upgrade or pin to patched version |
| Dependency review blocks PR | GPL/AGPL license or critical vulnerability | Replace package or justify exception |
| Docker build fails (master) | Missing file in Docker context or broken Dockerfile | Check `services/chatbot/Dockerfile` references |
| CodeQL alert | Security-relevant code pattern | Fix the pattern; suppress with inline comment only if false positive |

---

## Workflow-impact checklist

Before merging any chatbot/core change:

- [ ] **Impact level classified** — 0 through 6, based on what the change touches
- [ ] **Affected workflows identified** — listed which of the 6 workflows are affected
- [ ] **Tests pass locally** — `cd services/chatbot && pytest tests/ -v --timeout=60`
- [ ] **Lint passes** — `python -m compileall services/ app/src/` (if Level 2+)
- [ ] **Dependencies in sync** — package appears in both profile file and `services/chatbot/requirements.txt` (if Level 3+)
- [ ] **No security anti-patterns** — no `eval()`, `shell=True`, hardcoded secrets (if Level 4+)
- [ ] **Env defaults safe for CI** — new env vars have defaults; existing `TESTING`/`MONGODB_ENABLED` assumptions unchanged (if Level 5+)
- [ ] **Docs updated** — README, `.claude/skills/repo-guidelines/AGENTS.md`, env examples updated if runtime behavior changed (if Level 3+)
- [ ] **Workflow YAML valid** — syntax checked, tested in branch (if Level 6)
- [ ] **pip-audit loop updated** — new service `requirements.txt` added to `security-scan.yml` if applicable

---

## Related skills

- **requirements-profile-selection** — determines which profile a dependency belongs in
- **test-impact-mapper** — maps changed files to the smallest sufficient test set
- **docs-drift-sync** — enforces doc updates when runtime behavior changes
- **shared-env-contract** — env loading rules that affect CI env assumptions
- **service-health-check-audit** — startup behavior that CI test jobs depend on
