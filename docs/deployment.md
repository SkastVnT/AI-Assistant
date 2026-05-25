# Deployment Guide — AI-Assistant

## Docker setup (recommended for chatbot + MongoDB)

### Prerequisites
- Docker Engine 24+ and Docker Compose v2
- API keys in `app/config/.env` (see `.env.example`)
- Service-local keys in `services/chatbot/.env` (optional; for FAL, StepFun, etc.)

### Start core stack

```bash
docker compose up -d                        # MongoDB + ChatBot
docker compose logs -f chatbot              # tail logs
curl http://localhost:5000/api/v1/health    # verify
```

### Optional profiles

```bash
docker compose --profile tools up -d       # + last30days social-research sidecar
docker compose --profile hermes up -d      # + Hermes Agent sidecar (port 8080)
docker compose --profile character-select up -d  # + SAA character picker (port 51028)
docker compose --profile all up -d         # all of the above
```

> **Not in docker-compose:** Stable Diffusion (7861) and Edit Image/ComfyUI (8100) require GPU
> access and `venv-image`. Run them separately on the host.

---

## Building the Docker image

The build context is the repo root so the Dockerfile can access `app/requirements/profile_core_services.txt`:

```bash
docker build -t ai-assistant-chatbot:dev -f services/chatbot/Dockerfile .
```

The image installs only `profile_core_services.txt` — no torch, no image-stack packages.

---

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `FLASK_SECRET_KEY` | **Yes (non-dev)** | — | Required outside `env=dev` and `TESTING=true` |
| `MONGODB_URI` | No | `mongodb://localhost:27017` | Overridden by compose |
| `FLASK_PORT` | No | `5000` | Container port |
| `MONGO_ROOT_PASSWORD` | No | `changeme` | **Must override in non-dev environments** |

Full variable reference: [README.md § Biến môi trường](../README.md)

---

## Non-root user

The `chatbot` Docker image runs as `appuser` (uid 1000). Volumes mapped to the container must be
writable by uid 1000. If you mount host directories:

```bash
chown -R 1000:1000 ./storage ./logs
```

---

## Health checks

| Service | URL |
|---|---|
| ChatBot | `GET http://localhost:5000/api/v1/health` |
| MongoDB | `mongosh --eval "db.adminCommand('ping')"` |

Compose readiness:
```bash
docker compose ps
```

---

## Stopping and cleaning up

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers + delete volumes (destroys DB data)
docker image prune -f        # remove dangling images
```

---

## Local development (no Docker)

See [onboarding-dev.md](onboarding-dev.md) for the full venv-based workflow.
