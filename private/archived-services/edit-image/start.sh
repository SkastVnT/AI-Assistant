#!/bin/bash
# ==============================================================================
# Edit Image Service - Startup Script (Linux/Mac)
# ==============================================================================

echo ""
echo "============================================================"
echo "  Edit Image Service - Starting..."
echo "============================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -f "venv/bin/activate" ]; then
    echo "[INFO] Activating virtual environment..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "[INFO] Activating virtual environment..."
    source .venv/bin/activate
else
    echo "[WARN] No virtual environment found. Using system Python."
fi

# Check Python
if ! command -v python &> /dev/null; then
    echo "[ERROR] Python is not installed or not in PATH."
    exit 1
fi

echo "[INFO] Python version:"
python --version

# Check if dependencies are installed
if ! python -c "import torch; import diffusers; import gradio" 2>/dev/null; then
    echo ""
    echo "[INFO] Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies."
        exit 1
    fi
fi

# Check CUDA availability
echo ""
echo "[INFO] Checking GPU/CUDA availability..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

# Create necessary directories
mkdir -p outputs logs models

# Start the service
echo ""
echo "============================================================"
echo "  Starting Edit Image Service..."
echo "  Web UI: http://localhost:8100"
echo "  API Docs: http://localhost:8100/docs"
echo "============================================================"
echo ""

python -m app.main
