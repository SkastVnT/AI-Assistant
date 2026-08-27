# AI-Assistant

AI-Assistant is a local-first AI workspace that combines a Python chatbot service, multi-provider LLM routing, RAG, MCP tools, image and video generation, ComfyUI/edit-image integration, and an Electron desktop shell.

**Version:** 0.2.0 — Thinking-with-Images chat bridge (phase 1a) + anime pipeline ControlNet/critique fixes.

## Capabilities

- Streaming chatbot UI with conversations, memory, web search, OCR, STT, and MCP file tools.
- Multi-provider chat across hosted and local LLM providers.
- Image generation through hosted providers and local ComfyUI/Stable Diffusion paths.
- Video generation through OpenAI Sora-compatible routes.
- RAG services, optional sidecars, Docker support, and an Electron desktop app.

## Architecture

| Area | Path | Notes |
|---|---|---|
| Chatbot service | `services/chatbot/` | Flask monolith, SSE streaming, routes, skills, memory, image/video proxies |
| Shared service code | `services/shared_env.py`, `app/src/` | Shared environment loading, cache, database, health, security helpers |
| MCP server | `services/mcp-server/` | FastMCP stdio server used by the chatbot |
| Image pipeline | `app/image_pipeline/` | Local reasoning/anime pipeline modules |
| ComfyUI/edit image | `ComfyUI/` (submodule), `services/edit-image/` | Local image workflow runtimes and integrations |
| RAG | `app/rag/` | API, worker, libraries, tests, and compose file |
| Desktop | `app/electron/` | Electron wrapper and installer workflow |
| Deployment | `docker-compose.yml`, `app/docker/` | Local Docker entrypoint and supporting assets |

## Quick Start

### Chatbot (Windows)

```powershell
python -m venv venv-core
.\venv-core\Scripts\Activate.ps1
pip install -r app/requirements/freeze-venv-core.txt
copy app\config\.env.example app\config\.env
copy services\chatbot\.env.example services\chatbot\.env
python services\chatbot\run.py
```

### Chatbot (Linux / VPS)

> `app/requirements/freeze-venv-core.txt` is a Windows lock file — **do not use it on Linux**. Use the cross-platform profile instead.

```bash
python3 -m venv venv-core
source venv-core/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r app/requirements/profile_core_services.txt
cp app/config/.env.example app/config/.env
cp services/chatbot/.env.example services/chatbot/.env
python services/chatbot/run.py
```

> **Chatbot-only (lighter install):** skips the local audio and OCR stack
> (20 packages: faster-whisper, pyannote, librosa, paddleocr, PyMuPDF, ...).
>
> ```bash
> pip install -r app/requirements/profile_chatbot_minimal.txt
> ```

Open `http://127.0.0.1:5000`.

### Desktop

```powershell
cd app\electron
npm install
npm run dev
```

### Docker

```bash
docker compose up -d
docker compose --profile all up -d
docker compose config
```

The root `docker-compose.yml` remains the compatibility entrypoint for local Docker usage.

## Submodules

`ComfyUI/` and `private/` are submodules. After a fresh clone:

```bash
git submodule update --init --recursive
python scripts/apply_patches.py
```

`ComfyUI/` is pinned to upstream v0.7.0; `scripts/apply_patches.py` applies the
local fixes in `patches/` on top. See [patches/README.md](patches/README.md).

## Environment Setup

Copy examples before running local services:

```powershell
copy app\config\.env.example app\config\.env
copy services\chatbot\.env.example services\chatbot\.env
```

At least one LLM API key is required for hosted chat. Local image, video, and ComfyUI features also require local model files that are not tracked in Git. Keep ad-hoc local binaries, caches, and scratch files under `.local/`.

## Main Services

| Service | Default port | Entry point | Notes |
|---|---:|---|---|
| Chatbot | `5000` | `services/chatbot/run.py` | Primary UI/API service |
| MCP server | stdio | `services/mcp-server/server.py` | Started by clients, not an HTTP server |
| Stable Diffusion | `7861` | `services/stable-diffusion/` | Local image backend |
| Edit Image / ComfyUI | `8100` | `services/edit-image/` | ComfyUI-backed image editing |
| CLIP embed sidecar | `8200` | `services/clip-embed/server.py` | Optional image-RAG encoder (venv-image); off unless `RAG_IMAGE_ENABLED=true` |
| RAG API | service config | `app/rag/apps/api/` | Uses `app/rag/docker-compose.yml` for local infra |
| Electron | app window | `app/electron/` | Desktop shell around the chatbot |

## Development Commands

```powershell
python -m compileall services app
pytest
cd app\electron
npm run dev
docker compose config
```

Run GPU/model checks only on machines with the required local model files.

## Documentation

- [Docs index](app/docs/README.md)
- [API reference](app/docs/API_REFERENCE.md)
- [Environment variables](app/docs/ENVIRONMENT.md)
- [Deployment](app/docs/DEPLOYMENT.md)
- [Local runtime data](app/docs/LOCAL_RUNTIME.md)
- [LLM providers](app/docs/LLM_PROVIDERS.md)
- [Image generation](app/docs/IMAGE_GENERATION.md)
- [Video generation](app/docs/VIDEO_GENERATION.md)
- [MCP server](app/docs/MCP_SERVER.md)
- [Repository structure](app/docs/REPO_STRUCTURE.md)
- [Agent guidelines](.claude/skills/repo-guidelines/SKILL.md)

## License

This repository is licensed under the terms in [LICENSE](LICENSE).
