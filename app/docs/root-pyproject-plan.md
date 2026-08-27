# Root pyproject.toml — Dependency Groups Plan

> **Scope:** Design document for consolidating all requirements files into a single
> root `pyproject.toml` with `[project.optional-dependencies]` groups.
> **Status:** P1.2 — plan only. No packages deleted, upgraded, or moved yet.
> **Pre-requisites before migration:** P1.3 lockfile strategy settled, pymongo 3→4
> upgrade risk resolved, `ultralytics` moved out of core profile.
> **Cross-reference:** [docs/dependency-contract.md](dependency-contract.md)

---

## 1. Motivation

The repo currently has 15+ requirements files across three layers
(`app/requirements/`, `services/chatbot/`, `services/mcp-server/`).
The chunk-and-profile system works but is opaque to new contributors and
makes dependency-group installs (`pip install -e ".[test]"`) impossible.

The goal of this plan is to define the target state clearly **before** touching
any file, so that the migration can happen in one atomic step per group
without destabilizing the running environment.

---

## 2. Proposed Extras Groups

The following groups map to `[project.optional-dependencies]` entries in a
root `pyproject.toml`. Groups are designed to be composable:
`pip install -e ".[core,test]"` should produce a working chatbot test environment.

### `core`

Runtime dependencies for the Flask chatbot and the MCP server.

| Package | Version floor | Source chunk |
|---|---|---|
| setuptools | <81.0.0 | chunk_1_core |
| numpy | >=1.20.0,<2.0.0 | chunk_1_core |
| pyyaml | >=6.0.0 | chunk_1_core |
| python-dotenv | >=1.0.0 | chunk_1_core |
| requests | >=2.31.0 | chunk_1_core |
| tqdm | >=4.65.0 | chunk_1_core |
| colorama | >=0.4.6 | chunk_1_core |
| rich | >=13.7.0 | chunk_1_core |
| psutil | >=5.9.0 | chunk_1_core |
| filelock | >=3.12.0 | chunk_1_core |
| jsonschema | >=4.17.0 | chunk_1_core |
| flask | >=3.0.0 | chunk_2_web |
| flask-cors | >=4.0.0 | chunk_2_web |
| flask-socketio | >=5.3.0 | chunk_2_web |
| python-socketio | >=5.10.0 | chunk_2_web |
| werkzeug | >=3.0.0 | chunk_2_web |
| eventlet | >=0.33.0 | chunk_2_web |
| fastapi | >=0.94.0 | chunk_2_web ¹ |
| uvicorn | >=0.20.0 | chunk_2_web ¹ |
| python-multipart | >=0.0.6 | chunk_2_web |
| watchdog | >=2.0.0 | chunk_2_web |
| aiofiles | >=23.0.0 | chunk_2_web |
| starlette | >=0.27.0 | chunk_2_web ¹ |
| pymongo | >=4.6.0 | chunk_3_database ² |
| dnspython | >=2.4.0 | chunk_3_database ² |
| redis | >=5.0.0 | chunk_3_database |
| clickhouse-connect | >=0.7.7 | chunk_3_database |
| pandas | >=2.0.0 | chunk_3_database |
| sqlparse | >=0.4.4 | chunk_3_database |
| openpyxl | >=3.1.0 | chunk_3_database |
| openai | >=1.0.0 | chunk_4_ai_apis |
| pydantic | >=2.0.0,<3.0.0 | chunk_4_ai_apis |
| google-genai | >=1.56.0 | chunk_4_ai_apis |
| httpx | >=0.27.0 | chunk_4_ai_apis |
| anyio | >=4.0.0 | chunk_4_ai_apis |
| Pillow | >=10.3.0 | profile_core_services ³ |
| mcp[cli] | >=1.27.1 | reconciled ⁴ |

**Footnotes:**

¹ `fastapi`, `uvicorn`, `starlette` — FastAPI was removed as a runtime path in May 2026.
These packages remain in `core` because the MCP SDK (`mcp[cli]`) pulls them in
transitively. Do not remove until the MCP transitive dep tree is verified clean.
Mark clearly as "retained for transitive dep, not an active request handler."

