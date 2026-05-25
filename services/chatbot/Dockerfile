# ChatBot Service Dockerfile
FROM python:3.11-slim

LABEL maintainer="AI Assistant Team"
LABEL description="ChatBot Service with Multi-Model AI Support"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_PORT=5000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching.
# profile_core_services.txt references chunk files with -r, so copy the full
# requirements directory so pip can resolve all relative includes.
COPY app/requirements/ app/requirements/

# Install Python dependencies (core profile only — no torch, no image stack)
RUN pip install --no-cache-dir -r app/requirements/profile_core_services.txt

# Copy application code
COPY services/chatbot/ .

# Copy shared service module (imported by chatbot_main.py and config loaders)
COPY services/shared_env.py services/shared_env.py

# Create necessary directories
RUN mkdir -p Storage/Image_Gen data/memory logs

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check — /api/v1/health is the registered public endpoint on the Flask monolith
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/v1/health', timeout=5)" || exit 1

# Run application — use run.py for all startup modes
CMD ["python", "run.py"]
