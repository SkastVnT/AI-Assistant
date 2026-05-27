# Video Generation

Video generation is exposed through chatbot routes under `/api/video/*`.

| Route | Purpose |
|---|---|
| `POST /api/video/generate` | Start an async generation request |
| `POST /api/video/generate-sync` | Run a synchronous generation request where supported |
| `GET /api/video/status/{id}` | Check job status |
| `GET /api/video/download/{id}` | Download generated output |
| `GET /api/video/list` | List video jobs |

OpenAI/Sora-compatible features require `OPENAI_API_KEY`. Generated video files belong in runtime storage and should not be committed.
