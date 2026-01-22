#!/bin/bash

echo "🚀 Starting AI-Assistant services (except Hub)..."

# Create logs directory
mkdir -p /workspace/AI-Assistant/logs

# Kill existing processes
echo "🔄 Stopping existing services..."
pkill -f "main.py --listen" 2>/dev/null || true
pkill -f "uvicorn.*5000" 2>/dev/null || true
pkill -f "uvicorn.*5001" 2>/dev/null || true
pkill -f "uvicorn.*5002" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 2

# Start services
echo "📦 Starting ComfyUI (port 8189)..."
cd /workspace/ComfyUI && nohup python3 main.py --listen 0.0.0.0 --port 8189 > /workspace/AI-Assistant/logs/comfyui.log 2>&1 &

echo "💬 Starting Chatbot (port 5000)..."
cd /workspace/AI-Assistant/services/chatbot && nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 5000 > /workspace/AI-Assistant/logs/chatbot.log 2>&1 &

echo "🗣️  Starting Speech2Text (port 5001)..."
cd /workspace/AI-Assistant/services/speech2text/app/api && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 5001 > /workspace/AI-Assistant/logs/speech2text.log 2>&1 &

echo "🗄️  Starting Text2SQL (port 5002)..."
cd /workspace/AI-Assistant/services/text2sql && nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 5002 > /workspace/AI-Assistant/logs/text2sql.log 2>&1 &

echo "⏳ Waiting 10 seconds for services to start..."
sleep 10

# Start Cloudflare tunnels
echo "🌐 Starting Cloudflare tunnels..."
cloudflared tunnel --url http://localhost:5000 > /workspace/AI-Assistant/logs/tunnel-chatbot.log 2>&1 &
cloudflared tunnel --url http://localhost:8189 > /workspace/AI-Assistant/logs/tunnel-comfyui.log 2>&1 &
cloudflared tunnel --url http://localhost:5002 > /workspace/AI-Assistant/logs/tunnel-text2sql.log 2>&1 &
cloudflared tunnel --url http://localhost:5001 > /workspace/AI-Assistant/logs/tunnel-speech2text.log 2>&1 &

echo "⏳ Waiting 10 seconds for tunnels to initialize..."
sleep 10

# Check services
echo ""
echo "==================================="
echo "📊 SERVICE STATUS"
echo "==================================="

check_service() {
    local name=$1
    local url=$2
    if curl -s --max-time 3 "$url" > /dev/null 2>&1; then
        echo "✅ $name - Running"
    else
        echo "❌ $name - Failed"
    fi
}

check_service "ComfyUI (8189)" "http://localhost:8189"
check_service "Chatbot (5000)" "http://localhost:5000/health"
check_service "Speech2Text (5001)" "http://localhost:5001/health"
check_service "Text2SQL (5002)" "http://localhost:5002/health"

# Extract tunnel URLs
echo ""
echo "==================================="
echo "🌐 PUBLIC URLS"
echo "==================================="

sleep 3
for log in /workspace/AI-Assistant/logs/tunnel-*.log; do
    if [ -f "$log" ]; then
        url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$log" | head -1)
        service=$(basename "$log" | sed 's/tunnel-//;s/.log//')
        if [ ! -z "$url" ]; then
            echo "🔗 $service: $url"
        fi
    fi
done

echo ""
echo "✅ All services started!"
echo "📋 Logs: /workspace/AI-Assistant/logs/"