² `pymongo`/`dnspython` — declared floor is `>=4.6.0`/`>=2.4.0` but installed
versions are 3.12.0/1.16.0 (see Section 4, Conflict #1). The declared floors
are correct targets; the installed versions are the blocker. Do not lower the
declared floor; fix the install in a dedicated upgrade job before migrating.

³ `Pillow` — added to core in May 2026 for the anime pipeline orchestrator's
reference-image encode/decode. Not in the original chunk files.

⁴ `mcp[cli]` — `profile_core_services.txt` declares `>=1.0.0`; `services/mcp-server/requirements.txt`
declares `>=1.27.1`. Reconcile to `>=1.27.1` at migration time.

---

### `mcp`

Standalone install for the MCP server only (minimal, no chatbot stack needed).

| Package | Version floor |
|---|---|
| mcp[cli] | >=1.27.1 |

Usage: `pip install -e ".[mcp]"` inside `venv-core`.

---

### `test`

Test runner and mocking tools. Required for `pytest tests/` in `services/chatbot/`.

| Package | Version floor | Source |
|---|---|---|
| pytest | >=7.4.0 | tests/requirements-test.txt |
| pytest-cov | >=7.1.0 | tests/requirements-test.txt |
| pytest-mock | >=3.12.0 | tests/requirements-test.txt |
| pytest-asyncio | >=0.21.0 | tests/requirements-test.txt |
| pytest-flask | >=1.3.0 | tests/requirements-test.txt |
| pytest-timeout | >=2.2.0 | tests/requirements-test.txt |
| requests-mock | >=1.12.1 | tests/requirements-test.txt |
| coverage | >=7.13.5 | tests/requirements-test.txt |

---

### `dev`

Code quality, monitoring, and optional UI tools. Not required at runtime.

| Package | Version floor | Source |
|---|---|---|
| black | >=23.0.0 | chunk_10_tools |
| flake8 | >=6.0.0 | chunk_10_tools |
| isort | >=5.12.0 | chunk_10_tools |
| mypy | >=1.8.0 | chunk_10_tools |
| scikit-learn | >=1.3.0 | chunk_10_tools |
| tensorboard | >=2.13.0 | chunk_10_tools |
| wandb | >=0.15.0 | chunk_10_tools |
| GitPython | >=3.1.0 | chunk_10_tools |
| jsonmerge | >=1.9.0 | chunk_10_tools |
| gradio | >=3.0.0 | profile_core_services ⁵ |

⁵ `gradio` — currently declared in `profile_core_services.txt` as a runtime dep,
but it is only used by optional UI routes. Move to `dev` in migration. **Flag
for removal from `profile_core_services.txt`** before or during the app factory
job (P1.5) — it is the largest unnecessary transitive pull in `venv-core`.

---

### `rag`

RAG subsystem: vector store, relational DB, cloud storage, embeddings.
Only needed when the RAG subsystem (`src/rag/`) is active.

| Package | Version floor | Source |
|---|---|---|
| chromadb | >=0.5.0 | chatbot/requirements.txt |
| sqlalchemy[asyncio] | >=2.0.0 | chatbot/requirements.txt |
| alembic | >=1.13.0 | chatbot/requirements.txt |
| pgvector | >=0.3.0 | chatbot/requirements.txt |
| psycopg2-binary | >=2.9.12 | chatbot/requirements.txt |
| boto3 | >=1.43.6 | chatbot/requirements.txt |
| beautifulsoup4 | >=4.12.0 | chatbot/requirements.txt |
| pymupdf | >=1.24.0 | chatbot/requirements.txt |
| sentence-transformers | >=2.2.2 | chatbot/requirements.txt |
| scipy | >=1.11.0 | chatbot/requirements.txt |

---

### `audio`

Speech and audio processing. The `speech2text` service is archived; this group
is retained for local Whisper transcription routes in `src/audio_transcription.py`.

| Package | Version floor | Source |
|---|---|---|
| faster-whisper | ==1.0.3 | chunk_7_audio |
| pyannote.audio | ==3.1.1 | chunk_7_audio |
| speechbrain | >=1.0.0 | chunk_7_audio |
| pyannote.core | >=5.0.0 | chunk_7_audio |
| pyannote.database | >=5.0.0 | chunk_7_audio |
| pyannote.metrics | >=3.2.0 | chunk_7_audio |
| pyannote.pipeline | >=3.0.0 | chunk_7_audio |
| librosa | ==0.10.1 | chunk_7_audio |
| soundfile | ==0.12.1 | chunk_7_audio |
| audioread | ==3.0.1 | chunk_7_audio |
| av | >=12.0.0 | chunk_7_audio |
| scipy | >=1.11.0 | chunk_7_audio |
| pydub | >=0.25.1 | chunk_7_audio |

---

### `ocr`

Document processing and OCR. PaddleOCR/PaddlePaddle are heavy GPU-optional
frameworks. PyMuPDF and markitdown are lighter and more broadly useful.

| Package | Version floor | Source |
|---|---|---|
| paddleocr | ==2.7.3 | chunk_8_document |
| paddlepaddle | ==2.6.2 | chunk_8_document |
| PyMuPDF | ==1.23.8 | chunk_8_document |
| albumentations | >=1.3.0 | chunk_8_document |
| markitdown[all] | >=0.1.0 | chunk_8_document |

Recommended split at migration time: consider a `doc-light` sub-group
(`PyMuPDF`, `markitdown[all]`) vs `doc-heavy` (`paddleocr`, `paddlepaddle`,
`albumentations`) since the light subset is useful without the GPU deps.

---

### `image`

Full diffusion, upscale, and ML core stack. Requires PyTorch CUDA wheels
installed separately (not pinned here — see [vram_12gb_guide.md](vram_12gb_guide.md)).

| Package | Version floor | Source |
|---|---|---|
| transformers | >=4.41,<5.1 | chunk_5_ml_core |
| accelerate | >=0.27.0 | chunk_5_ml_core |
| sentencepiece | >=0.2.0 | chunk_5_ml_core |
| safetensors | >=0.4.0 | chunk_5_ml_core |
| huggingface-hub | >=0.21.4 | chunk_5_ml_core |
| peft | >=0.4.0 | chunk_5_ml_core |
| datasets | >=2.14.0 | chunk_5_ml_core |
| protobuf | >=3.20.0,<=6.33.4 | chunk_5_ml_core |
| omegaconf | >=2.3.0 | chunk_5_ml_core |
| sentence-transformers | >=2.2.2 | chunk_5_ml_core |
| Pillow | >=10.3.0 | chunk_6_image (also in core) |
| opencv-python | <=4.13.0.90 | chunk_6_image |
| scikit-image | >=0.19.3 | chunk_6_image |
| einops | >=0.4.0 | chunk_6_image |
| lpips | >=0.1.4 | chunk_6_image |
| resize-right | >=0.0.2 | chunk_6_image |
| piexif | >=1.1.3 | chunk_6_image |
| blendmodes | >=2022.0.0 | chunk_6_image |
| kornia | >=0.7.0 | chunk_6_image |
| tomesd | >=0.1.3 | chunk_6_image |
| lark | >=1.1.5 | chunk_6_image |
| inflection | >=0.5.1 | chunk_6_image |
| pytorch_lightning | >=2.0.0 | chunk_6_image |
| torchdiffeq | >=0.2.3 | chunk_6_image |
| torchsde | >=0.2.5 | chunk_6_image |
| clean-fid | >=0.1.35 | chunk_6_image |
| diffusers | >=0.21.0 | chunk_6_image |
| open-clip-torch | >=2.20.0 | chunk_6_image |
| timm | >=0.9.0 | chunk_6_image |
| basicsr | >=1.4.2 | chunk_9_upscale |
| facexlib | >=0.2.5 | chunk_9_upscale |
| gfpgan | >=1.3.5 | chunk_9_upscale |
| realesrgan | >=0.3.0 | chunk_9_upscale |
| ultralytics | >=8.0.0 | profile_core_services ⁶ |

⁶ `ultralytics` — currently in `profile_core_services.txt` (core venv) because
the anime pipeline imports it when `IMAGE_PIPELINE_V2=true`. It pulls in
`torch`/`torchvision`/`opencv-python` transitively, making `venv-core`
significantly heavier. **Move to `image` group at migration time.** The anime
pipeline import should be guarded with `importlib.util.find_spec("ultralytics")`
so the core venv can operate without it.

---

### `desktop`

No Python dependencies. The Electron desktop wrapper (`app/electron/`) is
managed entirely by `package.json` / npm. This group is a placeholder to
document that fact and to provide a pip-installable no-op for CI scripts that
iterate over all groups.

---

## 3. Conflicts and Tensions

These must be resolved **before** the actual migration job runs.
Do not close this doc until all items are marked ✓.

| # | Conflict | Blocker? | Resolution path |
|---|---|---|---|
| 1 | `pymongo` 3.12.0 installed vs `>=4.6.0` declared. PyMongo 4.x has breaking API changes (`count()` removed, find behavior). | **Yes** — migration cannot pin >=4.6.0 while 3.12.0 is installed. | Audit all pymongo call sites; upgrade in a dedicated job before migration. |
| 2 | `fastapi`/`uvicorn`/`starlette` in `core` — FastAPI is not an active runtime path but MCP SDK depends on it transitively. | No — keep in `core`; document clearly. | Verify MCP transitive dep tree before removing. |
| 3 | `mcp[cli]` version skew: `>=1.0.0` in `profile_core_services.txt` vs `>=1.27.1` in `services/mcp-server/requirements.txt`. | Minor — no current breakage. | Reconcile to `>=1.27.1` at migration time. |
| 4 | `numpy<2.0.0` hard upper bound in chunk_1 — future torch upgrades may require NumPy 2.x. | Not now. | Test before loosening; do not change the cap without a torch compatibility check. |
| 5 | `gradio>=3.0.0` in `profile_core_services.txt` — declared as runtime dep, but is dev/optional only. | No — but inflates `venv-core`. | Move to `dev` group at migration. Flag for removal from core profile in P1.5 (app factory). |
| 6 | `services/chatbot/requirements.txt` header reads `Python: 3.10.6` — stale since P1.1 pinned 3.11.9. | No — documentation only. | Fix header in P1.8 (route/docs cleanup). |

---

## 4. Phased Migration Path

### Phase 0 (current — P1.2)

Document only. No file changes to requirements files or pyproject.toml.

### Phase 1 (P1.3)

Choose a lock tool (`pip-tools` / `uv` / `poetry`) — one tool only.
Generate scoped lock files per group using this plan as the group definition.
See [docs/supply-chain.md](supply-chain.md) (to be created in P1.3).

### Phase 2 (post-P1.3, pre-P1.5)

Resolve Conflict #1 (pymongo upgrade) and Conflict #5 (remove `gradio`/`ultralytics`
from core profile) so `venv-core` install is lean before the app factory refactor.

