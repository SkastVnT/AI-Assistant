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
3. Local `CharacterRegistry` (`storage/character_db/`)
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
[`services/chatbot/config/character_overrides.example.json`](../services/chatbot/config/character_overrides.example.json).

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

- No network or web-search fallback.
- No web crawler.
- No vision / image classifier on uploaded references.
- No automatic LoRA training.
- No automatic promotion of generated images or user references into the
  registry.
- No automatic LoRA attachment from override text alone.
- No frontend redesign.
- No edits to `image_pipeline/` or ComfyUI.
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

## Verification

```powershell
cd services/chatbot
..\..\venv-core\Scripts\python.exe -m py_compile core/character_understanding.py core/image_gen/cost_estimator.py
..\..\venv-core\Scripts\python.exe -m pytest tests/ -k "character_understanding or reasoning_image_gen or preflight or image_request_cost or can_attach" -v
```
