# STORAGE_CURATION_ROADMAP.md

How generated images and user-supplied references are curated **today**,
what is intentionally deferred, and where future work plugs in. Read
this together with [CHARACTER_PROFILE_FALLBACK.md](CHARACTER_PROFILE_FALLBACK.md)
and [IDENTITY_COLLISION_POLICY.md](IDENTITY_COLLISION_POLICY.md).

> Scope rule: this roadmap describes chatbot-side curation only.
> `image_pipeline/` and `ComfyUI/` are out of scope for chatbot tasks.

---

## What ships today

### CPU-only image storage curator

Script: [`scripts/curate_image_storage.py`](../scripts/curate_image_storage.py).

Walks `storage/outputs/` and `storage/intermediate/`, validates each
image, detects near-duplicates, picks up sidecar / manifest metadata,
and emits a curation report under `storage/metadata/curation/`.

```powershell
# CPU-only. Pillow required, OpenCV optional (used only for blur).
.\venv-core\Scripts\python.exe scripts\curate_image_storage.py `
    --root storage `
    --output-dir storage\metadata\curation `
    --avg-vision-sec 5
```

**Outputs (JSON Lines + summary):**

| File | Contents |
|---|---|
| `rejected.jsonl` | Failed a hard gate (extension, size, dimension). |
| `duplicates.jsonl` | Exact (sha1) or near-dup (dHash Hamming ≤ 5). |
| `candidates.jsonl` | Decoded cleanly but cannot auto-promote — review. |
| `promote_candidates.jsonl` | Score ≥ 90 **and** governance not blocked. Still requires a human to actually promote. |
| `failures.jsonl` | Could not be opened / decoded. |
| `summary.json` | Counts, score histogram, governance-block reasons, estimated vision-time saved. |

**Score rubric (additive, max 100):**

| Signal | Points |
|---|---|
| Valid (decoded) | +30 |
| Resolution ≥ 512² | +20 |
| File size in 50 KiB – 30 MiB | +10 |
| Not blank/black/white | +15 |
| Not blurry **or** blur skipped (cv2 missing) | +10 |
| Sidecar / manifest metadata present | +10 |
| Not duplicate | +5 |

**Governance (cannot auto-promote, even at score 100):**

- `mode ∈ {ambiguous, unresolved_unknown, low_data_profile}`
- `data_status ∈ {unknown, low_data, manual_override}`
- `needs_review: true`
- Missing `canonical_id`
- No manifest at all (origin cannot be trusted)

These rules mirror [IDENTITY_COLLISION_POLICY.md](IDENTITY_COLLISION_POLICY.md)
verbatim. If that policy changes, update `_BLOCKING_MODES` /
`_BLOCKING_DATA_STATUS` in the curator script too.

**Constraints:**

- CPU-only. No GPU.
- No vision / no image classifier.
- No network. No web crawl.
- No `image_pipeline` import.
- **Never deletes or moves files.** The storage tree is read-only as
  far as this script is concerned. The output directory is the only
  thing it writes to.

---

## Non-goals (intentionally deferred)

These are listed explicitly so future contributors do not silently
expand the scope:

| Non-goal | Why deferred |
|---|---|
| **No web crawl / web search for character data.** | Identity must come from a trusted source (registry, SAA, manual override, or user pin). A scraped page is not trustworthy enough to attach a LoRA. |
| **No vision scoring of generated or reference images.** | Vision adds GPU + latency + a second source of confident-wrong identity calls. The CPU-only score rubric is sufficient for the curation tier today. |
| **No automatic LoRA training from curated images.** | Training requires verified identity AND a curator review pass. Automating it would amplify any identity-resolution bug into a permanent model artifact. |
| **No automatic promotion** of generated images, user-supplied references, or curator candidates into `storage/character_db/` / `storage/references/`. | Promotion is a human decision. The curator script produces `promote_candidates.jsonl` as a worklist; nothing else is automated. |
| **No ComfyUI runtime / VRAM optimisation in this layer.** | Out of scope for chatbot tasks. See `ComfyUI/` and `image_pipeline/` owners. |

---

## Where future work plugs in

When (and only when) the runtime gains the capability, the following
hooks are the right insertion points. Do **not** pre-build the
abstractions before the capability lands.

| Future capability | Hook |
|---|---|
| Reasoning runner ingests per-character reference bytes | `image_pipeline.reasoning.execution.run_panel` — also flip `supported_by_pipeline` to `True` in `_collect_request_references()` in [`services/chatbot/routes/reasoning_image_gen.py`](../services/chatbot/routes/reasoning_image_gen.py). |
| Curator promotes a candidate into the registry | New CLI subcommand on `scripts/curate_image_storage.py` (e.g. `--promote <hash>`). Must also write a registry entry under `storage/character_db/` and an audit log. |
| Vision-assisted scoring (opt-in) | New `--use-vision` flag on the curator. Must default OFF and must not change the existing rubric — only **add** signals. |
| Auto-fetch of remote previews | Separate, opt-in script. The chatbot itself must continue to NOT fetch remote URLs for previews. |

---

## Verification

```powershell
# Compile + dry-run (works on an empty storage tree).
.\venv-core\Scripts\python.exe -m py_compile scripts\curate_image_storage.py
.\venv-core\Scripts\python.exe scripts\curate_image_storage.py --root storage --avg-vision-sec 5
```

The script always writes `summary.json` even when zero files are
scanned, so cron / CI runs always have an artifact to inspect.
