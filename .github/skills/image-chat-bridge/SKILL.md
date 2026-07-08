---
name: image-chat-bridge
description: "Bridge the ComfyUI anime image pipeline into the chat SSE stream so image generation renders inline in the chat bubble. Use when: changing how image-generation events reach the chat UI, editing the force_image_bridge gate or the SSE forwarder in stream.py, touching cancel / GPU-leak handling (GeneratorExit → request_cancel → /free), the error_class taxonomy, the Phase 1b thinking-block nesting, or the Phase 3 WS live-preview; debugging why an image turn stalls, double-renders, leaks VRAM, or shows the wrong error; or running the PR4 verification harness. This subsystem deliberately spans services/chatbot/ AND app/image_pipeline/."
---

# Image Chat Bridge

## What this subsystem is

The **image-chat-bridge** lets an image-generation turn stream *inside* the normal chat bubble instead of a separate modal. When the frontend decides a message is an image request, it sets `force_image_bridge` in the `/chat/stream` payload. The backend then runs the ComfyUI anime pipeline in a worker thread and **forwards its `ap_*` SSE frames verbatim** into the chat stream. The browser's `AnimePipeline` module renders those frames inline.

This is the one subsystem that **crosses the normal scope boundary**: the bridge logic lives in `services/chatbot/` (in-scope for the core skills) but it drives `app/image_pipeline/anime_pipeline/` (normally off-limits per `CLAUDE.md`). That is why it needs its own skill — none of the 14 core-chatbot skills cover it, and `skills-dispatch-map` explicitly excludes image-pipeline work.

> **Scope rule still applies.** `CLAUDE.md` says do not touch `app/image_pipeline/` for chatbot tasks. Editing the `app/image_pipeline/` side of this bridge (`comfy_client.py`, `orchestrator.py`, agents, `schemas.py`) requires explicit authorization for the task. If the change can be made purely on the `services/chatbot/` side, prefer that.

## When to use this skill

- Changing the `force_image_bridge` gate or the `_image_chat_bridge()` SSE forwarder in `routes/stream.py`.
- Touching cancel / GPU-leak handling: `GeneratorExit` → `request_cancel` → `_interrupt_comfyui` → `/free`.
- Editing the `error_class` 3-class taxonomy (retryable / config_or_workflow / resource) anywhere along its path.
- Changing how the image card nests inside the collapsible "Đang tạo ảnh" thinking-block (Phase 1b).
- Working on the ComfyUI `/ws` live-preview + progress-% feature (Phase 3, flag-gated).
- Debugging: image turn stalls forever, renders twice, leaks VRAM after Stop, shows the wrong error class, or the card gets wiped when the thinking-block finalizes.
- Running or extending the PR4 verification harness.

## Do not use for

- Modal-based image gen (`image-gen-v2.js` → `/api/image-gen/generate`) — that path bypasses `/chat/stream` entirely (see chat-ui-sync).
- The anime pipeline's *internal* architecture (orchestrator stages, profiles, vram_manager) when the change never touches the chat bridge — that is pure `app/image_pipeline/` work.
- Pure text chat streaming — see core-chatbot-routing-audit.

---

## Data flow

```
Frontend decides "this is an image request"
  → main.js: sendMessage() sets force_image_bridge=true in the /chat/stream body
  → routes/stream.py: gate reads data.get("force_image_bridge")  [stream.py ~1066 / ~1248]
  → _image_chat_bridge() worker thread drains stream_pipeline()   [stream.py ~1024]
  → each ap_* frame is re-emitted VERBATIM onto the chat SSE
  ← api-service.js SSE parser → main.js onAnimeEvent(name, data)   [main.js ~1283]
  ← window.animePipeline.injectSSEEvent(uid, name, data)          [main.js ~1313]
  ← AnimePipeline._handleInlineEvent()                            [anime-pipeline.js ~968]
  ← inline bubble rendered inside the image thinking-block
```

**Golden rule:** the bridge forwards `ap_*` frames **unchanged**. If you add a field to an `ap_*` event, it must be produced by `anime_pipeline_service.stream_pipeline()`, survive the verbatim forward in `stream.py`, and be consumed by `_handleInlineEvent`. Do not transform frames inside the bridge.

---

## Key anchors

Line numbers are **approximate landmarks** — code evolves. Search by the symbol name, not the line.

### Bridge + gate (services/chatbot/routes/stream.py)
| What | Symbol | ~Line |
|------|--------|-------|
| SSE forwarder worker | `_image_chat_bridge()` | 1024 |
| Bridge gate (inside stream) | `data.get("force_image_bridge")` | 1066 |
| Bridge gate (route decision) | `_force_bridge = bool(data.get("force_image_bridge"))` | 1248 |
| Cancel on disconnect | `except GeneratorExit:` → `request_cancel` + `_interrupt_comfyui` | 1176–1184 |

