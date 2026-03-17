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
- profile_core_services.txt
- profile_image_ai_services.txt

## Usage
Install the chunks individually or concatenate as needed, for example:

```bash
# install a specific chunk
pip install -r requirements/requirements_chunk_1_core.txt

# install everything (concatenate)
cat requirements/requirements_chunk_*.txt > /tmp/ai-assistant-all.txt
pip install -r /tmp/ai-assistant-all.txt
```

## Recommended environment profiles

Use isolated venv profiles to avoid cross-service dependency conflicts.

### core-services profile
Target services: hub-gateway, chatbot, speech2text, text2sql, document-intelligence, mcp-server.

```bash
# Windows PowerShell
pyenv install 3.11.9
pyenv shell 3.11.9
pyenv exec python -m venv venv-core
./venv-core/Scripts/python -m pip install -U pip setuptools wheel
./venv-core/Scripts/python -m pip install -r requirements/profile_core_services.txt
```

### image-ai-services profile
Target services: stable-diffusion, edit-image, image-upscale, lora-training, ComfyUI workflows.

```bash
# Windows PowerShell
pyenv install 3.11.9
pyenv shell 3.11.9
pyenv exec python -m venv venv-image
./venv-image/Scripts/python -m pip install -U pip setuptools wheel
./venv-image/Scripts/python -m pip install -r requirements/profile_image_ai_services.txt
```

Note: `profile_image_ai_services.txt` may still need CUDA-specific PyTorch index URLs depending on your GPU stack.
