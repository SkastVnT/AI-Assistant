# INTEGRATION_MAP.md â€” AI-Assistant

Single reference for how the integrated subsystems fit together. Read this
before touching anything that crosses **Hermes / Reasoning / SAA /
character registry / LoRA / ComfyUI / storage**.

This document is **descriptive**, not aspirational. If runtime behaviour
diverges from what is written here, the runtime is right and this file is
wrong â€” open a docs-drift fix.

> Scope rule (from `.claude/skills/repo-guidelines/CLAUDE.md`): chatbot tasks may edit
> `services/chatbot/`, `services/shared_env.py`, `services/mcp-server/`,
> `app/config/`, `app/src/`. They MUST NOT edit `ComfyUI/`,
> `app/image_pipeline/`, `services/stable-diffusion/`,
> `services/edit-image/`. The subsystems documented here include code
> outside that scope; this file maps the boundary, it does not authorise
> crossing it.

---

## Top-level diagram

```
                            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                            â”‚ User (chat UI / API)   â”‚
                            â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                          â”‚
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚                             â”‚                              â”‚
            â–¼                             â–¼                              â–¼
 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 â”‚ /chat/stream     â”‚        â”‚ /api/hermes/chat       â”‚      â”‚ /api/image-gen/*   â”‚
 â”‚ (primary chat)   â”‚        â”‚ (Hermes proxy + bridge)â”‚      â”‚ (multi-provider)   â”‚
 â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
          â”‚                             â”‚                              â”‚
          â”‚             â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                â”‚
          â”‚             â”‚ core/image_intent.py        â”‚                â”‚
          â”‚             â”‚ (ONLY chatbot importer of   â”‚                â”‚
          â”‚             â”‚  image_pipeline.reasoning)  â”‚                â”‚
          â”‚             â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                â”‚
          â”‚                             â”‚ if both flags on             â”‚
          â”‚                             â–¼                              â”‚
          â”‚             â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                 â”‚
          â”‚             â”‚ /api/reasoning-image-gen/* â”‚                 â”‚
          â”‚             â”‚ (multi-panel reasoning)    â”‚                 â”‚
          â”‚             â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                 â”‚
          â”‚                           â”‚                                â”‚
          â”‚                           â–¼                                â”‚
          â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”          â”‚
          â”‚   â”‚ image_pipeline.reasoning  (parse â†’ plan â†’   â”‚          â”‚
          â”‚   â”‚   run_panel â†’ maybe_correct â†’ assemble)     â”‚          â”‚
          â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜          â”‚
          â”‚                        â”‚                                   â”‚
 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”       â”Œâ”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 â”‚ /api/anime-     â”‚       â”‚ ComfyUI          â”‚         â”‚ core/image_gen/        â”‚
 â”‚  pipeline/*     â”‚â”€â”€â”€â”€â”€â”€â–¶â”‚ (local, port     â”‚â—€â”€â”€â”€â”€â”€â”€â”€â”€â”‚ (fal/bfl/replicate/    â”‚
 â”‚ (character-awareâ”‚       â”‚  8188 by default)â”‚         â”‚  stepfun + comfyui)    â”‚
 â”‚  layered)       â”‚       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
 â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                                   â”‚
          â”‚                                                            â”‚
          â–¼                                                            â–¼
 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 â”‚ Storage tiers:                                                         â”‚
 â”‚   app/storage/character_db/         (registry seed JSON)                   â”‚
 â”‚   app/storage/character_refs/<tag>/ (downloaded references + seen_urls)    â”‚
 â”‚   app/storage/character_loras/<tag>/(LoRA cache + meta)                    â”‚
 â”‚   app/storage/metadata/<job_id>.json(ResultStore manifests â€” anime path)   â”‚
 â”‚   ComfyUI/output/               (raw images from local ComfyUI)        â”‚
 â”‚   services/chatbot/app/storage/Image_Gen/ (multi-provider gallery)         â”‚
 â”‚   app/storage/{outputs,intermediate,references,prompts}/  (reserved, empty)â”‚
 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

       SAA picker (separate process)            Hermes Agent (separate process)
 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 â”‚ character_select_stand_alone â”‚         â”‚ NousResearch/hermes-agent          â”‚
 â”‚  _app-main/  (Electron)       â”‚         â”‚ HTTP, default :8080                â”‚
 â”‚ port 51028, npm start         â”‚         â”‚ HERMES_ENABLED=true to enable      â”‚
 â”‚ CHARACTER_SELECT_ENABLED=true â”‚         â”‚                                    â”‚
 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                â”‚ data/ files read in-proc by                â”‚
                â”‚ app/image_pipeline/anime_pipeline/             â”‚ HTTP proxy
                â”‚   saa_character_db.py                      â–¼
                â”‚ (no HTTP call from chatbot to SAA           core/hermes_adapter.py
                â”‚  for character lookup)
```

