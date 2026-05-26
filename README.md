# AI-Assistant

AI-Assistant is a local-first AI workspace that combines a Python chatbot service, multi-provider LLM routing, RAG, MCP tools, image and video generation, ComfyUI/edit-image integration, and an Electron desktop shell.

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
| Image pipeline | `image_pipeline/` | Local reasoning/anime pipeline modules |
| ComfyUI/edit image | `ComfyUI/`, `services/edit-image/` | Local image workflow runtimes and integrations |
| RAG | `rag/` | API, worker, libraries, tests, and compose file |
| Desktop | `desktop/electron/` | Electron wrapper and installer workflow |
| Deployment | `docker-compose.yml`, `app/docker/` | Local Docker entrypoint and supporting assets |

## Quick Start

### Chatbot

```powershell
python -m venv venv-core
.\venv-core\Scripts\Activate.ps1
pip install -r requirements-core.txt
copy app\config\.env.example app\config\.env
copy services\chatbot\.env.example services\chatbot\.env
python services\chatbot\run.py
```

Open `http://127.0.0.1:5000`.

### Desktop

```powershell
cd desktop\electron
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
| RAG API | service config | `rag/apps/api/` | Uses `rag/docker-compose.yml` for local infra |
| Electron | app window | `desktop/electron/` | Desktop shell around the chatbot |

## Development Commands

```powershell
python -m compileall services app image_pipeline rag
pytest
cd desktop\electron
npm run dev
docker compose config
```

Run GPU/model checks only on machines with the required local model files.

## Documentation

- [Docs index](docs/README.md)
- [API reference](docs/API_REFERENCE.md)
- [Environment variables](docs/ENVIRONMENT.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Local runtime data](docs/LOCAL_RUNTIME.md)
- [LLM providers](docs/LLM_PROVIDERS.md)
- [Image generation](docs/IMAGE_GENERATION.md)
- [Video generation](docs/VIDEO_GENERATION.md)
- [MCP server](docs/MCP_SERVER.md)
- [Repository structure](docs/REPO_STRUCTURE.md)
- [Agent guidelines](.claude/skills/repo-guidelines/SKILL.md)

## License

This repository is licensed under the terms in [LICENSE](LICENSE).
