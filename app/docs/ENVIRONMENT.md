# Environment

Environment files are local configuration and must not be committed. Use examples as templates.

## Files

| File | Purpose |
|---|---|
| `app/config/.env.example` | Shared template for core services |
| `app/config/.env` | Local shared config |
| `services/chatbot/.env.example` | Chatbot-local template |
| `services/chatbot/.env` | Chatbot-local overrides |
| `app/rag/.env.example` | RAG template |

## Common Variables

| Area | Variables |
|---|---|
| LLMs | `OPENAI_API_KEY`, `GROK_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `QWEN_API_KEY`, `OPENROUTER_API_KEY`, `STEPFUN_API_KEY` |
| Search | `SERPAPI_API_KEY`, `GOOGLE_SEARCH_API_KEY`, `GOOGLE_CSE_ID`, `SAUCENAO_API_KEY` |
| Image providers | `FAL_API_KEY`, `BFL_API_KEY`, `REPLICATE_API_KEY`, `TOGETHER_API_KEY` |
| Database | `MONGODB_URI`, `MONGODB_DB_NAME` |
| Runtime flags | `AUTO_START_IMAGE_SERVICES`, `REASONING_PIPELINE`, `HERMES_ENABLED`, `LAST30DAYS_ENABLED`, `CHARACTER_SELECT_ENABLED` |

The shared loader is `services/shared_env.py`. Avoid adding new independent `load_dotenv` calls.
