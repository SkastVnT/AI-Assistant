# Supply Chain Strategy — AI-Assistant

This document defines how dependency locking, auditing, and SBOM generation work for this project.

Related: [dependency-contract.md](dependency-contract.md), [root-pyproject-plan.md](root-pyproject-plan.md)

---

## Tool choice: pip-tools

**pip-tools** (`pip-compile`) is the chosen lock tool.

Rationale:
- Integrates with existing `requirements.txt`-based workflow; no migration needed.
- Produces plain-text `*.txt` lock files compatible with `pip install -r`.
- Lower overhead than poetry or uv for a project that already manages two separate venvs manually.
- `pip-sync` enforces exact reproducibility per environment.

Install in each venv when needed:
```
pip install pip-tools
```

---

## Lock file targets

One lock file per dependency group. Inputs are the group source files from `app/requirements/`:

| Lock file | Input | venv |
|---|---|---|
| `locks/core.lock.txt` | `app/requirements/profile_core_services.txt` | `venv-core` |
| `locks/mcp.lock.txt` | `services/mcp-server/requirements.txt` | `venv-core` |
| `locks/test.lock.txt` | `services/chatbot/tests/requirements-test.txt` + `app/requirements/profile_core_services.txt` | `venv-core` |
| `locks/image.lock.txt` | `app/requirements/profile_image_ai_services.txt` | `venv-image` |

Lock files live in `locks/` at the repo root and are committed to source control.

> **Status (May 2026):** Lock files are NOT yet generated. A pymongo 3→4 version conflict between
> `services/chatbot/requirements.txt` (pins `pymongo==3.12.3`) and `profile_core_services.txt`
> (unpinned) must be resolved first. See [root-pyproject-plan.md § Conflicts](root-pyproject-plan.md)
> Conflict #1 for details. Lock generation is gated on that resolution (P2 milestone).

---

## Generating lock files (when ready)

Run from the repo root with the target venv active:

```powershell
# venv-core
venv-core\Scripts\activate
pip-compile app/requirements/profile_core_services.txt -o locks/core.lock.txt --strip-extras
pip-compile services/mcp-server/requirements.txt -o locks/mcp.lock.txt --strip-extras
pip-compile services/chatbot/tests/requirements-test.txt app/requirements/profile_core_services.txt `
  -o locks/test.lock.txt --strip-extras

# venv-image (separate terminal)
venv-image\Scripts\activate
pip-compile app/requirements/profile_image_ai_services.txt -o locks/image.lock.txt --strip-extras
```

To install from a lock file exactly:
```powershell
pip-sync locks/core.lock.txt
```

---

## Updating lock files

When adding or upgrading a package:
1. Edit the appropriate source file in `app/requirements/` or the service `requirements.txt`.
2. Re-run `pip-compile` for the affected group(s).
3. Review the diff — confirm only expected changes appear.
4. Commit both the source edit and the updated lock file together.

Do **not** edit lock files by hand.

---

## SBOM generation (pip-audit)

`pip-audit` can produce a CycloneDX SBOM from any lock file:

```powershell
# Install
pip install pip-audit

# Generate SBOM for core group
pip-audit -r locks/core.lock.txt --format cyclonedx-json -o sbom-core.json

# Generate SBOM for all groups
foreach ($group in @("core", "mcp", "test", "image")) {
    pip-audit -r "locks/$group.lock.txt" --format cyclonedx-json -o "sbom-$group.json"
}
```

> Until lock files are generated (see Status above), run pip-audit against the profile files
> directly as a best-effort audit:
> ```
> pip-audit -r app/requirements/profile_core_services.txt --desc
> ```

---

## CI integration (planned, P2)

Once lock files exist, the CI `security-scan.yml` step should:
1. Run `pip-audit -r locks/core.lock.txt` — fail on HIGH/CRITICAL.
2. Produce a CycloneDX SBOM artifact per group.
3. Upload SBOMs to the `security-reports-*` artifact bucket.

The current `security-scan.yml` already audits `profile_core_services.txt` as an interim measure.

---

## Supply-chain hygiene rules

1. **Never install from `requirements.txt` (root) or `services/chatbot/requirements.txt`** for CI.
   Those files exist for reference / legacy compatibility; they include the full RAG + Firebase stack.
   Always use the profile files in `app/requirements/`.

2. **Do not mix venv-core and venv-image packages.**
   `torch`, `diffusers`, `gradio` belong only in `venv-image`.
   See [dependency-contract.md § Dependency profiles](dependency-contract.md) for the full boundary.

3. **pip-audit must not be silenced** with `continue-on-error: true` in CI.
   A decorative scan is equivalent to no scan.

4. **Lock files and lock-file inputs must be committed together.**
   Reviewing lock file diffs is the primary supply-chain defence against dependency confusion.