### Phase 3 (post-P1.5)

Create root `pyproject.toml` with:

```toml
[project]
name = "ai-assistant"
version = "2.0.0"
requires-python = ">=3.11"

[project.optional-dependencies]
core    = [...]
mcp     = [...]
test    = [...]
dev     = [...]
rag     = [...]
audio   = [...]
ocr     = [...]
image   = [...]
```

Keep old chunk files in place initially. Switch CI/CD to
`pip install -e ".[core,test]"` first, then deprecate chunk files one-by-one
after confirming each group installs cleanly in CI.

### Phase 4 (P3.3)

Archive or delete the following after Phase 3 is confirmed stable:

| File | Reason |
|---|---|
| `requirements.txt` (repo root) | Stale all-in-one; archived services |
| `app/requirements/requirements_unified_3119*.txt` | One-time pip-list artifacts |
| `app/requirements/requirements_chunk_10_tools.txt` | Replaced by `dev` group |
| `app/requirements/PROFILE_SERVICE_MAP.md` | Superseded by this doc and group names |

Do **not** delete `requirements-core.txt` or `requirements-image.txt` until
the lock-file strategy (Phase 1) provides an equivalent freeze artifact.

---

## 5. Install Reference (current state → target state)

| Scenario | Current command | Target command |
|---|---|---|
| Chatbot runtime | `pip install -r app/requirements/profile_core_services.txt` | `pip install -e ".[core]"` |
| Chatbot + tests | + `pip install -r services/chatbot/tests/requirements-test.txt` | `pip install -e ".[core,test]"` |
| MCP server only | `pip install -r services/mcp-server/requirements.txt` | `pip install -e ".[mcp]"` |
| Chatbot + RAG | + `pip install -r services/chatbot/requirements.txt` | `pip install -e ".[core,rag]"` |
| Image services | `pip install -r app/requirements/profile_image_ai_services.txt` | `pip install -e ".[image]"` |
| Full dev | *(no single command)* | `pip install -e ".[core,test,dev,rag,audio,ocr]"` |
