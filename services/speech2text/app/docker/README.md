# 🐳 Docker Deployment

## Quick Start

```bash
# 1. Copy your audio file
mkdir -p docker/input
cp your_audio.mp3 docker/input/audio.mp3

# 2. Set HuggingFace token
echo "HF_API_TOKEN=hf_your_token" > docker/.env

# 3. Build & Run
cd docker
docker-compose up --build

# 4. Get results
ls output/vistral/
```

## Build Only

```bash
cd docker
docker build -t s2t-system .
```

## Run Manually

```bash
docker run --gpus all \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output \
  -e HF_API_TOKEN=your_token \
  s2t-system
```

## Requirements

- Docker 20.10+
- Docker Compose 1.29+
- NVIDIA Docker runtime
- GPU with 6GB+ VRAM

## Environment Variables

```env
HF_API_TOKEN=hf_xxxxx        # HuggingFace token (required)
AUDIO_PATH=/app/input/audio.mp3  # Input file path
CUDA_VISIBLE_DEVICES=0       # GPU device ID
```

## Output Structure

```
docker/output/
├── raw/
│   ├── whisper_xxx.txt
│   └── phowhisper_xxx.txt
└── vistral/
    └── dual_fused_xxx.txt   # MAIN OUTPUT
```

## Troubleshooting

**GPU not detected?**
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**Models downloading slow?**
```bash
# Pre-download models before building
huggingface-cli login
huggingface-cli download openai/whisper-large-v3
huggingface-cli download vinai/PhoWhisper-large
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct
```

**Out of memory?**
- Ensure GPU has 6GB+ VRAM
- Close other GPU applications
- Reduce concurrent processes