### Pipeline → SSE (services/chatbot/core/anime_pipeline_service.py)
| What | Symbol | ~Line |
|------|--------|-------|
| SSE generator | `stream_pipeline()` | 662 |
| error_class → recoverable map | `_RECOVERABLE_BY_CLASS` | 95 |
| Derive the `recoverable` UI flag | `_derive_recoverable()` | 102 |
| `ap_error` emit sites | (search `"ap_error"`) | 707, 759, 1051, 1064, 1094 |
| Heartbeat carries live data | `progress_pct` / `preview_b64` | 1041–1044 |

### Cancel + VRAM /free (services/chatbot/routes/anime_pipeline.py)
| What | Symbol | ~Line |
|------|--------|-------|
| `/cancel` route | `cancel_pipeline()` | 890 |
| `/cancel-all` route | `cancel_all_pipelines()` | 948 |
| Skip /free if another job runs | `_other_active_jobs()` | 968 |
| Interrupt + /free (the ONE choke point) | `_interrupt_comfyui()` | 983 |
| Unload models | `free_models_between_passes(base)` | 1038–1041 |

All three cancel paths (`/cancel`, `/cancel-all`, and the bridge's `GeneratorExit`) funnel through **`_interrupt_comfyui()`** — fix cancel/VRAM behavior there once, not three times.

### error_class taxonomy (app/image_pipeline/anime_pipeline/comfy_client.py) — authorization-gated
| What | Symbol | ~Line |
|------|--------|-------|
| Resource-error substrings | `_RESOURCE_ERROR_PATTERNS` | 47 |
| OOM/CUDA detector | `is_resource_error()` | 56 |
| Classifier (resource / config_or_workflow) | `classify_comfy_error()` | 62 |
| Result field | `error_class: str \| None` | 177 |
| Set sites | retry-exhaustion→`retryable` (426), HTTP-reject→`config_or_workflow` (614), execution-error→`classify_comfy_error` (860) | — |

Taxonomy path end-to-end: `comfy_client` (set `error_class`) → `schemas.AnimePipelineJob.error_class` → agents copy `job.error_class = getattr(result, "error_class", None)` → `orchestrator` threads it into `stage_error`/`pipeline_error` → `anime_pipeline_service` maps it via `_derive_recoverable` into the `ap_error` frame → `anime-pipeline.js` shows a 3-class hint.

### Phase 1b — thinking-block nesting (frontend)
| What | File | Symbol | ~Line |
|------|------|--------|-------|
| Collapsible host, created lazily on first anime frame | main.js | `imageThinkingBlock` | 1131 |
| Create the block | message-renderer.js | `createThinkingSection(thinkingProcess, isLoading, label)` | 1241 |
| Mount card into the block | anime-pipeline.js | `beginInlineFromChat(uid, prompt, { parentEl })` | 525 |
| Finalize WITHOUT wiping the card | message-renderer.js | `finalizeThinkingKeepContent()` | 1402 |
| ⚠️ Standard finalize (rebuilds innerHTML) | message-renderer.js | `finalizeThinking()` | 1340 |

### Phase 3 — WS live preview (flag-gated, default OFF)
| What | File | Symbol | ~Line |
|------|------|--------|-------|
| Flag reader | comfy_client.py | `ws_preview_enabled()` | 71 |
| Pure binary-frame parser (unit-tested) | comfy_client.py | `parse_ws_preview_frame()` | 89 |
| Register progress/preview callbacks | comfy_client.py | `set_preview_callbacks()` | 226 |
| Daemon reader (no-op unless flag+callback) | comfy_client.py | `_maybe_start_ws_reader()` | 654 |
| Inline `<img>` refresh | anime-pipeline.js | `_inlineSetLivePreview()` / `_inlineClearLivePreview()` | 678 / 709 |
| Launch flag → ComfyUI arg | run.py | `--preview-method auto` when `ANIME_PIPELINE_WS_PREVIEW` | 257–258 |
| Dependency | requirements.txt | `websocket-client>=1.6` (import-guarded) | 11 |

Flag env var: **`ANIME_PIPELINE_WS_PREVIEW`** (default OFF). Polling stays the source of truth; the WS reader only *enriches* heartbeats with `progress_pct` + throttled `preview_b64`.

---

## Critical pitfalls

### Pitfall 1 — Transforming `ap_*` frames in the bridge
❌ Rewriting/renaming event fields inside `_image_chat_bridge()`.
✅ The bridge forwards verbatim. Produce the field in `stream_pipeline()`, consume it in `_handleInlineEvent`. If the browser doesn't see a field, check the producer and the JS consumer — not the bridge.

### Pitfall 2 — Fixing cancel/VRAM in only one path
❌ Adding a `/free` or interrupt to `cancel_pipeline()` alone.
✅ All three cancel entrypoints route through `_interrupt_comfyui()`. Edit it once. Verify `_other_active_jobs()` still gates `/free` so a second concurrent job isn't starved of its models.

### Pitfall 3 — Routing the image card through standard finalize
❌ Calling `finalizeThinking()` on the image thinking-block — it rebuilds `innerHTML` and **wipes the nested image card**.
✅ Use `finalizeThinkingKeepContent()`, which flips loading→done and keeps the block expanded without rebuilding. The image turn must never hit the standard finalize path.

### Pitfall 4 — The `?v=` cache-bust 3-place sync
Any edit to `main.js`, `anime-pipeline.js`, `message-renderer.js`, or `anime-pipeline.css` must bump the `?v=` token in **all** places that reference it, or Electron/browsers serve a stale module and `injectSSEEvent` looks "missing":
1. `templates/partials/chat/_scripts.html` — `main.js?v=...`
2. `templates/partials/chat/_head_assets.html` — `anime-pipeline.css?v=...`
3. `static/js/main.js` import lines — `message-renderer.js?v=...` and `anime-pipeline.js?v=...`

The current token is `20260703a`. The frontend already logs a warning (`main.js ~1285`) when `injectSSEEvent` is missing — that almost always means a stale cache, i.e. a missed `?v=` bump.

### Pitfall 5 — Test-isolation: re-import rebinds the package attribute
❌ `sys.modules.pop("core.anime_pipeline_service")` then `import core.anime_pipeline_service as svc` inside a test. The fresh import **rebinds the `core` package attribute**, so `patch("core.anime_pipeline_service.X")` targets the *duplicate* while the route resolves the original via `sys.modules` → the patch silently misses and the real pipeline/network probe runs. This produced 6 phantom full-suite-only failures.
✅ Patch the module global directly (e.g. `monkeypatch.setattr("core.anime_pipeline_service.stream_pipeline", ...)` with a string target, or set `svc._PIPELINE_QUEUE_TIMEOUT_SEC` on the already-imported module). Do not reimport. Use `monkeypatch.delitem` (not raw `pop`) if you must touch `sys.modules`.

### Pitfall 6 — Phase 3 dependency assumptions
❌ Importing `websocket` at module top level.
✅ It's import-guarded because `websocket-client` is opt-in. The reader is a **no-op** unless `ANIME_PIPELINE_WS_PREVIEW` is on AND a callback is registered (`_maybe_start_ws_reader` returns `None` otherwise). Preview frames also need ComfyUI launched with `--preview-method` — `run.py` adds it only when the flag is on.

---

## Verification

**Automated (PR4 harness):** `services/chatbot/scripts/verify_image_chat_bridge.py` drives the real backend + ComfyUI. Phases: `happy` (full flow → 1 image saved), `cancel` (hard-close mid-stream → `cancel_requested` + ComfyUI queue drained), `rollback`, `wspreview` (heartbeat carries `progress_pct` + `preview_b64`). Needs an RTX-class GPU + ComfyUI on :8188.

**Unit:** `tests/test_comfy_ws_preview.py` (frame parser + flag gating), plus the bridge tests in `tests/test_image_chat_bridge.py` and `tests/test_anime_pipeline_cancel.py`. Run `cd services/chatbot && pytest tests/ -v` (venv-core).

**Manual (Electron only — not scriptable):** persistence-after-reload, modal fallback UX, DOM duplicate-save, no-caption-after-Stop, and the Phase 1b/3 visual rendering.

### Checklist before merging a bridge change
- [ ] `ap_*` frames still forwarded verbatim — new fields produced in `stream_pipeline()` AND consumed in `_handleInlineEvent`.
- [ ] Cancel/VRAM changes made in `_interrupt_comfyui()` (all 3 paths), `_other_active_jobs()` gate intact.
- [ ] Image thinking-block finalized via `finalizeThinkingKeepContent`, never `finalizeThinking`.
- [ ] `?v=` bumped in all 3 places if any JS/CSS touched.
- [ ] `error_class` set at the `comfy_client` site AND mapped in `_derive_recoverable` AND hinted in JS.
- [ ] Phase 3 stays default-OFF; reader still no-ops without flag+callback.
- [ ] Tests patch module globals (string target), never reimport the service module.
- [ ] PR4 `happy` + `cancel` pass live if the GPU path changed.

---

## Related skills

- **chat-ui-sync** — the modal image path, SSE-event→callback map, and the `/chat/stream` payload contract this bridge extends with `force_image_bridge`.
- **tool-response-contract** — exact SSE frame shapes; `ap_*` frames must obey the same wire discipline.
- **core-chatbot-routing-audit** — `stream.py` blueprint wiring and the request path the bridge hooks into.
- **requirements-profile-selection** — `websocket-client` classification (venv-core, opt-in).
- **test-impact-mapper** — which tests to run for a bridge change.
- **docs-drift-sync** — update README/PROGRESS when bridge runtime behavior changes.
