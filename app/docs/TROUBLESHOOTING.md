# Troubleshooting

## Chatbot Does Not Start

- Confirm Python dependencies are installed from `requirements-core.txt`.
- Confirm `app/config/.env` exists and contains at least one usable LLM provider key.
- Run from the repository root: `python services/chatbot/run.py`.

## Docker Compose Fails

- Validate configuration with `docker compose config`.
- Confirm `app/config/.env` and `services/chatbot/.env` exist when starting the chatbot container.
- Run GPU-heavy image services with their service-specific launchers rather than the root compose file.

## Cloudflared Is Missing

Install Cloudflare Tunnel locally and make `cloudflared` available on `PATH`. The repository does not track `cloudflared.exe`; local copies can live under `.local/bin/`.

## Generated Files Appear In Git Status

Check `.gitignore` first. New ad-hoc local artifacts should live under `.local/`. Existing compatibility runtime paths such as `app/storage/`, `logs/`, `local_data/`, `ComfyUI/output/`, and service-specific output directories are ignored.

## Tests Cannot Import Dependencies

Do not install GPU/ComfyUI dependencies unless needed. Use the core profile for chatbot and MCP checks:

```powershell
.\venv-core\Scripts\Activate.ps1
pip install -r requirements-core.txt
pytest
```