---

## 1. Hermes Agent

**Purpose.** External chat agent (NousResearch). Used as an alternative
chat backend exposed via a single proxy endpoint. Optional bridge to the
reasoning image pipeline when image-style messages are detected.

**Entry files.**
- Route: [services/chatbot/routes/hermes.py](../../services/chatbot/routes/hermes.py) â€” `POST /api/hermes/chat`.
- Adapter: [services/chatbot/core/hermes_adapter.py](../../services/chatbot/core/hermes_adapter.py) â€” HTTP client.
- Env: `HERMES_ENABLED`, `HERMES_API_URL` (default `http://localhost:8080`), `HERMES_TIMEOUT`, `HERMES_API_KEY`.

**Input.** JSON `{message, conversation_history?, model?}`.

**Output.** JSON `{success, result, error, elapsed_s}`. `result` is markdown
text (tool-response-contract).

**Owner / responsibility.** Proxy only. Owns nothing about identity,
images, or storage.

**Fallback behaviour.**
- `HERMES_ENABLED=false` â†’ 422 with Vietnamese "chÆ°a báº­t" message.
- Bridge (image redirect) is opt-in: requires `HERMES_ENABLED=true` AND
  `REASONING_PIPELINE=true`. Redirect fires only when **all three**
  conditions hold:
    1. The message contains an explicit image-generation keyword
       (Vietnamese or English) â€” see `_IMAGE_KEYWORD_RE` in
       [routes/hermes.py](../../services/chatbot/routes/hermes.py).
    2. `capability_router.classify()` returns one of `IMAGE_KINDS_NAMES`.
    3. `decision.confidence >= 0.75`.
  Any bridge import / classify / pipeline error is swallowed and the
  request falls through to Hermes unchanged (fails-safe).
- Sidecar unreachable â†’ adapter returns `success=false` with HTTP error.

**Current runtime.** The bridge logic lives in the Flask route
([routes/hermes.py](../../services/chatbot/routes/hermes.py)). The previous
FastAPI mirror was removed in May 2026; do not reintroduce a parallel
framework without an explicit task.

**MUST NOT.**
- Be wired into `routes/stream.py` (primary `/chat/stream`).
- Persist images, write to `app/storage/`, or own job state.
- Import `image_pipeline.*` directly. The bridge MUST go through
  `core/image_intent.py`.

---

## 2. Reasoning Image Generation

**Purpose.** Multi-panel image / comic generation backed by local
ComfyUI. Cycles 1â€“6 of `app/image_pipeline/reasoning/`.

**Entry files.**
- Route: [services/chatbot/routes/reasoning_image_gen.py](../../services/chatbot/routes/reasoning_image_gen.py) â€” `POST /api/reasoning-image-gen/generate`, `GET /status`.
- Pipeline: `app/image_pipeline/reasoning/{capability_router,prompt_parser,prompt_revision,schemas,state/,execution/}`.
- Env: `REASONING_PIPELINE` (alias `REASONING_PIPELINE_ENABLED`),
  `REASONING_PIPELINE_COMFY_URL` (default `COMFYUI_URL` or
  `http://localhost:8188`), `REASONING_PIPELINE_MAX_PANELS`,
  `REASONING_PIPELINE_MAX_CORRECTION_PASSES`.

**Input.** Free-text prompt, optional layout, optional panel count.

**Output.** JSON descriptor + base64 image(s). **Does not persist to
disk.** No gallery, no job manifest, no character_key consumption today.

