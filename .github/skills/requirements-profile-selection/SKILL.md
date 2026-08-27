---
name: requirements-profile-selection
description: "Teach Copilot how to choose the correct dependency profile when working on the core chatbot and tools, and avoid dragging image-service dependencies into chatbot-only tasks. Use when: adding, removing, or upgrading a Python package; reviewing a dependency change; debugging import errors or version conflicts; checking whether a package belongs in venv-core or venv-image; auditing CI workflow install steps; or verifying that a chatbot-only change does not pull in image-stack packages."
---

# Requirements Profile Selection

## When to use this skill

- Adding, removing, or upgrading a Python package in any requirements file.
- Reviewing a PR that touches `requirements*.txt` or `profile_*.txt`.
- Debugging an `ImportError`, version conflict, or protobuf/numpy mismatch.
- Checking whether a new dependency belongs in `venv-core` or `venv-image`.
- Auditing CI workflow install steps after a dependency change.
- Verifying that a chatbot-only change does not leak image-stack packages into the core profile.

## Do not use for

- ComfyUI custom-node dependencies — those are managed inside `ComfyUI/` and are out of scope.
- General Python packaging advice unrelated to this repository.

---

## Dependency source-of-truth files

### Profile files (authoritative for local venv setup)

| File | Profile | venv | Target services |
|------|---------|------|-----------------|
| `app/requirements/profile_core_services.txt` | core | `venv-core` | chatbot, MCP server, hub-gateway, speech2text, text2sql, document-intelligence |
| `app/requirements/profile_image_ai_services.txt` | image | `venv-image` | stable-diffusion, edit-image, image-upscale, lora-training, ComfyUI workflows |

### Service-local requirements (authoritative for CI and per-service installs)

| File | Used by |
|------|---------|
| `services/chatbot/requirements.txt` | CI (`tests.yml`, `ci-cd.yml`), chatbot service |
| `services/mcp-server/requirements.txt` | MCP server |

### Chunk files (building blocks for profiles)

| Chunk | Contents | Used by core | Used by image |
|-------|----------|:---:|:---:|
| `chunk_1_core.txt` | setuptools, numpy, pyyaml, requests, tqdm, etc. | ✅ | ✅ |
| `chunk_2_web.txt` | Flask, FastAPI, uvicorn, werkzeug, etc. | ✅ | ✅ |
| `chunk_3_database.txt` | pymongo, redis, clickhouse, pandas, etc. | ✅ | ❌ |
| `chunk_4_ai_apis.txt` | openai, google-genai, pydantic, httpx | ✅ | ❌ |
| `chunk_5_ml_core.txt` | transformers, accelerate, HuggingFace hub, protobuf | ❌ | ✅ |
| `chunk_6_image.txt` | Pillow, opencv, diffusers, open-clip-torch, kornia | ❌ | ✅ |
| `chunk_7_audio.txt` | faster-whisper, pyannote, librosa, speechbrain | ✅ | ❌ |
| `chunk_8_document.txt` | paddleocr, paddlepaddle, PyMuPDF | ✅ | ❌ |
| `chunk_9_upscale.txt` | basicsr, gfpgan, realesrgan | ❌ | ✅ |
| `chunk_10_tools.txt` | gradio, pytest, flake8, tensorboard, wandb, mcp | mixed | mixed |

### Pinned lock files (generated, not manually edited)

| File | Purpose |
|------|---------|
| `app/requirements/freeze-venv-core.txt` (repo root) | Full pip freeze of `venv-core` |
| `app/requirements/freeze-venv-image.txt` (repo root) | Full pip freeze of `venv-image` |

**Rule:** Never hand-edit the root lock files. They are regenerated from `pip freeze` after installing from profile files.

---

## Profile boundaries

### Packages that belong ONLY in `venv-core`

These are chatbot/MCP runtime dependencies. They must not require image-stack packages.

```
flask, flask-cors, fastapi, uvicorn, werkzeug
openai, google-genai, httpx, pydantic
pymongo, dnspython, redis
mcp[cli]
chromadb, sqlalchemy, alembic, pgvector, psycopg2-binary, boto3
firebase-admin, google-auth, google-api-python-client
sentence-transformers (chatbot semantic search)
Pillow (lightweight image handling only — no diffusion)
```

### Packages that belong ONLY in `venv-image`

These are heavy ML/diffusion packages. They must never appear in `profile_core_services.txt` or `services/chatbot/requirements.txt`.

```
torch (with CUDA), torchvision, torchaudio (when used for diffusion)
diffusers, open-clip-torch, kornia, tomesd
basicsr, gfpgan, realesrgan, facexlib
pytorch_lightning, torchdiffeq, torchsde
transformers (image-pipeline usage), accelerate (image-pipeline usage)
xformers
```

