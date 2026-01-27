# Dependency Chunks

This folder only groups the split requirement files to keep the repo root tidy. Use them exactly as before; paths just moved here.

## Files
- requirements_chunk_1_core.txt
- requirements_chunk_2_web.txt
- requirements_chunk_3_database.txt
- requirements_chunk_4_ai_apis.txt
- requirements_chunk_5_ml_core.txt
- requirements_chunk_6_image.txt
- requirements_chunk_7_audio.txt
- requirements_chunk_8_document.txt
- requirements_chunk_9_upscale.txt
- requirements_chunk_10_tools.txt

## Usage
Install the chunks individually or concatenate as needed, for example:

```bash
# install a specific chunk
pip install -r requirements/requirements_chunk_1_core.txt

# install everything (concatenate)
cat requirements/requirements_chunk_*.txt > /tmp/ai-assistant-all.txt
pip install -r /tmp/ai-assistant-all.txt
```
