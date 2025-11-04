# Speech2Text Service Dockerfile
FROM python:3.10-slim

LABEL maintainer="AI Assistant Team"
LABEL description="Speech2Text Service - Vietnamese ASR with Diarization"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_PORT=7860 \
    HF_HOME=/app/data/models \
    TRANSFORMERS_CACHE=/app/data/models

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    ffmpeg \
    libsndfile1 \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies (GPU version with CUDA 11.8)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu118 && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories before copying code
RUN mkdir -p data/audio data/models data/results results logs

# Copy application code
COPY . .

# Expose port
EXPOSE 7860

# Health check using curl (more reliable than Python)
HEALTHCHECK --interval=60s --timeout=15s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Run application
CMD ["python", "app/web_ui.py"]
