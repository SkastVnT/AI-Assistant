# AI-Assistant Scripts

Operational scripts for local development, service startup, deployment helpers,
and maintenance tasks. Run these paths from the repository root unless a script
states otherwise.

## Quick Start

```bash
bash app/scripts/setup-all.sh
bash app/scripts/start-all.sh
bash app/scripts/health-check-all.sh
bash app/scripts/expose-public.sh
```

```bat
app\scripts\setup-all.bat
app\scripts\start-all.bat
app\scripts\health-check-all.bat
```

## Common Scripts

| Script | Purpose |
|---|---|
| `start-all.*` | Start the local service set |
| `stop-all.*` | Stop local services |
| `health-check-all.*` | Check service health |
| `setup-all.*` | First-time setup helpers |
| `deploy-chatbot.*` | Chatbot deployment helper |
| `rollback-chatbot.*` | Chatbot rollback helper |
| `scan_lora_inventory.py` | Build `app/storage/lora_inventory.json` |
| `curate_image_storage.py` | Inspect generated image storage |
| `validate_lora_registry.py` | Validate `app/configs_vps/lora_registry.yaml` |
| `check_system.py` | Local environment and requirements check |

## Notes

- Scripts were consolidated under `app/scripts/` during the repo cleanup.
- Root `menu.bat` and `menu.sh` launchers are not present in this layout.
- Generated logs, caches, local binaries, and runtime outputs should stay out of Git.
