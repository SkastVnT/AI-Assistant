#!/bin/bash
# Setup LoRA Training Tool Environment
# Creates virtual environment and installs all dependencies

echo "==============================================="
echo "LoRA Training Tool - Environment Setup"
echo "==============================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found!"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

echo "[1/5] Creating virtual environment..."
if [ -d "./lora" ]; then
    echo "[WARNING] Virtual environment already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing old environment..."
        rm -rf ./lora
    else
        echo "Skipping virtual environment creation"
        source ./lora/bin/activate
        echo "[2/5] Activating existing virtual environment..."
        skip_venv=1
    fi
fi

if [ -z "$skip_venv" ]; then
    python3 -m venv lora
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
    echo "[OK] Virtual environment created"
    
    # Activate virtual environment
    echo ""
    echo "[2/5] Activating virtual environment..."
    source ./lora/bin/activate
fi

# Upgrade pip
echo ""
echo "[3/5] Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel --quiet

# Install PyTorch
echo ""
echo "[4/5] Installing PyTorch..."
echo ""
echo "Select PyTorch version:"
echo "  1. CPU only (smaller, faster download)"
echo "  2. CUDA 11.8 (for NVIDIA GPU)"
echo "  3. CUDA 12.1 (for latest NVIDIA GPU)"
echo ""
read -p "Select option (1-3): " choice

case $choice in
    3)
        echo "Installing PyTorch with CUDA 12.1..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        ;;
    2)
        echo "Installing PyTorch with CUDA 11.8..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        ;;
    *)
        echo "Installing PyTorch CPU version..."
        pip install torch torchvision torchaudio
        ;;
esac

# Install main dependencies
echo ""
echo "[5/5] Installing dependencies..."
pip install --quiet --upgrade \
    diffusers \
    transformers \
    accelerate \
    safetensors \
    bitsandbytes \
    peft \
    xformers \
    pillow \
    opencv-python \
    numpy \
    pandas \
    tqdm \
    omegaconf \
    einops \
    tensorboard \
    wandb \
    flask \
    flask-socketio \
    flask-cors \
    python-socketio \
    eventlet \
    redis \
    google-generativeai \
    huggingface-hub \
    onnxruntime

# Install WD14 Tagger dependencies
pip install --quiet onnxruntime huggingface-hub pillow

echo ""
echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your API keys"
echo "  2. Run ./start_webui_with_redis.sh to start WebUI"
echo ""
echo "Optional:"
echo "  - Start Redis: docker run -d -p 6379:6379 redis:7-alpine"
echo "  - View logs: tail -f logs/training.log"
echo ""

# Make start script executable
chmod +x start_webui_with_redis.sh
echo "[OK] Made start script executable"
