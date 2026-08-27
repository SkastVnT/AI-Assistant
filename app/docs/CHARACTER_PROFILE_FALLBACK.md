# Character Profile Fallback

This document describes the **unknown / low-data character profile** layer
that lives in `services/chatbot/core/character_understanding.py`. It is a
backend-only, rule-based system. No web search, no crawl, no GPU, no
vision.

## Why it exists

Image generation requests routinely reference characters that are:

- brand-new (just released by a game / anime)
- niche (small fan communities, original characters)
- missing from SAA's WAI database
- missing from the local registry
- collisions with same-named characters in other franchises
- described only in free-form prompt text

If the resolver silently picks the *nearest popular* character it knows,
the system attaches the wrong LoRA and produces a confidently wrong
image. The fallback layer prevents this.

## Resolution priority

`resolve_character()` tries sources in this order:

1. `selected_character` payload (UI picker — trusted)
2. **Manual override** (`config/character_overrides.json`)
3. Local `CharacterRegistry` (`app/storage/character_db/`)
4. SAA WAI character DB
5. Built-in alias table (small, hand-maintained)
6. **Unknown profile fallback** (only if the prompt looks character-named)
7. Empty / unresolved (when the prompt has no character at all)

The `mode` values exposed on the result:

| `mode` | Meaning | `safe_to_attach_lora` |
|---|---|---|
| `resolved_known` | A trusted source produced a single high-confidence candidate with an exact canonical identity | `True` (route still applies its own confidence gate, default `>= 0.8`) |
| `ambiguous` | Multiple candidates within the confidence band; identity not pinned | `False` |
| `low_data_profile` | Manual override matched (curated text, no certified LoRA) | `False` unless the override sets both `lora_hint` AND `safe_to_attach_lora: true` |
| `unresolved_unknown` | Prompt looks character-named but no source recognized it | `False` |
| `""` (empty — `no_character_detected`) | Prompt has no character reference at all (generic art, scenery, abstract) | `False` (irrelevant — nothing to attach) |

### Why we never *guess* an unknown character

The resolver refuses to substitute a same-named or near-name match from
a different franchise. Guessing produces confidently wrong images: wrong
hair, wrong outfit, wrong weapon, wrong universe — usually after the
2000-second ComfyUI run has already finished. The four "did not resolve
cleanly" outcomes (`ambiguous`, `low_data_profile` without explicit LoRA
opt-in, `unresolved_unknown`, and empty) all set
`safe_to_attach_lora=False`. The route then either:

- runs the prompt **without** a character LoRA (safer, generic identity),
- short-circuits via the preflight gate (see below), or
- defers to the user via `selected_character` (Prompt 5 frontend picker —
  not yet shipped; will further improve accuracy by removing the resolver
  guess entirely for the supplied request).

### `original_character` (informal sub-case)

There is no dedicated `mode` value for original characters. Prompts
containing phrases like "OC", "original character", or "my character"
are treated by `extract_prompt_entities` as having no canonical name; the
resolver then returns `""` (`no_character_detected`) so nothing is pinned
or attached. This is intentional — original characters by definition do
not belong in the registry.

## Why `low_data_profile` does not auto-attach LoRA

A manual override is curated text only. It tells the model what the
character *looks like*, but it does not certify that any LoRA file
matching the canonical id is safe / accurate. The override must
**explicitly** opt in by setting both fields:

```json
{
  "canonical_id": "verified_char@verified_series",
  "lora_hint": "verified_char_v1.safetensors",
  "safe_to_attach_lora": true
}
```

Even then, the route applies a confidence gate (`>= 0.8`) before the
hint is auto-filled.

## Adding a new character without code changes

Drop a JSON entry into `services/chatbot/config/character_overrides.json`
(create the file if it does not exist — it is gitignored). Schema:

```json
{
  "characters": [
    {
      "canonical_id": "char_slug@series_slug",
      "display_name": "Display Name",
      "aliases": ["alt name 1", "alt name 2"],
      "series_slug": "series_slug",
      "visual_traits": ["..."],
      "outfit_traits": ["..."],
      "negative_identity_guard": [
        "do not substitute with another known character"
      ],
      "lora_hint": null,
      "safe_to_attach_lora": false,
      "data_status": "manual_override",
      "needs_review": true
    }
  ]
}
```

A copy with all available fields lives in
[`services/chatbot/config/character_overrides.example.json`](../../services/chatbot/config/character_overrides.example.json).

The override file is loaded **lazily and fail-safe**:

- missing file → empty overrides
- invalid JSON → empty overrides + debug-level log line
- non-dict root → empty overrides

The system never crashes because of override-file problems.

## Collision safety

The series hint disambiguates same-named characters:

- `"Iroha trong Kaguya Cosmic Princess"` → `unknown:iroha@cosmic_princess_kaguya`
- `"Iroha trong Blue Archive"` → `iroha_blue_archive@blue_archive` (SAA hit)

