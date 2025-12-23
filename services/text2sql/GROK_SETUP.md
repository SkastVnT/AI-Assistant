# GROK API Setup for Text2SQL Service

## 🎯 Overview
Text2SQL service now uses **GROK-3 (xAI)** as the **default model** instead of Gemini to avoid quota limitations.

## 🔑 Setup Instructions

### 1. Get GROK API Key (FREE)
Visit [x.ai](https://x.ai) to get your FREE GROK API key.

### 2. Add to `.env` file
Add the following line to your `.env` file in the root directory:

```env
# GROK API (xAI - FREE tier with better SQL generation)
GROK_API_KEY=your-grok-api-key-here
```

### 3. Verify Setup
Run the Text2SQL service and check that GROK is listed as the default model:

```bash
cd services/text2sql
python app_simple.py
```

You should see:
```
🤖 Default Model: GROK-3 (xAI - FREE)
🔄 Available Models: grok, gemini, openai, deepseek
```

## 🚀 Usage

### Using GROK (Default)
No need to specify model - GROK is used by default:

```json
{
  "message": "Show all users",
  "db_type": "clickhouse"
}
```

### Using Other Models
Specify the model explicitly:

```json
{
  "message": "Show all users",
  "model": "gemini",
  "db_type": "clickhouse"
}
```

Available models:
- `grok` (default) - FREE, no quota limits
- `gemini` - FREE but has quota limits
- `openai` - Requires OpenAI API key
- `deepseek` - Requires DeepSeek API key

## ✨ Why GROK?

1. **FREE Tier** - No cost for usage
2. **No Quota Limits** - Unlike Gemini which frequently hits quota
3. **Better SQL Generation** - More accurate SQL queries
4. **Fast Response** - Quick generation times
5. **NSFW Support** - Can handle sensitive queries if needed

## 🔍 Health Check

Check which APIs are configured:

```bash
curl http://localhost:5002/health
```

Response:
```json
{
  "status": "ok",
  "service": "Text2SQL",
  "api_configured": {
    "grok": true,
    "gemini": true,
    "openai": false,
    "deepseek": true
  },
  "default_model": "grok",
  "schemas_loaded": 0
}
```

## 📝 Notes

- If GROK API key is not configured, the service will fall back to other available models
- You can still use Gemini, OpenAI, or DeepSeek by specifying the model parameter
- GROK API is provided by xAI (Elon Musk's AI company)
- The FREE tier is generous and suitable for most use cases

## 🐛 Troubleshooting

### "GROK API key not configured"
Make sure you've added `GROK_API_KEY` to your `.env` file.

### Service not starting
Check if the `.env` file is in the root directory, not in `services/text2sql/`.

### Still using Gemini
Verify that you're not explicitly specifying `"model": "gemini"` in your requests.
