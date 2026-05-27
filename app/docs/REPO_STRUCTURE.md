# Repository Structure

## Current Root Problems

- Runtime/data folders, app modules, docs, scripts, and deployment files were mixed at the repository root.
- Agent instructions previously lived at root instead of the `.claude/skills/` area.
- Root-level `storage/`, `image_pipeline/`, `rag/`, `configs/`, `docs/`, `scripts/`, and `desktop/electron/` made the GitHub landing view harder to scan.
- Some generated runtime data and local binaries had historically been easy to commit by accident.

## Target Structure

```text
.
  README.md
  LICENSE
  .gitignore
  .gitmodules
  package.json / package-lock.json
  requirements*.txt
  ruff.toml
  app/
    character_select_stand_alone_app-main/
    configs_vps/
    docs/
    electron/
    image_pipeline/
    rag/
    scripts/
    storage/
  services/
  ComfyUI/
  .github/
  .claude/
  docker-compose.yml
  private/
```

`ComfyUI/` intentionally remains at the repository root in this pass. This checkout already has both `ComfyUI/` and `app/ComfyUI/` tracked, so moving the root runtime would risk overwriting or confusing ComfyUI internals.

## Files Moved

| Old path | New path | Notes |
|---|---|---|
| `character_select_stand_alone_app-main/` | `app/character_select_stand_alone_app-main/` | SAA character picker sidecar |
| `image_pipeline/` | `app/image_pipeline/` | Import compatibility is handled by adding `app/` to chatbot startup paths |
| `rag/` | `app/rag/` | RAG workflow and docs references updated |
| `docs/` | `app/docs/` | Root README links now point to `app/docs/...` |
| `scripts/*` | `app/scripts/*` | Root scripts merged into the existing scripts directory |
| `storage/` | `app/storage/` | Generated content ignored; seed character DB remains tracked |
| `configs/` | `app/configs_vps/` | VPS/model YAML config location |
| `desktop/electron/` | `app/electron/` | Electron workflow and docs updated |
| `AGENTS.md` | `.claude/skills/repo-guidelines/AGENTS.md` | Repository guidance for coding agents |
| `CLAUDE.md` | `.claude/skills/repo-guidelines/CLAUDE.md` | Claude-specific guidance |

## Compatibility Notes

- Root `docker-compose.yml` remains in place so existing `docker compose` commands continue to work.
- Root requirements files remain because existing install commands and packaging workflows reference them.
- Root package files remain because the root workspace currently declares GitNexus tooling.
- `ComfyUI/` remains at root for this pass; path helpers default `COMFYUI_DIR` there unless overridden.
- `app/storage/character_db/*.json` remains tracked as seed registry data. Generated storage outputs and benchmark runs are ignored.
- No root `AGENTS.md` or `CLAUDE.md` stub was kept. Maintained agent guidance now lives under `.claude/skills/repo-guidelines/`.

## Import And Path Handling

- `services/chatbot/core/project_paths.py` defines canonical repo paths for chatbot integrations.
- Chatbot entrypoints add `app/` to `sys.path` so existing imports like `from image_pipeline...` continue to work.
- `app/image_pipeline/paths.py` centralizes image-pipeline filesystem paths after the move.
- Public API URLs such as `/storage/images/<filename>` are unchanged; only filesystem storage paths moved.

## Local Runtime Policy

- Use `app/storage/` for local generated image pipeline data.
- Keep local binaries and scratch files under `.local/`.
- Do not commit ComfyUI models, input/output files, generated images/videos, logs, local databases, or secrets.