**Owner / responsibility.** Owns: prompt â†’ panel spec â†’ ComfyUI workflow
â†’ image bytes. Owns the schema and the correction loop.

**Fallback behaviour.**
- Blueprint registered ONLY when `REASONING_PIPELINE_ENABLED=true`. With
  flag off, route is absent (URL map byte-identical to legacy).
- ComfyUI unreachable â†’ returns failure descriptor; no retry.
- Scorer / inpaint runner default to no-op; correction loop short-circuits.

**MUST NOT.**
- Be imported by chatbot code outside `core/image_intent.py`. All other
  `services/chatbot/` files are forbidden from `import image_pipeline.reasoning`.
- Replace path A (`/api/image-gen/*`) or path B (`/api/anime-pipeline/*`).
  These are parallel paths, not an inheritance chain.
- Write into `app/storage/`. (Today it doesn't. Future curator owns that.)

---

## 3. SAA character picker (sidecar + offline DB)

SAA = `app/character_select_stand_alone_app-main/`. Two distinct uses inside
the chatbot â€” keep them separated.

### 3a. SAA sidecar (Electron, port 51028)

**Purpose.** Optional GUI for manual character browsing. Runs as a
separate process when the user wants the rich picker UX.

**Entry files.**
- Route: [services/chatbot/routes/character_select.py](../../services/chatbot/routes/character_select.py) â€” `/api/character-select/status`, `/api/character-select/url`.
- Adapter: [services/chatbot/core/character_select_adapter.py](../../services/chatbot/core/character_select_adapter.py) â€” HTTP probe only.
- Env: `CHARACTER_SELECT_ENABLED`, `CHARACTER_SELECT_URL`.

**Input.** Reachability probes from the topbar.
**Output.** JSON `{enabled, reachable, running, installed, url}`.
**Owner.** Health and URL surfacing only.
**Fallback.** Not running â†’ status reports `reachable=false`; chatbot
continues without it. The in-app picker (3c) keeps working regardless.

**MUST NOT.** Make the chatbot block on the sidecar. The chatbot owns
zero data files inside `app/character_select_stand_alone_app-main/`.

### 3b. SAA offline DB (in-process, always available)

**Purpose.** In-memory access to the SAA data files
(`wai_characters.csv` â€” 5149 verified WAI SDXL characters,
`danbooru_e621_merged.csv` â€” tag autocomplete, `wai_character_thumbs.json`).

**Entry files.**
- Module: [app/image_pipeline/anime_pipeline/saa_character_db.py](../image_pipeline/anime_pipeline/saa_character_db.py) (read-only by chatbot).
- Routes: `/api/tags/autocomplete`, `/api/character-select/lookup`, plus
  `/api/local-image-gen/recent` and `/api/local-image-gen/file/<name>`
  in [routes/character_select.py](../../services/chatbot/routes/character_select.py).
- Augment in [routes/characters.py](../../services/chatbot/routes/characters.py) (extended search merges local registry + SAA hits).

**Input.** Free-text fragment / prefix.
**Output.** `WaiCharacterMatch` (display, tag, danbooru_tag, series_hint, score)
or `TagAutocomplete` records.
**Owner.** Read-only consumer of the SAA bundled CSV/JSON.
**Fallback.** SAA folder missing â†’ every function returns empty; rest
of the system continues.

**MUST NOT.** Mutate any file under `app/character_select_stand_alone_app-main/`.

### 3c. Picker UI (in-app)

**Purpose.** Topbar character picker that calls the chatbot's own API.

**Entry files.**
- Frontend: `services/chatbot/static/js/modules/character-picker.js`,
  `services/chatbot/static/js/modules/job-queue-panel.js`.
- Topbar buttons: `templates/index.html` â†’ `#characterPickerBtn`,
  `#jobQueueBtn`.

**Input.** User keystrokes.
**Output.** Sets `window.selectedCharacter`, `body[data-character-key]`,
fires `CustomEvent('character:selected')`.
**Owner.** UI surface only.
**Fallback.** API errors render an inline message; no character is set.

**MUST NOT.** Bypass `/api/characters/*`. The picker is not allowed to
talk to the SAA sidecar (port 51028) directly; it goes through the
chatbot's routes.

---

## 4. Character registry (canonical local DB)

**Purpose.** Hand-curated source of truth for important characters. Tiny
today (4 entries), but it is the layer where alias / series / collision
rules live.

**Entry files.**
- Singleton: [services/chatbot/core/character_registry.py](../../services/chatbot/core/character_registry.py) â€” `get_registry()`.
- Route: [services/chatbot/routes/characters.py](../../services/chatbot/routes/characters.py) â€” `/api/characters/*`.
- Data: [app/storage/character_db/characters.json](../storage/character_db/characters.json),
  [app/storage/character_db/series_aliases.json](../storage/character_db/series_aliases.json).

**Input.** Search query, series filter, character key.
**Output.** `CharacterRecord` (key, display_name, series, series_key,
character_tag, series_tag, aliases, thumbnail, lora_hint, solo_recommended,
category) â€” see `CharacterRecord` dataclass.

**Owner.** Local registry data + alias normalisation +
collision detection (`detect_collisions(display_name)`).

**Fallback.** Missing JSON file â†’ empty registry, warning logged. Search
endpoints with `extended=1` then augment from SAA DB (3b).

**MUST NOT.**
- Be the only character vocabulary â€” SAA covers long tail.
- Be edited via runtime API (no `POST /api/characters` create/update;
  `/reload` reloads from disk only).
- Be confused with `image_pipeline.anime_pipeline.character_parser`
  (which is heuristic, in-memory, dictionary-driven).

---

## 5. LoRA resolver

**Purpose.** Resolve a character identity to an actual LoRA file on
disk, downloading from CivitAI when needed and verifying with vision AI.

**Entry files.**
- Module: [app/image_pipeline/anime_pipeline/lora_manager.py](../image_pipeline/anime_pipeline/lora_manager.py).
- Registry: [app/configs_vps/lora_registry.yaml](../configs_vps/lora_registry.yaml).
- Cache: `app/storage/character_loras/<tag>/lora_meta.json` (7-day TTL).
- Files: `ComfyUI/models/loras/characters/<tag>/<filename>`.
- User-visible audit: `LORA/download_manifest.json`.

**Input.** A resolved character (typically `character_tag` in danbooru
form, e.g. `kafka_(honkai:_star_rail)`).

**Output.** Path to a `.safetensors` LoRA + verdict in the manifest.

**Owner.** CivitAI search, download, vision verification, manifest
append. Owns nothing about prompts.

**Fallback.**
- No CivitAI hit â†’ no LoRA, pipeline runs without one.
- Vision verdict below threshold â†’ file deleted, manifest records
  `verdict: "rejected"`, no LoRA returned.
- Cache hit within TTL â†’ skip network.

**MUST NOT.**
- Be called by chatbot routes directly; only `image_pipeline.anime_pipeline`
  invokes it. (Today the only caller chain is path B / anime pipeline.)
- Mutate `LORA/` files outside `download_manifest.json` and the
  `characters/<tag>/` subdirs of `ComfyUI/models/loras/`.

---

## 6. ComfyUI providers

**Purpose.** Submit workflows to a local ComfyUI server (`:8188` by
default) and return image bytes.

**Entry points (three independent callers).**
- Path A â€” `core/image_gen/providers/comfyui_provider.py` (one provider
  among fal/bfl/replicate/stepfun in the multi-provider router).
- Path B â€” `app/image_pipeline/anime_pipeline/comfy_client.py` used by
  `AnimePipelineOrchestrator`.
- Path C â€” `_ComfyClientAdapter` inside
  [routes/reasoning_image_gen.py](../../services/chatbot/routes/reasoning_image_gen.py),
  wrapping `src/utils/comfyui_client.ComfyUIClient`.

**Input.** A workflow dict (graph), optional `job_id`, optional
`pass_name`.

**Output.** Image bytes (or base64) plus duration and error fields.

**Owner.** Workflow submission, polling, image fetch. NOT prompt
construction.

**Fallback.** Timeout, missing `prompt_id`, missing image â†’ return
`success=false` with explicit error string. No silent retry.

**MUST NOT.**
- Be unified into a single client without explicit cross-path testing â€”
  the three callers have different timeout, polling, and workflow
  conventions today.
- Read or write to `app/storage/` directly. Output handling belongs to the
  caller.

---

## 7. Storage tiers

There is **no single output root**. Each path writes to a different
place. Future work (curator) is expected to consolidate, but today this
is the truth:

| Tier | Path | Writer | Notes |
|---|---|---|---|
| Registry seed | `app/storage/character_db/` | git (manual) | Source of truth for Â§4 |
| Reference images | `app/storage/character_refs/<tag>/` | `app/image_pipeline/anime_pipeline/character_research.py` | Includes `seen_urls.json` (url-hash + sha256 dedupe). Override reuse via `CHAR_RESEARCH_REUSE_REFS=1` |
| Research cache | `app/storage/character_research/<tag>/research.json` | `character_research.py` | 7-day TTL |
| LoRA cache + meta | `app/storage/character_loras/<tag>/lora_meta.json` | `lora_manager.py` | 7-day TTL |
| LoRA files | `ComfyUI/models/loras/characters/<tag>/` | `lora_manager.py` | Outside `app/storage/` |
| Anime job manifest | `app/storage/metadata/<job_id>.json` | `app/image_pipeline/anime_pipeline/result_store.py` | Path B only |
| Multi-provider gallery | `services/chatbot/app/storage/Image_Gen/` | `core/image_gen/storage.py` | Path A only |
| Video gallery | `services/chatbot/app/storage/Video_Gen/` | video routes | Path A video |
| ComfyUI raw output | `ComfyUI/output/` | ComfyUI itself | Surfaced via `/api/local-image-gen/recent` |
| LoRA download audit | `LORA/download_manifest.json` | `lora_manager.py` | Append-only |

**Reserved but empty (today):** `app/storage/outputs/`, `app/storage/intermediate/`,
`app/storage/references/`, `app/storage/prompts/` â€” only `.gitkeep`. These were
provisioned for a unified layout that has not landed. Do not start
writing into them ad-hoc; they are the curator's future home (Â§8).

**Owner / responsibility.** Each writer owns its tier. No tier is
authoritative across paths. The job queue
([core/job_queue.py](../../services/chatbot/core/job_queue.py)) is bounded
in-memory state (default 200), not durable storage.

**MUST NOT.**
- Hand storage paths around as strings â€” always use the writer's helper.
- Cross-write between tiers (path A must not write into Path B's manifest
  dir, and vice versa).
- Add a third gallery directory. New gallery work should go through the
  curator (Â§8) once it exists.

---

## 8. Future CPU-only storage curator (Phase 1)

> Not yet implemented. This section is a contract for the next builder
> so accidental work doesn't pre-empt it.

**Purpose.** Single, CPU-only process that:
1. Watches `ComfyUI/output/` and the existing per-path tiers.
2. Indexes new artefacts with the canonical character identity (Â§ Gaps)
   and a stable `asset_id`.
3. Promotes / archives / prunes artefacts according to a policy file.
4. Exposes a read-only API the UI can use as a unified gallery.

**Entry files (planned, not present yet).**
- Module: `services/chatbot/core/storage_curator.py` (does not exist).
- Route: `services/chatbot/routes/storage.py` (does not exist).
- Index: `app/storage/index/<asset_id>.json` (planned location â€” verify
  before adopting).

**Input.** Filesystem events + manifest writes from existing writers.

**Output.** A canonical record per asset linking: source path, character
canonical id, LoRA file used, reference URLs used, generation prompt,
provider, job_id, timestamp.

**Owner / responsibility.** Read across tiers, write **only** to its own
index dir. Owns retention policy.

**Fallback.** If curator is down, all existing writers keep working
unchanged. Curator failure is never fatal to generation.

**Phase-1 constraints (locked).**
- **CPU-only.** No vision model, no GPU dependency, no embedding model.
  Identity matching uses canonical IDs (Â§ Gaps), filename heuristics, and
  the manifests writers already emit. Vision-based curation is Phase 2.
- **Read-mostly.** No mutation of upstream artefacts. Move/symlink only
  if explicitly enabled by config; otherwise index in place.
- **No new storage tier.** Build on top of existing `app/storage/`,
  `ComfyUI/output/`, `services/chatbot/app/storage/Image_Gen/`. The reserved
  empty dirs (`app/storage/{outputs,intermediate,references,prompts}/`) are
  available for the curator to claim in this phase.

**MUST NOT.**
- Pull in any image-AI dependency (`venv-image`). Curator runs in
  `venv-core`.
- Block generation. All curator I/O must be off the request path.
- Become the writer for paths A/B/C. They keep writing where they write
  today; the curator only observes and indexes.

---

## Current known gaps

These are the active integration cliffs. Future work should resolve them
before adding more entry points.

1. **SAA is integrated as picker / API surface but is not the
   source-of-truth for image generation.**
   - Path A (`/api/image-gen/*`): cloud providers ignore the picker; only
     `comfyui_provider.py` calls `saa_character_db.lookup_character`.
   - Path B (`/api/anime-pipeline/*`): consumes `character_key` via
     `_enrich_with_character` (registry â†’ SAA â†’ `character_nlu`), but
     only as a prompt-prefix string. Structured identity is dropped before
     `character_parser` re-resolves.
   - Path C (`/api/reasoning-image-gen/*`): no SAA, no registry, no
     `character_key` at all.

2. **Hermes bridge is separate from storage curation.**
   The bridge (`core/image_intent.py`) only redirects. It does not
   record anything, does not write to storage, and does not coordinate
   with the job queue. When/if curator (Â§8) lands, bridge-routed runs
   must still flow through the same indexing seam as direct
   reasoning-pipeline calls â€” no special bridge-only path.

3. **Storage curator must be CPU-only in Phase 1, not vision.**
   Vision verification already exists inside `lora_manager.py` for LoRA
   acceptance. The curator must not duplicate or extend that into a
   GPU-bound dependency. Phase-1 curator is filesystem indexing +
   canonical-id linking only. Vision-based dedupe / quality scoring is
   explicitly Phase 2 and out of scope.

4. **Duplicate identity / alias / game / scene must be solved with
   canonical IDs.**
   Today, the same character can appear under three or more keys
   depending on entry path (e.g. `kafka_honkai_star_rail`,
   `kafka_(honkai:_star_rail)`, `kafka` from SAA augment). Variant
   ("swimsuit", "alt outfit") and scene have no schema slot. Required
   shape (proposed, not yet code):

   ```
   canonical_id := <series_key>:<character_slug>[:<variant_slug>]
   alias        := any string that resolves to canonical_id
   resolver     := single function with deterministic precedence
                   (registry > SAA > character_parser heuristic)
   ```

   Until canonical IDs exist, do NOT add new code paths that consume
   `character_key` â€” they will widen the drift.

5. **Three parallel image-generation paths, one picker, one bridge.**
   `/api/image-gen/*`, `/api/anime-pipeline/*`,
   `/api/reasoning-image-gen/*` are independent. Anything that claims
   to be "the" image flow is wrong. New work that touches identity must
   either pick one path explicitly or solve gap #4 first.

6. **Flask is the active chatbot runtime.** The previous FastAPI mirror
   package was removed in May 2026. Do not document or implement a
   second router path without an explicit migration task.

7. **Reserved storage dirs (`app/storage/outputs|intermediate|references|prompts`)
   are empty and undocumented as reserved.** Until the curator claims
   them, they look like dead code. Do not delete; do not start writing
   into them ad-hoc.

---

## How to use this document

- **Before adding a route**, find which numbered subsystem owns the
  behaviour. If two subsystems claim it, that is a Â§"Current known gaps"
  item and needs a separate decision before code lands.
- **Before adding a storage write**, check Â§ 7. If your tier isn't
  listed, you are probably about to invent an eighth one â€” stop and
  reread Â§ 8.
- **Before importing `image_pipeline.*` from chatbot code**, check
  Â§ Reasoning and Â§ ComfyUI providers. The only allowed import of
  `image_pipeline.reasoning` from `services/chatbot/` is in
  `core/image_intent.py`.
- **When this file goes stale** (port changes, route rename, env flag
  rename, new subsystem), update it in the same PR â€” see
  `.github/skills/docs-drift-sync/SKILL.md`.
