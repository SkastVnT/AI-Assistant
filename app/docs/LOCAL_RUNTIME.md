# Local Runtime Data

Local runtime data should stay out of Git. Use `.local/` as the shared home for manually downloaded binaries, scratch files, tool caches, and machine-specific artifacts.

## Preferred Local Layout

```text
.local/
  bin/        local executables such as cloudflared
  cache/      tool and provider caches
  tmp/        disposable scratch files
  exports/    ad-hoc local exports
```

## Compatibility Paths

Some existing code and scripts still read or write these paths directly:

| Path | Status | Notes |
|---|---|---|
| `app/storage/` | ignored except `.gitkeep` and `app/storage/character_db/*.json` | Image pipeline outputs, metadata, references, and cache data |
| `logs/` | ignored | Service logs and tunnel output |
| `local_data/` | ignored | Legacy local database/cache data |
| `outputs/` | ignored | Generated output folder |
| `ComfyUI/input/`, `ComfyUI/output/`, `ComfyUI/models/` | ignored | Local ComfyUI runtime data |
| `undefined/` | ignored if recreated | Legacy tool/cache spillover; prefer `.local/cache/` |

Do not move these compatibility paths unless the code that references them is updated and tested.

## Cloudflared

`cloudflared.exe` is not tracked. Keep a local copy on `PATH` or under `.local/bin/`.
