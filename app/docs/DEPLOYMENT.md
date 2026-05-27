# Deployment

## Local Docker

The root `docker-compose.yml` is the primary compatibility entrypoint for local Docker usage:

```bash
docker compose up -d
docker compose --profile tools up -d
docker compose --profile hermes up -d
docker compose --profile all up -d
docker compose config
```

The compose file starts MongoDB and the chatbot by default. Optional sidecars are controlled with Docker profiles. GPU-heavy image services are not included in the root compose file and should be run with their existing service-specific launchers.

## Local Services

Use the scripts in `app/scripts/` for Windows and shell-based service startup:

```powershell
app\scripts\start-chatbot.bat
app\scripts\start-stable-diffusion.bat
app\scripts\start-edit-image.bat
```

```bash
bash app/scripts/start-chatbot.sh
bash app/scripts/start-stable-diffusion.sh
bash app/scripts/start-edit-image.sh
```

## Environment

Copy the example files before starting services:

```powershell
copy app\config\.env.example app\config\.env
copy services\chatbot\.env.example services\chatbot\.env
```

Keep real secrets and local machine paths out of Git.

## Cloudflared

`cloudflared.exe` is a local binary and is not tracked in Git. Install it locally when needed:

- Windows: download Cloudflare Tunnel from Cloudflare's release page and place it on `PATH`, or keep a local copy under `.local/bin/`.
- Linux: install through the Cloudflare package repository or download the release binary.

The helper scripts expect the `cloudflared` command or a local executable to be available at runtime.

## Runtime Data

Do not commit generated outputs, logs, local databases, model binaries, ComfyUI input/output files, or secrets. Track only source code, docs, examples, and explicit seed data.
