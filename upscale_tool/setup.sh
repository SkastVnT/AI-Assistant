#!/bin/bash
# Setup script for upscale tool on Linux/Mac

echo "========================================"
echo "Upscale Tool - Setup Script"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python not found! Please install Python 3.8 or higher."
    exit 1
fi

echo "[1/4] Checking Python version..."
python3 --version

echo
echo "[2/4] Installing dependencies..."
pip install --upgrade pip
pip install -e .

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies!"
    exit 1
fi

echo
echo "[3/4] Creating necessary directories..."
mkdir -p models
mkdir -p outputs

echo
echo "[4/4] Checking if you want to download models now..."
read -p "Download pretrained models now? (y/n): " DOWNLOAD
if [[ $DOWNLOAD == "y" || $DOWNLOAD == "Y" ]]; then
    echo
    echo "Downloading models..."
    python3 models/download_models.py
fi

echo
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo
echo "Quick start:"
echo "  1. Download models: python3 models/download_models.py"
echo "  2. Run CLI: upscale-tool upscale -i input.jpg -o output.png"
echo "  3. Run Web UI: python3 -m upscale_tool.web_ui"
echo
echo "See QUICKSTART.md for more examples."
echo
