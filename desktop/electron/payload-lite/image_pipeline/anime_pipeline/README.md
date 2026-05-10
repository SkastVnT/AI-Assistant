# Anime Pipeline — Developer Documentation

## Canonical entry point

- HTTP (Flask blueprint): **`routes/anime_pipeline.py`** → `/api/anime-pipeline/{health,stream,generate,upload-refs}`
- Service bridge: **`services/chatbot/core/anime_pipeline_service.py`** (feature-flag gate, ComfyUI reachability, validation, SSE translation)
- Orchestrator: **`image_pipeline/anime_pipeline/orchestrator.py`** (single source of truth for stage order)
- Legacy compat route: `routes/image_gen.py` → `/api/image-gen/anime-pipeline` (deprecated, emits a warning; use the canonical endpoints for new work)

Feature flag: `IMAGE_PIPELINE_V2=true`.

## Architecture Overview

The anime pipeline is a **multi-pass image generation system** that produces high-quality anime artwork through ComfyUI. It follows an agent-based architecture where each stage is a standalone agent that reads from and writes to a shared `AnimePipelineJob` dataclass.

```
┌────────────────────────────────────────────────────────────────┐
│                    AnimePipelineOrchestrator                    │
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ 1. Vision │→│ 2. Layer │→│ 3. Compose   │→│ 4. Struct  │  │
│  │  Analyst  │  │  Planner │  │  (ComfyUI)  │  │   Lock    │  │
│  └──────────┘  └──────────┘  └─────────────┘  └───────────┘  │
│                                                    ↓           │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ 7. Up-   │←│ critique  │←│ 5. Beauty    │←│           │  │
│  │  scale   │  │  loop    │  │  Pass       │  │           │  │
│  └──────────┘  └──────────┘  └─────────────┘  └───────────┘  │
│                  ↺ retry                                       │
└────────────────────────────────────────────────────────────────┘
```

### Stage Descriptions

| # | Stage | Agent | External Call | Purpose |
|---|-------|-------|--------------|---------|
| 1 | Vision Analysis | `VisionAnalystAgent` | Gemini / GPT-4o vision | Analyze input image and references for subjects, pose, style |
| 2 | Layer Planning | `LayerPlannerAgent` | None (deterministic) | Build `LayerPlan` with pass configs, resolution, prompts |
| 3 | Composition Pass | `CompositionPassAgent` | ComfyUI `POST /prompt` | Generate initial draft (txt2img or img2img) |
| 4 | Structure Lock | `StructureLockAgent` | ComfyUI preprocessors | Extract lineart/depth/canny control layers |
| 5 | Beauty Pass | `BeautyPassAgent` | ComfyUI img2img+ControlNet | Detail-focused redraw with structure control |
| 6 | Critique | `CritiqueAgent` | Gemini / GPT-4o vision | Score result per dimension, suggest fixes |
| 7 | Upscale | `UpscaleAgent` | ComfyUI RealESRGAN | Final 2x upscale |

Stages 5-6 form a **critique loop**: if the critique score is below threshold, the beauty pass re-runs with patched parameters (up to `max_refine_rounds` times).

---

## File Map

```
image_pipeline/anime_pipeline/
├── __init__.py
├── orchestrator.py          # Main controller, runs stages sequentially
├── schemas.py               # All dataclasses (Job, Plan, Critique, etc.)
├── config.py                # AnimePipelineConfig, VRAM profiles, beauty presets
├── workflow_builder.py      # Builds ComfyUI JSON per pass
├── comfy_client.py          # HTTP client for ComfyUI API
├── vision_service.py        # Multi-provider vision API wrapper
├── vision_prompts.py        # System prompts for vision analysis
├── planner_presets.py       # Named presets (anime_quality, anime_speed, etc.)
├── result_store.py          # Save intermediates to disk
├── vram_manager.py          # VRAM cleanup + memory estimation
├── workflow_serializer.py   # Debug workflow JSON saving
├── agents/
│   ├── vision_analyst.py    # Stage 1: VisionAnalystAgent
│   ├── layer_planner.py     # Stage 2: LayerPlannerAgent (no external calls)
│   ├── composition_pass.py  # Stage 3: CompositionPassAgent
│   ├── structure_lock.py    # Stage 4: StructureLockAgent
│   ├── beauty_pass.py       # Stage 5: BeautyPassAgent
│   ├── critique.py          # Stage 6: CritiqueAgent
│   ├── detection_inpaint.py # Per-region ADetailer-style inpaint
│   ├── detection_detail.py  # YOLO detection (used by detection_inpaint)
│   ├── upscale.py           # Stage 7: UpscaleAgent (live)
│   ├── final_ranker.py      # Rank candidate images (live)
│   ├── output_manifest.py   # Build output manifest JSON (live)
│   │
│   ├── cleanup_pass.py      # NOT WIRED — optional stage 3.5 utility
│   ├── refine_loop.py       # NOT WIRED — helpers reused by orchestrator
│   └── upscale_service.py   # NOT WIRED — Ultimate SD Upscale alternative
```

