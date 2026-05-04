# IDENTITY_COLLISION_POLICY.md

Short, normative summary of how the chatbot handles character-identity
ambiguity in image-generation requests. Full background and code map
live in
[CHARACTER_PROFILE_FALLBACK.md](CHARACTER_PROFILE_FALLBACK.md).

## Rules

1. **Never substitute.** A name that resolves to multiple characters
   across franchises is `ambiguous`. The resolver does not pick the
   most popular one.
2. **Series hint is binding.** When the prompt says
   `"X trong Y"` / `"X in Y"`, the resolver only considers candidates
   from series `Y`. If none match, the result is `unresolved_unknown`
   for the exact `name@series` pair. It does **not** fall through to a
   same-named character from another series.
3. **No-LoRA without exact identity.** `safe_to_attach_lora=True`
   requires `mode == "resolved_known"` with a single high-confidence
   candidate, OR a manual override that explicitly opts in via both
   `lora_hint` and `safe_to_attach_lora: true`. All other modes
   (`ambiguous`, `low_data_profile` without opt-in, `unresolved_unknown`,
   empty/`no_character_detected`) → `False`.
4. **Original characters are never resolved.** Phrases like "OC",
   "original character", "my character" produce `no_character_detected`.
5. **High-risk identity blocks expensive runs (opt-in).** When the
   caller passes `require_preflight_pass: true`, a `high` risk verdict
   (e.g. `unresolved_unknown_no_traits`, `multiple_unknown_characters`)
   short-circuits the request before ComfyUI is invoked.
6. **`selected_character` overrides everything.** When the UI passes a
   trusted picker selection (Prompt 5 — frontend in progress), Priority
   1 wins and no resolver heuristics run for that request.

## Resolver mode → LoRA attachment quick reference

| `mode` | `safe_to_attach_lora` |
|---|---|
| `resolved_known` | `True` (gated by route confidence ≥ 0.8) |
| `low_data_profile` | `True` only if override sets both `lora_hint` and `safe_to_attach_lora: true` |
| `ambiguous` | `False` |
| `unresolved_unknown` | `False` |
| `""` (`no_character_detected`) | `False` |

## What this policy does not do

- No web search, no crawler, no vision, no auto-training, no automatic
  promotion of references into the registry, no ComfyUI runtime
  optimisation. See
  [CHARACTER_PROFILE_FALLBACK.md](CHARACTER_PROFILE_FALLBACK.md#what-is-intentionally-not-done)
  and [STORAGE_CURATION_ROADMAP.md](STORAGE_CURATION_ROADMAP.md#non-goals-intentionally-deferred).
