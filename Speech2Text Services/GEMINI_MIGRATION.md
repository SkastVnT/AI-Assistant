# Migration from Qwen to Gemini 2.0 Flash

## Summary

Successfully migrated the Speech2Text Services from using the local Qwen2.5-1.5B-Instruct model to the cloud-based **Google Gemini 2.0 Flash (Free)** model for transcript enhancement.

## Changes Made

### 1. Created New GeminiClient (`app/core/llm/gemini_client.py`)
- Implemented `GeminiClient` class using `google-generativeai` SDK
- Uses **gemini-2.0-flash-exp** model (free tier)
- Supports configurable temperature, top_p, and max_output_tokens
- Includes error handling and API key validation from environment variables

### 2. Updated LLM Module Exports (`app/core/llm/__init__.py`)
- Replaced `QwenClient` import with `GeminiClient`
- Updated module docstring to reflect Gemini usage
- Exported `GeminiClient` in `__all__` list

### 3. Added New Prompt Template (`app/core/prompts/templates.py`)
- Created `build_gemini_prompt()` method with the new STT cleaning instructions
- Prompt follows the expert STT transcript cleaner format provided
- Handles:
  - Filler words removal
  - Repeated words cleanup
  - Misheard phonetics correction
  - Vietnamese diacritics restoration
  - Punctuation and sentence boundary fixes
  - Speaker turn preservation
- Keeps `build_qwen_prompt()` for backward compatibility

### 4. Updated Web UI (`app/web_ui.py`)
- Changed import from `QwenClient` to `GeminiClient`
- Updated timing dictionary key from `'qwen'` to `'gemini'`
- Modified Step 7 section:
  - "QWEN FUSION" → "GEMINI ENHANCEMENT"
  - Progress messages updated to reflect Gemini usage
  - Uses `build_gemini_prompt()` instead of `build_qwen_prompt()`
- Updated server startup message: "Qwen enhancement" → "Gemini AI transcript cleaning (free)"

### 5. Updated Dependencies (`requirements.txt`)
- Removed comment about Qwen2.5-1.5B-Instruct
- Added `google-generativeai>=0.3.0` package

### 6. Environment Configuration
- GEMINI_API_KEY already exists in `.env.example`
- No changes needed to `.env` configuration

## New Prompt Format

The new Gemini prompt follows the STT cleaning expert format:

```
You are an expert Speech-to-Text (STT) transcript cleaner and text reconstruction assistant.

RULES:
1. DO NOT invent or add new information
2. Remove timestamps, logs, noise labels, system metadata
3. Fix STT errors (diacritics, misheard words, punctuation)
4. Preserve meaning exactly as spoken
5. Format cleanly with paragraphs and speaker turns
6. Preserve numbers, names, dates, codes exactly
7. Do NOT summarize, shorten, or add missing context

OUTPUT REQUIREMENTS:
✓ Clean
✓ Faithful to spoken content
✓ Fully readable
✓ No STT noise
✓ No invented text
```

## Benefits of Gemini 2.0 Flash

1. **Free to use** - No costs for API usage (within quota)
2. **Cloud-based** - No local GPU/CPU requirements
3. **Fast inference** - Optimized for speed
4. **Better at following instructions** - Structured prompt format
5. **No model download** - Instant availability
6. **Multilingual support** - Excellent Vietnamese handling

## Installation

To use the new Gemini integration:

1. Install the new dependency:
   ```powershell
   pip install google-generativeai
   ```

2. Set your Gemini API key in `.env`:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   Get your free API key at: https://aistudio.google.com/apikey

3. Run the application as normal:
   ```powershell
   python app/web_ui.py
   ```

## Migration Notes

- The old `QwenClient` code is still in `app/core/llm/qwen_client.py` (not deleted for reference)
- The old `build_qwen_prompt()` method is still in templates.py for backward compatibility
- No database or data migration needed - only code changes
- All existing transcripts remain compatible

## Testing

After migration, test the following:
1. Upload an audio file through the web UI
2. Verify progress messages show "Gemini" instead of "Qwen"
3. Check that transcript cleaning works correctly
4. Verify enhanced transcript is saved to `enhanced_transcript.txt`
5. Compare quality with previous Qwen outputs

## Rollback Instructions

If needed to rollback to Qwen:
1. Revert `app/core/llm/__init__.py` to import `QwenClient`
2. Revert `app/web_ui.py` changes (import and usage)
3. Revert `requirements.txt` changes
4. Run: `pip uninstall google-generativeai`

---

**Date**: November 26, 2025
**Model**: Gemini 2.0 Flash Experimental (gemini-2.0-flash-exp)
**Status**: ✅ Complete