### Wired vs utility agents

The live orchestrator imports only the agents listed as stages above. The three agents marked **NOT WIRED** are kept importable and tested, but are not called on the production path. See `image_pipeline/DEPRECATED.md` for the rule.

---

## Configuration

### Config File

`configs/anime_pipeline.yaml` (see `configs/anime_pipeline_example.yaml` for a complete template).

### Config Dataclass

`AnimePipelineConfig` in `config.py` with these key sections:

| Section | Key Settings |
|---------|-------------|
| **VRAM** | `vram_profile` (auto/normalvram/lowvram), max resolution, step cap |
| **Models** | `composition_model`, `beauty_model`, `final_model` — each has checkpoint, sampler, scheduler, steps, cfg |
| **Resolution** | `portrait_res`, `landscape_res`, `square_res` — auto-detected from prompt |
| **Structure** | `structure_layers` — list of ControlNet layer configs |
| **Vision** | `vision_model_priority` — fallback chain for critique/analysis |
| **Critique** | `quality_threshold`, `max_refine_rounds` |
| **Refine** | Denoise step up/down, control boost/reduce, artifact limits |
| **Pipeline** | `save_intermediates`, `stream_events`, `comfyui_url` |

### Environment Variable Overrides

All settings can be overridden via `ANIME_PIPELINE_*` env vars:

```
ANIME_PIPELINE_VRAM_PROFILE=lowvram
ANIME_PIPELINE_COMPOSITION_MODEL=animagine-xl-4.0-opt.safetensors
ANIME_PIPELINE_BEAUTY_MODEL=noobai-xl-1.1.safetensors
ANIME_PIPELINE_QUALITY_THRESHOLD=0.70
ANIME_PIPELINE_MAX_REFINE_ROUNDS=3
ANIME_PIPELINE_COMFYUI_URL=http://192.168.1.100:8188
ANIME_PIPELINE_DEBUG=true
```

---

## Model Slots

The pipeline uses 3 model slots:

| Slot | Purpose | Typical Checkpoint | Used In |
|------|---------|-------------------|---------|
| `composition` | Initial draft generation | animagine-xl-4.0-opt | Composition pass |
| `beauty` | Detail and refinement | noobai-xl-1.1 / flatpiececorexl | Beauty pass, cleanup |
| `final` | Final detail pass | Same as beauty (usually) | Last beauty round |

**Upscale model**: `RealESRGAN_x4plus_anime_6B` (configured separately, not a checkpoint).

---

## Required Custom Nodes (ComfyUI)

The following custom nodes must be installed in your ComfyUI instance:

| Node | Package | Purpose |
|------|---------|---------|
| `LoadImageFromBase64` | ComfyUI-API-base64 | Load base64 images into workflow |
| `AnimeLineArtPreprocessor` | comfyui_controlnet_aux | Lineart extraction |
| `DepthAnythingV2Preprocessor` | comfyui_controlnet_aux | Depth map extraction |
| `CannyEdgePreprocessor` | comfyui_controlnet_aux | Canny edge extraction |
| `ControlNetApplyAdvanced` | Built-in (ComfyUI ≥ 0.1.0) | ControlNet conditioning |
| `CLIPSetLastLayer` | Built-in | Clip skip for anime checkpoints |
| `UltimateSDUpscale` | ComfyUI-UltimateSDUpscale | Tiled img2img upscale (optional) |
| `ImageScale` | Built-in | Resize after model upscale |
| `UpscaleModelLoader` | Built-in | Load RealESRGAN models |
| `ImageUpscaleWithModel` | Built-in | Model-based upscaling |

### ControlNet Models

| Layer Type | ControlNet Model | Strength (default) |
|-----------|-----------------|-------------------|
| `lineart_anime` | `control_v11p_sd15_lineart_anime` | 0.80 |
| `depth` | `control_v11f1p_sd15_depth` | 0.45 |
| `canny` | `control_v11p_sd15_canny` | 0.60 |

---

## Vision Model Setup

The critique and vision analysis agents use multimodal vision models. Priority chain:

1. **Gemini 2.0 Flash** (primary) — requires `GOOGLE_API_KEY` or `GEMINI_API_KEY`
2. **GPT-4o-mini** (fallback) — requires `OPENAI_API_KEY`
3. **GPT-4o** (last resort) — requires `OPENAI_API_KEY`

If all vision models fail, critique returns neutral scores (5/10 per dimension) and the pipeline continues.

---

## VRAM Profiles

| Profile | Target GPU | Max Res | Step Cap | ControlNet Layers | CPU VAE |
|---------|-----------|---------|----------|------------------|---------|
| `normalvram` | 12+ GB | 1216 | 35 | 2 | No |
| `lowvram` | 8 GB | 1024 | 25 | 1 | Yes |

The `auto` profile reads from `ANIME_PIPELINE_VRAM_PROFILE` env var, defaulting to `normalvram`.

