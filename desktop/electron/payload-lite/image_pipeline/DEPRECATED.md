# image_pipeline — Subtree Status

This document clarifies which subpackages inside `image_pipeline/` are live on the production code path, and which are **deferred / not integrated**.

## Canonical live subtree

Only **`image_pipeline.anime_pipeline`** is wired into running code. It is reachable through:

- `services/chatbot/routes/anime_pipeline.py` → `/api/anime-pipeline/*`
  (canonical HTTP surface, bridged by `services/chatbot/core/anime_pipeline_service.py`)
- `services/chatbot/routes/image_gen.py` → `/api/image-gen/anime-pipeline`
  (legacy compatibility endpoint — emits `X-Deprecated-Endpoint` header;
  new callers should use `/api/anime-pipeline/*`)

The orchestrator (`image_pipeline/anime_pipeline/orchestrator.py`) is the single entry point and defines the active stage list. Anything not imported by that file is not part of the live pipeline.

## Deferred / not integrated subtree ("Nano Banana" blueprint)

These modules exist from an earlier design sketch and are **not imported by any running route or orchestrator**:

- `image_pipeline/job_schema.py`
- `image_pipeline/workflow/`
- `image_pipeline/planner/`
- `image_pipeline/evaluator/`
- `image_pipeline/semantic_editor/`
- `image_pipeline/multi_reference/`
- `image_pipeline/BLUEPRINT.md`

They are preserved as-is (with their own tests where present) for possible future restart, but must not be treated as authoritative. Do not wire them into routes without a design review.

## Deferred utility agents inside `anime_pipeline/agents/`

These agents are importable and tested, but **not called by the live orchestrator**:

| Module | Class | Why kept |
|---|---|---|
| `cleanup_pass.py` | `CleanupPassAgent` | Optional stage between structure lock and beauty pass; currently skipped |
| `upscale_service.py` | `UpscaleService` | Enhanced alternative to `UpscaleAgent` (Ultimate SD Upscale); orchestrator uses `UpscaleAgent` |
| `refine_loop.py` | `RefineLoopAgent` + helpers | Orchestrator inlines the critique→refine loop; helpers remain for tests and opt-in use |

Each file carries a "NOT WIRED" banner in its module docstring.

## Rule for new work

When extending the live pipeline, add imports in `anime_pipeline/orchestrator.py` and update this document and `image_pipeline/anime_pipeline/README.md`. Do not introduce a second orchestrator.
