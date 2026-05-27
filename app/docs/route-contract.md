# Route Contract â€” AI-Assistant Chatbot

This document is the authoritative reference for the chatbot HTTP surface.
It is generated from `chatbot_main.py` (inline routes) and the blueprints in `routes/`.

The regression test that guards this contract is `tests/test_route_contract.py`.

---

## Route registration pattern

Routes are registered in two ways:

1. **Inline on `app`** â€” defined directly in `chatbot_main.py` with `@app.route(...)`.
2. **Blueprints** â€” imported and registered at the bottom of `chatbot_main.py` via individual
   `app.register_blueprint(...)` calls inside `try/except ImportError` blocks.

The `register_blueprints()` function in `routes/__init__.py` is a legacy helper and is
**not used** by the live app. Blueprint registration is done inline in `chatbot_main.py`.

---

## Inline routes (chatbot_main.py)

| Method | Path | Notes |
|---|---|---|
| GET | `/` | Root â€” create/restore session, redirect to `/c/<id>` |
| GET | `/c/<conversation_id>` | Conversation permalink (regex `[A-Za-z0-9_\-]{1,64}`) |
| GET | `/mobile` | Mobile redirect |
| GET | `/desktop` | Desktop redirect |
| POST | `/chat` | Legacy sync chat (v1 path) |
| POST | `/clear` | Clear session |
| GET | `/history` | Get session history |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/<id>` | Get conversation |
| DELETE | `/api/conversations/<id>` | Delete conversation |
| POST | `/api/conversations/<id>/archive` | Archive conversation |
| POST | `/api/conversations/new` | Create new conversation |
| GET | `/api/sd-health` | SD proxy health |
| GET | `/sd-api/status` | SD health alias |
| GET | `/api/sd-models` | SD model list |
| GET | `/sd-api/models` | SD models alias |
| GET | `/api/sd-loras` | SD LoRA list |
| GET | `/sd-api/loras` | SD LoRAs alias |
| GET | `/api/sd-vaes` | SD VAE list |
| GET | `/sd-api/vaes` | SD VAEs alias |
| GET | `/api/sd-samplers` | SD sampler list |
| GET | `/sd-api/samplers` | SD samplers alias |
| GET | `/api/sd/samplers` | SD samplers alias 2 |
| POST | `/api/sd-change-model` | SD change model |
| POST | `/api/sd/change-model` | SD change model alias |
| POST | `/api/generate-image` | SD txt2img |
| POST | `/sd-api/text2img` | SD txt2img alias |
| POST | `/api/img2img` | SD img2img |
| POST | `/sd-api/img2img` | SD img2img alias |
| POST | `/api/img2img-advanced` | Advanced img2img |
| POST | `/api/extract-anime-features` | SD interrogate |
| POST | `/sd-api/interrogate` | SD interrogate alias |
| POST | `/api/extract-anime-features-multi` | Multi-model feature extraction |
| POST | `/api/generate-prompt-grok` | Prompt generation (Grok) |
| POST | `/api/generate-prompt` | Prompt generation (universal) |
| POST | `/api/share-image-imgbb` | Upload image to ImgBB |
| POST | `/api/save-generated-image` | Save generated image to storage |
| POST | `/api/save-image` | Save image to storage |
| GET | `/storage/images/<filename>` | Serve stored image |
| GET | `/static/Storage/Image_Gen/<filename>` | Serve generated image |
| GET | `/api/list-images` | List stored images |
| DELETE | `/api/delete-image/<filename>` | Delete stored image |
| POST | `/api/sd-interrupt` | Interrupt SD generation |
| GET | `/api/local-models-status` | Local model status |
| POST | `/api/unload-model` | Unload local model |
| POST | `/api/memory/save` | Save memory entry |
| GET | `/api/memory/list` | List memory entries |
| GET | `/api/memory/get/<id>` | Get memory entry |
| DELETE | `/api/memory/delete/<id>` | Delete memory entry |
| PUT | `/api/memory/update/<id>` | Update memory entry |
| POST | `/api/mcp/enable` | Enable MCP |
| POST | `/api/mcp/disable` | Disable MCP |
| POST | `/api/mcp/add-folder` | Add MCP folder |
| POST | `/api/mcp/remove-folder` | Remove MCP folder |
| GET | `/api/mcp/list-files` | List MCP files |
| GET | `/api/mcp/search-files` | Search MCP files |
| GET | `/api/mcp/read-file` | Read MCP file |
| POST | `/api/mcp/ocr-extract` | OCR via MCP |
| GET | `/api/mcp/grep` | Grep MCP files |
| POST | `/api/mcp/warm-cache` | Warm MCP cache |
| GET | `/api/mcp/status` | MCP status |
| POST | `/api/mcp/fetch-url` | Fetch URL via MCP |
| POST | `/api/mcp/upload-file` | Upload file to MCP |
| GET | `/api/anime-pipeline/images/<path>` | Serve anime pipeline images |
| POST | `/api/extract-file-text` | Extract text from file |
| POST | `/api/generate-title` | Generate conversation title |
| POST | `/api/chat/suggestions` | Chat suggestions |
| GET | `/api/db-health` | Database health |
| POST | `/api/v1/chat` | v1 chat API |
| POST | `/api/v1/context` | v1 context API |
| GET | `/api/v1/providers` | v1 provider list |
| GET | `/api/v1/health` | v1 health check |

---

## Blueprint routes

| Blueprint | Module | URL prefix | Key routes |
|---|---|---|---|
| `stream_bp` | `routes/stream.py` | (none) | `POST /chat/stream` (primary SSE), `POST /chat/async` |
| `async_bp` | `routes/async_routes.py` | (none) | `POST /chat/async` (async variant) |
| `conversations_bp` | `routes/conversations.py` | (none) | `/conversations/*`, `/new` |
| `memory_bp` | `routes/memory.py` | `/memory` | `/memory/{save,list,get,update,delete,search}` |
| `images_bp` | `routes/images.py` | (none) | `/images/*` |
| `mcp_bp` | `routes/mcp.py` | `/api/mcp` | (overlaps with inline MCP routes) |
| `sd_bp` | `routes/stable_diffusion.py` | (none) | SD proxy routes |
| `image_gen_bp` | `routes/image_gen.py` | (none) | `/api/image-gen/*` |
| `nano_banana_bp` | `routes/nano_banana.py` | (none) | Gemini image gen |
| `models_bp` | `routes/models.py` | (none) | `/health`, `/api/health/databases` |
| `skills_bp` | `routes/skills.py` | (none) | `/api/skills/*` |
| `last30days_bp` | `routes/last30days.py` | (none) | `/api/tools/last30days` |
| `hermes_bp` | `routes/hermes.py` | (none) | `/api/hermes/chat` |
| `character_select_bp` | `routes/character_select.py` | (none) | `/api/character-select/*`, `/api/local-image-gen/*` |
| `reasoning_image_gen_bp` | `routes/reasoning_image_gen.py` | (none) | `/api/reasoning-image-gen/*` (REASONING_PIPELINE=true only) |
| `anime_pipeline_bp` | `routes/anime_pipeline.py` | (none) | `/api/anime-pipeline/*` |
| `characters_bp` | `routes/characters.py` | (none) | `/api/characters/*` |
| `jobs_bp` | `routes/jobs.py` | (none) | `/api/jobs/*` |
| `video_bp` | `routes/video.py` | (none) | `/api/video/*` |

---

## Primary endpoint

```
POST /chat/stream   (stream_bp â€” routes/stream.py)
```

This is the canonical chat endpoint. All UI interactions go through here. It returns
Server-Sent Events (SSE) with `Content-Type: text/event-stream`.

The legacy `POST /chat` route (inline in chatbot_main.py) is retained for backward
compatibility with older clients.

---

## Route contract rules

1. **Never remove** routes listed in the `tests/test_route_contract.py` assertions without
   updating both the test and this document.

2. **Never return 404** from a route that was previously returning 200/400/500. A 404 means
   the route is gone from the URL map.

3. **Blueprint URL conflicts**: `memory_bp` (prefix `/memory`) and the inline `/api/memory/*`
   routes are separate. Both sets should remain registered until the inline routes are removed.

4. **Conditional routes**: `reasoning_image_gen_bp` is only registered when
   `REASONING_PIPELINE=true`. This is intentional â€” the route should NOT appear in the URL map
   when the flag is off.

5. **Auth blueprint**: `auth_bp` import is attempted but expected to fail gracefully (it was
   removed in May 2026). The `try/except ImportError` wrapper handles this.
