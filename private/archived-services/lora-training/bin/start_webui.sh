#!/bin/bash
# Start LoRA Training WebUI (Linux/Mac)

echo "==============================================="
echo "LoRA Training WebUI"
echo "==============================================="
echo ""

# Activate virtual environment
source ./lora/bin/activate

# Install WebUI dependencies if needed
echo "Checking dependencies..."
pip install flask flask-socketio flask-cors python-socketio eventlet --quiet

echo ""
echo "Starting WebUI server..."
echo ""
echo "==============================================="
echo "WebUI will open at: http://127.0.0.1:7860"
echo "==============================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start WebUI
python webui.py --host 127.0.0.1 --port 7860
