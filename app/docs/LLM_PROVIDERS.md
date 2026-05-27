# LLM Providers

LLM provider configuration is read from environment variables. Keep secrets in local `.env` files and out of Git.

| Provider | Primary env var | Notes |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | Chat, vision, and video-related features |
| xAI / Grok | `GROK_API_KEY` | Hosted chat provider |
| DeepSeek | `DEEPSEEK_API_KEY` | Hosted chat provider |
| Gemini | `GEMINI_API_KEY` or numbered variants | Vision-capable provider where enabled |
| Qwen | `QWEN_API_KEY` | Hosted chat provider |
| OpenRouter | `OPENROUTER_API_KEY` | Router for multiple hosted models |
| StepFun | `STEPFUN_API_KEY` | Chat and image-related integrations |
| Hugging Face | `HUGGINGFACE_API_KEY` or `HUGGINGFACE_TOKEN` | Model downloads and optional model calls |
| Ollama | local service | Local models selected by runtime configuration |

Provider routing lives under `services/chatbot/core/`. Update docs and tests when changing fallback order, env names, or response contracts.
