# Dependency Chunks

This folder only groups the split requirement files to keep the repo root tidy. Use them exactly as before; paths just moved here.

## Files
- requirements_chunk_1_core.txt
- requirements_chunk_2_web.txt
- requirements_chunk_3_database.txt
- requirements_chunk_4_ai_apis.txt
- requirements_chunk_5_ml_core.txt
- requirements_chunk_6_image.txt
- requirements_chunk_7_audio.txt
- requirements_chunk_8_document.txt
- requirements_chunk_9_upscale.txt
- requirements_chunk_10_tools.txt
- profile_core_services.txt
- profile_image_ai_services.txt

## Usage
Install the chunks individually or concatenate as needed, for example:

```bash
# install a specific chunk
pip install -r requirements/requirements_chunk_1_core.txt

# install everything (concatenate)
cat requirements/requirements_chunk_*.txt > /tmp/ai-assistant-all.txt
pip install -r /tmp/ai-assistant-all.txt
```

## Recommended environment profiles

Use isolated venv profiles to avoid cross-service dependency conflicts.

### core-services profile
Target services: hub-gateway, chatbot, speech2text, text2sql, document-intelligence, mcp-server.

```bash
# Windows PowerShell
pyenv install 3.11.9
pyenv shell 3.11.9
pyenv exec python -m venv venv-core
./venv-core/Scripts/python -m pip install -U pip setuptools wheel
./venv-core/Scripts/python -m pip install -r requirements/profile_core_services.txt
```

### image-ai-services profile
Target services: stable-diffusion, edit-image, image-upscale, lora-training, ComfyUI workflows.

```bash
# Windows PowerShell
pyenv install 3.11.9
pyenv shell 3.11.9
pyenv exec python -m venv venv-image
./venv-image/Scripts/python -m pip install -U pip setuptools wheel
./venv-image/Scripts/python -m pip install -r requirements/profile_image_ai_services.txt
```

Note: `profile_image_ai_services.txt` may still need CUDA-specific PyTorch index URLs depending on your GPU stack.

---

## Local anime image pipeline — dependency matrix

The chatbot imports `image_pipeline/anime_pipeline/` from the **core profile**
(`venv-core`). Only the minimum runtime pieces live in core; the heavy
diffusion / upscale stack stays in the image profile.

### Required (core profile)

These are imported at module/orchestrator load and must be present for the
local anime pipeline code paths to run at all.

| Package | Where declared | Why it belongs in core |
|---|---|---|
| `httpx` | `requirements_chunk_4_ai_apis.txt` | ComfyUI HTTP client, vision + CivitAI calls |
| `pyyaml` | `requirements_chunk_1_core.txt` | Loads `configs/anime_pipeline.yaml`, `configs/lora_registry.yaml` |
| `numpy` | `requirements_chunk_1_core.txt` | Detection mask math in `agents/detection_detail.py` |
| `requests` | `requirements_chunk_1_core.txt` | Reference image downloads |
| `Pillow` | `profile_core_services.txt` (direct) | Reference image encode/decode in orchestrator + detection agents |

### Optional — feature-flagged (core profile)

Installed in core so the feature can be toggled on via env flags without a
venv rebuild, but the pipeline gracefully skips the pass when missing.

| Package | Feature flag / gate | Notes |
|---|---|---|
| `ultralytics` | `IMAGE_PIPELINE_V2=true` + detection flag in `anime_pipeline.yaml` | Pulls torch + torchvision + opencv-python transitively. YOLO-based ADetailer-style inpaint for face/eye/hand/hair regions. Safe to comment out if the detection pass is not used. |

### GPU-sensitive (not pinned in profiles)

Install these manually according to the local CUDA/PyTorch stack. They are
**not** added to either profile because the correct wheel URL depends on the
host GPU driver.

| Package | When needed |
|---|---|
| `torch`, `torchvision` | Pulled in transitively by `ultralytics` and by the image profile. For CUDA wheels use the matching `--index-url https://download.pytorch.org/whl/cuXYZ`. |
| `xformers` | Optional acceleration for diffusion in the image profile only. |

### Debug-only (install on demand, do NOT add to profiles)

```bash
pip install matplotlib   # plot detection masks / critique overlays
pip install ipython      # interactive pipeline inspection / REPL
```

### Intentionally image-profile-only (do NOT add to core)

Keeping these out of core prevents numpy / protobuf / torch conflicts and
keeps the chatbot venv small.

| Package | Reason |
|---|---|
| `diffusers`, `open-clip-torch`, `timm`, `kornia`, `lpips`, `einops`, `torchdiffeq`, `torchsde`, `pytorch_lightning` | Declared in `requirements_chunk_6_image.txt` — only needed when running the full SDXL / ComfyUI stack locally. |
| `basicsr`, `gfpgan`, `realesrgan`, `facexlib`, `codeformer` | Upscale / restoration stack — `requirements_chunk_9_upscale.txt`. |
| `clean-fid`, `tomesd`, `blendmodes`, `resize-right`, `piexif`, `lark`, `inflection` | SD-specific — `requirements_chunk_6_image.txt`. |

### Quick gap check

If a fresh `venv-core` install fails with `ModuleNotFoundError` from the
anime pipeline, check in this order:

1. `from PIL import Image` — install/upgrade `Pillow`.
2. `from ultralytics import YOLO` — either install `ultralytics` or disable
   the detection feature flag.
3. `import httpx` / `import yaml` / `import numpy` — core chunks are missing;
   reinstall `-r profile_core_services.txt`.

