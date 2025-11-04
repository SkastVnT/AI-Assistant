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
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (CPU version)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/audio data/models data/results results logs

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=60s --timeout=15s --start-period=120s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/', timeout=10)" || exit 1

# Run application
CMD ["python", "app/web_ui.py"]
