# API Reference

The chatbot service is the main HTTP surface. Paths below are served by `services/chatbot/` unless noted otherwise.

## Chat And Conversations

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/chat/stream` | Primary SSE chat endpoint |
| `POST` | `/chat/async` | Async chat request path where enabled |
| `GET` | `/c/{conversation_id}` | Open a conversation by id |
| `GET` | `/conversations` | List conversations |
| `DELETE` | `/conversations/{id}` | Delete a conversation |
| `POST` | `/conversations/new` | Create a conversation |
| `POST` | `/conversations/{id}/switch` | Switch active conversation |
| `POST` | `/conversations/{id}/archive` | Archive a conversation |
| `POST` | `/clear` | Clear current session |
| `POST` | `/api/generate-title` | Generate a conversation title |

## Skills

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/skills` | List skills |
| `GET` | `/api/skills/{id}` | Get one skill |
| `GET` | `/api/skills/active` | Get active skill |
| `POST` | `/api/skills/activate` | Activate a skill |
| `POST` | `/api/skills/deactivate` | Deactivate a skill |

## Image And Video

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/image-gen/generate` | Generate an image |
| `POST` | `/api/image-gen/stream` | Stream image generation progress |
| `POST` | `/api/image-gen/edit` | Edit an image |
| `POST` | `/api/video/generate` | Start video generation |
| `POST` | `/api/video/generate-sync` | Synchronous video generation path |
| `GET` | `/api/video/status/{id}` | Video job status |
| `GET` | `/api/video/download/{id}` | Download video output |
| `GET` | `/api/video/list` | List video jobs |
| `GET` | `/api/reasoning-image-gen/status` | Reasoning pipeline status |
| `POST` | `/api/reasoning-image-gen/generate` | Reasoning image pipeline generation |

## MCP, Memory, Health

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/memory/save` | Save memory |
| `GET` | `/memory/list` | List memories |
| `GET` | `/memory/get/{id}` | Get memory |
| `PUT` | `/memory/update/{id}` | Update memory |
| `DELETE` | `/memory/delete/{id}` | Delete memory |
| `POST` | `/memory/search` | Search memory |
| `POST` | `/api/mcp/enable` | Enable MCP integration |
| `POST` | `/api/mcp/disable` | Disable MCP integration |
| `GET` | `/api/mcp/status` | MCP status |
| `GET` | `/health` | Service health |
| `GET` | `/api/health/databases` | Database health |

See `route-contract.md` for additional route details and compatibility notes.