### Packages in BOTH profiles (shared)

```
numpy, pyyaml, requests, tqdm, colorama, rich, psutil
setuptools, filelock, jsonschema
aiofiles, anyio
```

### Gray-area packages — require justification

| Package | Why it's gray | Rule |
|---------|---------------|------|
| `torch` | chatbot uses it for local model inference (sentence-transformers) | Allowed in `venv-core` if already present, but do NOT add `torchvision` or CUDA-specific torch to core |
| `transformers` | chatbot uses for local embeddings; image uses for diffusion | Allowed in both, but version ranges must not conflict |
| `accelerate` | transitive dep of transformers in both profiles | Same — version ranges must stay compatible |
| `protobuf` | needed by google-genai (core) and transformers (image) | Keep range wide (`>=3.20.0`), avoid pinning a version that breaks the other profile |
| `scipy` | chatbot uses for scikit-learn; image uses for signal processing | Allowed in both |
| `sentence-transformers` | chatbot needs for RAG; image profile doesn't need it | Core only |
| `gradio` | chatbot UI (optional); image services don't use it | Core only, optional |

---

## Classification rule

Every dependency change must be classified before committing:

| Classification | Meaning | Files to edit |
|----------------|---------|---------------|
| **core-only** | Package used exclusively by chatbot, MCP server, or shared utilities | `services/chatbot/requirements.txt`, optionally `profile_core_services.txt` or the relevant chunk |
| **image-only** | Package used exclusively by stable-diffusion, edit-image, or ComfyUI | `profile_image_ai_services.txt` or the relevant chunk. Do NOT touch chatbot requirements. |
| **shared** | Package used by both profiles (e.g., numpy, requests) | Edit the chunk file (`chunk_1_core.txt`, `chunk_2_web.txt`, etc.). Both profiles inherit it. |
| **workflow-only** | Package used only in CI/CD workflows (linting, testing tools) | `tests/requirements-test.txt` or inline `pip install` in workflow YAML. Not in runtime profiles. |
| **dev-only** | Package used only for local development (black, mypy, isort) | `chunk_10_tools.txt` or local dev instructions. Not in runtime profiles. |

**If you cannot classify a package, stop and ask.** Do not add it to "the closest profile."

---

## Justification requirement

When adding or upgrading a package, provide:

1. **What service needs it** — chatbot, MCP server, stable-diffusion, etc.
2. **Why it's needed** — which feature, route, or tool function uses it.
3. **Why this profile** — explain why it belongs in core vs image vs both.
4. **Transitive impact** — does it pull in heavy sub-dependencies? (e.g., adding `sentence-transformers` pulls `torch`)
5. **Version constraint** — pin to a range (`>=X.Y.Z,<X+1`) or exact version? Prefer ranges for libraries, exact for frameworks.

---

## Heavyweight package guardrails

Do NOT add these to `venv-core` / chatbot requirements without explicit justification:

| Package | Size (approx) | Why it's dangerous in core |
|---------|---------------|---------------------------|
| `torch` (CUDA build) | ~2 GB | Already present via sentence-transformers; adding CUDA-specific builds inflates core |
| `torchvision` | ~500 MB | Only needed for image pipelines |
| `diffusers` | ~200 MB + model downloads | Image generation only |
| `open-clip-torch` | ~400 MB | CLIP embeddings for image search — not needed for chatbot text search |
| `basicsr` / `realesrgan` | ~300 MB | Image upscaling only |
| `paddleocr` / `paddlepaddle` | ~1 GB | OCR — already in core but heavy; do not add more Paddle packages |
| `xformers` | ~200 MB + CUDA | GPU memory optimization for diffusion — never in core |
| `tensorboard` / `wandb` | ~100 MB each | ML experiment tracking — dev-only, not runtime |

**Rule:** If a chatbot feature can be implemented with `openai`, `google-genai`, or `httpx` (API calls), prefer that over adding a local ML package.

---

## CI workflow dependency assumptions

### `tests.yml` and `ci-cd.yml`

Both install from `services/chatbot/requirements.txt` — NOT from profile files. This means:

