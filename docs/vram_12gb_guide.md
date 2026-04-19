# Running the Layered Anime Pipeline on 12 GB VRAM

This guide covers practical limits, default settings, and tuning knobs
for running the multi-pass anime pipeline on a 12 GB VRAM GPU
(e.g. RTX 3060 12 GB, RTX 4070).

---

## VRAM Profiles

The pipeline supports three VRAM profiles, set via YAML or env var:

| Profile      | Max Res | Steps | ControlNet | CPU VAE | Upscale | Previews |
|-------------|---------|-------|------------|---------|---------|----------|
| `normalvram` | 1216    | 35    | 2 layers   | No      | 2×      | On       |
| `lowvram`    | 1024    | 25    | 1 layer    | Yes     | 1.5×    | Off      |
| `auto`       | Reads `ANIME_PIPELINE_VRAM_PROFILE` env var, defaults to `normalvram` |

### Setting the profile

**YAML** (`configs/anime_pipeline.yaml`):
```yaml
vram:
  profile: normalvram    # auto | normalvram | lowvram
```

**Environment variable** (overrides YAML):
```bash
export ANIME_PIPELINE_VRAM_PROFILE=lowvram
```

---

## Default Resolutions (SDXL-safe)

These are the **generation** resolutions — upscaling happens after
all passes are complete.

| Orientation | normalvram     | lowvram        |
|------------|----------------|----------------|
| Portrait   | 832 × 1216     | 832 × 1024     |
| Landscape  | 1216 × 832     | 1024 × 832     |
| Square     | 1024 × 1024    | 1024 × 1024    |

**Rule:** never start generation above 1216 on any dimension for
12 GB.  Upscale only after the composition is structurally stable.

---

## Sequential Model Loading

All SDXL checkpoints are ~6.5 GB in fp16.  Two models loaded
simultaneously would exceed 12 GB.

The pipeline uses **sequential loading** by default:
- `unload_between_passes: true` in YAML
- Before each stage, the orchestrator calls `POST /free` to ComfyUI
  to unload the previous model and free VRAM
- Each pass loads its own checkpoint (composition → beauty → final)
- The upscale model (~100 MB) loads after the main checkpoint is freed

**Cost:** ~2–4 s extra per model swap.  Worth it for OOM prevention.

---

## CPU VAE Fallback

SDXL VAE decode uses ~1.5 GB at 1024×1024.  On `lowvram` profile,
the pipeline enables `cpu_vae_offload: true`.

When enabled, ComfyUI decodes the VAE on CPU instead of GPU.
This is slower (~3–5 s per decode) but prevents the VAE decode
from competing with the UNet for VRAM.

**When to enable:**
- Your GPU has exactly 8 GB
- You see OOM errors during the final decode step
- You're running with ControlNet layers that consume extra VRAM

**Not needed on 12 GB** with normal resolutions.  The `normalvram`
profile leaves it off.

---

## Preview Suppression

ComfyUI `PreviewImage` nodes decode the latent to pixels and hold
the result in VRAM for the preview system.  In pipeline/worker mode,
nobody sees these previews.

- `normalvram`: previews left on (useful during development)
- `lowvram`: previews stripped from workflows automatically
- Set `disable_previews: true` in the VRAM profile for any profile

The `strip_preview_nodes()` function removes all `PreviewImage`
nodes from the workflow JSON before submission.

---

## OOM Retry Strategy

If a ComfyUI job fails with an OOM error, the pipeline retries
automatically:

```
Attempt 1: original resolution (e.g. 832×1216)
   ↓ OOM
Attempt 2: resolution - 128 → 704×1088
   ↓ OOM
Attempt 3: resolution - 128 → 576×960
   ↓ OOM (retries exhausted)
Escalate:  switch to lowvram profile, clamp to 1024 max
   ↓ final attempt at lowvram settings
```

### Retry parameters

| Parameter                 | normalvram | lowvram |
|--------------------------|------------|---------|
| `oom_retry_enabled`       | true       | true    |
| `oom_resolution_step_down`| 128 px     | 128 px  |
| `oom_max_retries`         | 2          | 3       |

### What gets logged

Every retry logs:
- **Estimated pass memory mode:** profile, resolution, megapixels
- **Retry cause:** which error triggered the retry
- **Final fallback:** the profile and resolution that succeeded (or failed)

Example log output:
```
[VRAMManager] pass=beauty_pass profile=normalvram res=832x1216 (1.01 MP) cpu_vae=False unload=True tile=512
[VRAMManager] pass=beauty_pass OOM retry cause: attempts=1/2 resolution=704x1088 escalated=False
[VRAMManager] pass=beauty_pass FINAL: profile=normalvram res=704x1088 attempts=1 escalated=False
```

---

## Practical 12 GB Limits

| Scenario | Feasible | Notes |
|----------|----------|-------|
| Single SDXL pass at 832×1216 | Yes | ~8 GB peak |
| + 1 ControlNet layer | Yes | ~9.5 GB peak |
| + 2 ControlNet layers | Tight | ~11 GB peak, may need unload |
| + 3 ControlNet layers | No | Use max 2, or switch to lowvram |
| Ultimate SD Upscale (tiled) at 2× | Yes | Tiles process sequentially |
| Simple upscale 4× model | Yes | Model is ~100 MB |
| Two SDXL models loaded | No | ~13 GB — always unload between |

---

## Recommended Configuration for 12 GB

```yaml
vram:
  profile: normalvram

pipeline:
  unload_between_passes: true

structure_lock:
  max_simultaneous: 2
  layers:
    - type: lineart_anime
      enabled: true
    - type: depth
      enabled: true
    - type: canny
      enabled: false          # disable 3rd layer to stay under budget

models:
  upscale:
    model: "RealESRGAN_x4plus_anime_6B"
    scale_factor: 2
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANIME_PIPELINE_VRAM_PROFILE` | `normalvram` | Override VRAM profile |
| `ANIME_PIPELINE_COMFYUI_URL` | `http://localhost:8188` | ComfyUI server |
| `ANIME_PIPELINE_DEBUG` | `false` | Save workflow JSON + images |
| `IMAGE_PIPELINE_V2` | `false` | Feature gate for the full pipeline |

---

## Troubleshooting

**OOM on first pass:**
Set `ANIME_PIPELINE_VRAM_PROFILE=lowvram`.  This caps resolution to
1024, reduces steps, and enables CPU VAE.

**OOM only on beauty pass:**
The beauty pass uses ControlNet which adds ~1.5 GB.  Try reducing
`structure_lock.max_simultaneous` to 1.

**OOM on upscale:**
The Ultimate SD Upscale path runs tiled img2img.  Reduce
`upscale_tile_size` from 512 to 384 or 256.  Or set
`upscale_factor` to 1.5 instead of 2.

**Slow but stable:**
If generation is stable but slow, you're likely on `lowvram` with
CPU VAE.  Switch to `normalvram` if you have 12 GB.
