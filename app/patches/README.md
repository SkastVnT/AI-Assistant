# Local patches for vendored submodules

`ComfyUI/` is a submodule pinned to upstream **v0.7.0**
(`comfyanonymous/ComfyUI`). It is *not* a fork — local fixes live here as
patch files and are applied on top after checkout.

## Applying

```bash
# Windows PowerShell / Git Bash / Linux
python app/scripts/apply_patches.py
```

Idempotent: already-applied patches are detected and skipped.

## Patch list

| Patch | Target | What it does |
|---|---|---|
| `0001-torch-compiler-is-compiling-hasattr-guard.patch` | `ComfyUI/comfy/ops.py`, `ComfyUI/comfy/model_management.py` | Guards `torch.compiler.is_compiling()` behind `hasattr`. `ComfyUI/requirements.txt` declares a bare `torch` with no lower bound; on torch < 2.1 the attribute does not exist and both call sites raise `AttributeError`. |

## When bumping the ComfyUI pin

1. `git -C ComfyUI fetch --tags && git -C ComfyUI checkout vX.Y.Z`
2. `python app/scripts/apply_patches.py` — if a patch no longer applies, check
   whether upstream fixed it. If so, delete the patch and this table row.
3. Commit the new submodule SHA.

Do not run repo-wide formatters over `ComfyUI/`. `ruff.toml` already excludes
it; black does not read that file, so scope black explicitly. A repo-wide
black run in commit `2117e4a` previously reformatted 391 vendored files,
which is why this submodule conversion was needed.