- `services/chatbot/requirements.txt` must be self-contained for chatbot CI.
- It must not `-r` reference chunk files (it doesn't currently).
- If you add a package to a chunk file but not to `services/chatbot/requirements.txt`, CI will not have it.

### `security-scan.yml`

Runs `pip-audit` against:
- `services/chatbot/requirements.txt`
- `services/stable-diffusion/requirements.txt`
- `services/edit-image/requirements.txt`
- `services/mcp-server/requirements.txt`

If you add a new service-local `requirements.txt`, add it to the pip-audit loop.

### Profile files vs CI files

| Context | Which file is used |
|---------|-------------------|
| Local dev (`venv-core`) | `app/requirements/profile_core_services.txt` → installs chunk files |
| Local dev (`venv-image`) | `app/requirements/profile_image_ai_services.txt` → installs chunk files |
| CI chatbot tests | `services/chatbot/requirements.txt` (self-contained) |
| CI security audit | Per-service `requirements.txt` files |
| CI lint | No runtime deps installed — just `flake8` |

**Consequence:** A package needed at runtime must appear in BOTH the profile file (for local dev) AND the service-local `requirements.txt` (for CI). These can drift — verify both when adding packages.

---

## Verification after dependency changes

### Minimal checks (always do)

1. **Classify the change** — core-only, image-only, shared, workflow-only, or dev-only.
2. **Check both files** — does the package appear in the correct profile file AND the correct service-local `requirements.txt`?
3. **Check for cross-contamination** — does the package or any of its transitive deps pull in image-stack packages into core?
4. **Check version ranges** — does the new range conflict with the same package pinned in the other profile?

### Deeper checks (for heavyweight or gray-area packages)

5. **Run `pip install --dry-run`** — check what gets pulled in transitively.
6. **Run chatbot tests** — `cd services/chatbot && pytest tests/ -v`.
7. **Check CI install** — does `services/chatbot/requirements.txt` still install cleanly without the chunk system?
8. **Check `pip-audit`** — does the new package introduce known vulnerabilities?

### Lock file update (when explicitly requested)

```powershell
# Regenerate core lock file
& .\venv-core\Scripts\Activate.ps1
pip freeze > app/requirements/freeze-venv-core.txt

# Regenerate image lock file
& .\venv-image\Scripts\Activate.ps1
pip freeze > app/requirements/freeze-venv-image.txt
```

Do NOT regenerate lock files unless the user asks or the profile file was changed.

---

## Common mistakes to avoid

| Mistake | Why it's wrong | Fix |
|---------|----------------|-----|
| Adding `diffusers` to chatbot requirements for "image description" | Use `openai` vision API instead — no local diffusion needed | Remove from chatbot, use API call |
| Adding `torch` with CUDA index URL to `profile_core_services.txt` | Bloats core venv, may conflict with image venv's CUDA version | Keep CPU-only torch in core, or rely on transitive install from sentence-transformers |
| Editing `app/requirements/freeze-venv-core.txt` (root) by hand | It's a generated lock file | Edit `profile_core_services.txt` or `services/chatbot/requirements.txt` instead |
| Adding package to chunk file but not to `services/chatbot/requirements.txt` | CI won't have it — tests may pass locally but fail in CI | Add to both |
| Pinning exact version in chunk file | Breaks flexibility for both profiles | Use range (`>=X.Y.Z`) in chunks, exact pins only in service-local or lock files |
| Adding dev tools (pytest, black) to runtime profile | Bloats production install | Put in `chunk_10_tools.txt` or `tests/requirements-test.txt` |

---

## Dependency-profile checklist

Before merging any dependency change:

- [ ] **Classified** — change is labeled core-only, image-only, shared, workflow-only, or dev-only
- [ ] **Correct profile** — package added to the right profile file and NOT the wrong one
- [ ] **Service-local sync** — if adding to a profile chunk, also added to the relevant `services/*/requirements.txt` for CI
- [ ] **No cross-contamination** — image-stack packages not leaking into `profile_core_services.txt` or `services/chatbot/requirements.txt`
- [ ] **No heavyweight surprise** — package does not transitively pull in large ML/CUDA deps into core
- [ ] **Version range compatible** — new range does not conflict with the same package in the other profile
- [ ] **Justified** — PR describes what service needs it, why, and why this profile
- [ ] **Tests pass** — `cd services/chatbot && pytest tests/ -v` still green
- [ ] **Lock files untouched** — root `app/requirements/freeze-venv-core.txt` and `app/requirements/freeze-venv-image.txt` not hand-edited (regenerate if needed)
- [ ] **CI workflow checked** — if a new service-local requirements file was added, it's included in `security-scan.yml` pip-audit loop

---

## Related skills

- **shared-env-contract** — env vars loaded per profile; new packages may need new env config
- **service-health-check-audit** — startup failures from missing packages
- **test-impact-mapper** — which tests to run after a dependency change
- **docs-drift-sync** — README dependency section must match actual profiles
