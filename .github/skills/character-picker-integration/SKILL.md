---
name: character-picker-integration
description: "Maintain the character picker, character registry, and local job queue tier added to AI-Assistant. Use when: editing app/storage/character_db/ data files; modifying core/character_registry.py or core/job_queue.py; changing /api/characters/* or /api/jobs/* routes; touching the character-picker.js / job-queue-panel.js frontend modules; integrating character_key into a new image-gen flow; or extending the queue lifecycle with new states."
---

# Character Picker Integration

## When to use this skill

- Adding/editing characters in `app/storage/character_db/characters.json`.
- Adding new series aliases in `app/storage/character_db/series_aliases.json`.
- Modifying `services/chatbot/core/character_registry.py` (registry singleton).
- Modifying `services/chatbot/core/job_queue.py` (queue singleton).
- Changing routes in `services/chatbot/routes/characters.py` or `services/chatbot/routes/jobs.py`.
- Touching `services/chatbot/static/js/modules/character-picker.js` or `job-queue-panel.js`.
- Wiring `character_key` into another image-gen route (only `/api/anime-pipeline/*` is wired today).
- Extending lifecycle states beyond `queued|running|completed|failed|cancelled`.

## Architecture summary

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ Frontend                                                     â”‚
â”‚  templates/index.html  â†’ buttons: characterPickerBtn,         â”‚
â”‚                          jobQueueBtn (topbar)                 â”‚
â”‚  static/js/modules/character-picker.js                        â”‚
â”‚    window.openCharacterPicker(onSelect)                       â”‚
â”‚    fires document event 'character:selected'                  â”‚
â”‚    sets window.selectedCharacter + body[data-character-key]   â”‚
â”‚  static/js/modules/job-queue-panel.js                         â”‚
â”‚    window.openJobQueuePanel() â€” polls /api/jobs every 3.5s    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Backend (Flask blueprints)                                   â”‚
â”‚  routes/characters.py  â†’ /api/characters/*                    â”‚
â”‚  routes/jobs.py        â†’ /api/jobs/*                          â”‚
â”‚  routes/anime_pipeline.py â†’ enriched: accepts character_key,  â”‚
â”‚                              writes to JobQueue               â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Core singletons                                              â”‚
â”‚  core/character_registry.py â€” CharacterRegistry, get_registry()â”‚
â”‚  core/job_queue.py          â€” JobQueue, get_queue()           â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Data                                                         â”‚
â”‚  app/storage/character_db/characters.json                         â”‚
â”‚  app/storage/character_db/series_aliases.json                     â”‚
â”‚  app/storage/metadata/<job_id>.json  (manifest, written by        â”‚
â”‚                                    ResultStore â€” pre-existing)â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Endpoint contract

| Method | URL | Purpose | Response |
|---|---|---|---|
| GET | `/api/characters` | List/search; params `q`, `series`, `limitâ‰¤200` | `{characters: [...], count, query, series_filter}` |
| GET | `/api/characters/series` | List unique series | `{series: [{key, name}]}` |
| GET | `/api/characters/<key>` | Get one + collisions | `{character: {...}, collisions: [...]}` |
| GET | `/api/characters/<key>/thumbnail` | Binary PNG/WebP | image bytes / 404 |
| POST | `/api/characters/reload` | Reload registry from disk | `{reloaded, count}` |
| POST | `/api/characters/resolve` | Body `{query}` â†’ best match | `{resolved, character?}` |
| GET | `/api/jobs` | List with `state`, `limit` filters | `{jobs, count, stats}` |
| GET | `/api/jobs/stats` | Counts by state | `{total, by_state, history_limit}` |
| GET | `/api/jobs/<job_id>` | Job record | `{job: {...}}` or 404 |
| GET | `/api/jobs/<job_id>/manifest` | Persisted manifest JSON | `{manifest, manifest_source, path}` |
| POST | `/api/jobs/<job_id>/cancel` | Best-effort cancel flag | `{cancelled, job_id}` |

## Character record shape (canonical)

```jsonc
{
  "key": "raiden_shogun_genshin_impact",       // unique, lowercase, snake_case
  "display_name": "Raiden Shogun",             // shown in UI
  "series": "Genshin Impact",                  // shown in UI
  "series_key": "genshin_impact",              // canonical key for filter
  "character_tag": "raiden_shogun",            // danbooru tag
  "series_tag": "genshin_impact",              // danbooru series tag
  "aliases": ["Ei", "Baal"],                   // searchable + resolve_query
  "thumbnail": "app/storage/character_refs/raiden_shogun/thumb.webp", // optional
  "lora_hint": null,                            // optional default LoRA key
  "solo_recommended": true,                    // hint for prompt builder
  "category": "character"                      // free-form tag
}
```

## Job record shape (canonical)

```jsonc
{
  "job_id": "abcd1234abcd",
  "state": "running",                  // queued|running|completed|failed|cancelled
  "created_at": 1700000000.0,
  "started_at": 1700000005.0,
  "completed_at": null,
  "prompt": "Raiden Shogun in Genshin Impact, ...",
  "character_key": "raiden_shogun_genshin_impact",
  "character_display": "Raiden Shogun",
  "series_key": "genshin_impact",
  "preset": "anime_quality",
  "model_slot": null,
  "progress_stage": "composition_pass",
  "progress_pct": 33.0,
  "error": null,
  "final_image_path": null,
  "manifest_path": null,
  "cancel_requested": false,
  "extra": {}
}
```

## Rules

1. **No second dotenv load.** This subsystem reads no env vars. If env access becomes necessary, route through `services/shared_env.py`.
2. **Registry singleton uses `get_registry()`** â€” do not instantiate `CharacterRegistry()` directly outside the singleton.
3. **JobQueue is in-memory only.** Persistence lives in the existing `ResultStore` (`app/storage/metadata/<job_id>.json`). Do not duplicate.
4. **Cancellation is cooperative.** `request_cancel()` sets a flag; pipeline code should call `q.is_cancel_requested(job_id)` between stages and abort itself. The orchestrator does NOT yet check this â€” wiring is a future task.
5. **Character JSON keys are lowercase snake_case** combining character + series, e.g. `kafka_honkai_star_rail`. Never use spaces.
6. **Series aliases are case-insensitive** but stored case-preserving; canonical values must match a `series_key` used by some character.
7. **Thumbnail paths are repo-relative.** The `/thumbnail` route resolves against repo root and refuses paths that escape it.

## SAA sidecar data path

The SAA (Stand-Alone App, Electron) character picker sidecar is **opt-in** via `CHARACTER_SELECT_ENABLED=true`. It runs as a separate Electron process at port 51028.

**Data files (read-only by chatbot â€” do not edit from Python):**

| File | Contents | Loaded by |
|---|---|---|
| `app/character_select_stand_alone_app-main/data/wai_characters.csv` | 5149 verified WAI SDXL characters (key, display_name, series, tags) | `app/image_pipeline/anime_pipeline/saa_character_db.py` at import time |
| `app/character_select_stand_alone_app-main/data/danbooru_e621_merged.csv` | Tag autocomplete vocabulary | `saa_character_db.py` at import time |
| `app/character_select_stand_alone_app-main/data/wai_character_thumbs.json` | Character thumbnail index (key â†’ URL/path) | `saa_character_db.py` at import time |

**Integration levels:**

1. `app/image_pipeline/anime_pipeline/saa_character_db.py` â€” reads the CSV/JSON files above at import time and builds in-memory indexes. Used by the 7-agent anime pipeline.
2. `services/chatbot/core/character_select_adapter.py` â€” HTTP probe to the SAA sidecar for status/reachability. Mirrors `hermes_adapter` contract: gates on `CHARACTER_SELECT_ENABLED`, returns `{success, result, error, elapsed_s}`.
3. `services/chatbot/routes/characters.py` â€” when `extended=true` param is present on `/api/characters`, augments local registry results with WAI characters from SAA database (5149 additional chars).
4. `services/chatbot/routes/character_select.py` â€” `/api/character-select/status`, `/api/character-select/url`, and `/api/local-image-gen/recent` proxy endpoints for the sidecar.

**Rules:**
- `saa_character_db.py` loads at **import time** â€” any import failure silently degrades extended search (no hard crash).
- SAA CSV/JSON files are owned by the SAA Electron app. Do not parse or modify them outside `saa_character_db.py`.
- The SAA sidecar port (51028) is not configurable from the chatbot â€” it is hardcoded in the Electron app.

## File monitor

| File | What to verify when changing |
|---|---|
| `app/storage/character_db/characters.json` | Valid JSON; every record has `key, display_name, series, series_key, character_tag`. |
| `app/storage/character_db/series_aliases.json` | Map of alias â†’ canonical `series_key` that exists in characters.json. |
| `core/character_registry.py` | Run `tests/test_character_registry.py`. |
| `core/job_queue.py` | Run `tests/test_job_queue.py`. |
| `core/character_select_adapter.py` | Verify probe URL uses env var; check `CHARACTER_SELECT_ENABLED` gate. |
| `routes/characters.py` | Smoke a `/api/characters` GET; check `count` matches registry. Smoke `?extended=true` when SAA running. |
| `routes/jobs.py` | Smoke `GET /api/jobs/stats` + `POST /api/jobs/<id>/cancel`. |
| `routes/character_select.py` | Smoke `/api/character-select/status` returns `{enabled, reachable}`. |
| `routes/anime_pipeline.py` | When changing `_enrich_with_character` or `_wrap_stream_with_queue`, re-test SSE flow. |
| `app/image_pipeline/anime_pipeline/saa_character_db.py` | After CSV schema changes, verify indexes rebuild without exception. |
| `chatbot_main.py` | After adding/removing blueprints in this subsystem, verify they appear in startup logs. |
| `templates/index.html` | After changing topbar buttons, verify lucide icons re-render and event listeners attach. |
| `static/js/modules/character-picker.js` | After API URL changes, sync with `routes/characters.py`. |
| `static/js/modules/job-queue-panel.js` | After API URL changes, sync with `routes/jobs.py`. |
| `static/css/character-picker.css` | Theme variables: `--bg-elevated, --bg-input, --border-color, --text-primary, --text-muted, --accent`. |

## Forbidden

- Do not hardcode characters in Python â€” extend `characters.json` instead.
- Do not couple registry/queue to MongoDB or Firebase. They are intentionally local + stateless across restarts.
- Do not import this subsystem from `app/image_pipeline/` (data flow is Flask route â†’ orchestrator one-way).
- Do not introduce a websocket/long-poll for the queue; HTTP polling at 3.5s is sufficient.

## How to add a new character

1. Edit `app/storage/character_db/characters.json`. Use a unique snake_case `key` ending with the series_key.
2. Optionally drop a thumbnail to `app/storage/character_refs/<character_tag>/thumb.webp`.
3. Hit `POST /api/characters/reload` (or restart) to refresh the in-memory registry.
4. Verify in UI by opening the picker.

## How to add a series alias

1. Edit `app/storage/character_db/series_aliases.json` â€” add `"<alias>": "<canonical_series_key>"`.
2. Reload via `POST /api/characters/reload`.
3. Verify with `GET /api/characters?series=<alias>` returns the right characters.

## Verification checklist for any change

- [ ] `python -m py_compile` on every changed `.py` file.
- [ ] `pytest services/chatbot/tests/test_character_registry.py services/chatbot/tests/test_job_queue.py -v` passes.
- [ ] Manual: open `/` in browser, click character picker button, search/filter works, selection sets `window.selectedCharacter`.
- [ ] Manual: click queue button, panel opens, polling refreshes.
- [ ] If anime pipeline route changed: send `POST /api/anime-pipeline/stream` with `character_key`; confirm prompt is enriched and JobQueue records the job.
