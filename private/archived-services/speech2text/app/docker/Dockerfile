# ============================================
# SPEECH-TO-TEXT SYSTEM - DOCKER IMAGE v3.5
# Whisper + PhoWhisper + Qwen2.5 + VAD
# Optimized multi-stage build
# ============================================

# ===== STAGE 1: Base image with dependencies =====
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CUDA_VISIBLE_DEVICES=0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --upgrade pip setuptools wheel

# ===== STAGE 2: Install Python dependencies =====
FROM base AS builder

WORKDIR /tmp

# Copy requirements
COPY requirements.txt .

# Install PyTorch first (separate step to avoid conflicts)
RUN pip3 install --no-cache-dir \
    torch==2.7.1 torchaudio==2.7.1 \
    --index-url https://download.pytorch.org/whl/cu118

# Install essential dependencies
RUN pip3 install --no-cache-dir \
    faster-whisper>=1.0.3 \
    transformers>=4.40.0 \
    flask>=3.0.0 \
    flask-socketio>=5.3.0 \
    flask-cors>=4.0.0 \
    python-dotenv>=1.0.0 \
    librosa>=0.10.0 \
    soundfile>=0.12.1 \
    pydub>=0.25.1

# ===== STAGE 3: Final image =====
FROM base AS final

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

# Set working directory
WORKDIR /app

# Copy application code
COPY app/core /app/core
COPY app/config /app/config
COPY app/tools /app/tools
COPY app/data /app/data
COPY app/tests /app/tests

# Create output directories
RUN mkdir -p /app/output/raw /app/output/vistral /app/output/dual \
    /app/audio /app/logs /app/data/results/sessions

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port for web UI
EXPOSE 5000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import torch; assert torch.cuda.is_available(), 'GPU not available'" || exit 1

# Default command
CMD ["python3", "core/run_with_diarization.py"]
