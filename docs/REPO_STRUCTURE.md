# Repository Structure

## Current Root Problems

- Root-level agent instructions were mixed with user-facing project files.
- A local `cloudflared.exe` binary and a second copy under `app/config/` were tracked.
- Runtime logs, a local ComfyUI database, and generated storage benchmark output were tracked.
- Long README content mixed quick start, API reference, provider matrices, deployment notes, and troubleshooting.
- Root-level package and requirements files are necessary today, but need clear compatibility notes.

## Conservative Root After Cleanup

```text
.
  README.md
  LICENSE
  .gitignore
  .gitmodules
  package.json / package-lock.json
  requirements*.txt
  app/
  services/
  image_pipeline/
  rag/
  desktop/
  configs/
  docs/
  scripts/
  .github/
  .claude/
  docker-compose.yml
  .gitnexusignore
  .local/                              ignored local runtime umbrella
  ComfyUI/                              legacy local runtime, not moved
  character_select_stand_alone_app-main/ sidecar app, not moved
  private/                              submodule
  storage/                              .gitkeep files plus seed registry data
```

The root still contains a few runtime-owned or submodule-like directories because moving them would be higher risk than this cleanup allows. New local-only binaries, caches, and scratch files should go under `.local/`.

## Files Moved

| Old path | New path | Notes |
|---|---|---|
| `AGENTS.md` | `.claude/skills/repo-guidelines/AGENTS.md` | Repository guidance for coding agents |
| `CLAUDE.md` | `.claude/skills/repo-guidelines/CLAUDE.md` | Claude-specific guidance |
| `docs/deployment.md` | `docs/DEPLOYMENT.md` | Match the docs index and README link |

No root `Dockerfile.vps` or `docker-compose.vps.yml` file exists in this checkout, so no VPS Docker file was moved. The root `docker-compose.yml` remains in place for compatibility.

## Files Removed From Tracking

| Path | Reason |
|---|---|
| `cloudflared.exe` | Local Cloudflare Tunnel binary |
| `app/config/cloudflared.exe` | Local Cloudflare Tunnel binary |
| `app/logs/cloudflare_err.txt` | Generated tunnel log |
| `app/logs/cloudflare_out.txt` | Generated tunnel log |
| `app/logs/public_urls.json` | Generated tunnel output |
| `services/edit-image/ComfyUI/user/comfyui.db` | Local ComfyUI database |
| `storage/metadata/benchmark/` | Generated benchmark output |

## Local-Only Files Moved

These files were moved on the local machine only; they remain ignored and are not part of Git:

| Old path | New path |
|---|---|
| `cloudflared.exe` | `.local/bin/cloudflared.exe` |
| `app/config/cloudflared.exe` | `.local/bin/cloudflared-app-config.exe` |
| `undefined/` | `.local/cache/undefined/` |

## Compatibility Notes

- Root `docker-compose.yml` remains in place so existing `docker compose` commands continue to work.
- Root requirements files remain because existing install commands and packaging workflows reference them.
- Root package files remain because the root workspace currently declares GitNexus tooling.
- `storage/character_db/*.json` remains tracked as seed registry data. Generated storage outputs and benchmark runs are ignored.
- `cloudflared.exe` can remain on a developer machine, preferably on `PATH` or under `.local/bin/`, but it is ignored and no longer tracked.
- No root `AGENTS.md` or `CLAUDE.md` stub was kept. Maintained agent guidance now lives under `.claude/skills/repo-guidelines/`.
