# Anime Pipeline — Migration Notes

## New Dedicated Blueprint (v2)

### What Changed

A new dedicated Flask blueprint and FastAPI router were created for the anime pipeline:

| Component | Path | New |
|-----------|------|-----|
| Flask blueprint | `services/chatbot/routes/anime_pipeline.py` | Yes |
| FastAPI router | `services/chatbot/fastapi_app/routers/anime_pipeline.py` | Yes |
| Service layer | `services/chatbot/core/anime_pipeline_service.py` | Yes |
| Frontend module | `services/chatbot/static/js/modules/anime-pipeline.js` | Yes |
| CSS styles | `services/chatbot/static/css/anime-pipeline.css` | Yes |

### Existing Endpoint

The existing `/api/image-gen/anime-pipeline` endpoint in `routes/image_gen.py` remains **unchanged**. It continues to work as before. The new blueprint provides a full-featured alternative with:

- Dedicated SSE streaming (`/api/anime-pipeline/stream`)
- Health check endpoint (`/api/anime-pipeline/health`)
- Blocking generation (`/api/anime-pipeline/generate`)
- Rate limiting (5 jobs / 120s window)
- Stage-level progress events

### Feature Flag

The `IMAGE_PIPELINE_V2` environment variable gates availability. When unset or false, the health endpoint reports the pipeline as unavailable and generation endpoints return 503.

### Registration Points

- **Flask**: `anime_pipeline_bp` registered in `chatbot_main.py` after `hermes_bp`
- **FastAPI**: Router included in `fastapi_app/__init__.py`
- **Frontend**: Button added to `templates/index.html` topbar, wired in `static/js/main.js`

### No Breaking Changes

- No existing routes, schemas, or response contracts were modified
- No existing image generation flows were touched
- The existing image_gen blueprint is unaffected
- Frontend: the anime pipeline button is hidden when the feature flag is off

### Environment Variables Added

| Variable | Purpose | Default |
|----------|---------|---------|
| `IMAGE_PIPELINE_V2` | Feature flag to enable pipeline | `false` |
| `ANIME_PIPELINE_VRAM_PROFILE` | VRAM management profile | `normalvram` |
| `ANIME_PIPELINE_COMFYUI_URL` | Override ComfyUI URL | `http://localhost:8188` |
| `ANIME_PIPELINE_DEBUG` | Enable debug output saving | `false` |
| `ANIME_PIPELINE_COMPOSITION_MODEL` | Override composition checkpoint | (from YAML) |
| `ANIME_PIPELINE_BEAUTY_MODEL` | Override beauty checkpoint | (from YAML) |
| `ANIME_PIPELINE_QUALITY_THRESHOLD` | Override critique threshold | `0.70` |
| `ANIME_PIPELINE_MAX_REFINE_ROUNDS` | Override max critique retries | `2` |

### Dependencies

No new Python packages were added. The pipeline uses:
- `httpx` (already in `venv-core`)
- `pyyaml` (already in `venv-core`)
- Standard library only for all agent logic
