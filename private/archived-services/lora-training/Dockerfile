# LoRA Training WebUI Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages for Redis integration
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    celery==5.3.4 \
    flask-caching==2.1.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/models /app/output /app/logs /app/webui/static /app/webui/templates

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/api/status || exit 1

# Run WebUI
CMD ["python", "webui.py", "--host", "0.0.0.0", "--port", "7860"]