Between passes, the orchestrator calls `POST /free` on ComfyUI to unload models and free VRAM (configurable via `unload_between_passes`).

---

## Debug Outputs

When `ANIME_PIPELINE_DEBUG=true` or `debug_mode=True` in config:

1. **Workflow JSON** saved per pass: `storage/debug/{job_id}_{pass_name}.json`
2. **Intermediate images** saved: `storage/intermediate/{job_id}/01_composition.png`, etc.
3. **Output manifest** includes runner-up candidates and per-stage timing
4. **ComfyClient** logs every request/response with job_id correlation

Stage filename convention:
```
01_composition.png
02_lineart.png / 02_depth.png / 02_canny.png
03_cleanup.png
04_beauty.png / 04_beauty_refined.png
05_upscaled.png
```

---

## Failure Recovery

| Failure | Behavior |
|---------|----------|
| ComfyUI unreachable | Retries 3x with exponential backoff + jitter |
| Workflow validation error | Returns immediately with error details |
| Vision model failure | Falls back through priority chain; neutral scores if all fail |
| Critique below threshold | Re-runs beauty pass with adjusted params (up to N rounds) |
| GPU OOM | If `oom_retry_enabled`, reduces resolution by `oom_resolution_step_down` and retries |
| Agent exception | Orchestrator catches, marks job FAILED, uses best intermediate as fallback |
| All critique rounds fail | Uses best-scoring intermediate if `return_best_on_fail=True` |

---

## SSE Event Wire Format

The orchestrator's `run_stream()` yields events for frontend consumption:

```
event: anime_pipeline_pipeline_start
data: {"job_id": "abc123", "stages": [...]}

event: anime_pipeline_stage_start
data: {"stage": "composition_pass", "stage_num": 3, "total_stages": 7}

event: anime_pipeline_stage_complete
data: {"stage": "composition_pass", "latency_ms": 2100}

event: anime_pipeline_refine_start
data: {"round": 1, "max_rounds": 2, "previous_score": 0.45}

event: anime_pipeline_pipeline_complete
data: {"job_id": "abc123", "status": "completed", "has_image": true, "total_latency_ms": 12500}

event: anime_pipeline_pipeline_error
data: {"job_id": "abc123", "error": "GPU OOM", "has_fallback_image": true}
```

All events are prefixed with `anime_pipeline_`.

---

## API Endpoints

### Flask Blueprint (`/api/anime-pipeline/`)

| Method | Path | Description |
|--------|------|------------|
| GET | `/api/anime-pipeline/health` | Check ComfyUI reachability + feature flag |
| POST | `/api/anime-pipeline/stream` | SSE streaming generation |
| POST | `/api/anime-pipeline/generate` | Blocking generation (returns final JSON) |

### Rate Limiting

5 jobs per 120-second window per client.

### Request Payload

```json
{
  "prompt": "1girl, silver hair, blue eyes, standing in cherry blossoms",
  "quality": "high",
  "preset": "anime_quality",
  "source_image": "<base64 or null>",
  "reference_images": ["<base64>"],
  "orientation": "portrait",
  "debug": false
}
```

---

## Running Tests

```bash
cd services/chatbot
..\..\venv-core\Scripts\python.exe -m pytest tests/test_planner_agent.py -v
..\..\venv-core\Scripts\python.exe -m pytest tests/test_critique_refine_ranker.py -v
..\..\venv-core\Scripts\python.exe -m pytest tests/test_workflow_builder.py -v
..\..\venv-core\Scripts\python.exe -m pytest tests/test_comfyui_integration.py -v
..\..\venv-core\Scripts\python.exe -m pytest tests/test_e2e_dry_run.py -v
```

Or run all anime pipeline tests:

```bash
..\..\venv-core\Scripts\python.exe -m pytest tests/test_planner_agent.py tests/test_critique_refine_ranker.py tests/test_workflow_builder.py tests/test_comfyui_integration.py tests/test_e2e_dry_run.py tests/test_anime_pipeline.py tests/test_anime_pipeline_integration.py -v
```

---

## Extending the Pipeline

### Adding a New Stage

1. Create agent in `agents/new_stage.py` with `execute(job: AnimePipelineJob) -> AnimePipelineJob`
2. Add the agent to `AnimePipelineOrchestrator.__init__` and the stage sequence in `run_stream()`
3. Update `_STAGE_FILENAMES` in `output_manifest.py`
4. Add workflow builder method if ComfyUI interaction is needed
5. Write tests

### Adding a New ControlNet Layer

1. Add `StructureLayerConfig` entry in your YAML config
2. The `StructureLockAgent` auto-discovers layers from config
3. Add preprocessor params in `WorkflowBuilder.build_structure_lock_layer()` if needed
4. Add the ControlNet model file to ComfyUI's `models/controlnet/` directory

### Adding a New Vision Model

1. Add model name to `vision_model_priority` in config
2. Implement `_critique_{provider}()` in `agents/critique.py`
3. Add the same in `vision_service.py` for vision analysis
