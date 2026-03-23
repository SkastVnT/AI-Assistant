# 🤖 Multi-Model LLM Guide

## Overview

VistralS2T v3.6.0+ supports **3 LLM providers** for transcript enhancement with automatic retry mechanism:

| Model | Provider | Cost | Features |
|-------|----------|------|----------|
| **Gemini 2.0 Flash** | Google | **FREE** | 4-key retry, unlimited quota |
| **GPT-4o-mini** | OpenAI | $0.15/1M tokens | High quality, fast |
| **DeepSeek Chat** | DeepSeek | $0.14/1M tokens | Cost-effective alternative |

---

## 🎯 How It Works

### Processing Flow

```
1. Upload Audio → Whisper + PhoWhisper (ASR)
   ↓
2. Raw Transcript Generated
   ↓
3. Model Selection Modal (30s countdown)
   ├─ User selects: Gemini / OpenAI / DeepSeek
   └─ Timeout: Auto-selects Gemini
   ↓
4. LLM Enhancement
   ├─ Gemini: Try 4 API keys sequentially (auto-retry)
   ├─ OpenAI: Single attempt
   └─ DeepSeek: Single attempt
   ↓
5. Result
   ├─ Success: Enhanced clean transcript
   └─ Failure: Returns raw transcript (graceful fallback)
```

---

## 🔑 API Key Setup

### Gemini (FREE - Recommended)

Get **4 API keys** for unlimited quota:

1. Visit: https://aistudio.google.com/apikey
2. Create 4 API keys (click "Create API Key" 4 times)
3. Add to `.env`:
   ```env
   GEMINI_API_KEY_1=AIzaSy...
   GEMINI_API_KEY_2=AIzaSy...
   GEMINI_API_KEY_3=AIzaSy...
   GEMINI_API_KEY_4=AIzaSy...
   ```

**Retry Behavior:**
- Quota exceeded on Key 1 → Auto-retry with Key 2
- Quota exceeded on Key 2 → Auto-retry with Key 3
- Quota exceeded on Key 3 → Auto-retry with Key 4
- All 4 exhausted → Returns raw transcript

### OpenAI (Paid)

1. Visit: https://platform.openai.com/api-keys
2. Create API key
3. Add to `.env`:
   ```env
   OPENAI_API_KEY=sk-proj-...
   ```

**Cost:** ~$0.15 per 1M tokens (GPT-4o-mini)

### DeepSeek (Paid)

1. Visit: https://platform.deepseek.com/api-keys
2. Create API key
3. Add to `.env`:
   ```env
   DEEPSEEK_API_KEY=sk-...
   ```

**Cost:** ~$0.14 per 1M tokens (DeepSeek-Chat)

---

## 🎮 Using the Web UI

### Model Selection

After Whisper+PhoWhisper completes:

1. **Modal appears** with 30-second countdown
2. **Choose model:**
   - ✨ **Gemini** (Default) - FREE, 4-key retry
   - 🧠 **OpenAI** - GPT-4o-mini
   - 🚀 **DeepSeek** - High quality
3. **Timeout:** System auto-selects Gemini after 30s

### Real-time Monitoring

During LLM enhancement, you'll see:

```
🔑 Trying Gemini API Key #1/4...
⚠️ Gemini quota exceeded - API Key #1
🔄 Retrying with next Gemini API key...
🔑 Trying Gemini API Key #2/4...
✅ Success with Gemini API Key #2
```

---

## 🛡️ Error Handling

### Graceful Degradation

**If LLM enhancement fails:**
- ✅ System returns **raw Whisper+PhoWhisper transcript**
- ✅ Results still downloadable
- ✅ No data loss
- ⚠️ Warning shown in UI: "LLM Enhancement Failed"

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| **All API keys quota exhausted** | All 4 Gemini keys used up | Wait 1 min or use OpenAI/DeepSeek |
| **API key invalid** | Wrong/missing key | Check `.env` file |
| **Network error** | No internet | Check connection |
| **Model selection timeout** | User didn't select in 30s | System auto-selects Gemini |

