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
  pyproject.toml          ruff + pytest + bandit config
  conftest.py
  docker-compose.yml
  .gitignore / .gitattributes / .gitmodules
  .gitnexusignore
  .pre-commit-config.yaml
  app/
    config/               shared config + env loading
    configs_vps/          pipeline / model / lora YAML
    docker/
    docs/
    electron/             desktop shell
    image_pipeline/       anime_pipeline (live) + deferred subtrees
    requirements/         profiles + freeze snapshots
    patches/              local patches applied to the ComfyUI submodule
    scripts/              service + repo scripts (openapi.js, apply_patches.py)
    src/
    storage/
  services/
    chatbot/              Flask app, routes, tests
    clip-embed/
    edit-image/           ComfyUI integration (submodule custom_nodes)
    mcp-server/
    stable-diffusion/
  ComfyUI/                submodule, pinned upstream v0.7.0
  private/                submodule, archived material
  .github/                workflows + skills
  .claude/  .agents/      agent skill definitions (Claude Code / Codex)
```

`ComfyUI/` intentionally remains at the repository root as the primary runtime.
`services/edit-image/ComfyUI/` is a separate edit-service runtime. The former
tracked `app/ComfyUI/` mirror was removed because it duplicated the root tree.

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
