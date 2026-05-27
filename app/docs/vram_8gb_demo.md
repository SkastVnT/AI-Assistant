# 8 GB VRAM â€” Laptop Demo Setup

**Purpose:** Run the same 7-stage anime pipeline flow on an 8 GB VRAM laptop for workflow prototyping. Not a production-quality run â€” quality trade-offs are intentional.

**Constraint:** `app/configs_vps/anime_pipeline.yaml` and `app/configs_vps/models.yaml` are the official 12 GB PC configs and must not be modified.

---

## How it works

`app/image_pipeline/anime_pipeline/config.py` now reads `ANIME_PIPELINE_CONFIG` env var. If set, it loads that YAML instead of `app/configs_vps/anime_pipeline.yaml`. All other env overrides (`ANIME_PIPELINE_VRAM_PROFILE`, `ANIME_PIPELINE_COMPOSITION_MODEL`, etc.) still apply on top.

---

## Quick start

```bash
# Windows â€” PowerShell
$env:ANIME_PIPELINE_CONFIG = "app/configs_vps/anime_pipeline_laptop.yaml"
$env:REASONING_PIPELINE = "true"
python services/chatbot/run.py
```

```bash
# Windows â€” cmd
set ANIME_PIPELINE_CONFIG=app/configs_vps/anime_pipeline_laptop.yaml
set REASONING_PIPELINE=true
python services/chatbot/run.py
```

```bash
# Linux / macOS
ANIME_PIPELINE_CONFIG=app/configs_vps/anime_pipeline_laptop.yaml \
REASONING_PIPELINE=true \
python services/chatbot/run.py
```

---

## ComfyUI startup flags for 8 GB

Start ComfyUI with these flags before launching the chatbot:

```bash
python main.py --lowvram --cpu-vae --use-split-cross-attention
```

| Flag | Effect |
|---|---|
| `--lowvram` | Offloads model to CPU between inference steps |
| `--cpu-vae` | Runs VAE decode on CPU (saves ~1.5 GB GPU) |
| `--use-split-cross-attention` | Reduces peak attention VRAM |

The laptop config already sets `cpu_vae_offload: true` (via `lowvram` profile) and `unload_between_passes: true` â€” these are the ComfyUI API equivalents of the above flags at the workflow level.

---

## Checkpoint options

Edit `app/configs_vps/anime_pipeline_laptop.yaml` and change the three `checkpoint:` lines (composition, beauty, final) to one of:

### Option A â€” SDXL fp8 (recommended, ~4 GB)

```yaml
checkpoint: "waiIllustriousSDXL_v160_fp8.safetensors"
type: sdxl
```

Same WAI Illustrious series as production. fp8 quantization halves VRAM without major quality loss at 20 steps. Download: civitai.com search "WAI Illustrious fp8".

### Option B â€” SD 1.5 anime (~2 GB, maximum headroom)

```yaml
checkpoint: "anything-v5-PrtRE.safetensors"
type: sd15      # â† must change this line too
```

Compatible models: `anything-v5`, `counterfeitV30`, `dreamshaper_8`, `majicmixRealistic`. The ComfyUI KSampler graph is identical â€” only the checkpoint file changes. SD 1.5 native resolution is 512â€“768px; the laptop config sets portrait to 768Ã—1024 which is safe.

Also update resolutions for SD 1.5 in the YAML:
```yaml
resolutions:
  portrait:
    width: 640
    height: 896
  landscape:
    width: 896
    height: 640
  square:
    width: 768
    height: 768
```

### Option C â€” SDXL base 1.0 fp8 (~4 GB, generic fallback)

```yaml
checkpoint: "sd_xl_base_1.0_fp8.safetensors"
type: sdxl
```

Use when no WAI fp8 download is available. Lacks anime tuning â€” output quality is noticeably lower but the pipeline logic is fully exercised.

---

## What changes vs production

| Parameter | Production (12 GB) | Laptop demo (8 GB) |
|---|---|---|
| VRAM profile | normalvram | lowvram |
| Max resolution | 832Ã—1216 | 768Ã—1024 |
| Step cap | 35 | 25 |
| Composition steps | 28 | 20 |
| Beauty steps | 30 | 15 |
| CPU VAE offload | false | true |
| ControlNet layers | 2 (SD1.5 compat note) | 0 (disabled) |
| Max refine rounds | 8 | 2 |
| Quality threshold | 0.80 | 0.60 |
| Eye-refine pass | enabled | disabled |
| LoRAs | 2 default LoRAs | none |
| Upscale factor | 2Ã— | 2Ã— (same) |

---

## Pipeline stages exercised

All 7 stages run identically â€” the checkpoint name is just a string:

```
1. capability_router.classify()    â†’ determines if image-gen is needed
2. prompt_revision.revise()        â†’ rewrites prompt for anime style
3. prompt_parser.parse()           â†’ decomposes into panel/character tokens
4. execution_plan.plan_panel()     â†’ selects model from step.model string
5. comfy_workflow_builder.build()  â†’ generates ComfyUI JSON graph
6. runner.run_panel()              â†’ submits to local ComfyUI
7. critique loop                   â†’ vision LLM scores output (API call)
```

The pipeline is model-agnostic. `workflow_builder.py` only reads `pc.checkpoint` â€” it does not branch on `model_type`. Swapping to any checkpoint exercises the full flow.

---

## Per-run env var overrides (no YAML edit needed)

These can be layered on top of `anime_pipeline_laptop.yaml`:

```bash
# Reduce to 1 round for single-pass smoke test
ANIME_PIPELINE_MAX_REFINE_ROUNDS=1

# Further lower quality bar
ANIME_PIPELINE_QUALITY_THRESHOLD=0.50

# Override checkpoint without editing YAML
ANIME_PIPELINE_COMPOSITION_MODEL=anything-v5-PrtRE.safetensors
ANIME_PIPELINE_BEAUTY_MODEL=anything-v5-PrtRE.safetensors
ANIME_PIPELINE_FINAL_MODEL=anything-v5-PrtRE.safetensors

# Disable detection inpaint stage
ANIME_PIPELINE_DETECTION_INPAINT=0
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `CUDA out of memory` on composition | Reduce portrait to 640Ã—896, or add `--lowvram` flag to ComfyUI |
| `CUDA out of memory` on beauty | Set `ANIME_PIPELINE_MAX_REFINE_ROUNDS=1` and reduce `denoise_strength: 0.25` |
| VAE decode OOM | Restart ComfyUI with `--cpu-vae` flag |
| ControlNet node error | Confirm `structure_lock.layers: []` in laptop YAML (default is empty) |
| Model not found | Check the checkpoint filename matches exactly what's in ComfyUI's `models/checkpoints/` |
| Slow first run | fp8 checkpoints have a longer first-load time â€” expected |