When a series hint is present and **no source matches it**, the resolver
returns an unknown profile for that exact `name@series` combo. It does
not fall back to a same-named character from a different series.

When a name is collision-prone and there is no series hint, the resolver
returns `ambiguous` or `unresolved_unknown`. LoRA never auto-attaches.

## What the route does with the result

`POST /api/reasoning-image-gen/generate` echoes a debug payload back to
the frontend under `understanding`:

```json
{
  "understanding": {
    "mode": "unresolved_unknown",
    "character_mode": "unresolved_unknown",
    "canonical_id": null,
    "provisional_id": "unknown:iroha@cosmic_princess_kaguya",
    "data_status": "unknown",
    "needs_review": true,
    "safe_to_attach_lora": false,
    "reason": "no registry/SAA/alias/manual override hit; using unknown character profile fallback",
    "candidates": [],
    "unknown_profile": { "...": "..." },
    "character_identity_block": "Character (unknown / low-data, no LoRA): Iroha\nPossible series: cosmic_princess_kaguya\n..."
  }
}
```

Frontend / picker integrations (Phase 5+) will use `provisional_id` and
`needs_review` to surface a confirmation prompt to the user, and pass
the same id back as `selected_character` on the next request — at which
point Priority 1 short-circuits all further heuristics.

## What is intentionally not done

See also [STORAGE_CURATION_ROADMAP.md](STORAGE_CURATION_ROADMAP.md) for
the full non-goals list.

- No network or web-search fallback.
- No web crawler.
- No vision / image classifier on uploaded references.
- No automatic LoRA training.
- No automatic promotion of generated images or user references into the
  registry.
- No automatic LoRA attachment from override text alone.
- No frontend redesign.
- No edits to `app/image_pipeline/` or ComfyUI.
- No ComfyUI runtime / VRAM optimisation in this layer (deferred).

## Preflight + cost gates (how 2000-second wastes are avoided)

The reasoning route (`POST /api/reasoning-image-gen/generate`) runs two
cheap, opt-in checks **before** ComfyUI is invoked. Both are pure-Python
heuristics — no GPU, no network.

### Preflight risk gate

Computed by `_assess_preflight()` from the resolver result + prompt:

- `risk_level` — `"low" | "medium" | "high"`
- `multiple_characters` — `True` when more than one character name is
  detected in the prompt
- `blocking_reason` — short tag explaining a `high` verdict
  (e.g. `unresolved_unknown_no_traits`, `multiple_unknown_characters`)

Opt-in payload flags:

| Payload flag | Effect |
|---|---|
| `preflight_only: true` | Run resolver + preflight + cost; return JSON; **do not** call ComfyUI. Use this from a UI to show the user a "we're not sure who this is" prompt before spending GPU time. |
| `require_preflight_pass: true` | Block the request when `risk_level == "high"`. Returns 200 with `preflight_blocked: true`; ComfyUI is not called. |

### Cost-estimation gate

`estimate_image_request_cost()` (in
`services/chatbot/core/image_gen/cost_estimator.py`) inspects the
payload + preflight result and returns:

```json
{
  "estimated_cost_level": "low" | "medium" | "high",
  "reasons": ["..."],
  "recommended_mode": "fast" | "normal" | "ask_confirmation",
  "should_require_confirmation": true | false
}
```

High-cost signals: multi-panel layouts (`grid_2x2`, `comic`,
`storyboard`, …), `num_panels > 1`, total pixels ≥ 2 MP, `upscale` /
`hires_fix`, `attached_images >= 3`, correction-loop passes > 1, and any
`risk_level == "high"` from preflight.

Opt-in payload flags:

| Payload flag | Effect |
|---|---|
| `max_cost_level: "low" \| "medium" \| "high"` | When the estimate exceeds this cap, the route returns 200 with `needs_confirmation: true` and **does not** call ComfyUI. |
| `budget_mode: "fast"` | Sets `recommended_mode: "fast"` in the cost payload as a hint to the caller. The route does not currently auto-downgrade panel count or layout — the caller decides. |

The `cost` block is always attached to the response (preflight-only
return, blocked return, and successful generate return), so a UI can
display the estimate even when nothing is gated.

### Why this reduces bad 2000-second generations

1. **Identity risk is caught before GPU time.** A prompt that names an
   unknown character with no traits is flagged `unresolved_unknown_no_traits`
   in microseconds. The user can supply a manual override or pick a
   character via the picker before the 2000s pipeline runs.
2. **Expensive shapes are surfaced early.** A 3×3 grid with 9 panels is
   classified `high` cost before the planner expands it. The caller can
   shrink the layout or confirm explicitly.
3. **Wrong-LoRA / wrong-reference attachments are prevented.** When
   `safe_to_attach_lora` is `False`, the route runs without a character
   LoRA rather than guessing one. Bad LoRA renders are the single most
   common cause of throwaway generations.
4. **Reference / profile collection happens before generation.** With
   `preflight_only: true` the UI can ask "Who do you mean?" or "Add a
   reference image first" without burning GPU time.

