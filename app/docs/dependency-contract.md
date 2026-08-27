# Dependency Contract — AI-Assistant

> **Scope:** Python runtime and dependency ownership for all active services.
> **Status:** P1.1 — established 2026-05-15.
> **Owner:** Kept in sync by whoever changes a requirements file or adds/removes a service.

---

## 1. Canonical Python Runtime

| Setting | Value | Authoritative source |
|---|---|---|
| Python version | **3.11.9** | `.python-version` (repo root), `app/config/.python-version`, `services/chatbot/.python-version` |
| Minimum floor | `>=3.11` | `app/config/pyproject.toml` → `requires-python` |
| End-of-life date | October 2027 | [python.org/downloads](https://www.python.org/downloads/) |

**Why 3.11, not ">=3.10":** Both venv freeze snapshots (`app/requirements/freeze-venv-core.txt`, `app/requirements/freeze-venv-image.txt`) were generated against CPython 3.11.9 on Windows. Several transitive deps (ComfyUI frontend, pyannote, torch 2.10) assume 3.11. The old `>=3.10` floor in `pyproject.toml` was stale and has been corrected to `>=3.11`.

---

## 2. Two-Venv Model

The repo uses **two isolated Python environments** — never mix them.

| venv | Path | Purpose | Install from |
|---|---|---|---|
| `venv-core` | `venv-core/` at repo root | ChatBot (Flask), MCP Server | `app/requirements/profile_core_services.txt` |
| `venv-image` | `venv-image/` at repo root | Stable Diffusion, Edit Image / ComfyUI | `app/requirements/profile_image_ai_services.txt` |

Stable Diffusion and Edit Image each have **their own internal venv** (`services/stable-diffusion/venv`, `services/edit-image/venv`) managed by their own launchers. These are not `venv-core` or `venv-image`.

---

## 3. How to Install — Per Scenario

### 3a. Chatbot only (most common)

```powershell
# From repo root, with venv-core activated:
pip install -r app/requirements/profile_core_services.txt

# If running tests:
pip install -r services/chatbot/tests/requirements-test.txt

# If using RAG features (chromadb, pgvector, psycopg2):
pip install -r services/chatbot/requirements.txt
```

> `services/chatbot/requirements.txt` is a **superset** of `profile_core_services.txt` for chatbot use. It adds the RAG stack (chromadb, pgvector, psycopg2-binary, boto3). Install it only if the RAG subsystem is needed; otherwise the profile is sufficient.

### 3b. MCP Server only

```powershell
# Minimum install — MCP server has no other hard deps beyond venv-core:
pip install -r services/mcp-server/requirements.txt
# (or just pip install "mcp[cli]>=1.27.1")
```

The MCP server reuses `venv-core`; there is no separate venv for it.

### 3c. Image / ComfyUI services

```powershell
pip install -r app/requirements/profile_image_ai_services.txt
# PyTorch CUDA wheels must be installed manually — see vram_12gb_guide.md
```

### 3d. Running tests (chatbot)

```powershell
# Must be run from services/chatbot/ with venv-core active:
cd services/chatbot
pip install -r tests/requirements-test.txt
pytest tests/ -v
# Default gate (no external deps):
pytest tests/ -m "not integration and not image and not rag and not hermes and not mongo and not slow and not agentic" -q
```

The local gate script (`app/scripts/verify-local.ps1`) handles this automatically.

---

## 4. File Classification

### 4a. Active — use these

| File | Role | Edit when… |
|---|---|---|
| `app/requirements/profile_core_services.txt` | **Primary venv-core installer** (flat, self-contained). | Adding a new chatbot/MCP runtime dependency |
| `app/requirements/profile_image_ai_services.txt` | **Primary venv-image installer** (flat, self-contained). | Adding a new image-pipeline runtime dependency |
| `app/requirements/profile_chatbot_minimal.txt` | Chatbot + MCP only; `profile_core_services.txt` minus the audio and document blocks (20 packages). Strict subset. | Keep in sync when editing the core profile |
| `services/chatbot/requirements.txt` | Chatbot-extended install including RAG stack | Adding chatbot-specific deps not in the shared profile |
| `services/chatbot/tests/requirements-test.txt` | Test-only deps (pytest, pytest-mock, pytest-asyncio, etc.) | Adding or upgrading a test tool |
| `services/mcp-server/requirements.txt` | MCP server runtime (mcp[cli] only) | Upgrading the MCP package |

### 4b. Reference — do not edit manually

| File | Role |
|---|---|
| `app/requirements/freeze-venv-core.txt` | **Freeze snapshot of venv-core** (generated 2026-04-03, exact `==` pins, full pip list). Use as the source of truth for "what is actually installed." Do not pip-install this file — it contains platform-specific hashes and may not install cleanly from scratch. |
| `app/requirements/freeze-venv-image.txt` | **Freeze snapshot of venv-image** (same, 2026-04-03). Same caution. |

To regenerate a freeze: `pip list --format=freeze > app/requirements/freeze-venv-core.txt` (from inside an active venv-core).

### 4c. Orphaned — do not rely on

| File | Reason |
|---|---|

### 4d. Legacy / bridge — do not use for installs

| File | Why stale |
|---|---|
| `app/requirements/legacy-root-requirements.txt` | Last updated 2025-12-17. Lists nine services, most of which are archived (speech2text, text2sql, document-intelligence, lora-training, image-upscale, hub-gateway). Port table is wrong (SD shown as 7860). Mixes core and image stacks in one file. Do not `pip install -r requirements.txt`. |
| `app/requirements/PROFILE_SERVICE_MAP.md` | Service-to-profile map; **partially stale** — still lists archived services (speech2text, text2sql, document-intelligence, hub-gateway). Accurate for venv split (core vs image) but service list needs update in P1.3. |

---

## 5. Optional and Heavy Dependencies

These are installed by the core profile but can be omitted for a minimal chatbot-only setup:

| Package / Chunk | Why optional | How to exclude |
|---|---|---|
| Audio block in `profile_core_services.txt` (pyannote, faster-whisper, librosa, speechbrain) | The `speech2text` service is archived. Audio transcription (`src/audio_transcription.py`) uses the Whisper API, not the local stack. | Remove the audio block from `profile_core_services.txt` if local STT is not needed. |
| Document block in `profile_core_services.txt` (paddlepaddle, paddleocr, PyMuPDF) | PaddlePaddle is a heavy GPU-optional framework. PyMuPDF is used by `src/ocr_integration.py` and is lighter. `markitdown` is used by document processing. | Remove paddlepaddle/paddleocr from `profile_core_services.txt` if only text PDF reading is needed. PyMuPDF and markitdown should stay. |
| `ultralytics>=8.0.0` (in profile_core_services.txt) | YOLO-based detection/inpaint pass. Only active when `IMAGE_PIPELINE_V2=true`. Pulls in torch transitively. | Comment out in `profile_core_services.txt` if the detection pass is not used. |
| RAG stack (chromadb, pgvector, psycopg2-binary) | In `services/chatbot/requirements.txt` only, not in the profile. Only needed when the RAG subsystem is active. | Only install `services/chatbot/requirements.txt` if RAG is in use. |

---

## 6. Known Version Skews — P1.2 Upgrade Risks

The following discrepancies exist between what is declared in the install manifests and what is actually installed in `venv-core`. They are **deliberately not upgraded in P1.1** to avoid destabilizing the running environment before the app-factory refactor (P1.2). They must be resolved in P1.2.

| Package | Installed (venv-core) | Declared minimum | Risk |
|---|---|---|---|
| `pymongo` | 3.12.0 | `>=4.6.0` | PyMongo 4.x has breaking API changes (e.g., `count()` removed, `Collection.find()` behavior). Code that works on 3.12 may fail silently or loudly on upgrade. Audit all `pymongo` call sites before upgrading. |
| `dnspython` | 1.16.0 | `>=2.4.0` | PyMongo 4.x requires dnspython 2.x for SRV URI support (`mongodb+srv://`). Until pymongo is upgraded, this mismatch is non-critical for direct connections. |
| `mcp` | 1.26.0 | `>=1.27.1` (mcp-server req) | Minor version gap. The MCP server declares `>=1.27.1` but 1.26.0 is installed. Tool registration and stdio transport are stable across this range; upgrade on next venv rebuild. |

---

## 7. What Not to Edit Casually

- **`app/requirements/freeze-venv-core.txt` and `app/requirements/freeze-venv-image.txt`** — these are freeze snapshots. Do not edit by hand. Regenerate after a deliberate venv rebuild.
- **`app/requirements/legacy-root-requirements.txt`** — legacy stub. Do not add new packages here; they will be ignored by the profile system.
- **Web block in `app/requirements/profile_core_services.txt`** — contains `fastapi` and `uvicorn`. FastAPI is no longer a runtime path (removed May 2026) but is kept as a transitive dependency of the MCP client. Do not remove it from the profile unless the MCP dependency chain is verified to no longer need it.

---

## 8. Adding a New Dependency

1. Decide which venv it belongs to (core vs image — never mix).
2. Add it to the appropriate **profile file** (`profile_core_services.txt` or `profile_image_ai_services.txt`) with a lower-bound `>=` pin.
3. Re-run `pip install -r app/requirements/profile_core_services.txt` (or image profile) in the target venv.
4. After verifying it works, regenerate the freeze snapshot: `pip list --format=freeze > app/requirements/freeze-venv-core.txt`.
5. Run `app/scripts/verify-local.ps1` to confirm the gate is green.
6. If the dependency is test-only, add it to `services/chatbot/tests/requirements-test.txt` instead.
7. If the dependency is optional/heavy, add a note to the "Optional" section of this document.
