#!/bin/bash
# Start LoRA Training WebUI with Redis
# Enhanced version with dependency checks and Redis support

echo "==============================================="
echo "LoRA Training WebUI v2.3.1"
echo "==============================================="
echo ""

# Check if virtual environment exists
if [ ! -d "./lora" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "Please run setup.sh first to create the environment."
    exit 1
fi

# Activate virtual environment
echo "[1/4] Activating virtual environment..."
source ./lora/bin/activate

# Check Redis connection (optional)
echo ""
echo "[2/4] Checking Redis connection..."
if docker ps --filter "name=redis" --format "{{.Names}}" | grep -q redis; then
    echo "[OK] Redis container is running"
    export REDIS_HOST=localhost
    export REDIS_PORT=6379
else
    echo "[WARNING] Redis not running - starting Redis container..."
    if docker run -d -p 6379:6379 --name ai-assistant-redis redis:7-alpine > /dev/null 2>&1; then
        echo "[OK] Redis started successfully"
        sleep 2
        export REDIS_HOST=localhost
        export REDIS_PORT=6379
    else
        echo "[WARNING] Could not start Redis - will run in fallback mode"
        echo "WebUI will work but without caching features"
    fi
fi

# Install/update dependencies
echo ""
echo "[3/4] Checking dependencies..."
pip install --quiet --upgrade \
    flask \
    flask-socketio \
    flask-cors \
    python-socketio \
    eventlet \
    redis \
    pillow

echo "[OK] All dependencies installed"

# Set environment variables
export FLASK_PORT=7860
export FLASK_DEBUG=False
export PYTHONUNBUFFERED=1

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ""
    echo "[WARNING] .env file not found!"
    echo "Creating default .env file..."
    cat > .env << 'EOF'
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Gemini API Key (get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your-api-key-here

# Training Configuration
OUTPUT_DIR=./output
MODELS_DIR=./models
EOF
    echo "[OK] Created .env file - please edit it with your API keys"
fi

# Start WebUI
echo ""
echo "[4/4] Starting WebUI server..."
echo ""
echo "==============================================="
echo "  LoRA Training WebUI"
echo "==============================================="
echo "  URL:      http://127.0.0.1:7860"
echo "  Redis:    ${REDIS_HOST}:${REDIS_PORT}"
echo "  Logs:     ./logs/"
echo "==============================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run WebUI
python webui.py --host 127.0.0.1 --port 7860

# Cleanup on exit
echo ""
echo "WebUI stopped."