Frontend integration (Prompt 5 — `selected_character` picker) will
further improve accuracy by short-circuiting the resolver entirely when
the user has already pinned an identity.

## Frontend surfaces

These are documentation pointers — implementation lives in
`services/chatbot/static/js/modules/`.

### `selected_character` vs free-text prompt

| Source | Trust | Resolver behaviour |
|---|---|---|
| `selected_character` (UI picker / chip) | **Trusted** — Priority 1, no heuristics run | `mode = resolved_known` and `safe_to_attach_lora` follow the picked entry's flags |
| Prompt text only | Heuristic — runs the full priority chain | May land in `ambiguous`, `unresolved_unknown`, or empty mode |

When the user picks a character via the chip / picker, the request body
includes `selected_character: { canonical_id, character_slug, series_slug,
display_name, thumbnail, ... }`. The route hands this to
`resolve_character()` as the trusted-pin argument and **all later
priorities are skipped** for that request. Free-text prompts go through
the full chain and may need preflight to gate identity risk.

### Compact character preview UI

Rendered from `core.character_preview.build_preview()` and the
`/api/characters/preview` endpoint. The preview is a UI-only artifact —
it never causes generation, never writes to storage, and never decides
LoRA attachment.

Priority chain (also in the docstring of `core/character_preview.py`):

1. `selected_character.thumbnail`
2. `manual_profile.reference_images[0]`
3. `character_overrides.json` `reference_images[0]`
4. SAA offline thumbnail
5. Local on-disk cache (`services/chatbot/static/cache/character_previews/`)
6. Inline-SVG placeholder (data URI, no asset file required)

Constraints:

- **UI-only.** The preview URL is for display in the chip / picker. It
  is **not** auto-attached as a reference image to any generation
  request. (See "Request-only reference images" below for the explicit
  opt-in path.)
- **No auto-fetch.** External URLs are passed through unchanged. The
  chatbot does not download remote previews to populate the local cache
  on its own. Cache files are only created by curator workflows or by
  the explicit thumbnail-generation script in
  `app/character_select_stand_alone_app-main/scripts/python/thumb-generator/`.
- **No vision.** The preview pipeline never opens or classifies any
  image. It only resolves which URL to render.

### Manual profile for characters missing from SAA

When a character is not in the local registry, not in SAA, and not in
the alias table, the user can either:

1. **Add a permanent override** in
   `services/chatbot/config/character_overrides.json` (the
   `low_data_profile` path described above). Survives across requests
   and chatbots.
2. **Send a one-shot `manual_profile`** in the request body. The chip
   surfaces this as the "Details" panel. Schema (all optional except
   `display_name`):

   ```json
   {
     "display_name": "Original Mage Aria",
     "series_slug": "custom_setting",
     "visual_traits": ["silver hair", "violet eyes"],
     "outfit_traits": ["dark robe"],
     "personality_traits": ["calm"],
     "negative_identity_guard": ["no canon characters"],
     "reference_images": ["https://example.com/aria.png", "..."]
   }
   ```

   Same governance rule as overrides: a `manual_profile` **never** flips
   `safe_to_attach_lora` on its own. It supplies trait text that the
   prompt builder uses to anchor identity without a LoRA.

### Request-only reference images

The reasoning route accepts user-supplied reference images **as
request-scope debug metadata only**. Source priority is:

1. `manual_profile.reference_images`
2. `selected_character.reference_images`
3. top-level `payload.reference_images`

When any of these are set, `POST /api/reasoning-image-gen/generate`
echoes a `references` block in the response:

```json
{
  "references": {
    "reference_scope": "request_only",
    "canonical_id": null,
    "provisional_id": "unknown:aria@custom_setting",
    "needs_review": true,
    "count": 2,
    "source": "manual_profile",
    "items": ["https://example.com/aria.png", "..."],
    "supported_by_pipeline": false
  }
}
```

Rules:

- **Request-only.** Never auto-promoted, never moved into
  `app/storage/references/`, never persisted globally. Each request is
  independent.
- **No vision.** The bytes (or URLs) are passed through; nothing
  inspects them.
- **`supported_by_pipeline: false`** is the explicit signal that the
  reasoning runner does not yet ingest reference image bytes per
  character. The metadata is round-tripped so a curator UI can show
  what was attached, but it does not change generation output today.
  A `TODO(reasoning-pipeline)` comment in
  `services/chatbot/routes/reasoning_image_gen.py` names the exact
  integration point for the future wire-up.
- **Capped at 4** items per request to keep response payloads bounded.
- Strings only (URLs, data URIs, opaque IDs). Non-string entries are
  silently dropped.

## Verification

```powershell
cd services/chatbot
..\..\venv-core\Scripts\python.exe -m py_compile core/character_understanding.py core/image_gen/cost_estimator.py
..\..\venv-core\Scripts\python.exe -m pytest tests/ -k "character_understanding or reasoning_image_gen or preflight or image_request_cost or can_attach" -v
```
