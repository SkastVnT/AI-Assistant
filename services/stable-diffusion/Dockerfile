# Stable Diffusion WebUI Dockerfile
FROM python:3.10-slim

LABEL maintainer="AI Assistant Team"
LABEL description="Stable Diffusion WebUI with API Support"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    COMMANDLINE_ARGS="--api --listen --port 7861 --skip-torch-cuda-test"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install PyTorch (CPU version)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p models/Stable-diffusion models/Lora models/VAE outputs embeddings extensions

# Expose port
EXPOSE 7861

# Health check
HEALTHCHECK --interval=60s --timeout=15s --start-period=180s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7861/sdapi/v1/progress', timeout=10)" || exit 1

# Run application
CMD ["python", "launch.py", "--api", "--listen", "--port", "7861", "--skip-torch-cuda-test"]