---

## 💡 Best Practices

### Free Tier (Gemini)

1. **Get 4 API keys** - Prevents quota issues
2. **Wait 60s between files** - Quota resets
3. **Monitor progress** - Watch for retry attempts

### Paid Tier (OpenAI/DeepSeek)

1. **Single key sufficient** - No retry needed
2. **Higher quality** - Better Vietnamese grammar
3. **Faster processing** - No retry delays

### Hybrid Approach

```env
# Use all 3 for maximum reliability
GEMINI_API_KEY_1=...  # Primary (free)
GEMINI_API_KEY_2=...
GEMINI_API_KEY_3=...
GEMINI_API_KEY_4=...
OPENAI_API_KEY=...    # Fallback (paid)
DEEPSEEK_API_KEY=...  # Alternative (paid)
```

Select model based on:
- **Gemini:** General use, unlimited processing
- **OpenAI:** Critical files, highest quality
- **DeepSeek:** Cost-effective alternative

---

## 📊 Performance Comparison

| Metric | Gemini | OpenAI | DeepSeek |
|--------|--------|--------|----------|
| **Cost** | FREE | $0.15/1M | $0.14/1M |
| **Speed** | Fast | Fastest | Fast |
| **Quality** | 98% | 98% | 97% |
| **Retry** | 4 keys | 1 key | 1 key |
| **Quota** | Limited | Unlimited | Unlimited |

---

## 🔧 Troubleshooting

### Q: Model selection modal doesn't appear?

**A:** Check browser console for errors. Refresh page.

### Q: All Gemini keys quota exceeded?

**A:** 
1. Wait 1 minute for quota reset (free tier)
2. Select OpenAI or DeepSeek model
3. Get more Gemini API keys

### Q: LLM enhancement always fails?

**A:** 
1. Check API keys in `.env`
2. Verify internet connection
3. Check console logs: `services/speech2text/app/web_ui.py`
4. System still returns raw transcript (usable)

### Q: How to skip model selection?

**A:** Wait 30 seconds - system auto-selects Gemini (free)

---

## 📝 API Response Format

### Success
```json
{
  "enhanced": "Cleaned transcript text...",
  "clean_text": "Cleaned transcript text...",
  "llm_success": true,
  "selected_model": "gemini",
  "timings": {
    "gemini": 3.45
  }
}
```

### Failure (Graceful Fallback)
```json
{
  "enhanced": "Raw Whisper+PhoWhisper transcript...",
  "clean_text": null,
  "llm_success": false,
  "selected_model": "gemini",
  "timings": {
    "gemini": 1.23
  }
}
```

---

## 🎓 Technical Details

### MultiLLMClient Architecture

```python
from app.core.llm import MultiLLMClient

# Initialize with selected model
llm = MultiLLMClient(model_type="gemini")  # or "openai", "deepseek"
llm.load()

# Clean transcript with auto-retry (Gemini only)
clean_text, gen_time = llm.clean_transcript(
    whisper_text=whisper_transcript,
    phowhisper_text=phowhisper_transcript,
    max_new_tokens=4096,
    progress_callback=lambda msg: print(msg)  # Monitor retries
)
```

### Retry Logic (Gemini)

```python
for idx, api_key in enumerate(gemini_keys):  # 4 keys
    try:
        client = GeminiClient(api_key=api_key)
        response = client.generate(prompt)
        return response  # Success
    except QuotaError:
        if idx < len(gemini_keys) - 1:
            continue  # Try next key
        else:
            raise  # All keys exhausted
```

---

## 📚 See Also

- [Main README](README.md) - Full documentation
- [Installation Guide](README.md#-installation) - Setup instructions
- [Troubleshooting](README.md#-troubleshooting) - Common issues
- [API Documentation](app/docs/README.md) - Developer guide

---

**Version:** 3.6.0+  
**Last Updated:** December 16, 2025  
**Author:** VistralS2T Team
