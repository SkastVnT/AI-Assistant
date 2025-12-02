# Upscale Tool

Quick setup and usage guide.

## Quick Install

```bash
cd upscale_tool
pip install -e .
```

## Quick Use

```python
from upscale_tool import upscale

# One-line upscale
upscale('input.jpg', 'output.png', scale=4)
```

## CLI

```bash
# Install first
pip install -e .

# Download models
upscale-tool download-models

# Upscale
upscale-tool upscale -i input.jpg -o output.png --scale 4

# List models
upscale-tool list-models
```

## Full Documentation

See [README.md](README.md) for complete documentation.
